# Saturation handoff contract

This is the single normative source for the role result envelope, the canonical
state names, and the redaction rule. Role contracts and `SKILL.md` reference it
instead of restating it. The envelope is compact, redacted, and in memory only;
never save it as a run artifact.

## Canonical states

Use only these values in role results and checks:

- Role result: `complete`, `needs_repair`, `blocked`, or `not_applicable`.
- Check result: `pass`, `fail`, `skip`, or `not_applicable`.

Do not substitute synonyms such as `done`, `failed`, or `deferred`. A cycle may
be `active`, `complete`, or `blocked`; that lifecycle state is separate from the
role result.

## Redaction

Keep secrets, credentials, exploit payloads, unnecessary PII, prompts from other
roles, private reasoning, and raw tool output out of every brief, envelope,
result, and report. State facts, decisions, and evidence only. This rule applies
to the whole team; it is stated here once.

## Envelope

Return one envelope with this shape. `next_owner` is conditional and is included
only when repair or escalation is needed. The lead derives the normalized
`clearance` value after validating the envelope; a role must not self-authorize
it.

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

## Rules

- Include the current `cycle_id`; do not mix context or evidence from another
  cycle.
- Use repository-relative concrete paths in `changed_paths`; never use a broad
  path or a saturation runtime path as a substitute for the actual diff.
- Include an `evidence_id` for every applied check. A justified `skip` or
  `not_applicable` carries its reason instead, and needs no identifier of its
  own. An `evidence_id` is a stable, non-secret reference to observable redacted
  evidence for that check; it may point to an in-memory result.
- Use `complete` only when every applicable check passes and no blocking item
  remains. Use `needs_repair` when the owner can repair the result internally.
- Use `blocked` when authority, capability, an external dependency, or the
  per-cycle circuit breaker prevents progress.
- Use `not_applicable` only with the lead's recorded reason; it must not change
  product paths.
- A normalized `clearance: true` is derived only for a complete or accepted
  not-applicable result with no failed applicable check and valid evidence.
  Missing evidence for an applied check, an applicable skip, a failed check, a
  scope violation, or an unresolved blocking item yields `clearance: false`.
- Include `next_owner` and an explicit `open_items` entry for `needs_repair` or
  `blocked`; omit `next_owner` for `complete` and `not_applicable`.

## Parallel results

Parallel results move directly between roles, validated by the lead before
hand-off. A validated result carries only the envelope fields above plus the
upstream `assignment_id` values it depended on and the explicit next or
integration owner. There is no separate packet artifact.

## Validation

The lead must reject an envelope that is missing required fields, mixes cycle
IDs, has a failed applicable check with clearance, lacks evidence for an applied
check, points outside the assigned scope, misuses a conditional next owner,
contains private or sensitive payloads, or contradicts the frozen cycle context.
A rejected handoff returns to its source role or is reassigned with a new repair
scope.
