"""T02 disposable model call: one real request, one usage record.

Usage (credentials come from ANTHROPIC_API_KEY or an `ant auth login` profile):

    .venv/bin/python scripts/smoke_model_call.py

The usage record is appended to runs/smoke/usage.jsonl. Copy that line into
records/W01/ as evidence for the Week 1 completion check.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tiered_memory.model_client import call_model  # noqa: E402
from tiered_memory.usage import UsageLogger  # noqa: E402


def main() -> int:
    run_id = "smoke-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger = UsageLogger(ROOT / "runs" / "smoke" / "usage.jsonl")
    client = anthropic.Anthropic()
    try:
        reply = call_model(
            client,
            logger=logger,
            run_id=run_id,
            component="smoke_test",
            messages=[{"role": "user", "content": "Reply with the single word OK."}],
        )
    except TypeError as e:
        if "authentication method" not in str(e):
            raise
        print("No credentials found: set ANTHROPIC_API_KEY (or run `ant auth login`). Failure was logged.")
        return 2
    except anthropic.AuthenticationError:
        print("Authentication failed: set ANTHROPIC_API_KEY (or run `ant auth login`). Failure was logged.")
        return 2
    except anthropic.RateLimitError:
        print("Rate limited; try again later. Failure was logged.")
        return 3
    except anthropic.APIStatusError as e:
        print(f"API error {e.status_code}: {e.message}. Failure was logged.")
        return 4
    except anthropic.APIConnectionError:
        print("Network error; could not reach the API. Failure was logged.")
        return 5

    r = reply.record
    print(f"run_id={run_id} stop_reason={reply.stop_reason} reply={reply.text.strip()!r}")
    print(
        f"model_served={r.model_served} input_tokens={r.input_tokens} "
        f"output_tokens={r.output_tokens} duration_ms={r.duration_ms} fallback_used={r.fallback_used}"
    )
    print(f"logged to {logger.path}")
    return 0 if reply.stop_reason != "refusal" else 1


if __name__ == "__main__":
    raise SystemExit(main())
