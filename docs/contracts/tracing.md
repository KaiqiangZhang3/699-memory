# Component Contract — Run Manifest, Trace, Snapshots and Audit (v1)

| Field | Value |
|---|---|
| Task / commitment | T08 / C03 |
| Code | `src/tiered_memory/tracing/` (`run.py`, `trace.py`, `audit.py`, `diff.py`) |
| Schemas | `schemas/v1/trace_event.schema.json`, `schemas/v1/run_manifest.schema.json` |
| Tests | `tests/unit/test_tracing.py` |
| Proposal | 3.8, 4.6 (Table 11), 4.11, 4.14, 5.9, 5.10; threat TH11 |

## A run on disk

```
runs/<run_id>/manifest.json        what ran, under which versions and limits; output hashes
runs/<run_id>/trace.jsonl          hash-chained events
runs/<run_id>/usage.jsonl          model usage (usage-v0), one line per call
runs/<run_id>/snapshots/NNNN-<reason>.json
runs/<run_id>/memory/<project_id>/ the run's own store; runs never share memory (4.8)
```

## Using it

```python
with Run.start("runs", project_id="prj_taskservice", purpose="dev", condition="B") as run:
    run.task_boundary("tsk_T1", "start")
    run.writer.write_project("append", payload, provenance)   # traced + snapshotted
    run.maintenance_checkpoint("2026-11-10T00:00:00Z")
    run.before_recall("req_1")
    call_model(client, logger=run.usage, run_id=run.run_id, component="curator", messages=...)
# the context manager calls finish(); an exception records status "failed"
```

`run.writer` has the same interface as `VersionedWriter`. Components get `run.writer`, never `run.raw_writer`. A write through the raw writer is caught by the audit as an untraced record.

## What is recorded

| Moment (4.11) | Trace event | Snapshot reason |
|---|---|---|
| Run start | `run_start` (with manifest hash) | `initial` |
| Every write call | `write` (`event_id`, `decision_id`, tier, requested and executed operation, `record_id`, `content_hash`, file and `file_sha256`), or `write_rejected` (reason) | `write`, after every executed write (not for `no_op`) |
| Task boundary | `task_boundary` | `task_boundary` |
| Maintenance checkpoint | `maintenance_checkpoint` | `maintenance_checkpoint` |
| Immediately before recall | `recall` (phase `before`) | `pre_recall` |
| Deviation | `deviation`, also appended to `manifest.deviations` | — |
| Run end | `run_end` | `final` |

Every trace line has `seq`, UTC `at_utc`, monotonic `mono_ms`, `prev_hash` and `line_hash`. The event kinds for the Hook, queue, Curator, Router and Policy Gate (`event_captured`, `candidate_queued`, `curator_output`, `routing_proposal`, `policy_decision`, `review`) are already defined in the schema; T10–T13 will emit them.

## Manifest rules

- `status` is `running` until `finish()`, which fills `ended_at_utc` and `outputs`: trace hash and counts, writes, no-ops, rejections, the final snapshot hash and the usage count.
- A **formal** run is refused at start unless `model_config.pinned` is true, `protocol_version` is not `unfrozen`, and `code.dirty` is false (DEC-04, T23, 5.10).
- The defaults are honest placeholders until those decisions are made. `model_config.pinned` defaults to false, and `protocol_version` defaults to `"unfrozen"`.

## `audit_run(run_dir)` checks

1. The manifest validates, and the run finished.
2. Trace lines validate, `seq` is contiguous, `run_id` matches, the hash chain is unbroken, every `line_hash` recomputes, the monotonic time never goes back, and the trace ends with `run_end`.
3. Manifest `outputs` equal what the trace shows.
4. Every snapshot file exists and recomputes to its recorded hash; the first is `initial`; every executed write is followed by a `write` snapshot; the last snapshot equals `outputs.final_snapshot_sha256`.
5. Every `write` has an `event_id`; every written version file still has the bytes recorded at write time.
6. `MemoryStore.verify()` is clean, and the store on disk equals the final snapshot.
7. Every stored record has a traced write, and every traced write is in the store.
8. Every usage record carries this run's `run_id`, and the count matches the manifest.

A non-empty result means the run's metrics are **unassessable** until the cause is fixed and the run is redone, with the original kept (Table 14). `diff_snapshots(a, b)` lists the records added between two snapshots. Since records are never edited or removed, anything else it shows is an integrity problem.
