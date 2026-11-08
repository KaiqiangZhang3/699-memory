# Event Taxonomy — v1

| Field | Value |
|---|---|
| Task / commitment | T04 / C01 (design package), K04 (taxonomy as a contribution) |
| Source | Proposal 4.5 (ten families × six formal cases) and Appendix D (purpose, typical handling) |
| Machine-readable copy | `cases/event_families_v1.json`. Tests check that it agrees with the schemas. |
| Used by | T09 (12 development cases), T18 (60 formal cases), T20 (labels), T12 (Router tests) |

## 1. Two separate labels: what was observed and what it means

| Label | Set by | Values |
|---|---|---|
| **Hook event type**: what was observed | Hook adapter (T10), deterministically | `session_start`, `session_end`, `task_start`, `task_complete`, `command_run`, `test_run`, `code_change`, `user_message`, `maintenance_tick` |
| **Event family**: what the event means for memory | Reference label (T20) | F01–F10 below |

The two labels do not map one to one. A `test_run`, for example, can be F02 (validation passed), F04 (attempt failed) or F05 (retry). Telling them apart is exactly the semantic work the Curator does (FR3). The family label is the reference answer used for scoring: it is attached to a test case and is never given to the system.

## 2. The ten families

Each family's **expected handling** is a list of decisions, one per tier touched, given as *tier / operation / policy outcome*. Any listed alternative also counts as correct, because the proposal allows multiple acceptable outcomes (4.15). "L", "S" and "P" are Daily Log, Session Memory and Project Memory.

| ID | Family | Definition | Expected | Also acceptable | Must never happen |
|---|---|---|---|---|---|
| F01 | Stable project fact | A command, constraint, convention, architectural boundary or procedure that holds beyond the current task, with evidence meeting rule D3 | L append + P append | L append + P review (evidence borderline) | A P write that fails D3 or that the evidence does not support |
| F02 | Task completion and validation | A task finishes and validation runs | L append + S update | L + S + P append, if the validation also proves a reusable fact | A step marked done without a passing test; task progress promoted to P |
| F03 | Unfinished session state | A session ends with the task incomplete | L append + S update | — | An active or paused S without a next step; tentative findings in P |
| F04 | Failed attempt | An approach failed validation | L append + S update (failed attempt) | — | A failure written as a P rule; a failed attempt without failing evidence |
| F05 | Repeated event | A Hook retry or duplicate delivery | `no_op` on the original's tier | — | A second canonical record or version for the same content |
| F06 | Conflicting claim | New information contradicts an active P record and the winner is unclear | L append + P review | L append + P supersede, if the new evidence is authoritative | Silent overwrite; two contradicting active P records |
| F07 | Changed or stale reference | A path, command or interface named by memory has changed or disappeared | L append + P supersede | P update (status → `uncertain`); P review | The stale record left active; history erased |
| F08 | Explicit user correction | The user corrects a remembered fact or decision | L append + P supersede (`user_approved`, `user_correction` evidence) | L append + S update, if the corrected item was task state | A corrected version without the correction as evidence; the correction ignored |
| F09 | Synthetic sensitive string | The event contains a credential-like dummy string | Every durable write blocked | A redacted L append in addition | The secret appearing in memory, traces or a model request |
| F10 | Irrelevant event | No lasting value (e.g. an exploratory `ls`) | Skip: no write; decision trace only | — | Any P or S write |

## 3. Design rules this taxonomy relies on

1. **Every family except F05 and F10 leaves evidence in the Daily Log** (F09 only in redacted form), so the raw episode survives even when later summaries are wrong (2.5.2).
2. **Only F01, F06, F07 and F08 can change Project Memory.** F02 can too, if it meets D3. Every other family that tries to is counted as an *incorrect Project Memory write* (Table 10).
3. **There is no delete.** The strongest change is `supersede` or `archive`. F07 and F08 keep the old version.
4. **Review is a correct outcome, not a failure,** where the table lists it. Reviews outside those cells count as *false escalations* (EQ4).

## 4. Coverage plan for cases (T09, T18)

| Set | Per family | Total | Use |
|---|---|---|---|
| Development cases | 1–2 (12 in total; F01, F04, F06 and F07 get two) | 12 | Instrumentation, rubric v0, pilot. Excluded from formal scores. |
| Formal cases | 6 | 60 | Frozen before the pilot, labelled independently, replayed 3 times |

Within each family, the six formal cases should vary:

- which Hook event type triggers the case (use at least two types where the table lists more than one);
- evidence strength (at least one case at the D3 boundary, for F01, F06 and F07);
- distractors (at least one case where an irrelevant detail is mixed in).
