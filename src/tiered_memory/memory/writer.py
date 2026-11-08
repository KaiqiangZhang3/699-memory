"""Versioned Writer: the only component that writes memory (task T07, Table 5).

Guarantees:

* **Validate first.** Every record is fully built and passes ``validate_record``
  before anything touches disk. A rejected write leaves no trace in the store.
* **Atomic and write-once.** Version files are written to a temp file,
  fsynced, then hard-linked into place. Linking fails if the target exists,
  so a version is never overwritten. A Daily Log file is replaced atomically
  (temp file + ``os.replace``) with the new line appended.
* **Version chain.** Every change after v1 names the version it replaces
  (``supersedes``), and the caller must state which version it saw
  (``base_version_id``). A stale base is rejected as a conflict, not merged.
* **No delete.** The strongest action is ``archive``. ``rollback`` restores an
  old version by writing it forward as a new version.
* **Idempotent.** A retried or duplicate write becomes ``no_op`` (QR2, D4).
* **One project.** Payloads cannot name another project (IC2, TH09).

Operation meanings:

=========  ===============================================================
append     New Project Memory fact (v1), new Session Memory task (v1),
           or a new Daily Log entry
update     Same content, new status or evidence (e.g. mark ``uncertain``
           or record a revalidation). Changing the claim needs ``supersede``.
supersede  New content replaces the current version (Project Memory)
archive    New version with status ``archived``; history stays readable
=========  ===============================================================
"""

from __future__ import annotations

import copy
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..schemas import canonical_json, compute_content_hash, sha256_text, validate_record
from ..usage import utc_now_iso
from .store import MemoryStore, version_filename

CALLER_PROVENANCE = frozenset({"source_event_id", "decision_id", "policy_outcome", "review_id", "condition", "run_id"})

PROJECT_CONTENT = ("category", "claim", "paths", "tags")
PROJECT_MUTABLE = ("status", "support", "evidence", "source_commit", "verified_at_utc", "last_verification_event_id")
PROJECT_PAYLOAD = frozenset({"memory_id", *PROJECT_CONTENT, *PROJECT_MUTABLE})

SESSION_PAYLOAD = frozenset({
    "task_id", "status", "goal", "progress", "tentative_findings", "failed_attempts",
    "blockers", "next_steps", "evidence", "last_session_id",
})
LOG_PAYLOAD = frozenset({
    "event_id", "dedup_key", "run_id", "task_id", "session_id", "entry_type",
    "summary", "evidence", "corrects_entry_id",
})


class WriteRejected(Exception):
    """The write was refused. Nothing was written."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class WriteResult:
    tier: str
    requested: str
    executed: str  # the requested operation, or "no_op"
    record: dict[str, Any]  # the record written, or the existing record for no_op
    path: Path | None  # file written; None for no_op
    previous_version_id: str | None = None


# -- low-level file operations ----------------------------------------------

def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _encode(record: dict[str, Any]) -> bytes:
    return (canonical_json(record) + "\n").encode("utf-8")


def write_new_file(path: Path, data: bytes) -> None:
    """Create ``path`` atomically. Raises FileExistsError if it already exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.link(tmp, path)
    finally:
        os.unlink(tmp)
    _fsync_dir(path.parent)


def replace_file(path: Path, data: bytes) -> None:
    """Replace ``path`` atomically with ``data``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    _fsync_dir(path.parent)


# -- the writer ---------------------------------------------------------------

class VersionedWriter:
    def __init__(
        self,
        store: MemoryStore,
        clock: Callable[[], str] = utc_now_iso,
        new_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        self.store = store
        self.clock = clock
        self.new_id = new_id

    # -- shared helpers ----------------------------------------------------

    def _provenance(self, caller: dict[str, Any], operation: str, now: str) -> dict[str, Any]:
        unknown = set(caller) - CALLER_PROVENANCE
        if unknown:
            raise WriteRejected("bad_provenance", f"caller may not set {sorted(unknown)}")
        if caller.get("policy_outcome") != "accepted":
            raise WriteRejected("not_accepted", "only an accepted Policy Gate decision can produce a write")
        prov = {"review_id": None, "condition": "dev", "run_id": None, **caller}
        prov.update(operation=operation, written_at_utc=now, written_by="versioned_writer")
        return prov

    def _check_payload(self, payload: dict[str, Any], allowed: frozenset[str]) -> dict[str, Any]:
        if "project_id" in payload and payload["project_id"] != self.store.project_id:
            raise WriteRejected("cross_project", f"payload names {payload['project_id']}, store is {self.store.project_id}")
        unknown = set(payload) - allowed - {"project_id"}
        if unknown:
            raise WriteRejected("bad_payload", f"unexpected field(s) {sorted(unknown)}")
        return copy.deepcopy({k: v for k, v in payload.items() if k != "project_id"})

    @staticmethod
    def _check_base(current: dict[str, Any] | None, base_version_id: str | None, what: str) -> dict[str, Any]:
        if current is None:
            raise WriteRejected("unknown_record", f"{what} does not exist")
        if base_version_id is None:
            raise WriteRejected("missing_base", "base_version_id is required for changes after v1")
        if base_version_id != current["version_id"]:
            raise WriteRejected("stale_base", f"current version is {current['version_id']}, caller saw {base_version_id}")
        return current

    def _finish(self, record: dict[str, Any]) -> dict[str, Any]:
        record["content_hash"] = compute_content_hash(record)
        errors = validate_record(record)
        if errors:
            raise WriteRejected("invalid_record", "; ".join(errors))
        return record

    def _write_version(self, directory: Path, record: dict[str, Any]) -> Path:
        path = directory / version_filename(record["version"])
        try:
            write_new_file(path, _encode(record))
        except FileExistsError:
            raise WriteRejected("version_exists", str(path))
        return path

    # -- Project Memory ----------------------------------------------------

    @staticmethod
    def _semantic_key(record: dict[str, Any]) -> str:
        """Identity of a fact regardless of memory_id: same category, claim, paths and tags."""
        defaults = {"paths": [], "tags": []}
        return sha256_text(canonical_json({k: record.get(k, defaults.get(k)) for k in PROJECT_CONTENT}))

    def write_project(
        self,
        operation: str,
        payload: dict[str, Any],
        provenance: dict[str, Any],
        base_version_id: str | None = None,
    ) -> WriteResult:
        payload = self._check_payload(payload, PROJECT_PAYLOAD)
        now = self.clock()
        prov = self._provenance(provenance, operation, now)
        if payload.get("status") == "archived" and operation != "archive":
            raise WriteRejected("bad_payload", "use the archive operation to archive")

        if operation == "append":
            if "memory_id" in payload:
                raise WriteRejected("bad_payload", "append creates the memory_id")
            key = self._semantic_key(payload)
            for existing in self.store.project_active():
                if self._semantic_key(existing) == key:
                    return WriteResult("project", operation, "no_op", existing, None)
            record = {
                "schema_version": "pm-v1", "tier": "project", "project_id": self.store.project_id,
                "memory_id": "mem_" + self.new_id(), "version": 1, "version_id": "ver_" + self.new_id(),
                "supersedes": None, "status": "active", "tags": [],
                "verified_at_utc": now, "created_at_utc": now,
                **payload, "provenance": prov,
            }
            record = self._finish(record)
            path = self._write_version(self.store.project_dir(record["memory_id"]), record)
            return WriteResult("project", operation, operation, record, path)

        if operation not in ("update", "supersede", "archive"):
            raise WriteRejected("bad_operation", f"{operation!r} is not a Project Memory write")
        memory_id = payload.pop("memory_id", None)
        if memory_id is None:
            raise WriteRejected("bad_payload", "memory_id is required")
        current = self._check_base(self.store.project_current(memory_id), base_version_id, memory_id)

        if operation == "update" and any(k in payload and payload[k] != current[k] for k in PROJECT_CONTENT):
            raise WriteRejected("content_change", "update cannot change category, claim, paths or tags; use supersede")
        if operation == "archive":
            if set(payload) - {"status"}:
                raise WriteRejected("bad_payload", "archive takes no other fields")
            if current["status"] == "archived":
                return WriteResult("project", operation, "no_op", current, None)
            payload = {"status": "archived"}

        return self._next_version(
            "project", operation, current, payload, prov,
            changed_keys=PROJECT_CONTENT if operation == "supersede" else PROJECT_MUTABLE,
            directory=self.store.project_dir(memory_id),
        )

    def rollback_project(self, memory_id: str, to_version_id: str, provenance: dict[str, Any],
                         base_version_id: str) -> WriteResult:
        """Restore an earlier version's content as a new version (a supersede)."""
        versions = self.store.project_versions(memory_id)
        target = next((v for v in versions if v["version_id"] == to_version_id), None)
        if target is None:
            raise WriteRejected("unknown_record", f"{to_version_id} is not a version of {memory_id}")
        restored = {k: target[k] for k in (*PROJECT_CONTENT, *PROJECT_MUTABLE)}
        current = self._check_base(versions[-1] if versions else None, base_version_id, memory_id)
        prov = self._provenance(provenance, "supersede", self.clock())
        return self._next_version("project", "supersede", current, restored, prov,
                                  changed_keys=(*PROJECT_CONTENT, *PROJECT_MUTABLE),
                                  directory=self.store.project_dir(memory_id))

    # -- Session Memory ----------------------------------------------------

    def write_session(
        self,
        operation: str,
        payload: dict[str, Any],
        provenance: dict[str, Any],
        base_version_id: str | None = None,
    ) -> WriteResult:
        payload = self._check_payload(payload, SESSION_PAYLOAD)
        task_id = payload.get("task_id")
        if not task_id:
            raise WriteRejected("bad_payload", "task_id is required")
        now = self.clock()
        prov = self._provenance(provenance, operation, now)
        current = self.store.session_current(task_id)

        if operation == "append":
            if current is not None:
                raise WriteRejected("already_exists", f"session memory for {task_id} exists; use update")
            record = {
                "schema_version": "sm-v1", "tier": "session", "project_id": self.store.project_id,
                "session_memory_id": "smem_" + self.new_id(), "version": 1, "version_id": "ver_" + self.new_id(),
                "supersedes": None, "status": "active",
                "progress": [], "tentative_findings": [], "failed_attempts": [],
                "blockers": [], "next_steps": [], "evidence": [],
                "created_at_utc": now, "updated_at_utc": now,
                **payload, "provenance": prov,
            }
            record = self._finish(record)
            path = self._write_version(self.store.session_dir(task_id), record)
            return WriteResult("session", operation, operation, record, path)

        if operation not in ("update", "archive"):
            raise WriteRejected("bad_operation", f"{operation!r} is not a Session Memory write")
        current = self._check_base(current, base_version_id, task_id)
        if operation == "archive":
            if set(payload) - {"task_id", "status"}:
                raise WriteRejected("bad_payload", "archive takes no other fields")
            payload = {"status": "archived"}
        elif payload.get("status") == "archived":
            raise WriteRejected("bad_payload", "use the archive operation to archive")
        payload.pop("task_id", None)
        return self._next_version("session", operation, current, payload, prov,
                                  changed_keys=tuple(SESSION_PAYLOAD - {"task_id"}),
                                  directory=self.store.session_dir(task_id))

    # -- versioned tiers: build the next version ----------------------------

    def _next_version(self, tier: str, operation: str, current: dict[str, Any], payload: dict[str, Any],
                      prov: dict[str, Any], changed_keys, directory: Path) -> WriteResult:
        if not any(k in payload and payload[k] != current.get(k) for k in changed_keys):
            return WriteResult(tier, operation, "no_op", current, None)
        record = copy.deepcopy(current)
        record.update(copy.deepcopy(payload))
        record.update(
            version=current["version"] + 1,
            version_id="ver_" + self.new_id(),
            supersedes=current["version_id"],
            provenance=prov,
        )
        # A supersede is backed by fresh evidence, so it counts as a verification.
        # An update (e.g. marking a record uncertain) is not; the caller sets
        # verified_at_utc explicitly when it revalidates.
        if tier == "project" and operation == "supersede" and "verified_at_utc" not in payload:
            record["verified_at_utc"] = prov["written_at_utc"]
        if tier == "session":
            record["updated_at_utc"] = prov["written_at_utc"]
        record = self._finish(record)
        path = self._write_version(directory, record)
        return WriteResult(tier, operation, operation, record, path, previous_version_id=current["version_id"])

    # -- Daily Log -----------------------------------------------------------

    def append_log(self, payload: dict[str, Any], provenance: dict[str, Any]) -> WriteResult:
        payload = self._check_payload(payload, LOG_PAYLOAD)
        now = self.clock()
        prov = self._provenance(provenance, "append", now)
        dedup_key = payload.get("dedup_key")
        if dedup_key:
            existing = self.store.find_log_by_dedup_key(dedup_key)
            if existing is not None:
                return WriteResult("daily_log", "append", "no_op", existing, None)

        log_date = now[:10]
        entries = self.store.log_entries(log_date)
        record = {
            "schema_version": "dl-v1", "tier": "daily_log", "project_id": self.store.project_id,
            "entry_id": "log_" + self.new_id(), "log_date": log_date, "sequence": len(entries) + 1,
            "recorded_at_utc": now, "run_id": None, "task_id": None, "session_id": None,
            "corrects_entry_id": None,
            **payload,
            "prev_entry_hash": entries[-1]["content_hash"] if entries else None,
            "provenance": prov,
        }
        record = self._finish(record)
        path = self.store.log_path(log_date)
        existing_bytes = path.read_bytes() if path.exists() else b""
        replace_file(path, existing_bytes + _encode(record))
        return WriteResult("daily_log", "append", "append", record, path)
