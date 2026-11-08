# tiered-memory

Prototype for *Design and Evaluation of an Automated Three-Tier External Memory System for Long-Horizon Coding Agents* (CISC 699 Capstone II, Kaiqiang Zhang; GRAD 695 proposal, Sept 26, 2026).

Status: **Week 1 skeleton (T02).** Only the usage logger and a disposable model call exist. The component packages are empty placeholders.

## Setup

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```

Tested with Python 3.13.2, anthropic 2.6.0, pytest 9.2.0, jsonschema 4.26.0 and Git 2.49.0 (macOS).

## Disposable model call (T02)

```bash
export ANTHROPIC_API_KEY=...   # or: ant auth login
.venv/bin/python scripts/smoke_model_call.py
```

This sends one request and appends one record to `runs/smoke/usage.jsonl`. A failed call is logged too. The settings used here (`claude-opus-5-5`, effort `low`, server-side refusal fallback on) are **not** the pinned study configuration. That configuration is decided under DEC-04 before the Week 5 pilot.

## Layout

| Path | Purpose | Task |
|---|---|---|
| `src/tiered_memory/usage.py` | Usage logger: UTC timestamps, monotonic duration, per-component records, `"unavailable"` instead of 0 | T02 |
| `src/tiered_memory/model_client.py` | Messages API wrapper; logs one record per call | T02 |
| `src/tiered_memory/{memory,hooks,queue,curator,router,policy,review,maintenance,resume}/` | Components from proposal Table 5 | T07–T19 |
| `schemas/v1/` | P/L/S JSON schemas | T03 |
| `fixtures/pilot/`, `fixtures/formal/` | Kept separate (C02) | T06 (RC) |
| `cases/dev/`, `cases/formal/` | 12 development cases / 60 formal cases | T09, T18 |
| `prompts/` | Versioned Curator/Router prompts | T11 |
| `records/Wxx/` | Weekly short records | T32 |
| `runs/` | Raw run output (git-ignored) | — |

Tests never call a live model; they use a deterministic fake client (proposal 5.5).
