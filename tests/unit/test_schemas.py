"""T03 acceptance: sample records validate, and each rule rejects what it should."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tiered_memory.schemas import KINDS, SCHEMA_DIR, compute_content_hash, validate_record

EXAMPLES = sorted((SCHEMA_DIR / "examples").glob("*.json"))


def load(name):
    return json.loads((SCHEMA_DIR / "examples" / name).read_text())


def rehash(record):
    record["content_hash"] = compute_content_hash(record)
    return record


def assert_invalid(record, fragment):
    errors = validate_record(record)
    assert errors, "expected the record to be rejected"
    assert any(fragment in e for e in errors), errors


def test_schemas_are_valid_draft_2020_12():
    for path in SCHEMA_DIR.glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text()))


def test_every_tier_has_examples():
    tiers = {json.loads(p.read_text())["tier"] for p in EXAMPLES}
    assert tiers == set(KINDS)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_validate(path):
    assert validate_record(json.loads(path.read_text())) == []


# ---- shared rules -----------------------------------------------------------

def test_unknown_field_rejected():
    rec = load("project_auth_architecture_v1.json")
    rec["confidence"] = 0.9
    assert_invalid(rehash(rec), "Additional properties")


def test_non_utc_timestamp_rejected():
    rec = load("project_auth_architecture_v1.json")
    rec["created_at_utc"] = "2026-11-09T09:02:11-05:00"
    assert_invalid(rehash(rec), "created_at_utc")


def test_bad_id_prefix_rejected():
    rec = load("project_auth_architecture_v1.json")
    rec["memory_id"] = rec["memory_id"].replace("mem_", "evt_")
    assert_invalid(rehash(rec), "memory_id")


def test_tampered_content_hash_rejected():
    rec = load("project_auth_architecture_v1.json")
    rec["claim"] = "Authentication uses JWT bearer tokens."
    assert_invalid(rec, "content_hash")


def test_provenance_change_does_not_change_hash():
    rec = load("project_auth_architecture_v1.json")
    before = rec["content_hash"]
    rec["provenance"]["written_at_utc"] = "2026-11-10T00:00:00Z"
    assert compute_content_hash(rec) == before


def test_write_without_accepted_policy_outcome_rejected():
    rec = load("project_auth_architecture_v1.json")
    rec["provenance"]["policy_outcome"] = "review_required"
    assert_invalid(rec, "provenance/policy_outcome")


def test_write_by_hook_rejected():
    rec = load("project_auth_architecture_v1.json")
    rec["provenance"]["written_by"] = "hook"
    assert_invalid(rec, "provenance/written_by")


def test_absolute_or_parent_paths_rejected():
    for bad in ["/etc/passwd", "../other/repo.py"]:
        rec = load("project_auth_architecture_v1.json")
        rec["paths"] = [bad]
        assert_invalid(rehash(rec), "paths")


def test_test_evidence_needs_outcome():
    rec = load("project_test_command_v1.json")
    del rec["evidence"][0]["outcome"]
    assert_invalid(rehash(rec), "outcome")


def test_file_evidence_cannot_carry_outcome():
    rec = load("project_auth_architecture_v1.json")
    rec["evidence"][0]["outcome"] = "pass"
    assert_invalid(rehash(rec), "evidence/0")


# ---- Project Memory ---------------------------------------------------------

def test_project_claim_without_evidence_rejected():
    rec = load("project_auth_architecture_v1.json")
    rec["evidence"] = []
    assert_invalid(rehash(rec), "evidence")


def test_version_one_cannot_supersede():
    rec = load("project_auth_architecture_v1.json")
    rec["supersedes"] = rec["version_id"].replace("ver_", "ver_")[:-1] + "0"
    assert_invalid(rehash(rec), "supersedes")


def test_later_version_must_supersede():
    rec = load("project_test_command_v2.json")
    rec["supersedes"] = None
    assert_invalid(rehash(rec), "supersedes")


def test_user_approved_needs_user_evidence():
    rec = load("project_test_command_v2.json")
    rec["evidence"] = [e for e in rec["evidence"] if e["kind"] == "test"]
    assert_invalid(rehash(rec), "evidence")


def test_episodic_category_not_allowed_in_project_memory():
    rec = load("project_auth_architecture_v1.json")
    rec["category"] = "failed_attempt"
    assert_invalid(rehash(rec), "category")


def test_command_needs_test_or_user_support():
    rec = load("project_test_command_v1.json")
    rec["support"] = "repository_evidence"
    assert_invalid(rehash(rec), "support")


def test_decision_needs_user_approval():
    rec = load("project_auth_architecture_v1.json")
    rec["category"] = "decision"
    assert_invalid(rehash(rec), "support")


def test_test_validated_needs_a_passing_test():
    rec = load("project_test_command_v1.json")
    rec["evidence"][0]["outcome"] = "fail"
    assert_invalid(rehash(rec), "evidence")


def test_architecture_may_rest_on_repository_evidence():
    assert load("project_auth_architecture_v1.json")["support"] == "repository_evidence"
    assert validate_record(load("project_auth_architecture_v1.json")) == []


def test_unchanged_content_keeps_hash_across_versions():
    rec = load("project_auth_architecture_v1.json")
    v2 = copy.deepcopy(rec)
    v2.update(version=2, supersedes=rec["version_id"], version_id="ver_" + "1" * 32,
              verified_at_utc="2026-12-01T00:00:00Z", status="uncertain")
    assert compute_content_hash(v2) == rec["content_hash"]
    v2["claim"] += " (changed)"
    assert compute_content_hash(v2) != rec["content_hash"]


def test_daily_log_hash_covers_timestamps():
    rec = load("daily_log_2026-11-09_001.json")
    before = rec["content_hash"]
    rec["recorded_at_utc"] = "2026-11-09T23:59:59Z"
    assert compute_content_hash(rec) != before


def test_v2_supersedes_v1():
    v1, v2 = load("project_test_command_v1.json"), load("project_test_command_v2.json")
    assert v2["memory_id"] == v1["memory_id"]
    assert v2["supersedes"] == v1["version_id"]
    assert v1["status"] == "superseded" and v2["status"] == "active"


# ---- Daily Log --------------------------------------------------------------

def test_daily_log_hash_chain():
    e1, e2 = load("daily_log_2026-11-09_001.json"), load("daily_log_2026-11-09_002.json")
    assert e1["prev_entry_hash"] is None
    assert e2["prev_entry_hash"] == e1["content_hash"]


def test_daily_log_later_entry_needs_prev_hash():
    rec = load("daily_log_2026-11-09_002.json")
    rec["prev_entry_hash"] = None
    assert_invalid(rehash(rec), "prev_entry_hash")


def test_daily_log_only_appends():
    rec = load("daily_log_2026-11-09_001.json")
    rec["provenance"]["operation"] = "update"
    assert_invalid(rec, "provenance/operation")


# ---- Session Memory ---------------------------------------------------------

def test_done_step_needs_evidence():
    rec = load("session_T4_v2.json")
    rec["progress"][0]["evidence_ids"] = []
    assert_invalid(rehash(rec), "progress/0")


def test_failed_attempt_needs_evidence():
    rec = load("session_T4_v2.json")
    rec["failed_attempts"][0]["evidence_ids"] = []
    assert_invalid(rehash(rec), "failed_attempts/0")


def test_dangling_evidence_id_rejected():
    rec = load("session_T4_v2.json")
    rec["evidence"] = rec["evidence"][:1]
    assert_invalid(rehash(rec), "is not in the record's evidence list")


def test_paused_session_needs_next_step():
    rec = load("session_T4_v2.json")
    rec["next_steps"] = []
    assert_invalid(rehash(rec), "next_steps")


def test_completed_session_may_have_no_next_step():
    rec = load("session_T4_v2.json")
    rec["status"] = "completed"
    rec["next_steps"] = []
    assert validate_record(rehash(rec)) == []
