from types import SimpleNamespace

import pytest

from tiered_memory.model_client import FALLBACK_BETA, call_model
from tiered_memory.usage import UNAVAILABLE, UsageLogger


class FakeMessages:
    """Deterministic test double for client.beta.messages."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def fake_client(messages):
    return SimpleNamespace(beta=SimpleNamespace(messages=messages))


def fake_response(stop_reason="end_turn", text="OK", usage=None, model="claude-opus-5-5"):
    if usage is None:
        usage = SimpleNamespace(
            input_tokens=12,
            output_tokens=4,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            iterations=[SimpleNamespace(type="message")],
        )
    resp = SimpleNamespace(
        model=model,
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        usage=usage,
    )
    resp._request_id = "req_test"
    return resp


def test_success_logs_one_record_with_tokens(tmp_path):
    logger = UsageLogger(tmp_path / "u.jsonl")
    msgs = FakeMessages(fake_response())
    reply = call_model(fake_client(msgs), logger=logger, run_id="r", component="smoke_test",
                       messages=[{"role": "user", "content": "hi"}])
    assert reply.text == "OK"
    rows = logger.read_all()
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "ok"
    assert row["input_tokens"] == 12 and row["output_tokens"] == 4
    assert row["model_served"] == "claude-opus-5-5"
    assert row["request_id"] == "req_test"
    assert row["fallback_used"] is False
    assert row["duration_ms"] >= 0


def test_request_shape(tmp_path):
    msgs = FakeMessages(fake_response())
    call_model(fake_client(msgs), logger=UsageLogger(tmp_path / "u.jsonl"), run_id="r",
               component="curator", messages=[{"role": "user", "content": "hi"}], effort="medium")
    sent = msgs.calls[0]
    assert sent["model"] == "claude-opus-5-5"
    assert sent["output_config"] == {"effort": "medium"}
    assert sent["betas"] == [FALLBACK_BETA] and sent["fallbacks"] == "default"
    assert "thinking" not in sent and "temperature" not in sent


def test_no_fallback_option(tmp_path):
    msgs = FakeMessages(fake_response())
    call_model(fake_client(msgs), logger=UsageLogger(tmp_path / "u.jsonl"), run_id="r",
               component="curator", messages=[], use_fallback=False)
    assert "fallbacks" not in msgs.calls[0] and "betas" not in msgs.calls[0]


def test_fallback_detected(tmp_path):
    usage = SimpleNamespace(input_tokens=1, output_tokens=1,
                            iterations=[SimpleNamespace(type="message"), SimpleNamespace(type="fallback_message")])
    logger = UsageLogger(tmp_path / "u.jsonl")
    call_model(fake_client(FakeMessages(fake_response(usage=usage, model="claude-opus-4-8"))),
               logger=logger, run_id="r", component="curator", messages=[])
    row = logger.read_all()[0]
    assert row["fallback_used"] is True
    assert row["model_served"] == "claude-opus-4-8"
    assert row["cache_read_input_tokens"] == UNAVAILABLE


def test_refusal_returns_no_text(tmp_path):
    logger = UsageLogger(tmp_path / "u.jsonl")
    reply = call_model(fake_client(FakeMessages(fake_response(stop_reason="refusal", text="partial"))),
                       logger=logger, run_id="r", component="curator", messages=[])
    assert reply.text == "" and reply.stop_reason == "refusal"
    assert logger.read_all()[0]["stop_reason"] == "refusal"


def test_error_is_logged_then_reraised(tmp_path):
    logger = UsageLogger(tmp_path / "u.jsonl")
    with pytest.raises(RuntimeError):
        call_model(fake_client(FakeMessages(error=RuntimeError("boom"))), logger=logger,
                   run_id="r", component="router", messages=[])
    row = logger.read_all()[0]
    assert row["status"] == "error"
    assert row["error_type"] == "RuntimeError"
    assert row["input_tokens"] == UNAVAILABLE
