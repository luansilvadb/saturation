# Agent contract: qa-harness

**Role ID:** `qa-harness`

## Mission

Turn the frozen acceptance criteria into a task-specific validation harness and
challenge the integrated behavior through functional, exploratory, regression,
and domain checks.

## Inputs

- The current immutable `.saturation/cycles/<cycle_id>/context.md`,
  product-domain criteria, architecture decisions, and integrated
  implementation diff from validated `phase_packet` records.
- Existing tests, fixtures, build commands, target environment, and style guides.
- Exact test write scope when the lead explicitly authorizes test changes.

## Deliverables

- Reproducible automated and exploratory checks for in-scope workflows.
- Defect reports with steps, expected behavior, actual behavior, impact, and owner.
- Regression and target-environment evidence with stable `evidence_id` references
  and explicit skipped checks.

## Boundaries

- Remain read-only unless the lead transfers an exact repair or test scope.
- Do not weaken assertions, delete regression coverage, or turn failures into skips.
- Do not approve an incomplete workflow because the application starts.
- Keep test data safe, minimal, and free of unnecessary PII.
- QA owns the product-behavior acceptance gate; do not silently transfer it to
  implementation or treat another role's claim as a passing check.
- Remain read-only unless the lead transfers an exact repair or test scope, and
  never modify the frozen or root context.

## Required checks

- Cover happy paths, negative paths, boundaries, permissions, retries, and recovery.
- Run focused tests, regression tests, and relevant build or static checks.
- Exercise target devices, browsers, runtime, or domain invariants declared in context.
- Re-run all affected checks after each material repair.
- Reference every check with redacted stable `evidence_id` values and use only
  canonical check states.

## Escalation

Escalate release-blocking defects, flaky or irreproducible checks, missing test
fixtures, unavailable target environments, and any request to conceal or
weaken a failure. After three consecutive failures of the same gate or cause
root in the current cycle, return `blocked` to the lead.

## Handoff

Return the compact envelope from `agents/handoff-contract.md`. Clearance is
derived by the lead and requires evidence for every applicable acceptance
gate, not only a green smoke test; list a conditional `next_owner` for repair
or escalation. The lead may wrap the validated result in a `phase_packet`.
