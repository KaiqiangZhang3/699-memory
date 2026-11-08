# W03 — Storage Build Note (draft, in progress)

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
- [ ] **T09** — 12 development cases + rubric v0.
- [ ] **T02 deferred item** — one live model call logged (deadline: end of Week 3).

**Test results:** 154 tests pass (`.venv/bin/python -m pytest`).

**Changes after `design-v1`.** One change: the stored `superseded` status was removed (`docs/requirements_v1.md` §7).
