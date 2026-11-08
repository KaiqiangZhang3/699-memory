# Component Contract — Memory Store and Versioned Writer (v1)

| Field | Value |
|---|---|
| Task / commitment | T07 / C03 |
| Code | `src/tiered_memory/memory/store.py` (read only), `src/tiered_memory/memory/writer.py` (the only writer) |
| Tests | `tests/unit/test_memory_writer.py` |
| Proposal | Table 5 (Versioned Writer), FR2, QR1, QR2, 3.11; decisions D1 and D4 |

## Who may call it

Only the Policy Gate (T13) and the review flow, after an `accepted` decision. Hooks, the Curator and the Router get **no writer object** (FR1, TH10). The writer also refuses any provenance whose `policy_outcome` is not `accepted`.

## Operations

| Call | Tier | Effect | Becomes `no_op` when | Rejected (`WriteRejected.reason`) when |
|---|---|---|---|---|
| `write_project("append", payload, prov)` | P | Creates `memory_id` and writes v1 | An active or uncertain record already has the same category, claim, paths and tags | `invalid_record` (schema / D3), `cross_project`, `bad_payload`, `not_accepted` |
| `write_project("update", {memory_id, …}, prov, base)` | P | New version. Only status, support, evidence, source_commit, verified_at_utc and last_verification_event_id may change. | None of those fields change | `content_change` (the claim, category, paths or tags differ; use supersede), `stale_base`, `missing_base`, `unknown_record` |
| `write_project("supersede", {memory_id, …}, prov, base)` | P | New version with new content; `verified_at_utc` = now | The content is unchanged | same as update |
| `write_project("archive", {memory_id}, prov, base)` | P | New version with `status: archived` | Already archived | same as update |
| `rollback_project(memory_id, to_version_id, prov, base)` | P | Writes the old version's content **forward** as a new version (operation `supersede`) | The target content equals the current content | `unknown_record` |
| `write_session("append" / "update" / "archive", …)` | S | v1 for a new `task_id`, then new versions | The content is unchanged | `already_exists` (append on an existing task) + the same reasons as P |
| `append_log(payload, prov)` | L | Appends one line; sets `sequence` and `prev_entry_hash` | The `dedup_key` is already in the log | `invalid_record`, `cross_project`, `bad_payload`, `not_accepted` |

`base` is the `version_id` the caller last read. A mismatch means someone else wrote in between. The write is refused (`stale_base`) and the caller must re-read; there is no automatic merge.

## Guarantees

1. **Validate before disk.** The complete record passes `validate_record` before any file is created, so a rejected call leaves the store byte-for-byte unchanged (tested).
2. **Write-once versions.** A version file is written to a temp file, fsynced, then hard-linked into place. The link fails if the name exists, so no version is ever overwritten. Old versions stay byte-identical.
3. **Atomic log append.** The day's JSONL file is rewritten in full to a temp file and swapped in with `os.replace`. A crash leaves either the old file or the new one, never a half-written line.
4. **"Superseded" is derived.** Because files never change, an old version keeps its original `status`. A version is superseded if and only if a later version exists.
5. **No delete.** The strongest action is archive; rollback moves forward.
6. **One project per store.** `project_id` comes from the store. A payload naming another project is refused (IC2).

## Audit hooks

- `MemoryStore.verify()` checks schema validity, `content_hash`, contiguous version numbers, `supersedes` links, ID/directory agreement, and the Daily Log sequence, hash chain and unique `dedup_key`. It also reports stray files such as left-over temp files.
- `MemoryStore.snapshot()` returns every stored record in a stable order. T08 hashes and persists it at every write and checkpoint (4.11).

## Not covered yet

- Markdown views for human reading (generated, never authoritative) are planned with the Resume Pack (T14).
- Concurrent writers are not supported: the prototype runs one process per run (1.10).
