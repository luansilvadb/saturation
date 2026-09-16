# Saturation handoff contract

Use this contract for every delegated role result. The envelope is compact,
redacted, and in memory only; pass it through the implicit lead and never save
it as a run artifact. The `lead` contract describes the main-session function,
so it has no delegated lead assignment or lead handoff.

## Canonical states

Use only these state values in role results and checks:

- Role result: `complete`, `needs_repair`, `blocked`, or `not_applicable`.
- Check result: `pass`, `fail`, `skip`, or `not_applicable`.

Do not substitute synonyms such as `done`, `failed`, or `deferred`. A cycle may
be `active`, `complete`, or `blocked`, but that lifecycle state is separate from
the role result below.

## Envelope

Return one producer envelope with this shape. `next_owner` is conditional and
is included only when repair or escalation is needed. The lead derives the
normalized `clearance` value after validating the envelope; a role must not
self-authorize it.

```yaml
handoff:
  version: "1"
  cycle_id: "cycle-id"
  assignment_id: "opaque-assignment-id"
  agent_id: "role-id"
  status: "complete" # complete | needs_repair | blocked | not_applicable
  summary: "Short description of the result"
  changed_paths: []
  checks:
    - name: "check name"
      status: "pass" # pass | fail | skip | not_applicable
      evidence_id: "EV-cycle-scope-001"
  open_items: []
  # Include only for needs_repair or blocked:
  next_owner: "role-id or lead"
  # Derived by the lead in the normalized handoff, never a role claim:
  clearance: false
```

`evidence_id` is a stable, non-secret reference to observable redacted
evidence for that check. It may point to an in-memory result or a redacted
per-cycle report, but the envelope does not contain raw command output,
prompts, traces, or private reasoning.

## Rules

- Include the current `cycle_id`; do not mix context or evidence from another cycle.
- Use repository-relative concrete paths in `changed_paths`; never use a broad
  path or a saturation runtime path as a substitute for the actual diff.
- Include one `evidence_id` for every check, including a justified skip or
  `not_applicable` result.
- Use `complete` only when every applicable check passes and no blocking item
  remains. Use `needs_repair` when the owner can repair the result internally.
- Use `blocked` when authority, capability, an external dependency, or the
  per-cycle circuit breaker prevents progress.
- Use `not_applicable` only with the lead's recorded reason and coverage
  decision; it must not change product paths.
- A normalized `clearance: true` is derived only for a complete or accepted
  not-applicable result with no failed applicable check and valid evidence.
  Missing evidence, an applicable skip, a failed check, a scope violation, or
  an unresolved blocking item yields `clearance: false`.
- Include `next_owner` and an explicit `open_items` entry for `needs_repair` or
  `blocked`; omit `next_owner` for `complete` and `not_applicable`.
- State facts, decisions, and evidence only. Do not include private scratchpads,
  prompts, chain-of-thought, secrets, credentials, unnecessary PII, or raw
  evaluator traces.

## Phase packets

Parallel results move through an in-memory `phase_packet`, not through role
chat or persisted handoffs. A packet carries only `version`, `cycle_id`, an
opaque `packet_id`, upstream `assignment_id` values, dependency state,
validated changed paths, `evidence_id` references, and the explicit next or
integration owner. The lead emits a packet only after validating each source
handoff and its scope. Packets do not carry prompts, raw tool output, secrets,
or private reasoning.

## Validation

The lead must reject an envelope that is missing required fields, mixes cycle
IDs, has a failed applicable check with clearance, lacks evidence IDs, points
outside the assigned scope, misuses a conditional next owner, contains private
or sensitive payloads, or contradicts the frozen cycle context. A rejected
handoff returns to its source role or is reassigned with a new repair scope.
