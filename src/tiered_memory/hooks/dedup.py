"""Deduplication key for observed events (defined in T09, used by Hook adapters in T10).

Two observations get the same key exactly when they are the same event
delivered twice: same Hook type, same task and session, same source, same
content. The observation time is deliberately left out, so a retry that
arrives later still matches (family F05, QR2).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_dedup_key(
    *,
    hook_event_type: str,
    task_id: str | None,
    session_id: str | None,
    source_kind: str,
    source_locator: str,
    content: str,
) -> str:
    payload = {
        "hook_event_type": hook_event_type,
        "task_id": task_id,
        "session_id": session_id,
        "source_kind": source_kind,
        "source_locator": source_locator,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def dedup_key_for_case_event(event: dict[str, Any], session_id: str) -> str:
    return compute_dedup_key(
        hook_event_type=event["hook_event_type"],
        task_id=event["task_id"],
        session_id=session_id,
        source_kind=event["source"]["kind"],
        source_locator=event["source"]["locator"],
        content=event["content"],
    )
