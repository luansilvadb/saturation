---
name: saturation
description: "Orchestrate implementation through subagents from the current session context. Use when the user invokes /saturation to implement, review, and repair a task while preserving its intent and scope."
---

Language policy: this skill is English-only. Write all human-readable
instructions, handoffs, reports, and other artifacts in English. Preserve
machine-readable contract keys, identifiers, enum values, and paths exactly as
defined.

When `/saturation` starts, the orchestrator reads `code_styleguides/SKILL.md`
and the active context, records the objective, scope, quality, constraints,
decisions, principles, and verification criteria in `.saturation/context.md`,
and freezes it before the first handoff. Use this file as the single source of
truth and do not write to it after the freeze; changes to intent, scope,
quality, or constraints require an explicit user decision.

Split the work into coherent and disjoint assignments, each with an owner,
`read_scope`, and `write_scope` relative to the repository. `read_scope`
contains only normalized paths under `.saturation/context.md` or
`.agents/skills/saturation/evals`; every event or tool-call read belongs to the
declared assignment's `read_scope`. All product writes use a fresh session and
remain within `write_scope`; promotion has its own assignment. Each handoff is
a validatable JSON payload, never loose prose, with the existing `context`,
`assignment`, `state`, `evidence`, and `fresh_session` fields, plus:

- `context`: `{ "path": ".saturation/context.md", "frozen": true }`;
- `assignment`: `{ "id": string, "owner_actor_id": string, "read_scope": string[], "write_scope": string[] }`, with fields exactly matching the declaration and registered assignment;
- `state`: `{ "phase": string, "status": "ready|running|needs_repair|verified|blocked", "decision": "continue|repair|verify|promote|escalate|complete|reject" }`;
- `input`: `{ "objective": string, "scope": string[], "acceptance": string[], "constraints": string[] }`;
- `output`: `{ "status": "complete|needs_repair|blocked", "event_ref": string, "changed_paths": string[], "verification_evidence": ["EV-..."], "unresolved_risks": string[], "evidence": ["EV-..."] }`, with `event_ref` pointing to the target action and `changed_paths` matching its writes;
- `error`: `null` on success or `{ "code": string, "message": string, "retryable": boolean, "escalate": boolean, "evidence": ["EV-..."] }` on error;
- `stop`: `null` if the flow can continue or `{ "required": true, "reason": string, "evidence": ["EV-..."] }` for a blocker or unresolved risk;
- `tool_call_ref`: the observable `call_id` returned by the action or decision;
- `evidence`: non-empty IDs that resolve in the evidence registry; and
- `fresh_session: true` whenever delegation occurs.

For a `complete` return, `error` and `stop` are null and `unresolved_risks` is
empty; `needs_repair` keeps `error` and `stop` null and lists the risks;
`blocked` requires a typed `error`, unresolved risks, and
`stop.required: true`. Every action records a unique ID, actor, session, phase,
`reads`, and `writes`; `tool_call_ref` resolves to a tool call by the same
actor, and each `evidence.source_id` resolves to an event or call, with
observable `paths` in `reads`/`writes`. Decisions and state transitions also
point to evidence; do not accept state, decision, or claim without a link.

After each implementation, a fresh, adversarial, read-only reviewer reads the
candidate and its evidence, records gaps, and points to the review tool call.
After each repair, a fresh, read-only verifier checks every gap and each
acceptance criterion. It emits `result: "pass|fail"`, `independent: true`,
`rechecks`, `tool_call_ref`, and the minimum dimensions of `completeness`,
`clarity`, `consistency`, and `testability`. `trace_contract.verifier.dimensions`
declares exactly those four base dimensions and may declare, in order,
`behavior`, `error_handling`, and `task_completion`; the payload and evidence
must cover exactly every declared dimension. Also include the trace dimensions
(`context_freeze`, `tool_order`, `session_freshness`, `write_scope`,
`handoff_payload`, `readonly_review`, `evidence`, `repair_reverify`,
`completion_gates`, `escalation`). Each dimension has `id`, `applicable`,
`result: "pass|fail|not_applicable"`, a non-empty claim, and non-empty evidence
linked to an observable source; a missing, unsupported, or failed dimension
prevents completion. A declared optional dimension that is not applicable uses
`applicable: false`, `result: "not_applicable"`, and evidence for that decision.
A failed check returns `output.status: "needs_repair"`; a blocker returns
`output.status: "blocked"`, a typed `error`, and `stop.required: true`.
Repeat `implement → review → repair → verify` until the final review finds no
material gaps and all dimensions pass; only then promote.

Keep reviewers and verifiers write-free, keep assignments and promotion within
scope, and keep the frozen context immutable. Escalate real conflicts, scope or
quality changes, data/effect operations, and blockers to the user; record the
escalation type, decision, and evidence, and never conclude with an unresolved
risk. Technical decisions, sequencing, research, tests, and repairs remain with
the orchestrator. Every report must list exact `changed_paths`,
`verification_evidence`, and `unresolved_risks` (use `[]` when none exist); the
orchestrator consolidates reports only after the final gates.
