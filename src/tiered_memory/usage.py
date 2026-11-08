"""Model-usage logger (task T02).

Writes one JSON line per model call. The rules come from the proposal:

* every call records which component made it, so cost can be split by
  coding agent, Curator, Router, retrieval and maintenance (4.12, Table 11);
* timestamps are UTC and durations come from a monotonic clock (4.11);
* a token count the provider did not return is written as ``"unavailable"``,
  never as 0 (4.6).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

USAGE_SCHEMA_VERSION = "usage-v0"
UNAVAILABLE = "unavailable"

COMPONENTS = frozenset(
    {"coding_agent", "curator", "router", "retrieval", "maintenance", "smoke_test"}
)

TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class UsageRecord:
    run_id: str
    component: str
    provider: str
    model_requested: str
    started_at_utc: str
    ended_at_utc: str
    duration_ms: float
    status: str  # "ok" | "error"
    model_served: str | None = None
    request_id: str | None = None
    stop_reason: str | None = None
    effort: str | None = None
    fallback_used: bool | None = None
    input_tokens: int | str = UNAVAILABLE
    output_tokens: int | str = UNAVAILABLE
    cache_creation_input_tokens: int | str = UNAVAILABLE
    cache_read_input_tokens: int | str = UNAVAILABLE
    error_type: str | None = None
    error_message: str | None = None
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    schema_version: str = USAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.component not in COMPONENTS:
            raise ValueError(f"unknown component {self.component!r}; expected one of {sorted(COMPONENTS)}")
        if self.status not in ("ok", "error"):
            raise ValueError(f"status must be 'ok' or 'error', got {self.status!r}")
        for name in TOKEN_FIELDS:
            value = getattr(self, name)
            if value is None:
                setattr(self, name, UNAVAILABLE)
            elif value != UNAVAILABLE and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise ValueError(f"{name} must be a non-negative int or {UNAVAILABLE!r}, got {value!r}")


def tokens_from_usage(usage: Any) -> dict[str, int | str]:
    """Read token counts from an SDK usage object; missing values become 'unavailable'."""
    out: dict[str, int | str] = {}
    for name in TOKEN_FIELDS:
        value = getattr(usage, name, None) if usage is not None else None
        out[name] = value if isinstance(value, int) and not isinstance(value, bool) else UNAVAILABLE
    return out


class UsageLogger:
    """Appends UsageRecords to a JSONL file. Each record is flushed and fsynced."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: UsageRecord) -> UsageRecord:
        line = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return record

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


class CallTimer:
    """Captures UTC start/end stamps plus a monotonic duration for one call."""

    def __init__(self, monotonic: Callable[[], float] = time.monotonic, clock: Callable[[], str] = utc_now_iso) -> None:
        self._monotonic = monotonic
        self._clock = clock
        self.started_at_utc = ""
        self.ended_at_utc = ""
        self.duration_ms = 0.0

    def __enter__(self) -> "CallTimer":
        self.started_at_utc = self._clock()
        self._t0 = self._monotonic()
        return self

    def __exit__(self, *exc: object) -> None:
        self.duration_ms = round((self._monotonic() - self._t0) * 1000, 3)
        self.ended_at_utc = self._clock()
