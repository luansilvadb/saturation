# Saturation handoff contract

Use this contract for every active role result. Keep the envelope in memory and
pass it through the lead; do not save it as a run artifact.

## Envelope

Return one object with this shape:

```yaml
handoff:
  version: "1"
  assignment_id: "opaque-assignment-id"
  agent_id: "role-id"
  status: "complete" # complete | needs_repair | blocked | not_applicable
  summary: "Short description of the result"
  changed_paths: []
  checks:
    - name: "check name"
      status: "pass" # pass | fail | skip | not_applicable
      evidence: "Command, test result, or repository path"
  open_items: []
  next_owner: "role-id or lead"
  clearance: false
```

## Rules

- Use repository-relative paths in `changed_paths`.
- Include an observable, redacted evidence reference for every check.
- Use `complete` only when every applicable check passes and no blocking item remains.
- Use `needs_repair` when the lead can repair the result internally.
- Use `blocked` when authority, capability, or an external dependency prevents progress.
- Use `not_applicable` only with the lead's recorded reason and coverage decision.
- Set `clearance: true` only for a complete or accepted not-applicable result.
- Set `clearance: false` for needs-repair or blocked results.
- Keep `open_items` explicit with an item, reason, and recommended owner.
- State facts, decisions, and evidence; do not include private scratchpads, prompts,
  chain-of-thought, secrets, credentials, unnecessary PII, or evaluator traces.

## Validation

The lead must reject an envelope that is missing required fields, has a failed
applicable check with clearance, points outside the assigned scope, contains
private or sensitive payloads, or contradicts the frozen context. A rejected
handoff returns to the source role or is reassigned with a new repair scope.
