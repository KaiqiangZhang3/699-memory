"""Read-only access to the three memory tiers on disk (task T07, decision D1).

Layout under ``root``::

    <project_id>/project/<memory_id>/v0001.json     one file per Project Memory version
    <project_id>/session/<task_id>/v0001.json       one file per Session Memory version
    <project_id>/daily_log/<YYYY-MM-DD>.jsonl       one Daily Log file per UTC date

This class has no methods that write. Only ``VersionedWriter`` writes
(FR1, threat TH10).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from ..schemas import validate_record

PROJECT_ID = re.compile(r"^prj_[a-z0-9][a-z0-9-]{0,62}$")
VERSION_FILE = re.compile(r"^v(\d{4})\.json$")


def version_filename(version: int) -> str:
    if not 1 <= version <= 9999:
        raise ValueError(f"version out of range: {version}")
    return f"v{version:04d}.json"


class MemoryStore:
    def __init__(self, root: str | Path, project_id: str) -> None:
        if not PROJECT_ID.match(project_id):
            raise ValueError(f"invalid project_id {project_id!r}")
        self.root = Path(root)
        self.project_id = project_id
        self.base = self.root / project_id

    # -- paths -------------------------------------------------------------

    def project_dir(self, memory_id: str) -> Path:
        return self.base / "project" / memory_id

    def session_dir(self, task_id: str) -> Path:
        return self.base / "session" / task_id

    def log_path(self, log_date: str) -> Path:
        return self.base / "daily_log" / f"{log_date}.jsonl"

    # -- generic -----------------------------------------------------------

    @staticmethod
    def _versions(directory: Path) -> list[dict[str, Any]]:
        if not directory.is_dir():
            return []
        files = sorted(p for p in directory.iterdir() if VERSION_FILE.match(p.name))
        return [json.loads(p.read_text(encoding="utf-8")) for p in files]

    @staticmethod
    def _ids(directory: Path) -> list[str]:
        if not directory.is_dir():
            return []
        return sorted(p.name for p in directory.iterdir() if p.is_dir() and not p.name.startswith("."))

    # -- Project Memory ----------------------------------------------------

    def project_memory_ids(self) -> list[str]:
        return self._ids(self.base / "project")

    def project_versions(self, memory_id: str) -> list[dict[str, Any]]:
        return self._versions(self.project_dir(memory_id))

    def project_current(self, memory_id: str) -> dict[str, Any] | None:
        versions = self.project_versions(memory_id)
        return versions[-1] if versions else None

    def project_active(self) -> list[dict[str, Any]]:
        """Current version of every record that is not archived (active or uncertain)."""
        out = []
        for memory_id in self.project_memory_ids():
            current = self.project_current(memory_id)
            if current and current["status"] != "archived":
                out.append(current)
        return out

    # -- Session Memory ----------------------------------------------------

    def session_task_ids(self) -> list[str]:
        return self._ids(self.base / "session")

    def session_versions(self, task_id: str) -> list[dict[str, Any]]:
        return self._versions(self.session_dir(task_id))

    def session_current(self, task_id: str) -> dict[str, Any] | None:
        versions = self.session_versions(task_id)
        return versions[-1] if versions else None

    # -- Daily Log ---------------------------------------------------------

    def log_dates(self) -> list[str]:
        directory = self.base / "daily_log"
        if not directory.is_dir():
            return []
        return sorted(p.stem for p in directory.glob("*.jsonl"))

    def log_entries(self, log_date: str | None = None) -> list[dict[str, Any]]:
        dates = [log_date] if log_date else self.log_dates()
        entries: list[dict[str, Any]] = []
        for d in dates:
            path = self.log_path(d)
            if path.exists():
                with path.open(encoding="utf-8") as fh:
                    entries.extend(json.loads(line) for line in fh if line.strip())
        return entries

    def find_log_by_dedup_key(self, dedup_key: str) -> dict[str, Any] | None:
        for entry in self.log_entries():
            if entry["dedup_key"] == dedup_key:
                return entry
        return None

    # -- audit -------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Every stored record, in a stable order. T08 hashes and persists this."""
        return copy.deepcopy({
            "project_id": self.project_id,
            "project": {m: self.project_versions(m) for m in self.project_memory_ids()},
            "session": {t: self.session_versions(t) for t in self.session_task_ids()},
            "daily_log": {d: self.log_entries(d) for d in self.log_dates()},
        })

    def verify(self) -> list[str]:
        """Check every record and every chain. Returns a list of problems (empty = consistent)."""
        problems: list[str] = []

        def check_chain(label: str, directory: Path, versions: list[dict], id_field: str) -> None:
            files = sorted(p.name for p in directory.iterdir() if VERSION_FILE.match(p.name)) if directory.is_dir() else []
            stray = [p.name for p in directory.iterdir() if not VERSION_FILE.match(p.name)] if directory.is_dir() else []
            for name in stray:
                problems.append(f"{label}: unexpected file {name}")
            expected_ids = {v.get(id_field) for v in versions}
            if len(expected_ids) > 1:
                problems.append(f"{label}: versions disagree on {id_field}")
            prev = None
            for n, (name, rec) in enumerate(zip(files, versions), start=1):
                where = f"{label}/{name}"
                if name != version_filename(n):
                    problems.append(f"{where}: version files are not contiguous")
                if rec.get("version") != n:
                    problems.append(f"{where}: version field is {rec.get('version')}, expected {n}")
                if rec.get("project_id") != self.project_id:
                    problems.append(f"{where}: project_id {rec.get('project_id')} does not match the store")
                expected_prev = prev["version_id"] if prev else None
                if rec.get("supersedes") != expected_prev:
                    problems.append(f"{where}: supersedes link broken")
                problems.extend(f"{where}: {e}" for e in validate_record(rec))
                prev = rec

        for memory_id in self.project_memory_ids():
            versions = self.project_versions(memory_id)
            check_chain(f"project/{memory_id}", self.project_dir(memory_id), versions, "memory_id")
            if any(v.get("memory_id") != memory_id for v in versions):
                problems.append(f"project/{memory_id}: memory_id does not match its directory")
        for task_id in self.session_task_ids():
            versions = self.session_versions(task_id)
            check_chain(f"session/{task_id}", self.session_dir(task_id), versions, "session_memory_id")
            if any(v.get("task_id") != task_id for v in versions):
                problems.append(f"session/{task_id}: task_id does not match its directory")

        seen_keys: set[str] = set()
        for log_date in self.log_dates():
            prev = None
            for n, entry in enumerate(self.log_entries(log_date), start=1):
                where = f"daily_log/{log_date}#{n}"
                if entry.get("log_date") != log_date:
                    problems.append(f"{where}: log_date does not match the file")
                if entry.get("sequence") != n:
                    problems.append(f"{where}: sequence is {entry.get('sequence')}, expected {n}")
                if entry.get("prev_entry_hash") != (prev["content_hash"] if prev else None):
                    problems.append(f"{where}: hash chain broken")
                if entry.get("project_id") != self.project_id:
                    problems.append(f"{where}: project_id does not match the store")
                if entry.get("dedup_key") in seen_keys:
                    problems.append(f"{where}: duplicate dedup_key")
                seen_keys.add(entry.get("dedup_key"))
                problems.extend(f"{where}: {e}" for e in validate_record(entry))
                prev = entry
        return problems
