"""T09 acceptance: 12 development cases cover all 10 families; labels and rubric v0 are consistent."""

import json
from collections import Counter

import pytest

from tiered_memory.evaluation import (
    load_cases, load_labels, matches_list, scan_forbidden_strings, score_case, seed_case, session_id_for,
)
from tiered_memory.evaluation.cases import CASES_DIR
from tiered_memory.hooks.dedup import compute_dedup_key, dedup_key_for_case_event
from tiered_memory.tracing import Run, audit_run

CASES = load_cases("dev")
LABELS = load_labels(CASES_DIR / "dev" / "labels" / "rubric-v0_claude-a.json")["labels"]
TAXONOMY = {f["id"]: f for f in json.loads((CASES_DIR / "event_families_v1.json").read_text())["families"]}
FIXTURE = json.loads((CASES_DIR.parent / "fixtures" / "manifest.json").read_text())["fixtures"][0]


def canon(decisions):
    return sorted(json.dumps(d, sort_keys=True) for d in decisions)


def test_twelve_cases_cover_all_ten_families():
    counts = Counter(c["family"] for c in CASES)
    assert len(CASES) == 12
    assert set(counts) == set(TAXONOMY)
    assert counts["F01"] == counts["F06"] == 2
    assert all(c["set"] == "dev" for c in CASES)


def test_cases_use_the_fixture_baseline_commit():
    for c in CASES:
        assert c["fixture"] == {"path": FIXTURE["path"], "initial_commit": FIXTURE["initial_commit"]}


def test_hook_event_type_is_typical_for_the_family():
    for c in CASES:
        assert c["event"]["hook_event_type"] in TAXONOMY[c["family"]]["typical_hook_events"], c["case_id"]


def test_every_case_has_exactly_one_label():
    assert set(LABELS) == {c["case_id"] for c in CASES}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_label_lists_come_from_the_family(case):
    family = TAXONOMY[case["family"]]
    allowed = [canon(family["expected"])] + [canon(a) for a in family["acceptable_alternatives"]]
    label = LABELS[case["case_id"]]
    for decisions in [label["expected"], *label["acceptable_alternatives"]]:
        assert canon(decisions) in allowed, f"{case['case_id']}: {decisions} is not a family-level answer"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_target_ref_names_a_seed(case):
    target = LABELS[case["case_id"]].get("target_ref")
    if target is not None:
        assert target in {s["ref"] for s in case["starting_memory"]}
    ops = {d["operation"] for d in LABELS[case["case_id"]]["expected"]}
    if ops & {"update", "supersede", "archive", "no_op", "review"} and case["family"] not in ("F09",):
        assert target is not None, f"{case['case_id']} changes a record but names no target"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_case_seeds_and_audits_cleanly(case, tmp_path):
    run = Run.start(tmp_path, project_id="prj_taskservice", case_id=case["case_id"], code={"commit": None, "dirty": None})
    refs = seed_case(case, run)
    run.finish()
    assert set(refs) == {s["ref"] for s in case["starting_memory"]}
    assert audit_run(run.dir) == []


def test_repeated_event_seed_shares_the_event_dedup_key(tmp_path):
    case = next(c for c in CASES if c["family"] == "F05")
    run = Run.start(tmp_path, project_id="prj_taskservice", code={"commit": None, "dirty": None})
    refs = seed_case(case, run)
    run.finish()
    assert refs["dl_first"]["dedup_key"] == dedup_key_for_case_event(case["event"], session_id_for(case))


def test_dedup_key_ignores_time_but_not_content():
    base = dict(hook_event_type="test_run", task_id="tsk_T1", session_id="ses_" + "1" * 32,
                source_kind="test", source_locator="tests/", content="22 passed")
    assert compute_dedup_key(**base) == compute_dedup_key(**base)
    assert compute_dedup_key(**base) != compute_dedup_key(**{**base, "content": "21 passed"})
    assert compute_dedup_key(**base) != compute_dedup_key(**{**base, "session_id": "ses_" + "2" * 32})


def test_secret_case_contains_its_forbidden_strings():
    case = next(c for c in CASES if c["family"] == "F09")
    for s in LABELS[case["case_id"]]["forbidden_strings"]:
        assert s in case["event"]["content"]


def test_no_case_contains_a_realistic_secret_format_outside_f09():
    for c in CASES:
        if c["family"] != "F09":
            assert "AKIA" not in json.dumps(c)


# ---- scorer -------------------------------------------------------------------

L = lambda tier, op, out="accepted": {"tier": tier, "operation": op, "policy_outcome": out}


def test_matching_ignores_order():
    ref = [L("daily_log", "append"), L("project", "append")]
    assert matches_list(ref, [L("project", "append"), L("daily_log", "append")])
    assert not matches_list(ref, [L("daily_log", "append")])
    assert not matches_list(ref, [L("daily_log", "append"), L("project", "append"), L("session", "update")])


def test_skip_matches_only_nothing():
    assert matches_list([], [])
    assert not matches_list([], [L("daily_log", "append")])


def test_wildcard_block():
    ref = [{"tier": "*", "operation": "*", "policy_outcome": "blocked"}]
    assert matches_list(ref, [L("project", "append", "blocked"), L("session", "update", "blocked")])
    assert not matches_list(ref, [L("project", "append", "blocked"), L("daily_log", "append")])
    assert not matches_list(ref, [])
    alt = ref + [L("daily_log", "append")]
    assert matches_list(alt, [L("project", "append", "blocked"), L("daily_log", "append")])


def test_score_reports_best_or_alternative():
    label = LABELS["dev-F07-01"]
    best = score_case(label, [L("daily_log", "append"), L("project", "supersede")])
    alt = score_case(label, [L("daily_log", "append"), L("project", "update")])
    wrong = score_case(label, [L("daily_log", "append")])
    assert (best["tier_operation_correct"], best["matched"]) == (True, "expected")
    assert (alt["tier_operation_correct"], alt["matched"]) == (True, "alternative_1")
    assert (wrong["tier_operation_correct"], wrong["matched"]) == (False, None)


def test_false_escalation_counted():
    s = score_case(LABELS["dev-F02-01"], [L("daily_log", "append"), L("session", "update", "review_required")])
    assert s["false_escalations"] == 1 and not s["tier_operation_correct"]
    ok = score_case(LABELS["dev-F06-01"], [L("daily_log", "append"), L("project", "review", "review_required")])
    assert ok["false_escalations"] == 0 and ok["tier_operation_correct"]


def test_unexpected_project_write_flagged():
    s = score_case(LABELS["dev-F04-01"], [L("daily_log", "append"), L("project", "append")])
    assert s["unexpected_project_writes"] == 1
    s = score_case(LABELS["dev-F06-01"], [L("daily_log", "append"), L("project", "supersede")])
    assert s["unexpected_project_writes"] == 1, "supersede is not allowed without authoritative evidence"


def test_forbidden_string_scan(tmp_path):
    (tmp_path / "a.jsonl").write_text("clean\n")
    (tmp_path / "b.json").write_text('{"x": "AKIAFIXTUREDUMMY0000"}')
    hits = scan_forbidden_strings(sorted(tmp_path.iterdir()), ["AKIAFIXTUREDUMMY0000"])
    assert len(hits) == 1 and "b.json" in hits[0]


# ---- agreement ----------------------------------------------------------------

def test_agreement_with_itself_is_perfect():
    from tiered_memory.evaluation.agreement import compare
    labels = load_labels(CASES_DIR / "dev" / "labels" / "rubric-v0_claude-a.json")
    r = compare(labels, labels)
    assert r["expected_agree"] == r["answer_sets_equal"] == r["cases"] == 12
    assert r["kappa_expected"] == 1.0


def test_agreement_detects_a_disagreement():
    import copy
    from tiered_memory.evaluation.agreement import compare, to_markdown
    a = load_labels(CASES_DIR / "dev" / "labels" / "rubric-v0_claude-a.json")
    b = copy.deepcopy(a)
    b["labeler"] = "other"
    b["labels"]["dev-F06-01"]["expected"] = [L("daily_log", "append"), L("project", "supersede")]
    b["labels"]["dev-F06-01"]["acceptable_alternatives"] = []
    r = compare(a, b)
    assert r["expected_agree"] == 11 and r["answer_sets_overlap"] == 11
    assert r["kappa_expected"] < 1.0
    row = next(x for x in r["rows"] if x["case_id"] == "dev-F06-01")
    assert row["a_only"] == ["L append + P review?"] and row["b_only"] == ["L append + P supersede"]
    assert "**no**" in to_markdown(r)


def test_kappa_known_value():
    from tiered_memory.evaluation.agreement import cohens_kappa
    # 2x2 example: po = 0.7, pe = 0.5 -> kappa = 0.4
    a = ["x"] * 5 + ["y"] * 5
    b = ["x"] * 4 + ["y"] + ["x"] * 2 + ["y"] * 3
    assert abs(cohens_kappa(a, b) - 0.4) < 1e-9


@pytest.mark.parametrize("name", ["rubric-v0_claude-a.json", "rubric-v0_claude-b.json"])
def test_every_label_set_is_complete_and_family_consistent(name):
    data = load_labels(CASES_DIR / "dev" / "labels" / name)
    assert data["labeler_kind"] in ("human", "ai") and data["labeler_note"]
    assert set(data["labels"]) == {c["case_id"] for c in CASES}
    for case in CASES:
        family = TAXONOMY[case["family"]]
        allowed = [canon(family["expected"])] + [canon(a) for a in family["acceptable_alternatives"]]
        label = data["labels"][case["case_id"]]
        for decisions in [label["expected"], *label["acceptable_alternatives"]]:
            assert canon(decisions) in allowed, (name, case["case_id"])
