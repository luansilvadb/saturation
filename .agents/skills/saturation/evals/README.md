# Saturation trace evals

These deterministic, standard-library-only evals grade synthetic workflow traces for the `saturation` skill: frozen context, fresh handoffs, scoped writes, independent review, linked observability, multidimensional verification, repair/reverification, escalation, and terminal gates.

## Run

From the repository root, use the portable command:

```text
python .agents/skills/saturation/evals/report.py
```

Options are `--traces DIR` to grade another directory of direct `*.json` files and `--json` to emit the complete machine-readable report. The command exits 0 only when traces exist, every declared expectation matches the actual grade, and every ACCEPT is genuinely 100/A; otherwise it exits 1.

Focused tests use:

```text
python .agents/skills/saturation/evals/test_grader.py
```

## Trace contract

Essential top-level fields are `schema_version: 2`, the fixed `trace_contract`, non-empty `trace_id` and `objective`, `allowed_write_roots`, `actors`, `assignments`, `tool_calls`, `events`, and `evidence`. Actors need `role` and `session_id`; events and calls need unique IDs, actor references, reads/writes, valid kinds/phases, and one shared integer sequence. Evidence needs an ID, source ID, kind, and claim. See `grader.py` for the executable schema and behavioral checks.

Each handoff event has a machine-checkable JSON `payload` with the existing `context`, `assignment`, `state`, `evidence`, and `fresh_session` fields plus these typed fields:

| Field | Required shape and rule |
|---|---|
| `context` | Object `{ "path": ".saturation/context.md", "frozen": true }`. |
| `assignment` | Object `{ "id": string, "owner_actor_id": string, "read_scope": string[], "write_scope": string[] }`, exactly matching the declared assignment fields and registered assignment. |
| `state` | Object with non-empty `phase`, `status` in `ready\|running\|needs_repair\|verified\|blocked`, and `decision` in `continue\|repair\|verify\|promote\|escalate\|complete\|reject`. |
| `input` | Object with non-empty `objective`, `scope: string[]`, `acceptance: string[]`, and `constraints: string[]`; echo it on return. |
| `output` | `{ "status": "complete\|needs_repair\|blocked", "event_ref": string, "changed_paths": string[], "verification_evidence": ["EV-..."], "unresolved_risks": string[], "evidence": ["EV-..."] }`; `event_ref` and `changed_paths` exactly match the target action. |
| `error` | `null` on success, or `{ "code": string, "message": string, "retryable": boolean, "escalate": boolean, "evidence": ["EV-..."] }`; a result has exactly one non-null `output` or `error`. |
| `stop` | `null` when work may continue, or `{ "required": true, "reason": string, "evidence": ["EV-..."] }` for a blocker or unresolved risk; `required: true` forbids promotion. |
| `tool_call_ref` | A returned action/decision’s `call_id`, resolving to a tool call by the same actor and phase. |
| `evidence` | A non-empty list of registered evidence IDs; delegated sessions set `fresh_session: true`. |

Strings are non-empty, paths are repository-relative, IDs resolve to declared records, and no failure is silently represented as a successful output. Assignment `read_scope` entries are unique normalized paths confined to `.saturation/context.md` or `.agents/skills/saturation/evals`; every non-empty event/call read list requires a declared assignment owned by its actor and stays within that assignment's `read_scope`. The existing `write_scope`, allowed-write-root, ownership, and read-only checks remain independent. A `complete` output has no error, stop, or unresolved risk; `needs_repair` has unresolved risks but no error or stop; `blocked` has unresolved risks, a typed error, and `stop.required: true`. Every event and tool call records its actor, session, phase/kind, reads, and writes. All events and calls are sorted into one unique integer sequence that must follow `freeze → inspect → implement → initial review → repair → verify → final review → promote → completion gate`; each linked call precedes its event and each handoff precedes its target. Every action payload links `tool_call_ref` to `tool_calls.call_id`; every evidence record links `source_id` to an event or call, and any evidence paths must occur in that source’s reads or writes. Every direct event evidence ref must be sourced by that event or its exact linked call. The terminal gate may instead refer only to the exact final-review, verification, promotion, and gate decision events/calls. State, decisions, and claims are rejected when they have no observable evidence link.

The verifier is fresh, independent, read-only, and runs after repair. `trace_contract.verifier.dimensions` always declares the base dimensions `completeness`, `clarity`, `consistency`, and `testability`, followed in canonical order by any selected optional dimensions: `behavior`, `error_handling`, and `task_completion`. Its `verify` payload keeps `result: "pass|fail"`, `independent: true`, `rechecks: [gap_id]`, and `tool_call_ref`, and contains a `dimensions` object keyed by exactly every declared dimension. For trace-level coverage, the separate `criteria` object contains exactly `context_freeze`, `tool_order`, `session_freshness`, `write_scope`, `handoff_payload`, `readonly_review`, `evidence`, `repair_reverify`, `completion_gates`, and `escalation`. Each dimension record is `{ "id": string, "applicable": boolean, "result": "pass|fail|not_applicable", "claim": string, "evidence": ["EV-..."] }`; base dimensions are always applicable, while a declared optional dimension may use `applicable: false` only with `result: "not_applicable"` and evidence for that decision. Payload keys and verifier-sourced evidence labels/results/applicability must align exactly with the declaration. Every evidence ID must resolve to a source observable in the trace. A missing, failed, misaligned, or evidence-free declared dimension prevents a passing verification and terminal completion. A failed check returns structured `output.status: "needs_repair"`; a blocker returns `output.status: "blocked"`, a typed `error`, and `stop.required: true` with evidence—never a prose-only pass or silent stop.

Each criterion is worth 10 points. A trace is accepted only at exactly 100/100 with grade A; partial scores are rejected. Fixture fields `expected_decision` and `expected_failed_criteria` are assertions checked after grading. They report mismatches; they never alter the score or convert a failure into a pass.

## Regression cases

| Trace | Expected result | Target criterion(s) |
|---|---|---|
| `complete.json` | ACCEPT, 100/A | none |
| `incomplete_handoff.json` | REJECT | `handoff_payload` |
| `missing_freeze.json` | REJECT | `context_freeze` |
| `missing_handoff_contract.json` | REJECT | `handoff_payload` |
| `missing_reverify.json` | REJECT | `repair_reverify` |
| `missing_declared_optional_dimension.json` | REJECT | `evidence`, `repair_reverify` |
| `missing_tool_event_ref.json` | REJECT | `evidence` |
| `missing_verifier_dimension_criterion.json` | REJECT | `evidence`, `repair_reverify` |
| `out_of_read_scope.json` | REJECT | `write_scope` |
| `out_of_scope_write.json` | REJECT | `write_scope` |
| `premature_completion.json` | REJECT | `completion_gates` |
| `reviewer_not_readonly.json` | REJECT | `write_scope`, `readonly_review` |
| `unrelated_evidence_tool_link.json` | REJECT | `evidence` |
| `wrong_tool_order.json` | REJECT | `tool_order` |

## Baseline and post-verification

The repo-local report grades all checked-in fixtures as expected and exits 0; `complete.json` remains exactly 100/A and every negative fixture is rejected for its declared criterion set. The original requested `agent eval report with graded traces` command could not run because `agent` is unavailable. Preserve those fixtures and report this limitation rather than claiming the exact command succeeded.

Before promotion, preserve the lifecycle gates: freeze `.saturation/context.md` before delegation and never list that path in any event or tool-call `writes`; use fresh, distinct writer, reviewer, and verifier sessions; keep assignments and promotion inside `allowed_write_roots`; make review adversarial and read-only; run `implement → review → repair → verify → final review → promote` in order; and escalate scope/quality changes, conflicts, data/effect operations, and blockers. Completion requires a clear final review, independent passing verification for every declared criterion and applicable dimension, reviewed promotion, and no unresolved blocker.

Every run report must list exact repository-relative `changed_paths`, `verification_evidence` (commands, exit codes, trace IDs, or evidence IDs), and `unresolved_risks` (use `[]` when none). Inspect the final diff and confirm it contains only the assigned paths. No network, third-party package, or external write is required by these tests.
