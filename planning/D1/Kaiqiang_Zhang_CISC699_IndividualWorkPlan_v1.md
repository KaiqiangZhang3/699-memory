# Individual Research Work Plan — CISC 699 Capstone II

| Field | Value |
|---|---|
| Title | Individual Research Work Plan: Automated Three-Tier External Memory for Long-Horizon Coding Agents |
| Student | Kaiqiang Zhang |
| Partner | Ruifeng Cui |
| Project / topic | Design and Evaluation of an Automated Three-Tier External Memory System for Long-Horizon Coding Agents — T3 Agent Memory |
| Proposal version | GRAD 695 Final Proposal Report, submitted September 26, 2026 |
| Plan version / date | v1 — Week 2, calendar date [TO CONFIRM] |
| Individual responsibility | Memory core and automated lifecycle; Stage One execution and analysis; integration of my own D1–D4 packages (see §6; split agreed, DEC-02) |
| Companion schedule | `Kaiqiang_Zhang_CISC699_13WeekSchedule_v1` — uses the same task IDs (T01–T32), commitment IDs (C01–C12) and weeks |

---

## 1. Execution Objective and Scope (carried forward)

**Objective (Proposal 1.5).** Design and evaluate a bounded prototype for automated external-memory management.

**Research question.** How can event-driven and scheduled lifecycle automation reduce manual memory-management work for coding agents while preserving memory integrity and software-task performance?

**Supporting questions and evaluation questions.**
- RQ1: how to separate the three tiers.
- RQ2: automation versus effort and quality.
- RQ3: task success and errors at acceptable cost.
- These are answered through EQ1–EQ4 (Proposal 4.3).

**Comparison (Proposal 4.4).**
- **Condition A** is a semi-manual three-tier baseline driven by an operator checklist.
- **Condition B** is the automated lifecycle: Hooks → Candidate Queue → AI Curator → Memory Router → Policy Gate → versioned write → Resume Pack, plus Cron maintenance.
- Both conditions use the same schema, validators, fixtures, tasks, tests, recall limit, model and resource ceiling.

**Evaluation scale.**
- Stage One: 60 formal event cases (10 families × 6) × 3 replays, plus 12 separate development cases.
- Stage Two: six connected coding tasks, with three paired sequence runs per condition (A/B, B/A, A/B).

**In scope.** One local Python repository, Markdown/JSON memory, one pinned model configuration, a lightweight queue and scheduler, and synthetic data.

**Out of scope (Proposal 1.9–1.10).** Model training, enterprise identity, and universal cross-agent memory.

**Optional work (Proposal 5.2).** Additional repositories, a no-memory baseline, a UI, learned routing and long-duration deployment. These start only after the primary study is complete.

**Not repeated from GRAD 695.** Problem definition, literature review, architecture rationale and evaluation design. These are inputs to this plan.

## 2. Work Packages and Task Register

The eight work packages follow Proposal 5.2. The full task register, with predecessors and hours, is in the W01 record. A summary:

| WP | Proposal package | Tasks | Commitments | Weeks |
|---|---|---|---|---|
| WP1 | Schemas, requirements, fixtures | T01–T06 | C01, C02 | 1–3 |
| WP2 | Storage and deterministic infrastructure | T07, T08, T10 | C03, C04 | 3–4 |
| WP3 | AI interpretation, routing, policy, maintenance, recall | T11–T14, T19 | C05, C06 | 4–5, 7 |
| WP4 | Evaluation cases and labels | T09, T15, T18, T20, T21 | C07, C08 | 3, 5–7 |
| WP5 | Pilot and protocol freeze | T16, T22, T23 | C09 | 5–8 |
| WP6 | Formal collection | T24, T25 | C10 | 9–10 |
| WP7 | Analysis | T26, T27 | C11 | 10 |
| WP8 | Documentation, report, presentation, package | T17, T28–T31 | C12 | 6, 10–13 |
| — | Weekly records | T32 | — | 1–13 |

## 3. Milestones

| Milestone (Proposal 5.3) | Week | Output | Acceptance criterion | Depends on |
|---|---|---|---|---|
| M-A Approved design baseline | 2 | `design-v1` tag, schemas, taxonomy, threat model; D1 submitted | Sample records validate; baseline tests pass | T01–T04 |
| M-B Tested three-tier store | 3 | Stores, versioned writer, traces | Snapshots match recorded writes | M-A |
| M-C Integrated automated lifecycle (preliminary) | 6 | End-to-end Condition B on dev cases; **D2 + demo** | No direct Hook → memory write; pilot metrics regenerate | M-B |
| M-C′ Lifecycle complete incl. maintenance | 7 | Cron + controlled clock | Maintenance passes through the same Policy Gate | M-C |
| M-D Frozen evaluation protocol | 8 | `protocol-v1`, freeze manifest, two label sets | IDs, timers, snapshots and usage reconcile in the pilot | M-C′, labels, Stage Two fixture |
| M-E Complete formal dataset | 9–10 | Run ledger, raw logs, snapshots | All attempts and failures kept or documented | M-D |
| M-F Audited analysis | 10 | **D3** memo, scripts, figures | Every result has a denominator, a protocol version and a raw-evidence link | M-E |
| M-G Reproducible final artifact | 13 | **D4**: final report, tagged software, archive, slides | Passes the Proposal 5.12 checklist (§12) | M-F |

## 4. Resources and Access

| Resource (Proposal Table 13) | Use | Status |
|---|---|---|
| Python, pytest | Prototype, tests | Available locally — versions [TO CONFIRM] in W01 |
| Git | Versioning, tags, hashes | Available locally |
| Markdown / JSON / JSONL | Memory tiers, traces | No dependency |
| Pinned model interface | Curator; limited Router interpretation | **Pending** — provider and version [TO CONFIRM], to be pinned before the pilot in Week 5 |
| Model budget | Curator/Router calls in Stage One and Stage Two | **Pending** — ceiling [TO CONFIRM]; actual usage reported, and unavailable usage marked as missing, not zero |
| Coding agent for Stage Two | Running the six connected tasks | **Pending** — agent and version [TO CONFIRM] (DEC-04) |
| Lightweight queue and scheduler | Hooks/Cron with a controlled clock | Standard library or a small package, chosen by Week 4 |
| Fixture task service | Stage Two | Built locally by the partner (T06, T21) |
| Instructor | Label and comparison review; D-package feedback | Assumed per course |

## 5. Technical Environment

- One local Python project under Git.
- Pytest for unit, integration, acceptance and regression tests.
- JSONL for events and decisions; Markdown/JSON for memory.
- UTC timestamps and monotonic timers.
- A controlled clock for maintenance checkpoints, plus a separate scheduler smoke test.

Planned repository layout:

```
src/{memory,hooks,queue,curator,router,policy,resume,maintenance}
tests/
schemas/
fixtures/{pilot,formal}
cases/{dev,formal}
protocol/
runs/<run_id>/
analysis/
records/W01..W13/
docs/
```

Credentials stay outside the repository and outside any folder the agent can read. Protected hidden tests are stored separately from the agent workspace.

## 6. Individual and Partner Responsibilities (agreed, DEC-02)

| Area | Kaiqiang (individually verifiable output) | Ruifeng | Handoff |
|---|---|---|---|
| Design | Schemas, requirements, threat model | Reviews | `design-v1` (Week 2) |
| Memory core and lifecycle | Stores, writer, traces, Hooks, Queue, Curator, Router, Policy Gate, Resume Pack, Cron | Code review | Release tags |
| Stage Two fixture | Reviews | Task service, six tasks, hidden tests | Fixture tag (Week 7) |
| Condition A | Reviews that A invokes the same functions | Operator checklist, human-action logger | Checklist v1 (Week 5) |
| Event cases | Co-authors 60 formal + 12 dev cases; **independent label set 1** | Co-authors; **independent label set 2** | Adjudication meeting (Week 7) |
| Formal runs | Stage One replays; one operator role in Stage Two | Other operator role in Stage Two | Run ledger |
| Analysis | Stage One analysis; integration of the D3 memo | Stage Two analysis | Shared scripts in `analysis/` |
| Reports and presentations | My own D1–D4, report and defense | Their own | — |

Neither student claims the other's components as their own work. Shared work, such as the joint labels and the paired runs, is identified as shared in every package.

## 7. Risks

| Risk (Proposal Table 14 + course) | P | I | Trigger | Mitigation | Contingency |
|---|---|---|---|---|---|
| R1 Model output varies | High | Med | Different routing for the same fixture | Pin the configuration; repeat cases; keep traces | Deterministic rules for safety-critical checks |
| R2 Scope exceeds the term | Med | High | Core modules unfinished by Week 7 | Protect the minimum prototype | Drop optional work; DEC-06 minimum path |
| R3 Ambiguous labels | Med | Med | Frequent disagreement | Allow acceptable outcome sets; freeze the rubric | Report unresolved cases separately |
| R4 Baseline not comparable | Low | High | Schema, model or limits differ between A and B | One shared implementation; audit run manifests | Rerun the affected pair under a new version |
| R5 Incomplete logging | Med | High | Missing event→write or recall→task link | Pilot reconciliation before the freeze | Mark metrics unassessable; repair and rerun, keeping the original record |
| R6 Provider cost or access changes | Med | Med | Budget ceiling hit or model unavailable | Confirm access before Week 5 | Pinned alternative chosen before the freeze; documented amendment |
| R7 Tasks too easy | Med | Med | Both conditions reach ceiling in the pilot | Calibrate on pilot tasks only | Keep task-success guardrails; report the ceiling |
| R8 Sensitive content in logs | Low | High | Scanner flags non-fixture content | Dummy secrets; local fixtures only | Redact before sharing |
| R9 **Compressed timeline** (13 weeks instead of 14) | Med | High | Freeze not reached by the end of Week 8 | Week 8 kept light as a buffer | Collection overflows into early Week 10 (DEC-06) |
| R10 **Partner dependency** | Med | High | Stage Two fixture not ready by Week 7 | Weekly sync; fixture skeleton by Week 3 | Stage One proceeds independently; Stage Two scope decided with the instructor |

## 8. Quality and Data-Validation Checks

- **Tests.** Unit, schema, idempotency and integration tests, plus fixture postconditions.
- **Gate before formal collection.** The pilot (Weeks 5–8) must show that IDs, snapshots, timers and usage records reconcile.
- **Hidden tests.** Fixed and hashed before either condition runs.
- **Labels.** Two independent label sets; agreement is reported before adjudication.
- **Data checks.** Required IDs, event ordering, evidence links, agreement between writes and snapshots, and test-log reconciliation.
- **Failures.** Failed and inconvenient runs are kept. Technical failures are logged separately from substantive tool failures. A documented retry keeps the original attempt.
- **Reporting.** Repeats are nested within cases. The 36 task attempts are reported as six sequences, not as 36 independent experiments.
- **After the freeze.** No tuning of thresholds, prompts or labels on formal outcomes.

## 9. Configuration and Version Management

- Git versions code, schemas, prompts, fixtures, tests, rubrics, diagrams and scripts.
- Tags: `design-v1` (Week 2), `d2-demo` (Week 6), `protocol-v1` plus the release tag (Week 8), `final` (Week 13).
- Each run manifest records the repository hash, model configuration, budgets, task versions and clock schedule.
- Any change after the freeze requires a written amendment and a new version. Affected comparisons are rerun, or the gap is declared as a limitation.

## 10. Weekly Short-Deliverable and Evidence-Retention Process

- Each week ends with a record (W01–W13) of 150–300 words, stored in `records/Wxx/`.
- Fields: objective and task IDs; work actually completed; evidence paths and versions; decisions; deviations and blockers; individual contribution; AI assistance and how it was verified; next action; final-report use.
- Planned work is kept separate from completed work.
- Presentation weeks (6 and 13) also record the demo version, the findings shown and the feedback received.
- The record names for each week are listed in the schedule.

## 11. Documentation and Final-Report Preparation

- **Documentation set (Proposal 5.11):** architecture description, component contracts, memory schema guide, prompt and policy versions, event-case catalog, operator checklist, evaluation protocol, data dictionary, risk register, run ledger, analysis documentation, user guide.
- **Final-report guide:** provided by the instructor. A copy (*CISC 699 Final Report Guide*) is on hand; its issue date is [TO CONFIRM].
- **Report timeline:**
  - Week 10: confirm the current guide version and map weekly evidence to the report sections (Prompt 10).
  - Week 11: full draft and review.
  - Week 12: revision and checks.
  - Week 13: **submit the final Capstone II report** with D4.
- Approved proposal text is reused where it is still accurate. Inherited material is labeled separately from new Capstone II work.

## 12. Completion and Acceptance Checklist

| Proposal 5.12 condition | Evidence | Week |
|---|---|---|
| Bounded prototype implemented | Tagged release; tests | 8 |
| Three tiers and guarded lifecycle run end to end | Decision traces; D2 demo | 6–7 |
| Critical component and integrity tests pass | pytest logs; integrity report | 8 |
| 60 formal cases and paired sequences executed or accounted for | Run ledger | 9–10 |
| Data audited | Audit log | 10 |
| Comparative results and failures analyzed | D3 memo; figures | 10 |
| Threats and limitations documented | Report chapters | 11–12 |
| Code, fixtures, protocol, results, user guide, report and slides packaged | D4 archive | 13 |

| Chapter 6 expectation | Evidence that would support it |
|---|---|
| K01 Auditable prototype | Event → decision → memory → recall traces |
| K02 Practical pattern | EQ1 effort results together with zero integrity violations |
| K03 Trade-off evidence | Stage One + Stage Two metrics against Proposal Table 10 |
| K04 Taxonomy, metrics, protocol | Frozen catalog, data dictionary, protocol |

These are expected contributions, not results. A rigorous negative or inconclusive finding still meets the execution completion criteria.

**Course submissions:**
- **Week 2:** submit both individual plans (this work plan and the 13-week schedule).
- **Week 6:** D2 and the implemented-tools presentation.
- **Week 10:** D3.
- **Week 13:** D4, the final presentation and defense, and **submission of the final Capstone II report**.

## 13. Changes from the Proposal and Unresolved Decisions

| ID | Change or decision | Reason | Needs |
|---|---|---|---|
| DEC-01 | Compress the 14-week proposal schedule to 13 weeks. The pilot moves from Week 9 to Weeks 5–8, the freeze to Week 8, formal collection to Weeks 9–10 (from 10–11), and analysis to Week 10 (from 12). | Course rules: D2 needs pilot results in Week 6; the freeze is required by Week 8; D3 is due in Week 10 | Instructor confirmation |
| DEC-02 | Responsibility split in §6 — **resolved: adopted as drafted** | The proposal does not assign roles | Closed; shared for instructor awareness |
| DEC-03 | 18 h/week capacity — **resolved: confirmed** | Within the handbook range (15–20 h) | Closed |
| DEC-04 | Model provider/version, budget ceiling, coding agent for Stage Two | Proposal 5.5 and 6.6 leave these open | Fix before the Week 5 pilot |
| DEC-05 | The Final Report Guide asks for a complete draft in Week 10 and a revised report in Week 11. The handbook says Week 11 has no extra submission. | The two course documents conflict | Instructor clarification |
| DEC-06 | Minimum completion path: all of Stage One plus at least two complete A/B pairs if Stage Two cannot finish | Timeline risk R9/R10 | Instructor approval before collection, never after seeing results |
| DEC-07 | Calendar dates | Term dates not supplied | Add when known |
