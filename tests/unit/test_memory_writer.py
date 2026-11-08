"""T07 acceptance: three stores + versioned writer (atomic write, supersedes, rollback).

"Snapshots equal recorded writes": after any sequence of writes, the store
holds exactly the records the writer reported, in order, and verify() is clean.
"""

import hashlib
import itertools
import json

import pytest

from tiered_memory.memory import MemoryStore, VersionedWriter, WriteRejected
from tiered_memory.memory.writer import write_new_file

PROJECT = "prj_taskservice"
COMMIT = "a" * 40
COMMIT2 = "b" * 40


class Clock:
    """Controlled clock: each call advances one minute from a fixed start."""

    def __init__(self, day="2026-11-09", hour=9):
        self.day, self.n, self.hour = day, 0, hour

    def __call__(self):
        self.n += 1
        return f"{self.day}T{self.hour:02d}:{self.n % 60:02d}:00+00:00"


def ids():
    counter = itertools.count(1)
    return lambda: f"{next(counter):032x}"


def h(label):
    return hashlib.sha256(label.encode()).hexdigest()


def evt(label):
    return "evt_" + h(label)[:32]


def prov(label="x"):
    return {"source_event_id": evt(label), "decision_id": "dec_" + h(label)[:32], "policy_outcome": "accepted"}


def evidence(label, kind="test", outcome="pass", commit=COMMIT):
    ev = {"evidence_id": "evd_" + h(label)[:32], "kind": kind, "locator": "tests/", "source_hash": "sha256:" + h(label),
          "source_commit": commit, "captured_at_utc": "2026-11-09T08:00:00Z", "event_id": evt(label)}
    if kind in ("test", "command"):
        ev.update(outcome=outcome, exit_code=0 if outcome == "pass" else 1)
    return ev


def fact(claim="Run tests with `python -m pytest -q`.", **over):
    payload = {"category": "command", "claim": claim, "support": "test_validated",
               "evidence": [evidence("e1")], "paths": ["tests/"], "source_commit": COMMIT,
               "last_verification_event_id": evt("e1")}
    payload.update(over)
    return payload


def session(**over):
    payload = {"task_id": "tsk_T4", "goal": "Add audit logging.", "next_steps": ["Write the first audit test."],
               "last_session_id": "ses_" + "1" * 32}
    payload.update(over)
    return payload


def log(label="l1", **over):
    payload = {"event_id": evt(label), "dedup_key": h(label), "entry_type": "test_result",
               "summary": f"suite passed ({label})", "evidence": [evidence(label)]}
    payload.update(over)
    return payload


@pytest.fixture
def env(tmp_path):
    store = MemoryStore(tmp_path, PROJECT)
    clock = Clock()
    writer = VersionedWriter(store, clock=clock, new_id=ids())
    return store, writer, clock


def all_files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


# ---- Project Memory ---------------------------------------------------------

def test_append_creates_v1_on_disk(env, tmp_path):
    store, writer, _ = env
    res = writer.write_project("append", fact(), prov())
    assert res.executed == "append"
    rec = res.record
    assert rec["version"] == 1 and rec["supersedes"] is None and rec["status"] == "active"
    assert res.path == tmp_path / PROJECT / "project" / rec["memory_id"] / "v0001.json"
    assert json.loads(res.path.read_text()) == rec
    assert rec["provenance"]["written_by"] == "versioned_writer"
    assert rec["provenance"]["operation"] == "append"
    assert store.verify() == []


def test_duplicate_fact_is_no_op(env, tmp_path):
    _, writer, _ = env
    first = writer.write_project("append", fact(), prov("a"))
    before = all_files(tmp_path)
    again = writer.write_project("append", fact(evidence=[evidence("e2")]), prov("b"))
    assert again.executed == "no_op" and again.path is None
    assert again.record["memory_id"] == first.record["memory_id"]
    assert all_files(tmp_path) == before


def test_update_marks_uncertain_without_touching_v1(env):
    store, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    v1_bytes = store.project_dir(v1["memory_id"]).joinpath("v0001.json").read_bytes()
    res = writer.write_project("update", {"memory_id": v1["memory_id"], "status": "uncertain"}, prov("u"),
                               base_version_id=v1["version_id"])
    v2 = res.record
    assert (res.executed, v2["version"], v2["supersedes"], v2["status"]) == ("update", 2, v1["version_id"], "uncertain")
    assert v2["verified_at_utc"] == v1["verified_at_utc"], "marking uncertain is not a verification"
    assert v2["content_hash"] == v1["content_hash"], "same content, same hash (D4)"
    assert store.project_dir(v1["memory_id"]).joinpath("v0001.json").read_bytes() == v1_bytes
    assert store.project_current(v1["memory_id"]) == v2
    assert store.verify() == []


def test_update_cannot_change_the_claim(env):
    _, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    with pytest.raises(WriteRejected) as e:
        writer.write_project("update", {"memory_id": v1["memory_id"], "claim": "new"}, prov(),
                             base_version_id=v1["version_id"])
    assert e.value.reason == "content_change"


def test_update_with_nothing_new_is_no_op(env):
    _, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    res = writer.write_project("update", {"memory_id": v1["memory_id"], "status": "active"}, prov(),
                               base_version_id=v1["version_id"])
    assert res.executed == "no_op"


def test_supersede_replaces_claim(env):
    store, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    new = fact("Run tests with `python -m pytest -q --ignore=tests/hidden`.", source_commit=COMMIT2,
               evidence=[evidence("e2", commit=COMMIT2)], last_verification_event_id=evt("e2"))
    res = writer.write_project("supersede", {"memory_id": v1["memory_id"], **new}, prov("s"),
                               base_version_id=v1["version_id"])
    v2 = res.record
    assert res.executed == "supersede" and res.previous_version_id == v1["version_id"]
    assert v2["content_hash"] != v1["content_hash"]
    assert v2["created_at_utc"] == v1["created_at_utc"] and v2["verified_at_utc"] > v1["verified_at_utc"]
    assert [v["version"] for v in store.project_versions(v1["memory_id"])] == [1, 2]
    assert store.verify() == []


def test_supersede_with_same_content_is_no_op(env):
    _, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    res = writer.write_project("supersede", {"memory_id": v1["memory_id"], "claim": v1["claim"]}, prov(),
                               base_version_id=v1["version_id"])
    assert res.executed == "no_op"


def test_stale_base_is_a_conflict(env, tmp_path):
    _, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    writer.write_project("update", {"memory_id": v1["memory_id"], "status": "uncertain"}, prov(),
                         base_version_id=v1["version_id"])
    before = all_files(tmp_path)
    with pytest.raises(WriteRejected) as e:
        writer.write_project("supersede", {"memory_id": v1["memory_id"], "claim": "other"}, prov(),
                             base_version_id=v1["version_id"])
    assert e.value.reason == "stale_base"
    assert all_files(tmp_path) == before


def test_change_without_base_rejected(env):
    _, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    with pytest.raises(WriteRejected) as e:
        writer.write_project("update", {"memory_id": v1["memory_id"], "status": "uncertain"}, prov())
    assert e.value.reason == "missing_base"


def test_unknown_memory_rejected(env):
    _, writer, _ = env
    with pytest.raises(WriteRejected) as e:
        writer.write_project("update", {"memory_id": "mem_" + "f" * 32, "status": "uncertain"}, prov(),
                             base_version_id="ver_" + "f" * 32)
    assert e.value.reason == "unknown_record"


def test_archive_keeps_history_and_is_idempotent(env):
    store, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    v2 = writer.write_project("archive", {"memory_id": v1["memory_id"]}, prov("a"), base_version_id=v1["version_id"]).record
    assert v2["status"] == "archived"
    assert store.project_active() == []
    assert len(store.project_versions(v1["memory_id"])) == 2
    again = writer.write_project("archive", {"memory_id": v1["memory_id"]}, prov("a"), base_version_id=v2["version_id"])
    assert again.executed == "no_op"


def test_archived_status_only_via_archive(env):
    _, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    with pytest.raises(WriteRejected):
        writer.write_project("update", {"memory_id": v1["memory_id"], "status": "archived"}, prov(),
                             base_version_id=v1["version_id"])


def test_rollback_writes_old_content_forward(env):
    store, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    v2 = writer.write_project("supersede", {"memory_id": v1["memory_id"], "claim": "Wrong claim."}, prov("bad"),
                              base_version_id=v1["version_id"]).record
    res = writer.rollback_project(v1["memory_id"], v1["version_id"], prov("rb"), base_version_id=v2["version_id"])
    v3 = res.record
    assert (v3["version"], v3["supersedes"], v3["claim"]) == (3, v2["version_id"], v1["claim"])
    assert v3["content_hash"] == v1["content_hash"]
    assert v3["provenance"]["operation"] == "supersede"
    assert [v["claim"] for v in store.project_versions(v1["memory_id"])] == [v1["claim"], "Wrong claim.", v1["claim"]]
    assert store.verify() == []


def test_rollback_to_unknown_version_rejected(env):
    _, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    with pytest.raises(WriteRejected):
        writer.rollback_project(v1["memory_id"], "ver_" + "e" * 32, prov(), base_version_id=v1["version_id"])


# ---- rejections leave nothing behind ---------------------------------------

@pytest.mark.parametrize("bad, reason", [
    (dict(evidence=[]), "invalid_record"),
    (dict(support="repository_evidence"), "invalid_record"),
    (dict(project_id="prj_other"), "cross_project"),
    (dict(confidence=0.9), "bad_payload"),
    (dict(memory_id="mem_" + "1" * 32), "bad_payload"),
])
def test_rejected_append_writes_nothing(env, tmp_path, bad, reason):
    _, writer, _ = env
    with pytest.raises(WriteRejected) as e:
        writer.write_project("append", fact(**bad), prov())
    assert e.value.reason == reason
    assert all_files(tmp_path) == []


@pytest.mark.parametrize("override, reason", [
    ({"policy_outcome": "review_required"}, "not_accepted"),
    ({"policy_outcome": "blocked"}, "not_accepted"),
    ({"written_by": "hook"}, "bad_provenance"),
])
def test_only_accepted_decisions_write(env, tmp_path, override, reason):
    _, writer, _ = env
    with pytest.raises(WriteRejected) as e:
        writer.write_project("append", fact(), {**prov(), **override})
    assert e.value.reason == reason
    assert all_files(tmp_path) == []


def test_unknown_operation_rejected(env):
    _, writer, _ = env
    with pytest.raises(WriteRejected) as e:
        writer.write_project("delete", {"memory_id": "mem_" + "1" * 32}, prov())
    assert e.value.reason == "bad_operation"


def test_files_are_never_overwritten(tmp_path):
    path = tmp_path / "v0001.json"
    write_new_file(path, b"first")
    with pytest.raises(FileExistsError):
        write_new_file(path, b"second")
    assert path.read_bytes() == b"first"
    assert [p.name for p in tmp_path.iterdir()] == ["v0001.json"], "no temp files left behind"


def test_store_exposes_no_write_methods():
    public = {n for n in dir(MemoryStore) if not n.startswith("_")}
    assert not any(n.startswith(("write", "append", "update", "delete", "save", "put", "set")) for n in public)


# ---- Session Memory ---------------------------------------------------------

def test_session_append_update_and_no_op(env):
    store, writer, _ = env
    v1 = writer.write_session("append", session(), prov()).record
    assert v1["version"] == 1 and v1["status"] == "active"
    ev = evidence("audit-pass")
    v2 = writer.write_session("update", {"task_id": "tsk_T4", "evidence": [ev], "progress": [
        {"item": "create is logged", "state": "done", "evidence_ids": [ev["evidence_id"]]}]}, prov("u"),
        base_version_id=v1["version_id"]).record
    assert v2["version"] == 2 and v2["supersedes"] == v1["version_id"]
    assert v2["updated_at_utc"] > v1["updated_at_utc"]
    same = writer.write_session("update", {"task_id": "tsk_T4", "goal": v1["goal"]}, prov(), base_version_id=v2["version_id"])
    assert same.executed == "no_op"
    assert store.verify() == []


def test_session_append_twice_rejected(env):
    _, writer, _ = env
    writer.write_session("append", session(), prov())
    with pytest.raises(WriteRejected) as e:
        writer.write_session("append", session(), prov())
    assert e.value.reason == "already_exists"


def test_session_rules_still_enforced(env, tmp_path):
    _, writer, _ = env
    v1 = writer.write_session("append", session(), prov()).record
    with pytest.raises(WriteRejected) as e:
        writer.write_session("update", {"task_id": "tsk_T4", "next_steps": []}, prov(), base_version_id=v1["version_id"])
    assert e.value.reason == "invalid_record"
    with pytest.raises(WriteRejected):
        writer.write_session("update", {"task_id": "tsk_T4", "progress": [
            {"item": "x", "state": "done", "evidence_ids": ["evd_" + "9" * 32]}]}, prov(), base_version_id=v1["version_id"])


def test_session_archive(env):
    store, writer, _ = env
    v1 = writer.write_session("append", session(), prov()).record
    v2 = writer.write_session("archive", {"task_id": "tsk_T4"}, prov(), base_version_id=v1["version_id"]).record
    assert v2["status"] == "archived" and store.session_current("tsk_T4") == v2


# ---- Daily Log -------------------------------------------------------------

def test_log_sequence_and_hash_chain(env):
    store, writer, _ = env
    e1 = writer.append_log(log("l1"), prov("l1")).record
    e2 = writer.append_log(log("l2"), prov("l2")).record
    assert (e1["sequence"], e2["sequence"]) == (1, 2)
    assert e1["prev_entry_hash"] is None and e2["prev_entry_hash"] == e1["content_hash"]
    assert store.log_entries("2026-11-09") == [e1, e2]
    assert store.verify() == []


def test_log_retry_is_no_op(env):
    store, writer, _ = env
    writer.append_log(log("l1"), prov("l1"))
    again = writer.append_log(log("l1"), prov("l1-retry"))
    assert again.executed == "no_op"
    assert len(store.log_entries()) == 1


def test_log_new_day_restarts_sequence(env):
    store, writer, clock = env
    writer.append_log(log("l1"), prov())
    clock.day = "2026-11-10"
    e = writer.append_log(log("l2"), prov()).record
    assert (e["log_date"], e["sequence"], e["prev_entry_hash"]) == ("2026-11-10", 1, None)
    assert store.log_dates() == ["2026-11-09", "2026-11-10"]


def test_log_is_append_only_on_disk(env):
    store, writer, _ = env
    writer.append_log(log("l1"), prov())
    first_line = store.log_path("2026-11-09").read_text().splitlines()[0]
    writer.append_log(log("l2"), prov())
    assert store.log_path("2026-11-09").read_text().splitlines()[0] == first_line


# ---- audit: verify() and "snapshots equal recorded writes" ------------------

def test_verify_detects_tampering(env):
    store, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    writer.append_log(log("l1"), prov())
    writer.append_log(log("l2"), prov())
    path = store.project_dir(v1["memory_id"]) / "v0001.json"
    tampered = json.loads(path.read_text())
    tampered["claim"] = "Tests are optional."
    path.write_text(json.dumps(tampered))
    logfile = store.log_path("2026-11-09")
    lines = logfile.read_text().splitlines()
    logfile.write_text(lines[1] + "\n")  # drop the first entry
    problems = store.verify()
    assert any("content_hash" in p for p in problems)
    assert any("hash chain broken" in p or "sequence" in p for p in problems)


def test_verify_detects_stray_files(env):
    store, writer, _ = env
    v1 = writer.write_project("append", fact(), prov()).record
    (store.project_dir(v1["memory_id"]) / "notes.txt").write_text("x")
    assert any("unexpected file" in p for p in store.verify())


def test_store_state_equals_recorded_writes(env):
    store, writer, clock = env
    results = []
    a = writer.write_project("append", fact(), prov("1")); results.append(a)
    results.append(writer.write_project("append", fact(), prov("dup")))  # no_op
    b = writer.write_project("append", fact("Route handlers call app/services/.", category="architecture",
                                            support="repository_evidence", evidence=[evidence("f", kind="file")],
                                            paths=["app/services/"]), prov("2")); results.append(b)
    u = writer.write_project("update", {"memory_id": a.record["memory_id"], "status": "uncertain"}, prov("3"),
                             base_version_id=a.record["version_id"]); results.append(u)
    s = writer.write_session("append", session(), prov("4")); results.append(s)
    results.append(writer.append_log(log("l1"), prov("5")))
    results.append(writer.append_log(log("l1"), prov("5b")))  # no_op
    clock.day = "2026-11-10"
    results.append(writer.append_log(log("l2"), prov("6")))
    results.append(writer.write_project("archive", {"memory_id": b.record["memory_id"]}, prov("7"),
                                        base_version_id=b.record["version_id"]))

    written = [r for r in results if r.executed != "no_op"]
    snap = store.snapshot()
    stored = (
        [v for versions in snap["project"].values() for v in versions]
        + [v for versions in snap["session"].values() for v in versions]
        + [e for entries in snap["daily_log"].values() for e in entries]
    )
    key = lambda r: r["provenance"]["written_at_utc"]
    assert sorted(stored, key=key) == sorted((r.record for r in written), key=key)
    assert len(stored) == len(written) == 7
    assert store.verify() == []
