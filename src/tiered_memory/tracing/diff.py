"""Compare two run snapshots: which records were added between them (task T08).

Stored records are never changed or removed (D1), so the only legitimate
difference between an earlier and a later snapshot is added records. Anything
else is reported as an integrity problem.
"""

from __future__ import annotations

from typing import Any


def _index(snap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for versions in snap["project"].values():
        for v in versions:
            out[v["version_id"]] = v
    for versions in snap["session"].values():
        for v in versions:
            out[v["version_id"]] = v
    for entries in snap["daily_log"].values():
        for e in entries:
            out[e["entry_id"]] = e
    return out


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list]:
    a, b = _index(before), _index(after)
    added = [
        {
            "tier": rec["tier"],
            "id": rid,
            "operation": rec["provenance"]["operation"],
            "source_event_id": rec["provenance"]["source_event_id"],
            "summary": rec.get("claim") or rec.get("summary") or rec.get("goal"),
            "status": rec.get("status"),
            "version": rec.get("version") or rec.get("sequence"),
        }
        for rid, rec in b.items() if rid not in a
    ]
    removed = sorted(rid for rid in a if rid not in b)
    changed = sorted(rid for rid in a if rid in b and a[rid] != b[rid])
    return {"added": sorted(added, key=lambda r: r["id"]), "removed": removed, "changed": changed}
