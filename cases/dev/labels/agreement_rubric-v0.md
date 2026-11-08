# Label Agreement — development cases, rubric v0 (before adjudication)

| Field | Value |
|---|---|
| Task | T09 (rubric v0), as a dry run of the T20 procedure |
| Set A | `rubric-v0_claude-a.json`. Claude, in the authoring session; the same agent wrote the cases, taxonomy and rubric. **AI, not independent of the case design.** |
| Set B | `rubric-v0_claude-b.json`. A fresh Claude subagent that saw only the blind packet below. **AI, independent context.** |
| Human review | **None yet.** Neither set has been reviewed by Kaiqiang Zhang. |
| Status | Disagreements recorded; **not adjudicated** (see §3). |

## 1. Results

| Measure | claude-a vs claude-b |
|---|---|
| Same best answer (`expected`) | 11/12 |
| At least one shared acceptable answer | 12/12 |
| Identical acceptable-answer sets | 9/12 |
| Same target record | 12/12 |
| Cohen's κ on `expected` (descriptive, n=12) | 0.90 |

| Case | A expected | B expected | Best agree | Overlap | Only A accepts | Only B accepts | Target agree | Uncertain |
|---|---|---|---|---|---|---|---|---|
| dev-F01-01 | L append + P append | L append + P append | yes | yes | — | — | yes |  |
| dev-F01-02 | L append + P append | L append + P append | yes | yes | L append + P review? | — | yes |  |
| dev-F02-01 | L append + S update | L append + S update | yes | yes | — | L append + P append + S update | yes |  |
| dev-F03-01 | L append + S update | L append + S update | yes | yes | — | — | yes |  |
| dev-F04-01 | L append + S update | L append + S update | yes | yes | — | — | yes |  |
| dev-F05-01 | L no_op | L no_op | yes | yes | — | — | yes |  |
| dev-F06-01 | L append + P review? | L append + P review? | yes | yes | — | — | yes |  |
| dev-F06-02 | L append + P supersede | L append + P review? | **no** | yes | — | — | yes | yes |
| dev-F07-01 | L append + P supersede | L append + P supersede | yes | yes | L append + P review? | — | yes |  |
| dev-F08-01 | L append + P supersede | L append + P supersede | yes | yes | — | — | yes | yes |
| dev-F09-01 | * *✗ | * *✗ | yes | yes | — | — | yes |  |
| dev-F10-01 | skip | skip | yes | yes | — | — | yes |  |

Notation: L = Daily Log, S = Session, P = Project; `?` = review_required, `✗` = blocked; `*` = any tier.

## 2. How set B was kept blind

The packet contained the case files with the `purpose` field removed, because that field states the author's intended handling. It also contained the family table, the taxonomy §1–3, the rubric §1–4 (with its one example that named a dev case removed), the tier and D1–D5 rules, the label schema, and `packet_rubric-v0/INSTRUCTIONS.md`. A check confirmed that no packet document except the case files themselves contains a dev case ID. Case titles were left in, as any labeller would see them. Some titles describe the evidence (e.g. "Unverified claim…"), which may have nudged both sets the same way.

| Packet file | sha256 (first 16) |
|---|---|
| `INSTRUCTIONS.md` | `c9ca4d56d1583f05` |
| `case_labels.schema.json` | `4744de0084747eef` |
| `cases/dev-F01-01.json` | `3077df3ee851a85e` |
| `cases/dev-F01-02.json` | `c6c592780251d33e` |
| `cases/dev-F02-01.json` | `61444b4b16961384` |
| `cases/dev-F03-01.json` | `aad2bb5f95a94961` |
| `cases/dev-F04-01.json` | `f674875e773e448f` |
| `cases/dev-F05-01.json` | `71a5bb29717182a3` |
| `cases/dev-F06-01.json` | `5936714bf5c6f442` |
| `cases/dev-F06-02.json` | `9c5bf84d5a1ded64` |
| `cases/dev-F07-01.json` | `df38c1d3286b0759` |
| `cases/dev-F08-01.json` | `a56b92b35ef3133e` |
| `cases/dev-F09-01.json` | `9f6e8bff5f42edcd` |
| `cases/dev-F10-01.json` | `6fd15694a1e5943a` |
| `common.schema.json` | `745e5caba466b0b8` |
| `event_families_v1.json` | `046407d16b01265e` |
| `event_taxonomy.md` | `506bc35af0e40659` |
| `memory_rules.md` | `77678f57c9fb523e` |
| `rubric.md` | `0db1be17e38d83c7` |

## 3. Disagreements and issues for adjudication

1. **dev-F06-02: best answer differs** (A: supersede; B: review, marked uncertain). Both accept both, so scoring is unaffected. Question: is a passing test whose behaviour is inferred mostly from its name "authoritative" under D3?
2. **dev-F02-01: B also accepts a P append** of the test command. A excluded it because the case is about task completion. Question: when a completion event also re-confirms an already-known command, is a P write acceptable, or should it be `no_op` against an existing record? (In this case, no command record exists in the starting memory.)
3. **dev-F01-02 and dev-F07-01: A accepts review, B does not.** B's position is that review is wrong when the evidence is unambiguous. Rubric v1 needs a rule for when review counts as an acceptable cautious answer and when it counts as a false escalation.
4. **Rule conflict found by B (dev-F08-01).** `memory_rules.md` D3 says a `command` needs `test_validated` *or* `user_approved`, but it also explains this as "a command must have actually run". A user correction to a command that has not been run satisfies the first reading but not the second. The schema implements the first reading. **D3's wording needs fixing before rubric v1.**

## 4. Limits of this agreement figure

- Both labellers are the same model (Claude). Agreement between two instances of one model overstates agreement between independent humans, so κ = 0.90 should not be read as evidence that the rubric is unambiguous.
- n = 12 development cases; κ is descriptive only.
- This is not the two-member independent labelling that proposal 4.14 requires for the formal cases (T20).
