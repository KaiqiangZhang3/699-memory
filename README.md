# tiered-memory

Prototype for *Design and Evaluation of an Automated Three-Tier External Memory System for Long-Horizon Coding Agents* (CISC 699 Capstone II, Kaiqiang Zhang; GRAD 695 proposal, Sept 26, 2026).

Status: **`design-v1`, Stage Two fixture skeleton, the memory store with its Versioned Writer, run tracing, and the development cases with rubric v0 (T01–T09).**

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

## Stage Two fixture (T06)

```bash
.venv/bin/python scripts/fixture_baseline.py formal/taskservice
```

This builds a fresh git repo from the fixture source (with a fixed commit SHA), runs its tests, and records the result in `fixtures/baselines/` and `fixtures/manifest.json`. Rerun it whenever the fixture source changes; a test fails if the manifest is out of date.

## Layout

| Path | Purpose | Task |
|---|---|---|
| `src/tiered_memory/usage.py` | Usage logger: UTC timestamps, monotonic duration, per-component records, `"unavailable"` instead of 0 | T02 |
| `src/tiered_memory/model_client.py` | Messages API wrapper; logs one record per call | T02 |
| `src/tiered_memory/memory/` | Read-only `MemoryStore` + `VersionedWriter` (the only writer); contract in `docs/contracts/memory_store.md` | T07 |
| `src/tiered_memory/tracing/` | Run manifest, hash-chained trace, snapshots, `audit_run`, `diff_snapshots`; contract in `docs/contracts/tracing.md` | T08 |
| `src/tiered_memory/{hooks,queue,curator,router,policy,review,maintenance,resume}/` | Remaining components from proposal Table 5 | T10–T19 |
| `schemas/v1/` | P/L/S JSON schemas | T03 |
| `fixtures/formal/taskservice/` | Stage Two fixture (state before task T1); `manifest.json` records the commit SHA and the baseline | T06 |
| `fixtures/pilot/` | Pilot fixture, kept separate from the formal one (C02); not built yet | T22 |
| `cases/dev/` | 12 development cases + labels (rubric v0, `docs/rubric_v0.md`) | T09 |
| `cases/formal/` | 60 formal cases (not yet written) | T18 |
| `src/tiered_memory/evaluation/` | Case loader / seeding, scorer v0 | T09 |
| `prompts/` | Versioned Curator/Router prompts | T11 |
| `records/Wxx/` | Weekly short records | T32 |
| `runs/` | Raw run output (git-ignored) | — |

Tests never call a live model; they use a deterministic fake client (proposal 5.5).
