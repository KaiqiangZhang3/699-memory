"""Load the v1 JSON schemas and validate memory records (task T03).

Two layers:

1. JSON Schema (Draft 2020-12) for structure, IDs, enums and simple
   conditional rules.
2. Checks that JSON Schema cannot express: content_hash matches the record,
   and every evidence_id used in Session Memory resolves to an evidence object.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "v1"
KINDS = {
    "project": "project_memory.schema.json",
    "daily_log": "daily_log.schema.json",
    "session": "session_memory.schema.json",
}
# What content_hash covers (decision D4 in docs/requirements_v1.md).
# Project and Session Memory hash only their *content* fields, so a new
# version whose content is unchanged gets the same hash and the writer can
# turn it into a no_op (QR2). Version links, status, timestamps and
# provenance are left out. The Daily Log hashes the whole entry except
# provenance, because its hash chain is the integrity check (4.14).
HASH_FIELDS: dict[str, frozenset[str] | None] = {
    "project": frozenset({"project_id", "memory_id", "category", "claim", "paths", "tags"}),
    "session": frozenset({
        "project_id", "session_memory_id", "task_id", "status", "goal", "progress",
        "tentative_findings", "failed_attempts", "blockers", "next_steps", "evidence",
    }),
    "daily_log": None,  # None = every field except the excluded ones below
}
ALWAYS_EXCLUDED = frozenset({"content_hash", "provenance"})


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_content_hash(record: dict[str, Any]) -> str:
    """sha256 of the canonical JSON of the fields that HASH_FIELDS selects for the record's tier."""
    tier = record.get("tier")
    if tier not in HASH_FIELDS:
        raise ValueError(f"cannot hash a record with tier {tier!r}")
    fields = HASH_FIELDS[tier]
    payload = {
        k: v for k, v in record.items()
        if k not in ALWAYS_EXCLUDED and (fields is None or k in fields)
    }
    return sha256_text(canonical_json(payload))


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resources.append((contents["$id"], Resource.from_contents(contents)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator_for(kind: str) -> Draft202012Validator:
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; expected one of {sorted(KINDS)}")
    schema = json.loads((SCHEMA_DIR / KINDS[kind]).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry())


def validate_record(record: dict[str, Any], kind: str | None = None) -> list[str]:
    """Return a list of human-readable problems; an empty list means the record is valid."""
    kind = kind or record.get("tier")
    if kind not in KINDS:
        return [f"cannot determine tier (got {kind!r})"]

    errors = [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in sorted(validator_for(kind).iter_errors(record), key=lambda e: list(e.absolute_path))
    ]
    if errors:
        return errors

    if record["content_hash"] != compute_content_hash(record):
        errors.append("content_hash: does not match the record content")

    if kind == "session":
        known = {e["evidence_id"] for e in record["evidence"]}
        used: list[str] = []
        for section in ("progress", "tentative_findings", "failed_attempts"):
            for item in record[section]:
                used.extend(item["evidence_ids"])
        for missing in sorted(set(used) - known):
            errors.append(f"evidence_ids: {missing} is not in the record's evidence list")
    return errors
