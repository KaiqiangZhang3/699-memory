"""T04 acceptance: each family has a definition and expected tier/operation, consistent with schemas v1."""

import json
from pathlib import Path

import pytest

from tiered_memory.schemas import SCHEMA_DIR

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = json.loads((ROOT / "cases" / "event_families_v1.json").read_text())
COMMON = json.loads((SCHEMA_DIR / "common.schema.json").read_text())["$defs"]
FAMILIES = TAXONOMY["families"]

TIERS = set(COMMON["tier"]["enum"])
OPERATIONS = set(COMMON["operation"]["enum"])
OUTCOMES = set(COMMON["policy_outcome"]["enum"])

APPENDIX_D_ORDER = [
    "stable_project_fact", "task_completion_validation", "unfinished_session_state", "failed_attempt",
    "repeated_event", "conflicting_claim", "changed_stale_reference", "explicit_user_correction",
    "synthetic_sensitive_string", "irrelevant_event",
]


def decision_lists(family):
    return [family["expected"], *family["acceptable_alternatives"]]


def test_ten_families_in_appendix_d_order():
    assert [f["id"] for f in FAMILIES] == COMMON["event_family"]["enum"]
    assert [f["key"] for f in FAMILIES] == APPENDIX_D_ORDER


def test_hook_event_types_match_schema():
    assert TAXONOMY["hook_event_types"] == COMMON["hook_event_type"]["enum"]


@pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f["id"])
def test_family_is_fully_specified(family):
    for field in ("name", "tests", "definition"):
        assert family[field].strip()
    assert family["forbidden"], "every family names at least one forbidden outcome"
    assert family["primary_metrics"]
    assert set(family["typical_hook_events"]) <= set(TAXONOMY["hook_event_types"])


@pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f["id"])
def test_decisions_use_schema_enums(family):
    for decisions in decision_lists(family):
        tiers = [d["tier"] for d in decisions]
        assert len(tiers) == len(set(tiers)), "one decision per tier"
        for d in decisions:
            assert d["tier"] in TIERS | {"*"}
            assert d["operation"] in OPERATIONS | {"*"}
            assert d["policy_outcome"] in OUTCOMES


@pytest.mark.parametrize("family", FAMILIES, ids=lambda f: f["id"])
def test_daily_log_never_rewritten(family):
    for decisions in decision_lists(family):
        for d in decisions:
            if d["tier"] == "daily_log":
                assert d["operation"] in {"append", "no_op"}


def test_only_some_families_change_project_memory():
    changing = {"append", "update", "supersede", "archive"}
    allowed = {"F01", "F02", "F06", "F07", "F08"}
    for family in FAMILIES:
        touches = any(
            d["tier"] == "project" and d["operation"] in changing and d["policy_outcome"] == "accepted"
            for decisions in decision_lists(family) for d in decisions
        )
        if touches:
            assert family["id"] in allowed, family["id"]


def test_irrelevant_event_is_skip():
    f10 = FAMILIES[9]
    assert f10["expected"] == [] and f10["acceptable_alternatives"] == []


def test_sensitive_string_blocks_every_write():
    f09 = FAMILIES[8]
    assert f09["expected"] == [{"tier": "*", "operation": "*", "policy_outcome": "blocked"}]
    for decisions in decision_lists(f09):
        assert {"tier": "*", "operation": "*", "policy_outcome": "blocked"} in decisions


def test_repeated_event_is_no_op():
    f05 = FAMILIES[4]
    for decisions in decision_lists(f05):
        assert all(d["operation"] == "no_op" for d in decisions)
