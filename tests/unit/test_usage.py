import json
from types import SimpleNamespace

import pytest

from tiered_memory.usage import UNAVAILABLE, CallTimer, UsageLogger, UsageRecord, tokens_from_usage


def make_record(**overrides):
    base = dict(
        run_id="r1",
        component="curator",
        provider="anthropic",
        model_requested="m",
        started_at_utc="2026-11-08T00:00:00.000+00:00",
        ended_at_utc="2026-11-08T00:00:01.000+00:00",
        duration_ms=1000.0,
        status="ok",
    )
    base.update(overrides)
    return UsageRecord(**base)


def test_missing_tokens_are_unavailable_not_zero():
    rec = make_record()
    assert rec.input_tokens == UNAVAILABLE
    assert rec.output_tokens == UNAVAILABLE


def test_none_tokens_normalised_to_unavailable():
    assert make_record(input_tokens=None).input_tokens == UNAVAILABLE


def test_zero_tokens_are_kept_as_zero():
    assert make_record(cache_read_input_tokens=0).cache_read_input_tokens == 0


@pytest.mark.parametrize("bad", [-1, 1.5, True, "12"])
def test_invalid_token_values_rejected(bad):
    with pytest.raises(ValueError):
        make_record(input_tokens=bad)


def test_unknown_component_rejected():
    with pytest.raises(ValueError):
        make_record(component="hook")


def test_tokens_from_usage_partial():
    usage = SimpleNamespace(input_tokens=10, output_tokens=3, cache_creation_input_tokens=None)
    tokens = tokens_from_usage(usage)
    assert tokens["input_tokens"] == 10
    assert tokens["output_tokens"] == 3
    assert tokens["cache_creation_input_tokens"] == UNAVAILABLE
    assert tokens["cache_read_input_tokens"] == UNAVAILABLE


def test_tokens_from_usage_none():
    assert set(tokens_from_usage(None).values()) == {UNAVAILABLE}


def test_logger_appends_one_json_line_per_record(tmp_path):
    logger = UsageLogger(tmp_path / "nested" / "usage.jsonl")
    logger.write(make_record(input_tokens=5))
    logger.write(make_record(component="router"))
    lines = (tmp_path / "nested" / "usage.jsonl").read_text().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["input_tokens"] == 5
    assert first["schema_version"] == "usage-v0"
    assert [r["component"] for r in logger.read_all()] == ["curator", "router"]
    assert first["record_id"] != json.loads(lines[1])["record_id"]


def test_call_timer_uses_monotonic_clock():
    ticks = iter([100.0, 100.25])
    stamps = iter(["start", "end"])
    with CallTimer(monotonic=lambda: next(ticks), clock=lambda: next(stamps)) as t:
        pass
    assert t.duration_ms == 250.0
    assert (t.started_at_utc, t.ended_at_utc) == ("start", "end")
