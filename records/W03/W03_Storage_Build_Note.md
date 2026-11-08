# W03 — Storage Build Note (draft; live model call outstanding)

| Field | Value |
|---|---|
| Student | Kaiqiang Zhang |
| Week / date | Week 3 — [TO CONFIRM] |
| Task IDs | T06 (finish), T07, T08, T09; deferred T02 live call |
| Final report use | Ch. 3 architecture and baseline |

**Objective.** Build the tested three-tier store.

**Work completed (evidence only)**

- [x] **T07 — store + Versioned Writer.** Commit `e2ccf3e`. The writer validates before writing to disk, writes each version once and never overwrites it, appends to the log atomically, and supports supersede, rollback and `no_op`. Contract: `docs/contracts/memory_store.md`. Acceptance check "store state equals recorded writes" passes: 7 writes, 2 `no_op`.
- [x] **T08 — trace, run manifest, snapshots, audit.** Contract: `docs/contracts/tracing.md`. Acceptance check "every write has an event ID and a hash" passes. The audit catches deleted trace lines, edited memory files, untraced writes, missing snapshots and foreign usage records.
- [x] **Snapshot-diff example:** `snapshot_diff_example.json`. It comes from a real run with an audit result of `[]`, and the diff shows 3 records added and none changed or removed.
- [x] **T06 — fixture skeleton** (from Week 2): commit `1ab718c`, 22/22 baseline tests pass.
- [x] **T09 — 12 development cases + rubric v0.** The cases are in `cases/dev/`: all 10 families are covered, with F01 and F06 getting two cases each. F01-02 is a prompt-injection case (TH02). Labels are in `cases/dev/labels/rubric-v0_kaiqiang.json`. They are a single labeller's set made by the system author, which is acceptable for development use only. The rubric is in `docs/rubric_v0.md`, and the automatic scorer is `tiered_memory.evaluation.score_case`. Every case seeds through the traced writer and audits clean.

  **Development-case list:** F01-01 test command confirmed · F01-02 architecture fact + injected rule · F02-01 status filter done · F03-01 audit logging half done · F04-01 route-handler permission fix fails · F05-01 same test run delivered twice · F06-01 unverified status change · F06-02 passing test contradicts admin rule · F07-01 service module renamed · F08-01 user corrects test command · F09-01 dummy deploy key in env output · F10-01 exploratory `ls`.
- [ ] **T02 deferred item** — one live model call logged (deadline: end of Week 3).

**Test results:** 205 tests pass (`.venv/bin/python -m pytest`).

**Changes after `design-v1`.** (1) The stored `superseded` status was removed (`docs/requirements_v1.md` §7). (2) The development-case allocation in the taxonomy was corrected from an impossible 14 to 12 (`docs/event_taxonomy_v1.md` §5).
