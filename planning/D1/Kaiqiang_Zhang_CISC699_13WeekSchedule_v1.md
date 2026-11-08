# Individual 13-Week Schedule — CISC 699 Capstone II

| Field | Value |
|---|---|
| Student | Kaiqiang Zhang |
| Partner | Ruifeng Cui (pair proposal; this schedule covers Kaiqiang's individual work and handoffs) |
| Project | Design and Evaluation of an Automated Three-Tier External Memory System for Long-Horizon Coding Agents |
| Topic | T3 Agent Memory |
| Source | GRAD 695 Final Proposal (Sept 26, 2026), Chapter 5 |
| Companion document | `Kaiqiang_Zhang_CISC699_IndividualWorkPlan_v1` (same task IDs T01–T32 and commitment IDs C01–C12) |
| Version / date | v1 — Week 2, calendar date [TO CONFIRM] |
| Capacity | 18 h/week average (confirmed); planned ≈ 218 h of 234 h |

**Notes**

- Calendar dates will be added when term dates are confirmed. Until then, weeks are numbered 1–13.
- **The final-report writing guide.** The instructor provides it. A copy, *CISC 699 Final Report Guide*, is already on hand; its official issue date is [TO CONFIRM]. Week 10 includes a check that this is the current version, and the guide is applied from Week 10 onward.
- **The 14-week proposal plan is compressed to 13 weeks** so that the pilot happens before D2 and the protocol is frozen by Week 8 (DEC-01, see the work plan §13).
- Each week has a short record, W01–W13. Each record is 150–300 words and is stored in `records/Wxx/` in the project repository. These records are kept, not submitted, unless the instructor asks for them.

| Week | Objective | Activities (task / commitment IDs) | Prerequisites | Est. h (+ cont.) | Short deliverable to retain (contents → location) | Completion check | Required submission / presentation | Final-report use |
|---|---|---|---|---|---|---|---|---|
| **1** | Turn the proposal into an executable plan; set up the environment | T01 extract Ch. 5/6, profile, C/K matrix, task register; T02 repo skeleton, pytest, disposable model call, usage logger; T03 start requirements and P/L/S schemas (C01) | Submitted proposal | 16 (+2) | **W01 Proposal Extraction & Planning Record**: extraction register, profile, matrix, task register → `records/W01/` | Extraction checked against the proposal; `pytest` runs; one model call logged | — | Ch. 4 methodology; planning-change log |
| **2** | Fix the design baseline; submit D1 | T03 finish schemas, tag `design-v1` (C01); T04 event taxonomy (10 families) + threat model with RC (C01); T05 write, audit and submit both plans; T06 review RC's fixture skeleton (C02) | W01 record; RC availability | 15 (+2) | **W02 Planning Decision Record**: decisions DEC-01…07, instructor questions, Prompt 7 audit, submission receipt → `records/W02/` | Sample records validate against schemas; audit passes | **Submit individual 13-week schedule** AND **Submit individual research work plan** (D1, 15%) | Ch. 3 design baseline; Ch. 4 scope |
| **3** | Build the tested three-tier store | T07 stores + versioned writer (C03); T08 JSONL traces, run manifest, snapshots (C03); T09 12 development cases + rubric v0 with RC (C07) | `design-v1` | 19 (+1) | **W03 Storage Build Note**: test results, snapshot-diff example, dev-case list → `records/W03/` | Unit tests pass; snapshots match recorded writes | — | Ch. 3 architecture & baseline |
| **4** | Capture and interpret events | T10 Hook adapters + idempotent Candidate Queue (C04); T11 AI Curator with schema-validated output and a deterministic test double (C05); T12 start Router (C05) | T08 | 19 (+1) | **W04 Capture & Curator Note**: idempotency test log, sample Curator traces, rejected-output example → `records/W04/` | Retries create no duplicates; malformed Curator output is rejected | — | Ch. 3 first implementation |
| **5** | Complete the guarded lifecycle; run the first pilot | T12 finish Router; T13 Policy Gate + review/escalation (C05); T14 Resume Pack Builder (C06); T15 review RC's operator checklist (C08); T16 pilot on the 12 dev cases (C09) | T11; dev cases | 20 (+0) | **W05 Pilot Note**: dev-case pilot metrics, blocked or escalated proposals, protocol revisions → `records/W05/` | No Hook writes memory directly; pilot metrics regenerate from logs | — | Ch. 4 pilot revision |
| **6** | **Demonstrate the implemented tool and preliminary results** | T16 finish pilot analysis; T17 D2 package + demo; T18 begin authoring 60 formal cases (C07); T21 review RC's six tasks (C08) | T13–T16 | 19 (+1) | **W06 Demo & Feedback Record**: demo version/tag, pilot findings shown, instructor feedback, actions → `records/W06/` | Demo shows event → Curator → Router → Gate → write → Resume Pack, plus one blocked proposal | **D2 Prototype & Pilot (25%) + 8–10 min implemented-tools presentation** | Ch. 3 integrated system; Ch. 4 readiness |
| **7** | Finish maintenance, labels and the Stage Two fixture | T19 Cron maintenance + controlled clock + scheduler smoke test (C06); T18 finish formal cases; T20 independent labeling + adjudication (C07); T21 hidden tests fixed (C08); T22 start pilot coding sequence (C09) | T13; RC fixture | 19 (+1) | **W07 Labels & Maintenance Record**: agreement table, unresolved cases, maintenance log sample, data shells → `records/W07/` | Two complete label sets; hidden tests hashed; maintenance runs through the Policy Gate | — | Ch. 4 data shells, annotation method |
| **8** | **Freeze the study**; core implementation ends | T22 finish pilot sequence + budget calibration (C09); T23 freeze manifest, `protocol-v1` and release tags, clean-install check (C09) | T19–T22 | 12 (+6) | **W08 Freeze Manifest**: code/prompt/case/label/metric versions, model config, budgets → `records/W08/` | IDs, snapshots, timers and usage reconcile; tags are immutable | — | Ch. 4 actual procedure; reproducibility |
| **9** | Run formal collection | T24 Stage One: 60 cases × 3 replays (C10); T25 Stage Two: paired sequences A/B, B/A, A/B with RC (C10) | `protocol-v1`; Stage One integrity tests pass (E5.7) | 14 (+4) | **W09 Run Ledger Summary**: completed/missing runs, failures, deviations, usage → `records/W09/` | 180 Stage One records or documented gaps; sequence runs logged | — | Ch. 5 dataset |
| **10** | Analyze the evidence and submit D3 | T25 finish any remaining paired sequence; T26 data audit, scripts, figures, failure tracing (C11); T27 findings memo; check the final-report guide version and start mapping evidence (Prompt 10) | T24–T25 | 20 (+0) | **W10 Findings & Evidence-Map Record**: metric table vs. thresholds, failure traces, report-section evidence map → `records/W10/` | Tables regenerate from raw data with one command; each claim links to case IDs | **D3 Evaluation Findings (25%)** | Ch. 5 results; Ch. 6 discussion |
| **11** | Package the software and draft the report | T28 final report draft per the Final Report Guide (C12); T29 clean-environment reproduction, user guide, README (C12) | D3 feedback | 19 (+1) | **W11 Draft & Reproduction Record**: report draft version, clean-run log, gaps list → `records/W11/` | Every guide-required section is drafted or flagged; clean run reproduces one principal analysis | Revised draft if the instructor requires it (DEC-05) | Whole report; reproducibility appendix |
| **12** | Revise the report and rehearse the defense | T30 reconcile every figure and claim with the data, revise the report, build slides, rehearse, record a backup demo; T29 finish packaging (C12) | Draft; feedback | 17 (+1) | **W12 Revision & Rehearsal Record**: corrections made, rehearsal timing, five defense questions with evidence → `records/W12/` | Figures reconcile with data; demo and limitations slide ready | — | Final checks; Ch. 7 conclusions |
| **13** | **Present the completed work and submit** | T31 final presentation, demo and individual defense; submit D4 package; keep the receipt (C12) | All prior | 9 (+9) | **W13 Final Submission Record**: final report version, submission date/channel, confirmation, defense feedback, remaining limits → `records/W13/` | Receipt kept; files open | **Submit final Capstone II report** + D4 package (35%) + 10–12 min final presentation and defense | Submitted report version |

**Weekly effort:** 16, 15, 19, 19, 20, 19, 19, 12, 14, 20, 19, 17, 9, for a total of about 218 h, which is within the 234 h confirmed capacity (13 × 18 h). No week goes over 20 h. Week 8 and Week 13 carry most of the contingency.

**Dependency conflicts flagged**
- Week 9 collection depends on the Week 8 freeze. If the freeze slips, Week 9 slips too, and Week 10 (D3) absorbs the overflow (DEC-06).
- Stage Two depends on Stage One integrity tests passing (E5.7).
- Stage Two depends on RC's fixture (T06, T21) being ready by Week 7.

## Commitment-to-Week Map

| Commitment | Weeks |
|---|---|
| C01 Design package | 1–2 |
| C02 Fixture repository | 2–3 (RC) |
| C03 Stores, writer, traces | 3 |
| C04 Hooks + queue | 4 |
| C05 Curator, Router, Policy Gate, review | 4–5 |
| C06 Cron + Resume Pack | 5, 7 |
| C07 Cases and dual annotation | 3, 6–7 |
| C08 Tasks, hidden tests, operator checklist | 5–7 (RC) |
| C09 Pilot + freeze | 5–8 |
| C10 Formal collection | 9–10 |
| C11 Audited analysis | 10 |
| C12 Documentation, report, presentation | 10–13 |

## Unresolved Decisions (details in the work plan §13; DEC-02 responsibility split and DEC-03 weekly hours are resolved)

DEC-01 13-week compression · DEC-04 model and budget · DEC-05 report-draft submissions in Weeks 10–11 · DEC-06 minimum completion path · DEC-07 term dates.
