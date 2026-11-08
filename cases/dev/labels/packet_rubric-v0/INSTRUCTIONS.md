# Blind labelling task — 12 development memory-event cases

You are an independent annotator. Label each case in `cases/` with the memory decisions a correct system should make.

## Use ONLY the files in this folder

- `cases/*.json` — 12 cases. Each one has a starting memory state and one observed event.
- `event_families_v1.json` and `event_taxonomy.md` — the 10 event families and their allowed handling.
- `memory_rules.md` — the three tiers and decisions D1–D5 (D3 = which evidence allows a Project Memory write).
- `rubric.md` — how to fill each label field.
- `case_labels.schema.json` and `common.schema.json` — the required output format.

Do **not** open, search or list anything outside this folder, including any project repository, git history or other label files. Your labels must be independent.

## What to produce

Write one JSON file, `output/labels.json`, that validates against `case_labels.schema.json`:

- `labels_version`: "labels-v1"; `rubric_version`: "rubric-v0"; `set`: "dev"
- `labeler`: "claude-b"; `labeler_kind`: "ai"
- `labeler_note`: one sentence saying that you are an AI labeller in a fresh context and saw only this packet
- `labeled_at_utc`: the current UTC time, e.g. "2026-11-08T13:00:00Z"
- `independent_of_system_output`: true
- `labels`: one entry per case_id. Each entry has `expected`, `acceptable_alternatives`, `target_ref` (the seed `ref` the change applies to, or null), `required_claim_points`, `forbidden` (at least one), `forbidden_strings` (only where literal strings must never appear), `rationale`, and `uncertain` (true if you are not confident).

Rules:

- Decide the family yourself from the event. The `family` field on each case says which family the case was written for. If you think the event belongs to a different family, label what a correct system should do, and say so in the rationale.
- Each decision list (expected, and each alternative) must be one of the lists allowed for that family in `event_families_v1.json`. Leave out alternatives whose conditions the case does not meet.
- Judge what is correct; do not guess what the case author intended.

When you are done, reply with a short summary: any cases where you set `uncertain`, where the rubric or rules were unclear, and where you disagreed with the case's stated family.
