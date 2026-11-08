"""Agreement between two independent label sets, reported before adjudication (proposal 4.12, 4.14).

Measures per case:

* ``expected_agree``: both labellers chose the same best decision list.
* ``answer_sets_overlap``: at least one list is acceptable to both (they
  would score some system outputs the same way).
* ``answer_sets_equal``: the full sets of acceptable lists are identical.
* ``target_agree``: same ``target_ref``.

Cohen's kappa is computed on the ``expected`` list, treated as a nominal
category. With 12 cases it is descriptive only.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any


def _key(decisions: list[dict[str, str]]) -> str:
    return json.dumps(sorted(json.dumps(d, sort_keys=True) for d in decisions))


def _unkey(key: str) -> list[dict[str, str]]:
    return [json.loads(x) for x in json.loads(key)]


def _answer_set(label: dict[str, Any]) -> set[str]:
    return {_key(label["expected"]), *(_key(a) for a in label["acceptable_alternatives"])}


def short(decisions: list[dict[str, str]]) -> str:
    """'L append + P review?' style text for tables."""
    if not decisions:
        return "skip"
    tier = {"daily_log": "L", "session": "S", "project": "P", "*": "*"}
    out = {"accepted": "", "review_required": "?", "blocked": "✗"}
    parts = sorted(f"{tier[d['tier']]} {d['operation']}{out[d['policy_outcome']]}" for d in decisions)
    return " + ".join(parts)


def cohens_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected == 1:
        return 1.0 if observed == 1 else None
    return (observed - expected) / (1 - expected)


def compare(labels_a: dict[str, Any], labels_b: dict[str, Any]) -> dict[str, Any]:
    la, lb = labels_a["labels"], labels_b["labels"]
    cases = sorted(set(la) | set(lb))
    rows = []
    for cid in cases:
        a, b = la.get(cid), lb.get(cid)
        if a is None or b is None:
            rows.append({"case_id": cid, "missing_in": "a" if a is None else "b"})
            continue
        sa, sb = _answer_set(a), _answer_set(b)
        rows.append({
            "case_id": cid,
            "a_expected": short(a["expected"]),
            "b_expected": short(b["expected"]),
            "expected_agree": _key(a["expected"]) == _key(b["expected"]),
            "answer_sets_overlap": bool(sa & sb),
            "answer_sets_equal": sa == sb,
            "a_only": sorted(short(_unkey(k)) for k in sa - sb),
            "b_only": sorted(short(_unkey(k)) for k in sb - sa),
            "target_agree": a.get("target_ref") == b.get("target_ref"),
            "uncertain": bool(a.get("uncertain")) or bool(b.get("uncertain")),
        })
    complete = [r for r in rows if "missing_in" not in r]
    n = len(complete)
    kappa = cohens_kappa(
        [_key(la[r["case_id"]]["expected"]) for r in complete],
        [_key(lb[r["case_id"]]["expected"]) for r in complete],
    )
    return {
        "labeler_a": labels_a["labeler"], "labeler_b": labels_b["labeler"],
        "cases": n,
        "expected_agree": sum(r["expected_agree"] for r in complete),
        "answer_sets_overlap": sum(r["answer_sets_overlap"] for r in complete),
        "answer_sets_equal": sum(r["answer_sets_equal"] for r in complete),
        "target_agree": sum(r["target_agree"] for r in complete),
        "kappa_expected": kappa,
        "rows": rows,
    }


def to_markdown(result: dict[str, Any]) -> str:
    n = result["cases"]
    k = result["kappa_expected"]
    lines = [
        f"| Measure | {result['labeler_a']} vs {result['labeler_b']} |",
        "|---|---|",
        f"| Same best answer (`expected`) | {result['expected_agree']}/{n} |",
        f"| At least one shared acceptable answer | {result['answer_sets_overlap']}/{n} |",
        f"| Identical acceptable-answer sets | {result['answer_sets_equal']}/{n} |",
        f"| Same target record | {result['target_agree']}/{n} |",
        f"| Cohen's κ on `expected` (descriptive, n={n}) | {'n/a' if k is None else f'{k:.2f}'} |",
        "",
        "| Case | A expected | B expected | Best agree | Overlap | Only A accepts | Only B accepts | Target agree | Uncertain |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    yn = lambda v: "yes" if v else "**no**"
    for r in result["rows"]:
        if "missing_in" in r:
            lines.append(f"| {r['case_id']} | missing in {r['missing_in']} | | | | | | | |")
            continue
        lines.append(
            f"| {r['case_id']} | {r['a_expected']} | {r['b_expected']} | {yn(r['expected_agree'])} | "
            f"{yn(r['answer_sets_overlap'])} | {'; '.join(r['a_only']) or '—'} | {'; '.join(r['b_only']) or '—'} | "
            f"{yn(r['target_agree'])} | {'yes' if r['uncertain'] else ''} |"
        )
    lines.append("")
    lines.append("Notation: L = Daily Log, S = Session, P = Project; `?` = review_required, `✗` = blocked; `*` = any tier.")
    return "\n".join(lines) + "\n"
