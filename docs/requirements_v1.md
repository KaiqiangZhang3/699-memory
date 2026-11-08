# Requirements and Memory Schemas — v1 (draft)

| Field | Value |
|---|---|
| Task / commitment | T03 / C01 (design package) |
| Status | **v1 candidate, Week 1.** Design questions are settled (§6). It will be tagged `design-v1` in Week 2, together with the event taxonomy and threat model (T04). |
| Source | GRAD 695 Final Proposal: 3.5 (Table 4), 3.7 (Table 5), 3.8, 3.10–3.11, 4.6 (Table 11), 4.11, Appendices B and D |
| Schemas | `schemas/v1/*.schema.json` (JSON Schema Draft 2020-12); samples in `schemas/v1/examples/` |
| Validator | `src/tiered_memory/schemas.py` → `validate_record(record)` |

## 1. Functional and quality requirements

Requirement IDs and wording come from proposal Table 4. The **acceptance check** column is what this project will test. **Schema support** names the v1 fields or rules that already enforce part of the requirement. Everything else is left to the component named in the Task column.

| ID | Requirement (Table 4) | Acceptance check | Schema support in v1 | Task |
|---|---|---|---|---|
| FR1 | Capture task, validation, correction and session-boundary events without giving Hooks write authority | Replaying each event family produces a queued candidate. No memory file changes until a Policy Gate decision is `accepted`. | `provenance.written_by` must be `versioned_writer`. `provenance.policy_outcome` must be `accepted`. | T10 |
| FR2 | Separate Project Memory, Daily Log and Session Memory stores with explicit schemas and version metadata | Each store validates against its own schema. Version chains are complete. | Three schemas. `version` / `version_id` / `supersedes` chain on P and S. Hash chain on L. | T03, T07 |
| FR3 | Extract candidate facts, progress, failures, decisions, uncertainty and conflicts from events that carry evidence | Curator output validates against the candidate schema. Every claim cites at least one evidence ID. | `evidence_ref` definition, reused by the candidate schema | T11 |
| FR4 | Choose tier, operation and recall scope separately from semantic extraction | Router tests on the development cases. Router input contains no raw event text. | `proposed_tier` and `operation` enums (Appendix B) | T12 |
| FR5 | Reject or escalate unsupported, sensitive, conflicting or destructive durable-memory operations | Policy Gate fixture tests, one per rule | Project Memory needs ≥1 evidence item. `user_approved` needs user evidence. No `delete` operation exists. | T13 |
| FR6 | Scheduled deduplication, revalidation, archival and garbage-collection candidacy, with no irreversible deletion | Controlled-clock maintenance tests. Archived records remain readable. | `status`: `uncertain` / `superseded` / `archived`. `verified_at_utc`, `last_verification_event_id`, `paths` for drift checks. | T19 |
| FR7 | Build a minimum, auditable Resume Pack linked to source memory records | Recall precision, coverage and token size. Every fact unit links to a `memory_id` and `version_id`. | Stable `memory_id` and `version_id` to cite | T14 |
| QR1 | Keep provenance from source event to final memory version to later recall | An audit script follows event → decision → version → recall with no missing link. | `provenance.source_event_id`, `decision_id`, `review_id`. `evidence_ref.event_id`. | T08 |
| QR2 | Idempotent queue processing and versioned writes; retries do not duplicate canonical state | Duplicate-event replay leaves exactly one canonical write. | `dedup_key` on Daily Log entries. `content_hash` lets the writer detect identical content. | T07, T10 |
| QR3 | Readable and reproducible local Markdown/JSON records and JSONL traces | Clean checkout → regenerate samples → tests pass | Plain JSON files. Deterministic sample builder (`scripts/build_schema_examples.py`). | T03, T29 |

Additional constraints from 3.11 and Table 10 (integrity checks):

| ID | Constraint | Schema support |
|---|---|---|
| IC1 | No committed synthetic secrets | None in the schema. This is a Policy Gate rule (T13). |
| IC2 | No cross-project writes | Every record carries `project_id`; the writer rejects a mismatch (T07). |
| IC3 | No unapproved permanent deletion | There is no delete operation; `archive` is the strongest action. |

## 2. The three tiers

| Tier | Holds | Mutability | One file = | Must have |
|---|---|---|---|---|
| **Project Memory** (`pm-v1`) | Commands, constraints, conventions, architecture, confirmed decisions, procedures | Versioned. A new version supersedes the old one, and the old version stays. | One version of one fact | ≥1 evidence item. `support` of `repository_evidence`, `test_validated` or `user_approved`. `source_commit`. |
| **Daily Log** (`dl-v1`) | Commands, test results, code changes, decisions, failures, corrections, session boundaries, maintenance | Append-only. A correction is a new entry with `corrects_entry_id`. | One entry | ≥1 evidence item. Per-day `sequence` and `prev_entry_hash` chain. `dedup_key`. |
| **Session Memory** (`sm-v1`) | Goal, progress, tentative findings, failed attempts, blockers and next steps for one task | Versioned per `task_id` | One version of one task's state | A step marked `done` and each failed attempt must cite evidence. `active` or `paused` tasks need a next step. |

Episodic material (attempts, failures) is deliberately kept out of Project Memory, following 2.3.1 and 2.6.2. Promoting a tentative finding into Project Memory requires evidence and passes through the Policy Gate. If the claim is uncertain, it goes to review (3.10).

## 3. IDs, time and hashes (design decisions)

| Decision | Choice | Why |
|---|---|---|
| ID format | `<prefix>_<32 hex>` (uuid4 hex in code). Prefixes: `prj` `run` `tsk` `ses` `evt` `dec` `rev` `mem` `smem` `log` `evd` `ver`. | A wrong ID type is caught by regex, and IDs are readable in traces. `prj_` and `tsk_` use readable slugs (`prj_taskservice`, `tsk_T3`). |
| Fact identity vs version | `memory_id` / `session_memory_id` stays the same across versions; `version_id` is unique per write | Resume Packs and decision traces must cite the exact version that was read (QR1). |
| Timestamps | UTC only, `Z` or `+00:00` | Proposal 4.11. Durations come from the monotonic clock (`usage.py`). |
| `content_hash` | `sha256:` + hex of the canonical JSON (sorted keys, no spaces, UTF-8) of the tier's content fields. See D4 in §6. | Identical content gets an identical hash, so the writer can detect duplicates (QR2). |
| `source_hash` | sha256 of the evidence content at capture time | Drift check: the same locator with a different hash means the evidence changed. |
| Daily Log integrity | `prev_entry_hash` = previous entry's `content_hash` on the same date | Makes silent edits or deletions detectable in the audit (4.14). |
| Deletion | Not representable | 3.11: automated permanent deletion is outside prototype authority. |

## 4. Field traceability

| Field(s) | Source in proposal |
|---|---|
| tier, status, content hash, source commit, created/verified time, supersedes | 3.8 (memory records); Table 11 (memory versions) |
| event_id, run/task/session IDs, source type and hash, capture time, dedup key | 3.8 (events); Table 11 (event and queue log) |
| evidence references, uncertainty (`tentative_findings`, `status: uncertain`) | 3.8 (candidate claims); 2.4.2; Appendix D |
| proposed_tier, proposed_operation, policy_outcome enums | Appendix B |
| decision_id, review_id, policy outcome in provenance | Table 5 (Policy Gate, Review Queue); 3.10 |
| paths, last verification event | 2.11 (drift checks: missing paths, changed commands) |
| goal, progress, failures, blockers, next steps | Glossary: Session Memory |
| condition (A / B / dev) | Table 8; 4.14 (pilot data kept separate) |

## 5. Out of scope for this draft

These schemas are planned next and will reuse `common.schema.json`:

- event / queue record (T04, T10)
- Curator candidate (T11)
- decision trace (T12–T13)
- Resume Pack (T14)
- run manifest (T08)
- event-case and label files (T09)

The usage record already exists as `usage-v0` in code (`src/tiered_memory/usage.py`); it gets a JSON schema with the run manifest in T08.

## 6. Design decisions (settled in Week 1)

| ID | Question | Decision | Consequence |
|---|---|---|---|
| D1 | Storage layout | **Project and Session Memory:** one JSON file per version, at `memory/<project_id>/project/<memory_id>/v0001.json` and `memory/<project_id>/session/<task_id>/v0001.json`. **Daily Log:** one JSONL file per UTC date, at `memory/<project_id>/daily_log/2026-11-09.jsonl`, one entry per line. Markdown views are generated for reading and are never authoritative (3.8). | A version file is written once and never edited, so snapshots and rollback reduce to file copies. JSONL fits an append-only log. Implemented in T07. |
| D2 | Are six Project Memory categories enough? | **Yes, keep six.** Checked against Appendix D: stable facts map to `command`, `constraint`, `convention` or `architecture`; confirmed decisions map to `decision`; validated reusable steps map to `procedure`. The other families change status or go to other tiers: completion goes to L+S, unfinished state to S, failed attempts to L+S, repeats to `no_op`, conflicts to review or `supersede`, stale references to `status: uncertain`, user corrections to a new version, secrets are blocked, and irrelevant events are skipped. | No category exists for failures or progress, so episodic material cannot end up in Project Memory. |
| D3 | When is evidence strong enough for Project Memory? | Enforced in the schema: **`command`** needs `test_validated` or `user_approved`; a command must have actually run. **`decision`** needs `user_approved`. **`architecture`, `constraint`, `convention`, `procedure`** may also rest on `repository_evidence`. **`test_validated`** requires a `test` or `command` evidence item with outcome `pass`. **`user_approved`** requires a `user_decision` or `user_correction` evidence item. | The Policy Gate (T13) may add stricter rules but cannot relax these. |
| D4 | What does `content_hash` cover? | **Project Memory:** `project_id`, `memory_id`, `category`, `claim`, `paths`, `tags`. **Session Memory:** `project_id`, `session_memory_id`, `task_id`, `status`, `goal`, `progress`, `tentative_findings`, `failed_attempts`, `blockers`, `next_steps`, `evidence`. **Daily Log:** every field except `content_hash` and `provenance`. | A new P or S version with unchanged content gets the same hash, so the writer records `no_op` instead of a duplicate version (QR2). Revalidation (new evidence, new `verified_at_utc`) does not change a P hash. Whole-file tamper detection for P and S therefore comes from the T08 snapshot hashes, not from `content_hash`. The Daily Log hash chain covers timestamps and sequence numbers. |
| D5 | Evidence format for the fixture | The Stage Two fixture (T06) must emit evidence that fits `evidence_ref`: pytest node IDs as `locator`, 40-character commit SHAs, and sha256 of the test output. | This becomes an acceptance check for T06. |

**Staffing change (2026-11-08).** The project is now carried out by one person. Tasks the plans assigned to Ruifeng Cui (T06, T15, T21) and shared tasks (T04, T09, T18, T20, T22, T25) are now Kaiqiang's. This affects the plan in two places: the hours in the work plan, and the dual independent annotation required by proposal 4.14. Both are handled outside this document.
