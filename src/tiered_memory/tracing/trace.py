"""Hash-chained JSONL trace for one run (task T08).

Each line carries ``prev_hash`` (the previous line's ``line_hash``) and its own
``line_hash`` over everything else. A deleted, reordered or edited line breaks
the chain, so missing evidence is detectable (threat TH11).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from ..schemas import canonical_json, schema_errors, sha256_text
from ..usage import utc_now_iso

TRACE_SCHEMA = "trace_event.schema.json"


def line_hash(event: dict[str, Any]) -> str:
    return sha256_text(canonical_json({k: v for k, v in event.items() if k != "line_hash"}))


class TraceLog:
    def __init__(
        self,
        path: str | Path,
        run_id: str,
        clock: Callable[[], str] = utc_now_iso,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.clock = clock
        self.monotonic = monotonic
        self._t0 = monotonic()
        self._seq = 0
        self._last_hash: str | None = None
        if self.path.exists() and self.path.stat().st_size:
            raise FileExistsError(f"{self.path} already has events; a trace is never reopened")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def count(self) -> int:
        return self._seq

    def emit(self, kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "trace_version": "trace-v1",
            "run_id": self.run_id,
            "seq": self._seq + 1,
            "at_utc": self.clock(),
            "mono_ms": round((self.monotonic() - self._t0) * 1000, 3),
            "kind": kind,
            "payload": payload or {},
            "prev_hash": self._last_hash,
        }
        event["line_hash"] = line_hash(event)
        errors = schema_errors(event, TRACE_SCHEMA)
        if errors:
            raise ValueError("invalid trace event: " + "; ".join(errors))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(canonical_json(event) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._seq += 1
        self._last_hash = event["line_hash"]
        return event


def read_trace(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
