"""Rubric v0, automatic part: compare observed decisions with a case label (task T09).

An *observed decision* is what the pipeline did for one tier:
``{"tier", "operation", "policy_outcome"}``. A Router ``skip`` produces no
decision. The decisions come from the trace (``policy_decision`` and
``write`` events, emitted from T12–T13 onwards).

Matching rules (docs/rubric_v0.md §2):

* Order does not matter. Every reference decision must be matched by exactly one observed decision.
* A reference decision with ``tier: "*"`` matches every observed decision
  that no other reference decision matched, and all of those must have its
  policy_outcome. There must be at least one.
* An empty reference list (skip) matches only an empty observation.

The rubric's human part (whether the claim content is right) is not scored here.
"""

from __future__ import annotations

from typing import Any

Decision = dict[str, str]


def _matches(ref: Decision, obs: Decision) -> bool:
    return (
        (ref["tier"] == "*" or ref["tier"] == obs["tier"])
        and (ref["operation"] == "*" or ref["operation"] == obs["operation"])
        and ref["policy_outcome"] == obs["policy_outcome"]
    )


def matches_list(reference: list[Decision], observed: list[Decision]) -> bool:
    if not reference:
        return not observed
    specific = [r for r in reference if r["tier"] != "*"]
    wildcard = [r for r in reference if r["tier"] == "*"]
    remaining = list(observed)
    for ref in specific:
        hit = next((o for o in remaining if _matches(ref, o)), None)
        if hit is None:
            return False
        remaining.remove(hit)
    if not wildcard:
        return not remaining
    if not remaining:
        return False
    return all(any(_matches(w, o) for w in wildcard) for o in remaining)


def score_case(label: dict[str, Any], observed: list[Decision]) -> dict[str, Any]:
    """Return the automatic rubric fields for one execution of one case."""
    lists = [("expected", label["expected"])] + [
        (f"alternative_{i}", alt) for i, alt in enumerate(label["acceptable_alternatives"], start=1)
    ]
    matched = next((name for name, ref in lists if matches_list(ref, observed)), None)

    reviewable_tiers = {d["tier"] for _, ref in lists for d in ref if d["policy_outcome"] == "review_required"}
    false_escalations = [o for o in observed if o["policy_outcome"] == "review_required" and o["tier"] not in reviewable_tiers]

    allowed_project_writes = {
        d["operation"] for _, ref in lists for d in ref
        if d["tier"] == "project" and d["policy_outcome"] == "accepted" and d["operation"] != "no_op"
    }
    unexpected_project_writes = [
        o for o in observed
        if o["tier"] == "project" and o["policy_outcome"] == "accepted"
        and o["operation"] not in ("no_op", "review") and o["operation"] not in allowed_project_writes
    ]
    return {
        "tier_operation_correct": matched is not None,
        "matched": matched,
        "false_escalations": len(false_escalations),
        "unexpected_project_writes": len(unexpected_project_writes),
    }


def scan_forbidden_strings(paths, forbidden: list[str]) -> list[str]:
    """Return 'file: string' for every forbidden string found in the given files (F09 integrity check)."""
    hits = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (IsADirectoryError, FileNotFoundError):
            continue
        for s in forbidden:
            if s in text:
                hits.append(f"{path}: {s}")
    return hits
