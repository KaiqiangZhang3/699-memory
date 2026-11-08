"""Regenerate the sample records in schemas/v1/examples/ (task T03).

IDs and hashes are derived from fixed labels, so the output is identical on
every run. The samples describe the planned Stage Two fixture (a small
task-management service, proposal 4.5); they are design samples, not data.

    .venv/bin/python scripts/build_schema_examples.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tiered_memory.schemas import compute_content_hash, sha256_text  # noqa: E402

OUT = ROOT / "schemas" / "v1" / "examples"
PROJECT = "prj_taskservice"
COMMIT_1 = hashlib.sha1(b"fixture-commit-1").hexdigest()
COMMIT_2 = hashlib.sha1(b"fixture-commit-2").hexdigest()


def hid(prefix: str, label: str) -> str:
    return f"{prefix}_{hashlib.sha256(label.encode()).hexdigest()[:32]}"


def provenance(label: str, operation: str, ts: str, review: bool = False) -> dict:
    return {
        "source_event_id": hid("evt", label),
        "decision_id": hid("dec", label),
        "policy_outcome": "accepted",
        "review_id": hid("rev", label) if review else None,
        "operation": operation,
        "written_at_utc": ts,
        "written_by": "versioned_writer",
        "condition": "dev",
        "run_id": hid("run", "example-run"),
    }


def evidence(label: str, kind: str, locator: str, ts: str, commit: str | None, **extra) -> dict:
    ev = {
        "evidence_id": hid("evd", label),
        "kind": kind,
        "locator": locator,
        "source_hash": sha256_text("content of " + label),
        "source_commit": commit,
        "captured_at_utc": ts,
        "event_id": hid("evt", label),
    }
    ev.update(extra)
    return ev


def finish(record: dict) -> dict:
    record["content_hash"] = compute_content_hash(record)
    return record


def project_examples() -> list[tuple[str, dict]]:
    t0, t1 = "2026-11-09T14:02:11Z", "2026-11-12T09:30:00Z"
    v1 = finish({
        "schema_version": "pm-v1", "tier": "project", "project_id": PROJECT,
        "memory_id": hid("mem", "test-command"), "version": 1,
        "version_id": hid("ver", "test-command-v1"), "supersedes": None,
        "category": "command",
        "claim": "Run the full test suite with `pytest -q tests/` from the repository root.",
        "status": "superseded", "support": "test_validated",
        "evidence": [evidence("pytest-run-1", "test", "tests/", t0, COMMIT_1, outcome="pass", exit_code=0)],
        "paths": ["tests/"], "tags": ["testing"],
        "source_commit": COMMIT_1, "created_at_utc": t0, "verified_at_utc": t0,
        "last_verification_event_id": hid("evt", "pytest-run-1"),
        "provenance": provenance("test-command-v1", "append", t0),
    })
    v2 = finish({
        **{k: v for k, v in v1.items() if k != "content_hash"},
        "version": 2, "version_id": hid("ver", "test-command-v2"), "supersedes": v1["version_id"],
        "claim": "Run the full test suite with `pytest -q tests/ --ignore=tests/hidden` from the repository root.",
        "status": "active", "support": "user_approved",
        "evidence": [
            evidence("pytest-run-2", "test", "tests/", t1, COMMIT_2, outcome="pass", exit_code=0),
            evidence("user-correction-1", "user_correction", "log:" + hid("log", "correction"), t1, COMMIT_2),
        ],
        "source_commit": COMMIT_2, "verified_at_utc": t1,
        "last_verification_event_id": hid("evt", "pytest-run-2"),
        "provenance": provenance("test-command-v2", "supersede", t1, review=True),
    })
    arch = finish({
        "schema_version": "pm-v1", "tier": "project", "project_id": PROJECT,
        "memory_id": hid("mem", "auth"), "version": 1,
        "version_id": hid("ver", "auth-v1"), "supersedes": None,
        "category": "architecture",
        "claim": "Authentication uses server-side session cookies; route handlers call app/services/ and never query SQLite directly.",
        "status": "active", "support": "repository_evidence",
        "evidence": [
            evidence("auth-file", "file", "app/auth.py:12", t0, COMMIT_1),
            evidence("services-dir", "file", "app/services/__init__.py", t0, COMMIT_1),
        ],
        "paths": ["app/auth.py", "app/services/"], "tags": ["auth", "architecture"],
        "source_commit": COMMIT_1, "created_at_utc": t0, "verified_at_utc": t0,
        "last_verification_event_id": hid("evt", "auth-file"),
        "provenance": provenance("auth-v1", "append", t0),
    })
    return [("project_test_command_v1.json", v1), ("project_test_command_v2.json", v2), ("project_auth_architecture_v1.json", arch)]


def daily_log_examples() -> list[tuple[str, dict]]:
    day, ts1, ts2 = "2026-11-09", "2026-11-09T14:02:11Z", "2026-11-09T14:20:45Z"
    common = {"schema_version": "dl-v1", "tier": "daily_log", "project_id": PROJECT, "log_date": day,
              "run_id": hid("run", "example-run"), "task_id": "tsk_T3", "session_id": hid("ses", "s1"),
              "corrects_entry_id": None}
    e1 = finish({
        **common, "entry_id": hid("log", "fail-1"), "sequence": 1, "recorded_at_utc": ts1,
        "event_id": hid("evt", "fail-1"), "dedup_key": hashlib.sha256(b"fail-1").hexdigest(),
        "entry_type": "failure",
        "summary": "Patch that checked ownership in the route handler failed tests/test_permissions.py::test_admin_can_edit.",
        "evidence": [evidence("fail-1", "test", "tests/test_permissions.py::test_admin_can_edit", ts1, COMMIT_1, outcome="fail", exit_code=1)],
        "prev_entry_hash": None,
        "provenance": provenance("fail-1", "append", ts1),
    })
    e2 = finish({
        **common, "entry_id": hid("log", "pass-1"), "sequence": 2, "recorded_at_utc": ts2,
        "event_id": hid("evt", "pass-1"), "dedup_key": hashlib.sha256(b"pass-1").hexdigest(),
        "entry_type": "test_result",
        "summary": "Permission check moved to app/services/tasks.py; full suite passes.",
        "evidence": [evidence("pass-1", "test", "tests/", ts2, COMMIT_2, outcome="pass", exit_code=0)],
        "prev_entry_hash": e1["content_hash"],
        "provenance": provenance("pass-1", "append", ts2),
    })
    return [("daily_log_2026-11-09_001.json", e1), ("daily_log_2026-11-09_002.json", e2)]


def session_examples() -> list[tuple[str, dict]]:
    t0, t1 = "2026-11-10T10:00:00Z", "2026-11-10T11:45:00Z"
    ev_test = evidence("audit-test-pass", "test", "tests/test_audit.py::test_create_logged", t1, COMMIT_2, outcome="pass", exit_code=0)
    ev_fail = evidence("audit-mw-fail", "test", "tests/test_audit.py::test_update_logged", t1, COMMIT_2, outcome="fail", exit_code=1)
    rec = finish({
        "schema_version": "sm-v1", "tier": "session", "project_id": PROJECT,
        "session_memory_id": hid("smem", "T4"), "task_id": "tsk_T4", "version": 2,
        "version_id": hid("ver", "T4-v2"), "supersedes": hid("ver", "T4-v1"),
        "status": "paused",
        "goal": "Add audit logging for task create, update and delete.",
        "progress": [
            {"item": "Audit log for task creation", "state": "done", "evidence_ids": [ev_test["evidence_id"]]},
            {"item": "Audit log for task update", "state": "in_progress", "evidence_ids": []},
            {"item": "Audit log for task delete", "state": "not_started", "evidence_ids": []},
        ],
        "tentative_findings": [
            {"finding": "Writing audit rows inside the service-layer transaction may be enough; not verified.", "evidence_ids": []},
        ],
        "failed_attempts": [
            {"approach": "Logging updates from HTTP middleware.",
             "outcome": "Middleware cannot see the task's previous field values; test_update_logged fails.",
             "evidence_ids": [ev_fail["evidence_id"]], "event_id": ev_fail["event_id"]},
        ],
        "blockers": [],
        "next_steps": ["Log updates from TaskService.update() with old and new values, then rerun tests/test_audit.py."],
        "evidence": [ev_test, ev_fail],
        "last_session_id": hid("ses", "s2"),
        "created_at_utc": t0, "updated_at_utc": t1,
        "provenance": provenance("T4-v2", "update", t1),
    })
    return [("session_T4_v2.json", rec)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, record in project_examples() + daily_log_examples() + session_examples():
        (OUT / name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()
