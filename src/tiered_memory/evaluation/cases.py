"""Load event cases and labels, and seed a case's starting memory into a run (task T09).

Seeds go through the run's traced writer, like any other write, so the
starting state is itself auditable (proposal 4.10: "formal component cases
will run from their specified starting states").

Short forms allowed in case seed payloads:

* evidence ``{"label", "kind", "locator", "outcome"?}``: expanded to a full
  evidence_ref with IDs and hashes derived from case_id + label;
* ``"$EVD:<label>"`` / ``"$EVT:<label>"``: the evidence_id / event_id of that evidence;
* ``"$EVENT_DEDUP_KEY"``: the dedup key of the case's own event (for F05 retries).
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from ..hooks.dedup import dedup_key_for_case_event
from ..schemas import schema_errors

REPO_ROOT = Path(__file__).resolve().parents[3]
CASES_DIR = REPO_ROOT / "cases"
SEED_TIME = "2026-11-01T08:00:00Z"


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def session_id_for(case: dict[str, Any]) -> str:
    return "ses_" + _h(f"{case['case_id']}:session:{case['event']['session_label']}")[:32]


def load_case(path: str | Path) -> dict[str, Any]:
    case = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = schema_errors(case, "event_case.schema.json")
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    if Path(path).stem != case["case_id"]:
        raise ValueError(f"{path}: file name does not match case_id {case['case_id']}")
    if not case["case_id"].startswith(f"{case['set']}-{case['family']}-"):
        raise ValueError(f"{path}: case_id does not match set and family")
    return case


def load_cases(set_name: str) -> list[dict[str, Any]]:
    return [load_case(p) for p in sorted((CASES_DIR / set_name).glob("*-F*-*.json"))]


def load_labels(path: str | Path) -> dict[str, Any]:
    labels = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = schema_errors(labels, "case_labels.schema.json")
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    return labels


class SeedContext:
    def __init__(self, case: dict[str, Any]) -> None:
        self.case = case
        self.commit = case["fixture"]["initial_commit"]
        self.evidence: dict[str, dict[str, Any]] = {}

    def evidence_ref(self, short: dict[str, Any]) -> dict[str, Any]:
        label = short["label"]
        base = f"{self.case['case_id']}:{label}"
        ev = {
            "evidence_id": "evd_" + _h(base + ":evd")[:32],
            "kind": short["kind"],
            "locator": short["locator"],
            "source_hash": "sha256:" + _h(base + ":content"),
            "source_commit": self.commit,
            "captured_at_utc": SEED_TIME,
            "event_id": "evt_" + _h(base + ":evt")[:32],
        }
        if short["kind"] in ("test", "command"):
            outcome = short.get("outcome", "pass")
            ev.update(outcome=outcome, exit_code=0 if outcome == "pass" else 1)
        self.evidence[label] = ev
        return ev

    def expand(self, value: Any) -> Any:
        if isinstance(value, dict):
            if set(value) >= {"label", "kind", "locator"} and set(value) <= {"label", "kind", "locator", "outcome"}:
                return self.evidence_ref(value)
            return {k: self.expand(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.expand(v) for v in value]
        if isinstance(value, str):
            if value == "$EVENT_DEDUP_KEY":
                return dedup_key_for_case_event(self.case["event"], session_id_for(self.case))
            if value.startswith("$EVD:"):
                return self.evidence[value[5:]]["evidence_id"]
            if value.startswith("$EVT:"):
                return self.evidence[value[5:]]["event_id"]
        return value


def seed_payload(case: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any]:
    ctx = SeedContext(case)
    payload = ctx.expand(copy.deepcopy(seed["payload"]))
    first = next(iter(ctx.evidence.values()), None)
    tier = seed["tier"]
    if tier == "project":
        payload.setdefault("source_commit", ctx.commit)
        if first:
            payload.setdefault("last_verification_event_id", first["event_id"])
    elif tier == "session":
        payload.setdefault("last_session_id", "ses_" + _h(f"{case['case_id']}:seed-session")[:32])
    elif tier == "daily_log":
        if first:
            payload.setdefault("event_id", first["event_id"])
        payload.setdefault("dedup_key", _h(f"{case['case_id']}:{seed['ref']}:dedup"))
    return payload


def seed_case(case: dict[str, Any], run) -> dict[str, dict[str, Any]]:
    """Write the case's starting memory through ``run.writer``. Returns {ref: written record}."""
    refs: dict[str, dict[str, Any]] = {}
    for seed in case["starting_memory"]:
        payload = seed_payload(case, seed)
        provenance = {
            "source_event_id": "evt_" + _h(f"{case['case_id']}:seed:{seed['ref']}")[:32],
            "decision_id": "dec_" + _h(f"{case['case_id']}:seed:{seed['ref']}")[:32],
            "policy_outcome": "accepted",
            "condition": "dev",
            "run_id": run.run_id,
        }
        if seed["tier"] == "project":
            result = run.writer.write_project("append", payload, provenance)
        elif seed["tier"] == "session":
            result = run.writer.write_session("append", payload, provenance)
        else:
            result = run.writer.append_log(payload, provenance)
        if result.executed == "no_op":
            raise ValueError(f"{case['case_id']}: seed {seed['ref']} was a no_op; seeds must be distinct")
        refs[seed["ref"]] = result.record
    return refs
