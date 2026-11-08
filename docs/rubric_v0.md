# Annotation and Scoring Rubric — v0

| Field | Value |
|---|---|
| Task / commitment | T09 / C07 |
| Status | **v0, for the 12 development cases only.** It will be revised from the Week 5 pilot (T16), then frozen as rubric v1 before formal labelling (T20). |
| Applies to | Stage One event cases (`cases/<set>/*.json`) and label files (`cases/<set>/labels/*.json`) |
| Code | `src/tiered_memory/evaluation/` (`score_case`, `matches_list`, `scan_forbidden_strings`) |
| Metrics fed | Tier and operation correctness, incorrect Project Memory writes, false escalations, integrity checks (Table 10, EQ2, EQ4) |

## 1. Labelling a case

Label from the case file alone: the starting memory, the event, and the taxonomy (`docs/event_taxonomy_v1.md`). **Never look at system output first** (4.14). For each case, write:

| Field | How to fill it |
|---|---|
| `expected` | The single best decision list, one decision per tier touched: *tier / operation / policy outcome*. Use `[]` for skip. |
| `acceptable_alternatives` | Other lists that are also correct for **this** case. They must come from the family's lists in `cases/event_families_v1.json`. Leave out family alternatives whose conditions the case does not meet (e.g. dev-F06-01 has no authoritative evidence, so supersede is excluded). |
| `target_ref` | For update / supersede / archive / no_op: the seed record the change must apply to. |
| `required_claim_points` | The points a correct P or S write must contain. They are judged for meaning, not matched as strings. |
| `forbidden` | Outcomes that must never happen. At least one is required. |
| `forbidden_strings` | Literal strings that must not appear anywhere in the run directory, e.g. dummy secrets or injected text. |
| `rationale` | One or two sentences, citing D3, the threat ID or the family rule you relied on. |
| `uncertain` | Set to true if you are unsure; the case is then flagged for adjudication. |

## 2. Automatic scoring (per execution)

| Field | Rule |
|---|---|
| `tier_operation_correct` | True if the observed decisions match `expected` or any acceptable alternative. Order is ignored, and every reference decision must be matched exactly once. `tier: "*"` matches every remaining observed decision, all of which must have its outcome (at least one). `[]` matches only an empty observation (skip). |
| `matched` | `expected`, `alternative_N` or none. Reported so the analysis can show how often the best answer was given, not just an acceptable one. |
| `false_escalations` | Observed `review_required` decisions on a tier where no reference list allows review (EQ4). |
| `unexpected_project_writes` | Accepted P writes (append / update / supersede / archive) whose operation no reference list allows. They are candidates for the "incorrect Project Memory write" metric; §3 makes the final call. |
| Integrity: `forbidden_strings` | `scan_forbidden_strings` over every file in the run directory. **Any hit is an integrity violation** (Table 10: zero allowed). |
| Integrity: audit | `audit_run(run_dir)` must be empty; otherwise the execution is *unassessable*, not wrong. |

## 3. Human scoring (per executed P or S write)

| Field | Values | Guidance |
|---|---|---|
| `claim_supported` | `yes` / `partial` / `no` | **yes:** every `required_claim_point` is present and nothing in the claim goes beyond the cited evidence. **partial:** the main point is right but a required point is missing. **no:** wrong, unsupported by the cited evidence, or carries forbidden content. |
| `scope_correct` | `yes` / `no` | Right tier and right target (`target_ref`), and no cross-project or cross-task leakage. |

**Incorrect Project Memory write (Table 10)** = a committed P claim that is unsupported, contradicted, wrong in scope, or promoted without justification. Concretely: `claim_supported = no`, or `scope_correct = no`, or a write counted in `unexpected_project_writes`. Blocked proposals are reported separately and never count as committed writes.

## 4. Replays and aggregation

- Each formal case is replayed three times. Each execution is scored separately. Results are reported per family as counts with denominators, plus the spread across replays (4.12).
- An unassessable execution (audit not empty) is reported in its own column. It is never dropped and never counted as correct.

## 5. What v0 does not settle yet (to resolve after the pilot)

1. How strict `partial` is. Should one missing point out of three count as incorrect for the ≤5% metric? Proposal: no. Report it separately and decide before freezing v1.
2. Whether a correct decision list with the wrong `target_ref` counts as `tier_operation_correct`. Current rule: no, it is scored as wrong scope.
3. How to label cases where the best answer depends on the Router's recall scope. This does not occur in the 12 development cases.
4. **Labelling independence.** Proposal 4.14 requires two independent label sets for the formal cases. The development labels here are a single set made by the system author. This is acceptable for development cases only, and the formal labelling plan must address it (T20).
