"""Thin wrapper around the Anthropic Messages API that logs usage for every call.

This is the disposable interface for T02. The model, effort and fallback
settings are **not** the pinned study configuration; that is decided under
DEC-04 before the Week 5 pilot.

The ``client`` argument is any object with ``beta.messages.create(...)``, so
tests can pass a deterministic fake and never touch the network (proposal 5.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .usage import CallTimer, UsageLogger, UsageRecord, tokens_from_usage

DEFAULT_MODEL = "claude-opus-5-5"
PROVIDER = "anthropic"
# Server-side refusal fallback ("default" routes by refusal category).
# NOTE for DEC-04: a fallback means another model may answer, which conflicts
# with a pinned model during formal collection. Every record logs
# model_served and fallback_used so this stays visible.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class ModelReply:
    text: str
    stop_reason: str | None
    record: UsageRecord


def _fallback_used(usage: Any) -> bool | None:
    iterations = getattr(usage, "iterations", None)
    if iterations is None:
        return None
    return any(getattr(it, "type", None) == "fallback_message" for it in iterations)


def call_model(
    client: Any,
    *,
    logger: UsageLogger,
    run_id: str,
    component: str,
    messages: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16000,
    effort: str | None = "low",
    system: str | None = None,
    use_fallback: bool = True,
) -> ModelReply:
    """Make one Messages API call and append exactly one usage record (success or failure)."""
    kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system is not None:
        kwargs["system"] = system
    if effort is not None:
        kwargs["output_config"] = {"effort": effort}
    if use_fallback:
        kwargs["betas"] = [FALLBACK_BETA]
        kwargs["fallbacks"] = "default"

    timer = CallTimer()
    try:
        with timer:
            response = client.beta.messages.create(**kwargs)
    except Exception as exc:  # the failure is logged, then re-raised to the caller
        logger.write(
            UsageRecord(
                run_id=run_id,
                component=component,
                provider=PROVIDER,
                model_requested=model,
                started_at_utc=timer.started_at_utc,
                ended_at_utc=timer.ended_at_utc,
                duration_ms=timer.duration_ms,
                status="error",
                effort=effort,
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
            )
        )
        raise

    usage = getattr(response, "usage", None)
    record = logger.write(
        UsageRecord(
            run_id=run_id,
            component=component,
            provider=PROVIDER,
            model_requested=model,
            model_served=getattr(response, "model", None),
            request_id=getattr(response, "_request_id", None),
            started_at_utc=timer.started_at_utc,
            ended_at_utc=timer.ended_at_utc,
            duration_ms=timer.duration_ms,
            status="ok",
            stop_reason=getattr(response, "stop_reason", None),
            effort=effort,
            fallback_used=_fallback_used(usage),
            **tokens_from_usage(usage),
        )
    )

    # Check stop_reason before reading content: a refusal may carry no text.
    text = ""
    if response.stop_reason != "refusal":
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    return ModelReply(text=text, stop_reason=response.stop_reason, record=record)
