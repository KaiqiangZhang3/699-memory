"""One run: manifest, trace, snapshots, usage log, and a writer that traces every write (task T08).

Directory layout::

    runs/<run_id>/manifest.json         written at start (status running), rewritten at finish
    runs/<run_id>/trace.jsonl           hash-chained events
    runs/<run_id>/usage.jsonl           model usage records (usage-v0)
    runs/<run_id>/snapshots/0001-initial.json
    runs/<run_id>/memory/...            the run's own memory store (never shared between runs, 4.8)

Snapshots are taken at the moments proposal 4.11 lists: the initial state,
every executed write, every task boundary, every maintenance checkpoint,
immediately before recall, and at the end.
"""

from __future__ import annotations

import hashlib
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from ..memory import MemoryStore, VersionedWriter, WriteRejected, WriteResult
from ..memory.writer import replace_file
from ..schemas import canonical_json, schema_errors, schemas_sha256, sha256_text
from ..usage import UsageLogger, utc_now_iso
from .trace import TraceLog

MANIFEST_SCHEMA = "run_manifest.schema.json"
REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_REASONS = ("initial", "write", "task_boundary", "maintenance_checkpoint", "pre_recall", "final")


def code_version(repo: Path = REPO_ROOT) -> dict[str, Any]:
    """Commit and dirty flag of the prototype repo; nulls if git is unavailable."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True).stdout
        return {"commit": commit, "dirty": bool(status.strip())}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_counts(snap: dict[str, Any]) -> dict[str, int]:
    return {
        "project_records": len(snap["project"]),
        "project_versions": sum(len(v) for v in snap["project"].values()),
        "session_tasks": len(snap["session"]),
        "session_versions": sum(len(v) for v in snap["session"].values()),
        "daily_log_entries": sum(len(v) for v in snap["daily_log"].values()),
    }


class RecordingWriter:
    """Wraps VersionedWriter: every call becomes a trace event, every executed write a snapshot.

    Same call signatures as VersionedWriter. Rejections are traced and then re-raised.
    """

    def __init__(self, run: "Run") -> None:
        self._run = run
        self._inner = run.raw_writer

    def _call(self, tier: str, requested: str, provenance: dict[str, Any], fn, *args, **kwargs) -> WriteResult:
        event_id = provenance.get("source_event_id")
        try:
            result: WriteResult = fn(*args, **kwargs)
        except WriteRejected as e:
            self._run.rejected += 1
            self._run.trace.emit("write_rejected", {
                "event_id": event_id, "decision_id": provenance.get("decision_id"),
                "tier": tier, "requested": requested, "reason": e.reason, "detail": e.detail[:500],
            })
            raise
        rec = result.record
        record_id = rec.get("version_id") or rec.get("entry_id")
        payload = {
            "event_id": event_id, "decision_id": provenance.get("decision_id"),
            "tier": tier, "requested": requested, "executed": result.executed,
            "record_id": record_id, "previous_version_id": result.previous_version_id,
            "content_hash": rec["content_hash"],
            "file": None, "file_sha256": None,
        }
        if result.executed == "no_op":
            self._run.no_ops += 1
        else:
            self._run.writes += 1
            payload["file"] = result.path.relative_to(self._run.memory_root).as_posix()
            payload["file_sha256"] = file_sha256(result.path)
        self._run.trace.emit("write", payload)
        if result.executed != "no_op":
            self._run.snapshot("write")
        return result

    def write_project(self, operation, payload, provenance, base_version_id=None):
        return self._call("project", operation, provenance, self._inner.write_project,
                          operation, payload, provenance, base_version_id)

    def rollback_project(self, memory_id, to_version_id, provenance, base_version_id):
        return self._call("project", "supersede", provenance, self._inner.rollback_project,
                          memory_id, to_version_id, provenance, base_version_id)

    def write_session(self, operation, payload, provenance, base_version_id=None):
        return self._call("session", operation, provenance, self._inner.write_session,
                          operation, payload, provenance, base_version_id)

    def append_log(self, payload, provenance):
        return self._call("daily_log", "append", provenance, self._inner.append_log, payload, provenance)


class Run:
    """Start with Run.start(...); always call finish() (or use it as a context manager)."""

    def __init__(self, run_dir: Path, manifest: dict[str, Any], clock, monotonic, new_id) -> None:
        self.dir = run_dir
        self.run_id = manifest["run_id"]
        self.manifest = manifest
        self.clock = clock
        self.memory_root = run_dir / "memory"
        self.store = MemoryStore(self.memory_root, manifest["project_id"])
        self.raw_writer = VersionedWriter(self.store, clock=clock, new_id=new_id)
        self.writer = RecordingWriter(self)
        self.trace = TraceLog(run_dir / "trace.jsonl", self.run_id, clock=clock, monotonic=monotonic)
        self.usage = UsageLogger(run_dir / "usage.jsonl")
        self.snapshots = 0
        self.writes = 0
        self.no_ops = 0
        self.rejected = 0
        self.finished = False
        self._last_snapshot_sha: str | None = None

    # -- lifecycle -----------------------------------------------------------

    @classmethod
    def start(
        cls,
        runs_root: str | Path,
        *,
        project_id: str,
        purpose: str = "dev",
        stage: str = "none",
        condition: str = "dev",
        operator: str = "kaiqiang",
        pair_id: str | None = None,
        case_id: str | None = None,
        task_version: str | None = None,
        fixture: dict[str, str] | None = None,
        protocol_version: str = "unfrozen",
        model_config: dict[str, Any] | None = None,
        budgets: dict[str, Any] | None = None,
        clock_mode: str = "real",
        checkpoints: list[str] | None = None,
        clock: Callable[[], str] = utc_now_iso,
        monotonic: Callable[[], float] = time.monotonic,
        new_id: Callable[[], str] = lambda: uuid.uuid4().hex,
        code: dict[str, Any] | None = None,
    ) -> "Run":
        run_id = "run_" + new_id()
        run_dir = Path(runs_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        manifest = {
            "manifest_version": "manifest-v1", "run_id": run_id, "status": "running",
            "purpose": purpose, "stage": stage, "condition": condition,
            "pair_id": pair_id, "case_id": case_id, "task_version": task_version,
            "project_id": project_id,
            "code": code if code is not None else code_version(),
            "schemas_sha256": schemas_sha256(),
            "fixture": fixture, "protocol_version": protocol_version,
            "model_config": model_config or {"pinned": False, "provider": None, "model": None, "effort": None, "fallback": None},
            "budgets": budgets or {"max_model_calls": None, "max_total_tokens": None, "max_seconds": None},
            "clock": {"mode": clock_mode, "checkpoints": checkpoints or []},
            "operator": operator, "started_at_utc": clock(), "ended_at_utc": None,
            "outputs": None, "deviations": [],
        }
        errors = schema_errors(manifest, MANIFEST_SCHEMA)
        if errors:
            run_dir.rmdir()
            raise ValueError("invalid run manifest: " + "; ".join(errors))
        run = cls(run_dir, manifest, clock, monotonic, new_id)
        run._write_manifest()
        run.trace.emit("run_start", {"manifest_sha256": file_sha256(run_dir / "manifest.json")})
        run.snapshot("initial")
        return run

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self.finished:
            self.finish(status="failed" if exc_type else "complete",
                        note=f"{exc_type.__name__}: {exc}" if exc_type else None)

    def finish(self, status: str = "complete", note: str | None = None) -> dict[str, Any]:
        if self.finished:
            raise RuntimeError("run already finished")
        final_sha = self.snapshot("final")
        self.trace.emit("run_end", {"status": status, "note": note})
        self.manifest.update(
            status=status,
            ended_at_utc=self.clock(),
            outputs={
                "trace_sha256": file_sha256(self.trace.path),
                "trace_events": self.trace.count,
                "snapshots": self.snapshots,
                "writes": self.writes,
                "no_ops": self.no_ops,
                "rejected_writes": self.rejected,
                "final_snapshot_sha256": final_sha,
                "usage_records": len(self.usage.read_all()),
            },
        )
        self._write_manifest()
        self.finished = True
        return self.manifest

    # -- recording -----------------------------------------------------------

    def snapshot(self, reason: str) -> str:
        if reason not in SNAPSHOT_REASONS:
            raise ValueError(f"unknown snapshot reason {reason!r}")
        snap = self.store.snapshot()
        data = (canonical_json(snap) + "\n").encode("utf-8")
        sha = sha256_text(canonical_json(snap))
        self.snapshots += 1
        rel = f"snapshots/{self.snapshots:04d}-{reason}.json"
        replace_file(self.dir / rel, data)
        self.trace.emit("snapshot", {
            "reason": reason, "snapshot_sha256": sha, "file": rel, "counts": snapshot_counts(snap),
            "unchanged_since_last": sha == self._last_snapshot_sha,
        })
        self._last_snapshot_sha = sha
        return sha

    def task_boundary(self, task_id: str, boundary: str) -> None:
        """boundary: 'start' or 'end'. Records the event and snapshots the store."""
        self.trace.emit("task_boundary", {"task_id": task_id, "boundary": boundary})
        self.snapshot("task_boundary")

    def maintenance_checkpoint(self, checkpoint_utc: str) -> None:
        self.trace.emit("maintenance_checkpoint", {"checkpoint_utc": checkpoint_utc})
        self.snapshot("maintenance_checkpoint")

    def before_recall(self, request_id: str) -> str:
        self.trace.emit("recall", {"request_id": request_id, "phase": "before"})
        return self.snapshot("pre_recall")

    def deviation(self, description: str) -> None:
        entry = {"at_utc": self.clock(), "description": description}
        self.manifest["deviations"].append(entry)
        self.trace.emit("deviation", entry)
        self._write_manifest()

    def _write_manifest(self) -> None:
        errors = schema_errors(self.manifest, MANIFEST_SCHEMA)
        if errors:
            raise ValueError("invalid run manifest: " + "; ".join(errors))
        replace_file(self.dir / "manifest.json", (canonical_json(self.manifest) + "\n").encode("utf-8"))
