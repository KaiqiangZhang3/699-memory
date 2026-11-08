"""T08 acceptance: every write has an event ID and a hash; trace, manifest, snapshots and store reconcile."""

import hashlib
import itertools
import json
from types import SimpleNamespace

import pytest

from tiered_memory.memory import WriteRejected
from tiered_memory.model_client import call_model
from tiered_memory.schemas import schema_errors
from tiered_memory.tracing import Run, TraceLog, audit_run, read_trace

PROJECT = "prj_taskservice"
COMMIT = "a" * 40
NO_GIT = {"commit": None, "dirty": None}


class Clock:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return f"2026-11-09T10:{self.n // 60:02d}:{self.n % 60:02d}+00:00"


class Mono:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        self.t += 0.005
        return self.t


def ids():
    c = itertools.count(1)
    return lambda: f"{next(c):032x}"


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def prov(label):
    return {"source_event_id": "evt_" + h(label)[:32], "decision_id": "dec_" + h(label)[:32], "policy_outcome": "accepted"}


def evidence(label):
    return {"evidence_id": "evd_" + h(label)[:32], "kind": "test", "locator": "tests/", "source_hash": "sha256:" + h(label),
            "source_commit": COMMIT, "captured_at_utc": "2026-11-09T08:00:00Z", "event_id": "evt_" + h(label)[:32],
            "outcome": "pass", "exit_code": 0}


FACT = {"category": "command", "claim": "Run tests with `python -m pytest -q`.", "support": "test_validated",
        "evidence": [evidence("e1")], "paths": ["tests/"], "source_commit": COMMIT,
        "last_verification_event_id": "evt_" + h("e1")[:32]}


def start(root, **kw):
    return Run.start(root, project_id=PROJECT, clock=Clock(), monotonic=Mono(), new_id=ids(), code=NO_GIT, **kw)


def fake_client():
    usage = SimpleNamespace(input_tokens=20, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0,
                            iterations=[SimpleNamespace(type="message")])
    resp = SimpleNamespace(model="claude-opus-5-5", stop_reason="end_turn", usage=usage,
                           content=[SimpleNamespace(type="text", text="ok")])
    resp._request_id = "req_x"
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: resp)))


def scripted_run(root):
    """A small but complete run touching every recorded moment in proposal 4.11."""
    run = start(root)
    w = run.writer
    run.task_boundary("tsk_T1", "start")
    w.append_log({"event_id": "evt_" + h("l1")[:32], "dedup_key": h("l1"), "entry_type": "test_result",
                  "summary": "suite passed", "evidence": [evidence("l1")]}, prov("l1"))
    fact = w.write_project("append", FACT, prov("p1")).record
    w.write_project("append", FACT, prov("p1-retry"))  # no_op
    with pytest.raises(WriteRejected):
        w.write_project("append", {**FACT, "claim": "x", "evidence": []}, prov("bad"))
    w.write_session("append", {"task_id": "tsk_T1", "goal": "Record constraints.", "next_steps": ["Check auth."],
                               "last_session_id": "ses_" + "1" * 32}, prov("s1"))
    run.maintenance_checkpoint("2026-11-10T00:00:00Z")
    w.write_project("update", {"memory_id": fact["memory_id"], "status": "uncertain"}, prov("p2"),
                    base_version_id=fact["version_id"])
    call_model(fake_client(), logger=run.usage, run_id=run.run_id, component="curator", messages=[])
    run.before_recall("req_1")
    run.task_boundary("tsk_T1", "end")
    run.finish()
    return run


def test_scripted_run_reconciles(tmp_path):
    run = scripted_run(tmp_path)
    assert audit_run(run.dir) == []
    m = json.loads((run.dir / "manifest.json").read_text())
    assert schema_errors(m, "run_manifest.schema.json") == []
    assert m["status"] == "complete"
    assert m["outputs"]["writes"] == 4 and m["outputs"]["no_ops"] == 1 and m["outputs"]["rejected_writes"] == 1
    assert m["outputs"]["usage_records"] == 1


def test_every_write_has_event_id_and_hash(tmp_path):
    run = scripted_run(tmp_path)
    writes = [e for e in read_trace(run.trace.path) if e["kind"] == "write"]
    assert len(writes) == 5
    for e in writes:
        p = e["payload"]
        assert p["event_id"].startswith("evt_") and p["content_hash"].startswith("sha256:")
        if p["executed"] != "no_op":
            assert p["file_sha256"].startswith("sha256:")


def test_snapshot_at_every_moment_in_4_11(tmp_path):
    run = scripted_run(tmp_path)
    reasons = [e["payload"]["reason"] for e in read_trace(run.trace.path) if e["kind"] == "snapshot"]
    assert reasons[0] == "initial" and reasons[-1] == "final"
    assert reasons.count("write") == 4
    assert {"task_boundary", "maintenance_checkpoint", "pre_recall"} <= set(reasons)


def test_rejected_write_is_traced(tmp_path):
    run = scripted_run(tmp_path)
    rejected = [e for e in read_trace(run.trace.path) if e["kind"] == "write_rejected"]
    assert len(rejected) == 1 and rejected[0]["payload"]["reason"] == "invalid_record"


def test_run_is_reproducible(tmp_path):
    a = scripted_run(tmp_path / "a")
    b = scripted_run(tmp_path / "b")
    assert a.trace.path.read_bytes() == b.trace.path.read_bytes()


# ---- the audit catches broken evidence --------------------------------------

def test_audit_detects_deleted_trace_line(tmp_path):
    run = scripted_run(tmp_path)
    lines = run.trace.path.read_text().splitlines()
    run.trace.path.write_text("\n".join(lines[:5] + lines[6:]) + "\n")
    problems = audit_run(run.dir)
    assert any("hash chain broken" in p for p in problems)
    assert any("trace_sha256" in p for p in problems)


def test_audit_detects_edited_memory_file(tmp_path):
    run = scripted_run(tmp_path)
    path = next((run.dir / "memory").rglob("v0001.json"))
    rec = json.loads(path.read_text())
    rec["goal" if "goal" in rec else "claim"] = "tampered"
    path.write_text(json.dumps(rec))
    problems = audit_run(run.dir)
    assert any("changed after it was written" in p for p in problems)
    assert any("final snapshot" in p for p in problems)


def test_audit_detects_untraced_write(tmp_path):
    run = start(tmp_path)
    run.raw_writer.write_project("append", FACT, prov("sneaky"))  # bypasses the RecordingWriter
    run.finish()
    assert any("has no write event in the trace" in p for p in audit_run(run.dir))


def test_audit_detects_missing_snapshot(tmp_path):
    run = scripted_run(tmp_path)
    next((run.dir / "snapshots").glob("*-pre_recall.json")).unlink()
    assert any("is missing" in p for p in audit_run(run.dir))


def test_audit_detects_unfinished_run(tmp_path):
    run = start(tmp_path)
    assert any("never finished" in p for p in audit_run(run.dir))


def test_audit_detects_foreign_usage_record(tmp_path):
    run = start(tmp_path)
    call_model(fake_client(), logger=run.usage, run_id="run_" + "f" * 32, component="curator", messages=[])
    run.finish()
    assert any("has run_id" in p for p in audit_run(run.dir))


# ---- manifest rules ----------------------------------------------------------

def test_failed_run_is_recorded_as_failed(tmp_path):
    with pytest.raises(RuntimeError):
        with start(tmp_path) as run:
            raise RuntimeError("boom")
    m = json.loads((run.dir / "manifest.json").read_text())
    assert m["status"] == "failed"
    assert audit_run(run.dir) == []


def test_formal_run_requires_pinned_model_frozen_protocol_clean_code(tmp_path):
    with pytest.raises(ValueError):
        start(tmp_path, purpose="formal")
    pinned = {"pinned": True, "provider": "anthropic", "model": "claude-opus-5-5", "effort": "medium", "fallback": "off"}
    with pytest.raises(ValueError):
        Run.start(tmp_path, project_id=PROJECT, purpose="formal", model_config=pinned, protocol_version="protocol-v1",
                  code={"commit": COMMIT, "dirty": True}, new_id=ids())
    run = Run.start(tmp_path, project_id=PROJECT, purpose="formal", model_config=pinned, protocol_version="protocol-v1",
                    code={"commit": COMMIT, "dirty": False}, new_id=ids())
    assert run.manifest["purpose"] == "formal"


def test_deviation_kept_in_manifest_and_trace(tmp_path):
    run = start(tmp_path)
    run.deviation("Operator restarted the session after a terminal crash.")
    run.finish()
    m = json.loads((run.dir / "manifest.json").read_text())
    assert m["deviations"][0]["description"].startswith("Operator restarted")
    assert any(e["kind"] == "deviation" for e in read_trace(run.trace.path))
    assert audit_run(run.dir) == []


def test_trace_is_never_reopened(tmp_path):
    t = TraceLog(tmp_path / "t.jsonl", "run_" + "1" * 32)
    t.emit("run_start")
    with pytest.raises(FileExistsError):
        TraceLog(tmp_path / "t.jsonl", "run_" + "1" * 32)


def test_trace_rejects_write_event_without_event_id(tmp_path):
    t = TraceLog(tmp_path / "t.jsonl", "run_" + "1" * 32)
    t.emit("run_start")
    with pytest.raises(ValueError):
        t.emit("write", {"tier": "project", "executed": "append"})


def test_finish_twice_rejected(tmp_path):
    run = start(tmp_path)
    run.finish()
    with pytest.raises(RuntimeError):
        run.finish()


def test_snapshot_diff_shows_only_additions(tmp_path):
    from tiered_memory.tracing import diff_snapshots
    run = scripted_run(tmp_path)
    files = sorted((run.dir / "snapshots").glob("*.json"))
    first, last = (json.loads(f.read_text()) for f in (files[0], files[-1]))
    d = diff_snapshots(first, last)
    assert d["removed"] == [] and d["changed"] == []
    assert sorted(r["tier"] for r in d["added"]) == ["daily_log", "project", "project", "session"]
    assert {r["operation"] for r in d["added"]} == {"append", "update"}
    assert diff_snapshots(last, first)["removed"], "going backwards shows removals"
