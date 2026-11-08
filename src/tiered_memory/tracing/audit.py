"""Reconcile a finished run (task T08; proposal 4.14, 5.9).

Formal collection may only start once the pilot shows that "identifiers,
snapshots, timers and usage records reconcile" (5.9). ``audit_run`` is that
check. If it reports problems, the run's metrics are treated as unassessable
(Table 14, risk "Logging is incomplete").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..memory import MemoryStore
from ..schemas import canonical_json, schema_errors, sha256_text
from .run import MANIFEST_SCHEMA, file_sha256
from .trace import TRACE_SCHEMA, line_hash, read_trace


def audit_run(run_dir: str | Path) -> list[str]:
    run_dir = Path(run_dir)
    problems: list[str] = []

    # 1. manifest
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return ["manifest.json is missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems += [f"manifest: {e}" for e in schema_errors(manifest, MANIFEST_SCHEMA)]
    if manifest.get("status") == "running":
        problems.append("manifest: run never finished (status is still 'running')")
    outputs = manifest.get("outputs") or {}

    # 2. trace: schema, chain, order, run_id
    trace_path = run_dir / "trace.jsonl"
    if not trace_path.exists():
        return problems + ["trace.jsonl is missing"]
    events = read_trace(trace_path)
    prev_hash, prev_mono = None, -1.0
    for n, ev in enumerate(events, start=1):
        where = f"trace#{n}"
        problems += [f"{where}: {e}" for e in schema_errors(ev, TRACE_SCHEMA)]
        if ev.get("seq") != n:
            problems.append(f"{where}: seq is {ev.get('seq')}, expected {n}")
        if ev.get("run_id") != manifest.get("run_id"):
            problems.append(f"{where}: run_id does not match the manifest")
        if ev.get("prev_hash") != prev_hash:
            problems.append(f"{where}: hash chain broken")
        if ev.get("line_hash") != line_hash(ev):
            problems.append(f"{where}: line_hash does not match the line")
        if ev.get("mono_ms", 0) < prev_mono:
            problems.append(f"{where}: monotonic time went backwards")
        prev_hash, prev_mono = ev.get("line_hash"), ev.get("mono_ms", 0)
    if events and events[-1].get("kind") != "run_end":
        problems.append("trace: last event is not run_end")

    # 3. manifest outputs agree with the trace
    kinds = [e["kind"] for e in events]
    writes = [e for e in events if e["kind"] == "write"]
    snaps = [e for e in events if e["kind"] == "snapshot"]
    expected = {
        "trace_sha256": file_sha256(trace_path),
        "trace_events": len(events),
        "snapshots": len(snaps),
        "writes": sum(e["payload"]["executed"] != "no_op" for e in writes),
        "no_ops": sum(e["payload"]["executed"] == "no_op" for e in writes),
        "rejected_writes": kinds.count("write_rejected"),
    }
    for key, value in expected.items():
        if outputs.get(key) != value:
            problems.append(f"manifest.outputs.{key} is {outputs.get(key)!r}, trace says {value!r}")

    # 4. snapshots: files exist, hashes recompute, one after every executed write
    for ev in snaps:
        path = run_dir / ev["payload"]["file"]
        if not path.exists():
            problems.append(f"snapshot {ev['payload']['file']} is missing")
            continue
        content = json.loads(path.read_text(encoding="utf-8"))
        if sha256_text(canonical_json(content)) != ev["payload"]["snapshot_sha256"]:
            problems.append(f"snapshot {ev['payload']['file']} does not match its recorded hash")
    for i, ev in enumerate(events):
        if ev["kind"] == "write" and ev["payload"]["executed"] != "no_op":
            nxt = events[i + 1] if i + 1 < len(events) else None
            if not nxt or nxt["kind"] != "snapshot" or nxt["payload"]["reason"] != "write":
                problems.append(f"trace#{i + 1}: executed write is not followed by a snapshot")
    if snaps and snaps[0]["payload"]["reason"] != "initial":
        problems.append("first snapshot is not 'initial'")
    if snaps and snaps[-1]["payload"]["snapshot_sha256"] != outputs.get("final_snapshot_sha256"):
        problems.append("manifest.outputs.final_snapshot_sha256 does not match the last snapshot")

    # 5. every executed write: event id, hash, and the bytes on disk match the trace
    memory_root = run_dir / "memory"
    for ev in writes:
        p = ev["payload"]
        if not p.get("event_id"):
            problems.append(f"trace#{ev['seq']}: write without an event_id")
        if p["executed"] == "no_op":
            continue
        path = memory_root / p["file"]
        if not path.exists():
            problems.append(f"trace#{ev['seq']}: written file {p['file']} is missing")
            continue
        if p["tier"] != "daily_log" and file_sha256(path) != p["file_sha256"]:
            problems.append(f"trace#{ev['seq']}: {p['file']} changed after it was written")

    # 6. the final store is internally consistent and equals the final snapshot
    store = MemoryStore(memory_root, manifest["project_id"])
    problems += [f"store: {e}" for e in store.verify()]
    if snaps:
        last = json.loads((run_dir / snaps[-1]["payload"]["file"]).read_text(encoding="utf-8"))
        if last != json.loads(canonical_json(store.snapshot())):
            problems.append("store on disk differs from the final snapshot")

    # 7. every record in the store was produced by a traced write
    traced_ids = {ev["payload"]["record_id"] for ev in writes if ev["payload"]["executed"] != "no_op"}
    snap = store.snapshot()
    stored_ids = (
        {v["version_id"] for versions in snap["project"].values() for v in versions}
        | {v["version_id"] for versions in snap["session"].values() for v in versions}
        | {e["entry_id"] for entries in snap["daily_log"].values() for e in entries}
    )
    for rid in sorted(stored_ids - traced_ids):
        problems.append(f"store: {rid} has no write event in the trace")
    for rid in sorted(traced_ids - stored_ids):
        problems.append(f"trace: write {rid} is not in the store")

    # 8. usage records belong to this run
    usage_path = run_dir / "usage.jsonl"
    if usage_path.exists():
        usage = [json.loads(line) for line in usage_path.read_text().splitlines() if line.strip()]
        if outputs.get("usage_records") != len(usage):
            problems.append("manifest.outputs.usage_records does not match usage.jsonl")
        for u in usage:
            if u.get("run_id") != manifest["run_id"]:
                problems.append(f"usage record {u.get('record_id')} has run_id {u.get('run_id')}")
    elif outputs.get("usage_records"):
        problems.append("usage.jsonl is missing")

    return problems
