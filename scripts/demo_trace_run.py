"""Demo run for T08: a few traced writes, then the audit and a snapshot diff.

    .venv/bin/python scripts/demo_trace_run.py [--out records/W03/snapshot_diff_example.json]

Uses the real clock and the git state of this repo. No model is called.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tiered_memory.tracing import Run, audit_run, diff_snapshots  # noqa: E402

FIXTURE = json.loads((ROOT / "fixtures" / "manifest.json").read_text())["fixtures"][0]
BASELINE = json.loads((ROOT / "fixtures" / "baselines" / "formal__taskservice.json").read_text())


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def prov(label: str) -> dict:
    return {"source_event_id": "evt_" + h(label)[:32], "decision_id": "dec_" + h(label)[:32], "policy_outcome": "accepted"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    commit = FIXTURE["initial_commit"]
    ev = {"evidence_id": "evd_" + h("baseline")[:32], "kind": "test", "locator": "tests/",
          "source_hash": BASELINE["output_sha256"], "source_commit": commit,
          "captured_at_utc": BASELINE["ended_at_utc"], "event_id": "evt_" + h("baseline")[:32],
          "outcome": "pass", "exit_code": 0}

    run = Run.start(ROOT / "runs", project_id="prj_taskservice", purpose="dev",
                    fixture={"path": FIXTURE["path"], "initial_commit": commit})
    w = run.writer
    run.task_boundary("tsk_T1", "start")
    w.append_log({"event_id": ev["event_id"], "dedup_key": h("baseline"), "entry_type": "test_result",
                  "summary": f"Baseline suite passed: {BASELINE['counts']['pass']} tests.", "evidence": [ev]}, prov("log"))
    fact = w.write_project("append", {
        "category": "command", "claim": "Run the test suite with `python -m pytest -q` from the repository root.",
        "support": "test_validated", "evidence": [ev], "paths": ["tests/"], "source_commit": commit,
        "last_verification_event_id": ev["event_id"]}, prov("fact")).record
    w.write_project("append", {
        "category": "command", "claim": "Run the test suite with `python -m pytest -q` from the repository root.",
        "support": "test_validated", "evidence": [ev], "paths": ["tests/"], "source_commit": commit,
        "last_verification_event_id": ev["event_id"]}, prov("fact-retry"))
    w.write_project("update", {"memory_id": fact["memory_id"], "status": "uncertain"}, prov("drift"),
                    base_version_id=fact["version_id"])
    run.task_boundary("tsk_T1", "end")
    run.finish()

    snaps = sorted((run.dir / "snapshots").glob("*.json"))
    diff = diff_snapshots(json.loads(snaps[0].read_text()), json.loads(snaps[-1].read_text()))
    problems = audit_run(run.dir)
    report = {
        "run_id": run.run_id,
        "manifest_outputs": run.manifest["outputs"],
        "audit_problems": problems,
        "snapshot_diff": {"from": snaps[0].name, "to": snaps[-1].name, **diff},
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
