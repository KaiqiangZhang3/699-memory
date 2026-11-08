"""T06 / C02 acceptance for the formal Stage Two fixture.

These checks live in the main repository, not in the fixture, so a coding
agent working on a fixture copy never sees them.
"""

import json
import subprocess
import sys
import textwrap

import pytest
from jsonschema import Draft202012Validator

from tiered_memory.fixture import FIXTURES_DIR, build_fixture_repo, run_baseline, source_tree_hash
from tiered_memory.schemas import _registry

SRC = FIXTURES_DIR / "formal" / "taskservice"
MANIFEST = json.loads((FIXTURES_DIR / "manifest.json").read_text())
ENTRY = next(f for f in MANIFEST["fixtures"] if f["path"] == "fixtures/formal/taskservice")
BASELINE = json.loads((FIXTURES_DIR / "baselines" / "formal__taskservice.json").read_text())


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    dest = tmp_path_factory.mktemp("taskservice")
    sha = build_fixture_repo(SRC, dest, "Initial fixture: formal/taskservice")
    return dest, sha


def test_manifest_matches_current_source():
    assert ENTRY["source_tree_hash"] == source_tree_hash(SRC), \
        "fixture source changed: rerun scripts/fixture_baseline.py formal/taskservice"


def test_build_is_deterministic(repo, tmp_path):
    _dest, sha = repo
    again = build_fixture_repo(SRC, tmp_path / "again", "Initial fixture: formal/taskservice")
    assert sha == again == ENTRY["initial_commit"] == BASELINE["commit"]


def test_build_refuses_non_empty_destination(repo):
    dest, _sha = repo
    with pytest.raises(FileExistsError):
        build_fixture_repo(SRC, dest, "x")


def test_baseline_tests_pass_and_match_record(repo, tmp_path):
    dest, sha = repo
    result = run_baseline(dest, tmp_path / "junit.xml")
    assert result["outcome"] == "pass" and result["exit_code"] == 0
    assert result["commit"] == sha
    assert [t["nodeid"] for t in result["tests"]] == [t["nodeid"] for t in BASELINE["tests"]]
    assert result["counts"]["pass"] == len(BASELINE["tests"]) >= 20


def test_formal_and_pilot_are_separate():
    roles = {f["role"]: f["path"] for f in MANIFEST["fixtures"]}
    assert set(roles) == {"formal", "pilot"}
    assert not roles["pilot"].startswith(roles["formal"]) and not roles["formal"].startswith(roles["pilot"])


def test_baseline_evidence_fits_evidence_ref():
    """D5: a baseline test result must be expressible as an evidence_ref."""
    validator = Draft202012Validator(
        {"$ref": "https://tiered-memory.local/schemas/v1/common.schema.json#/$defs/evidence_ref"},
        registry=_registry(),
    )
    test = BASELINE["tests"][0]
    evidence = {
        "evidence_id": "evd_" + "0" * 32,
        "kind": "test",
        "locator": test["nodeid"],
        "source_hash": BASELINE["output_sha256"],
        "source_commit": BASELINE["commit"],
        "captured_at_utc": BASELINE["ended_at_utc"],
        "event_id": "evt_" + "0" * 32,
        "outcome": test["outcome"],
        "exit_code": BASELINE["exit_code"],
    }
    assert list(validator.iter_errors(evidence)) == []


def _run_in_fixture(dest, code):
    proc = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=dest, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_planted_permissions_defect_present(repo):
    """Stage Two task T3 needs this defect: a member can PATCH another member's task."""
    dest, _sha = repo
    out = _run_in_fixture(dest, """
        from app.db import connect, init_db
        from app.seed import seed
        from app.services import TaskService, Forbidden
        conn = connect(); init_db(conn); ids = seed(conn)
        svc = TaskService(conn, lambda: "2026-11-01T00:00:00+00:00")
        alice = {"id": ids["alice"], "role": "member"}; bob = {"id": ids["bob"], "role": "member"}
        task = svc.create(alice, "alice task")
        try:
            svc.get(bob, task["id"]); print("read-allowed")
        except Forbidden:
            print("read-blocked")
        svc.update(bob, task["id"], {"status": "done"})
        print("update-allowed")
    """)
    assert out.splitlines() == ["read-blocked", "update-allowed"]


def test_features_for_later_tasks_absent(repo):
    """At baseline, T2 (filtering), T4 (audit log) and T6 (reporting) have not been built yet."""
    dest, _sha = repo
    files = {p.relative_to(dest).as_posix() for p in dest.rglob("*.py")}
    assert not any("audit" in f or "report" in f for f in files)
    assert "status=" not in (dest / "app" / "web.py").read_text()
