# W01 — Proposal Extraction and Planning Record

| Field | Value |
|---|---|
| Student | Kaiqiang Zhang |
| Partner | Ruifeng Cui (pair proposal; individual CISC 699 plans) |
| Project | Design and Evaluation of an Automated Three-Tier External Memory System for Long-Horizon Coding Agents |
| Primary topic | T3 Agent Memory (Prompt Pack §5) |
| Source proposal | `GRAD_695_Final_Proposal_Report.pdf`, submitted September 26, 2026 (GRAD 695, Instructor Abdel Ejnioui, Ph.D.) |
| Record version / date | v1 — Week 1, calendar date [TO CONFIRM] |
| Final report use | Methodology (Ch. 4), reproducibility appendix, planning-change log |

This record holds the outputs of Prompt Pack Prompts 1–4. It is a planning record. It does not claim that any implementation or evaluation has started.

---

## 1. Chapter 5 Extraction Register (Prompt 1)

| ID | Proposal section | Commitment (faithful summary) |
|---|---|---|
| E5.1 | 5.1 | Work is split into design finalization, prototype implementation, fixture and protocol preparation, pilot calibration, formal collection, analysis and reporting. Required work is separated from optional work. |
| E5.2 | 5.2 | Eight work packages: (1) schemas, requirements and fixtures; (2) storage and deterministic infrastructure; (3) AI interpretation, routing, policy, maintenance and recall; (4) evaluation case preparation and labeling; (5) pilot and protocol freeze; (6) formal collection; (7) analysis; (8) documentation. Each package has a versioned deliverable and an acceptance gate. **Optional work** (more repositories, a no-memory baseline, a UI, learned routing, long-duration deployment) begins only after the primary artifact and study are complete. |
| E5.3 | 5.3 | Milestones: approved design baseline → tested three-tier store → integrated automated lifecycle → frozen evaluation protocol → complete formal dataset → audited analysis → reproducible final artifact. |
| E5.4 | 5.4, Table 12 | **14-week** schedule. Ph1 W1–2 design package and baseline tests. Ph2 W3–5 stores, Hooks, queue, versioned writer, trace logging. Ph3 W6–7 Curator, Router, Policy Gate, review, Cron, Resume Pack. Ph4 W8 sixty formal cases, twelve pilot cases, rubric, hidden tests, operator checklist. Ph5 W9 pilot, calibration, freeze. Ph6 W10–11 formal collection. Ph7 W12 audit and analysis. Ph8 W13–14 documentation, report, presentation, package. If implementation slips, optional features are dropped before collection; the research question does not change. |
| E5.5 | 5.5, Table 13 | Resources: Python + pytest; Git; Markdown/JSON/JSONL; a pinned model interface (provider or local option to be fixed before the pilot); a local queue and scheduler with a controlled clock; a locally created fixture repository; scripted analysis. No external participants or production services. |
| E5.6 | 5.6 | Local Python project under Git. Pytest for unit, integration, acceptance and regression tests. JSON/JSONL traces. A controlled clock for maintenance checkpoints. |
| E5.7 | 5.7 | Formal collection depends on instrumentation, stable fixture tests, independent labels, a frozen protocol and a pinned model. Stage Two depends on the system passing the critical Stage One integrity tests. Provider access and budget must be confirmed before the pilot. A model replacement must be chosen before the freeze, never during collection. |
| E5.8 | 5.8, Table 14 | Eight risks: model variability, scope overrun, ambiguous labels, non-comparable baseline, incomplete logging, provider cost/access, tasks too easy, sensitive content in logs. |
| E5.9 | 5.9 | QA: unit, schema, idempotency and integration tests; fixture postconditions; code review; independent annotation; trace audits; reproducibility checks. Formal collection only starts after the pilot shows that IDs, snapshots, timers and usage records reconcile. Hidden acceptance tests are fixed before either condition runs. Failed runs are kept. |
| E5.10 | 5.10 | Git versions code, schemas, prompts, fixtures, tests, rubrics, diagrams and scripts. Run manifests record hashes, model config, budgets and task versions. Any change after the freeze needs a written amendment. |
| E5.11 | 5.11 | Documentation set: architecture description, component contracts, memory schema guide, prompt/policy versions, event-case catalog, operator checklist, evaluation protocol, data dictionary, risk register, run ledger, analysis documentation, user guide, final report. |
| E5.12 | 5.12 | Complete when: the bounded prototype is implemented; three tiers and the guarded lifecycle run end to end; critical tests pass; the 60 formal cases and the paired sequences are executed or transparently accounted for; data is audited; results and failures are analyzed; limitations are documented; everything is packaged under version control. A running demo alone does not count as completion. |

**Relevant Chapter 4 details (read only where Chapter 5 refers to them):**
- Conditions (4.4, Table 8): **A** = semi-manual three-tier memory driven by an operator checklist; **B** = automated (Hooks, Queue, Curator, Router, Policy Gate, review, Cron, Resume Packs). Both share the same schema, validators, fixtures, tasks, tests, recall limit, model and resource ceiling.
- Stage One (4.5): 60 formal event cases = 10 families × 6, replayed 3 times (180 executions). There are also 12 separate development cases, excluded from formal scores.
- Stage Two (4.5, Table 9): a local task-management service (cookie auth, service layer, SQLite, pytest) with six connected tasks T1–T6. Each condition runs 3 times; paired order is A/B, B/A, A/B (4.8).
- Metrics and criteria (4.7, Table 10): ≥30% fewer manual memory actions; ≥25% lower resume delay; ≥85% tier/operation correctness; ≤5% incorrect Project Memory writes; ≥80% recall precision; ≥80% recall coverage; task success in B no more than 5 points below A; zero integrity violations; cost reported.
- Both group members label the formal cases independently and adjudicate before execution (4.14).

**Chapter 6 extraction:** expected artifact (6.2); contribution to practice (6.3); contribution to knowledge (6.4); limitations (6.5): one repository, one model configuration, controlled tasks, three paired sequences, simulated maintenance time, researcher involvement; readiness (6.6): the exact model interface and the lightweight queue package are still open and will be fixed before the pilot and recorded in the protocol.

**Gaps or ambiguities found:**
1. The proposal schedule has 14 weeks; the CISC 699 course has 13. The course also requires D2 (prototype + pilot) in Week 6 and a protocol freeze by Week 8. The proposal places the pilot in Week 9 and collection in Weeks 10–11. → Decision DEC-01.
2. The proposal does not split responsibilities between the two authors. → DEC-02 (resolved in Week 2: split adopted as drafted).
3. The model provider and budget are not yet fixed (5.5, 6.6). Section 1.9 requires one pinned **coding-agent and model configuration**, so the coding agent must be pinned as well as the model. The queue package is also still open (6.6). → DEC-04.
4. The proposal's internal cross-references and terms are inconsistent. Section 3.7 cites "Table 3" for component responsibilities, which is actually Table 5. Section 4.7 cites "Table 8" for metrics, which is actually Table 10. Section 5.3 cites "Table 11" for the schedule, which is actually Table 12. The 12 non-scored cases are called "development cases" in 4.5 and "pilot cases" in Table 12. → This plan uses the correct table numbers and calls them **development cases** throughout. The final report must not copy the wrong references. No decision is needed.

**Verification (T01 completion check).** The extraction above was checked section by section against `GRAD_695_Final_Proposal_Report.pdf` (57 pages; Chapters 1–6 and Appendices A–D) in Week 1. E5.1–E5.12, the Chapter 4 details and the Table 10 thresholds match the source. Items 3–4 above and the 6.6 readiness note were added as a result of this check.

---

## 2. Individual Planning Profile (Prompt 2)

| Item | Status |
|---|---|
| Weekly capacity | **18 h/week average, confirmed** (handbook range 15–20 h; peak weeks up to 20 h) |
| Term dates | [TO CONFIRM] — weeks are labeled Week 1–13 |
| Solo or pair | Pair proposal with Ruifeng Cui; each student submits individual plans |
| Kaiqiang's individual responsibility | Memory core and automated lifecycle (stores, Hooks, Queue, Curator, Router, Policy Gate, Resume Pack, Cron), Stage One runner and Stage One analysis, own D-package integration (agreed, DEC-02) |
| Ruifeng's responsibility (handoffs) | Stage Two fixture service and six tasks, hidden acceptance tests, Condition A operator checklist, human-action logger, Stage Two analysis (agreed, DEC-02) |
| Shared | Event taxonomy, independent dual annotation of 60 formal cases, adjudication, protocol freeze, paired-sequence execution |
| Tools/access confirmed | Python, Git, pytest available locally [TO CONFIRM versions] |
| Model access | Provider and model version [TO CONFIRM]; must be pinned before the pilot (E5.7) |
| Budget ceiling | [TO CONFIRM] |
| Permissions | None needed: synthetic data only, no participants (4.16) |
| Completed prior work (not repeated) | Problem, research questions, literature review (20 verified sources), architecture, evaluation design, data plan (GRAD 695) |
| Unavailable weeks | [TO CONFIRM] |

---

## 3. Commitment-to-Evidence Matrix (Prompt 3)

| ID | Source | Commitment / expected contribution | Artifact needed | Evidence needed | Acceptance criterion | Owner |
|---|---|---|---|---|---|---|
| C01 | 5.4 Ph1 | Versioned design package | Requirements, JSON schemas for P/L/S tiers, event taxonomy, threat model | Tagged commit `design-v1` | Baseline tests pass; schemas validate sample records | KZ (taxonomy shared) |
| C02 | 5.4 Ph1, 4.5 | Fixture repository with formal and pilot fixtures kept separate | Task-service fixture, `fixtures/pilot/` vs `fixtures/formal/` | Baseline pytest log | Baseline tests pass; split recorded in manifest | RC (KZ reviews) |
| C03 | 5.4 Ph2 | Three stores, versioned writer, trace logging | `memory/` package, writer with supersedes and rollback, JSONL traces | Unit tests, snapshot diffs | Snapshots match recorded writes | KZ |
| C04 | 5.4 Ph2 | Hook adapters and idempotent queue | `hooks/`, `queue/` | Idempotency and retry tests | Retries do not create duplicate candidates | KZ |
| C05 | 5.4 Ph3 | Curator, Router, Policy Gate, review flow | `curator/`, `router/`, `policy/`, `review/` | Integration tests, decision traces | No Hook writes directly to memory; ambiguous proposals are escalated | KZ |
| C06 | 5.4 Ph3 | Cron maintenance and Resume Pack Builder | `maintenance/`, `resume/`, controlled clock | Scheduler smoke test, maintenance logs | End-to-end run locally with inspectable evidence | KZ |
| C07 | 5.4 Ph4, 4.14 | 60 formal + 12 development cases, rubric, dual annotation | Event-case catalog, rubric v1, label files | Two independent label sets, agreement table | Both label sets complete; disagreements resolved or marked | KZ + RC |
| C08 | 5.4 Ph4, 4.5, 4.8 | Six connected tasks, hidden tests, operator checklist | Task specs T1–T6, hidden tests, checklist v1 | Test inventory, checklist version | Hidden tests fixed before any condition runs | RC (KZ reviews) |
| C09 | 5.4 Ph5 | Pilot, calibration, frozen protocol | Pilot report, `protocol-v1` tag, freeze manifest | Pilot logs, budget calibration | IDs, snapshots, timers and usage records reconcile; immutable tags | KZ + RC |
| C10 | 5.4 Ph6 | Formal collection | Run ledger, raw logs, snapshots | 180 Stage One executions; 3 A/B pairs (36 task attempts) | All attempts, failures and deviations kept | KZ (S1), KZ + RC (S2) |
| C11 | 5.4 Ph7, 4.12–4.13 | Audited analysis | Analysis scripts, tables, figures, failure traces | Regenerated outputs from raw data | Every result links to raw evidence, denominator and protocol version | KZ (S1), RC (S2) |
| C12 | 5.4 Ph8, 5.11–5.12 | Documentation, final report, presentation, package | Report, user guide, slides, tagged release | Clean-install log, acceptance checklist | Package passes the 5.12 checklist | KZ (own report) |
| K01 | 6.2 | Local prototype that makes memory decisions auditable from event to recall | C03–C06 release | Decision traces linking event → recall → task | Traceability demonstrated on formal cases | — |
| K02 | 6.3 | Pattern that reduces routine save/reload work without giving the LLM unrestricted control | Architecture + Policy Gate | EQ1 effort measures; integrity checks | Reported against thresholds; a negative result is acceptable | — |
| K03 | 6.4 | Preliminary evidence on effort, quality, integrity and cost trade-offs | D3 findings memo | Stage One and Stage Two analyses | Bounded, evidence-linked conclusions | — |
| K04 | 6.4 | Event taxonomy, metric definitions, protocol | Case catalog, data dictionary, protocol | Frozen versions | Published in the final package | — |

**Traceability notes:** K02 and K03 are expected, not guaranteed. The planned evaluation is able to show a negative or inconclusive result (4.13). Each contribution has evidence scheduled for it, so no contribution is left without supporting evidence.

---

## 4. Task Register (Prompt 4) — Kaiqiang's tasks, with partner handoffs

Hours are planning estimates for KZ only, based on similar GRAD 695 build work and the handbook's 15–20 h/week. RC tasks list the handoff only.

| Task | Commit. | Action → output | Acceptance check | Owner | Pred. | Week | KZ h |
|---|---|---|---|---|---|---|---|
| T01 | — | Extract Ch. 5/6, write profile, matrix and task register → this record | Matches proposal sections | KZ | — | 1 | 4 |
| T02 | C03 | Create repo skeleton (Python, pytest, Git, folder layout), make a disposable model call, set up a usage logger | `pytest` runs; one model call logged with tokens | KZ | — | 1 | 5 |
| T03 | C01 | Finalize requirements and P/L/S JSON schemas, evidence fields and IDs → `schemas/v1` | Sample records validate; tag `design-v1` | KZ | T02 | 1–2 | 8 |
| T04 | C01 | Event taxonomy (10 families) and threat model | Each family has a definition and expected tier/operation | KZ + RC | T03 | 2 | 4 |
| T05 | — | Write, audit and submit D1 (schedule + work plan) | Prompt 7 audit passes; submission receipt kept | KZ | T01–T04 | 2 | 8 |
| T06 | C02 | Fixture task service skeleton and baseline tests (handoff from RC) | Baseline pytest log | RC (KZ review) | T03 | 2–3 | 1 |
| T07 | C03 | Three stores + versioned writer (atomic write, supersedes, rollback) | Unit tests; snapshots equal recorded writes | KZ | T03 | 3 | 10 |
| T08 | C03 | JSONL trace logging, run manifest, snapshot recorder | Every write has an event ID and a hash | KZ | T07 | 3 | 5 |
| T09 | C07 | 12 development cases + rubric v0 | Cases cover all 10 families | KZ + RC | T04 | 3 | 3 |
| T10 | C04 | Hook adapters + Candidate Queue (dedup key, retry) | Idempotency tests pass | KZ | T08 | 4 | 8 |
| T11 | C05 | AI Curator: prompt v0, structured output, schema validation, deterministic test double | Malformed output rejected; tests run without a live model | KZ | T10 | 4 | 7 |
| T12 | C05 | Memory Router (tier, operation, recall scope), separate from Curator | Router tests on dev cases | KZ | T11 | 4–5 | 5 |
| T13 | C05 | Policy Gate (schema, provenance, paths, secret patterns, version rules) + review/escalation path | Destructive or unsupported proposals blocked or escalated | KZ | T12 | 5 | 9 |
| T14 | C06 | Resume Pack Builder (minimum context, recall budget, fact units) | Pack within budget; selected IDs logged | KZ | T13 | 5 | 5 |
| T15 | C08 | Condition A operator checklist + human-action logger (handoff from RC) | Same functions invoked as in B | RC (KZ review) | T13 | 5 | 1 |
| T16 | C09 | Pilot on the 12 dev cases → preliminary metrics | Metrics regenerate from logs | KZ | T09, T14 | 5–6 | 5 |
| T17 | — | D2 package + 8–10 min demo | Demo shows the full event → recall path and one blocked proposal | KZ | T16 | 6 | 9 |
| T18 | C07 | Author 60 formal cases (6 × 10 families), kept out of development use | Catalog `cases/formal v1` | KZ + RC | T09 | 6–7 | 6 |
| T19 | C06 | Cron maintenance (dedup, drift revalidation, archive candidacy) + controlled clock + scheduler smoke test | Maintenance passes through the same Policy Gate | KZ | T13 | 7 | 9 |
| T20 | C07 | Independent labeling of 60 formal cases, then adjudication | Agreement table; unresolved cases marked | KZ + RC | T18 | 7 | 6 |
| T21 | C08 | Six connected tasks + hidden acceptance tests (handoff from RC) | Hidden tests fixed and hashed | RC (KZ review) | T06 | 6–7 | 2 |
| T22 | C09 | Short pilot coding sequence in both conditions; budget calibration | Budgets set; IDs/timers/usage reconcile | KZ + RC | T19, T21 | 7–8 | 6 |
| T23 | C09 | Freeze protocol: manifest, `protocol-v1` and release tags, clean-install check | Freeze manifest signed off | KZ | T20, T22 | 8 | 6 |
| T24 | C10 | Stage One formal replays (60 × 3) | 180 records or documented gaps | KZ | T23 | 9 | 5 |
| T25 | C10 | Stage Two formal: 3 paired sequences (A/B, B/A, A/B) | 6 sequence runs logged; failures kept | KZ + RC | T24 | 9–10 | 12 |
| T26 | C11 | Data audit, analysis scripts, figures, failure tracing | Tables regenerate from raw data with one command | KZ | T24, T25 | 10 | 10 |
| T27 | C11 | D3 findings memo | Each claim links to case IDs and scripts | KZ | T26 | 10 | 5 |
| T28 | C12 | Final report draft using the provided Final Report Guide | All required sections drafted or flagged | KZ | T27 | 10–11 | 14 |
| T29 | C12 | Clean-environment reproduction, user guide, packaging | Clean-run log; README reproduces one analysis | KZ | T26 | 11 | 6 |
| T30 | C12 | Revise report, reconcile figures, slides, rehearsal, backup recording | Figures match data; 10–12 min rehearsal | KZ | T28 | 12 | 14 |
| T31 | C12 | Final presentation, defense, submit D4 with the final report | Receipt kept | KZ | T30 | 13 | 8 |
| T32 | — | Weekly short records W01–W13 | One record per week | KZ | — | 1–13 | 10 |

**Capacity summary:** total KZ planned hours ≈ 218 h. Confirmed capacity is 13 × 18 = 234 h, leaving about 16 h (≈7%) of explicit contingency. Weeks 5 and 10 peak at about 20 h. Week 8 (about 12 h) and Week 13 (about 9 h) are deliberately light: Week 8 is the buffer before the freeze, and Week 13 is for the defense. Weeks 3–7, 10 and 11 run 1–2 h above the 18 h average; the light Weeks 8 and 13 offset this. The margin is thin, so if any week overruns by more than 4 h, DEC-06 is raised immediately.

**Critical path:** T03 → T07 → T08 → T10 → T11 → T12 → T13 → T19 → T22 → T23 → T24 → T25 → T26 → T28 → T30 → T31.

**Main risk to the critical path:** the 14-week proposal plan must fit into 13 weeks, and formal collection must happen in Weeks 9–10 instead of Weeks 10–11 (DEC-01).

**Minimum completion path** (only with an instructor-approved amendment, DEC-06): all of Stage One plus at least two complete A/B pairs. The missing pair would be reported as a limitation, and the research question would not change.

---

## 5. Week 1 Completion Status

| Completion check | Status | Evidence |
|---|---|---|
| Extraction checked against the proposal | Done | Verification note in §1 |
| `pytest` runs | Done | 18 tests pass (`tiered-memory`, commit `dd8738e`) |
| One model call logged | **Deferred to end of Week 3** | Logger and call script are done; the failure path was verified (one `status: "error"` record). The live call is waiting for an API key. |

**Deviation (T02).** The live model call is deferred because no API key is configured yet. No Week 1–3 task depends on a live model: T11 Curator tests use a deterministic test double, as proposal 5.5 allows. **New deadline:** configure the key and run `scripts/smoke_model_call.py` by the end of Week 3, then add the `status: "ok"` usage line here. **Risk R6 trigger:** no working key by the start of Week 4. This would also put DEC-04 (model pinned before the Week 5 pilot) at risk.
