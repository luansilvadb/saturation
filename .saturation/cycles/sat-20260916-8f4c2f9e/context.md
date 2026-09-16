# Saturation Context

## Cycle

- `cycle_id`: `sat-20260916-8f4c2f9e`
- `status`: `active`
- `owner`: main session lead
- `created_at`: `2026-09-16`
- `base_revision`: `a2b3b38`
- `mode`: `refactor`
- `quality_profile`: `maintainable_refactor`

## Objective and authorized intent

Apply the user-approved redesign to the saturation skill so it remains a
large-enterprise development organization while removing avoidable protocol
overhead. Preserve the nine-role roster, quality gates, safety boundaries,
independent final review, and explicit authority controls.

## Scope

- Update `.agents/skills/saturation/SKILL.md` and applicable role contracts.
- Update the handoff contract and evaluator contracts/tests to match the
  approved orchestration model.
- Update evaluator documentation and add only the tests needed to protect the
  new contracts.
- Preserve unrelated files and the existing `.saturation/context.md` from the
  earlier cycle.

## Non-goals

- Do not reduce the nine-role enterprise roster or quality bar.
- Do not change product source, product workflows, or external systems.
- Do not add secrets, prompts, transcripts, private reasoning, PII, or raw
  evaluator traces to durable files.
- Do not delete or overwrite the previous root context.

## Approved design decisions

- The lead is the main session function; there is no separate lead agent or
  lead handoff.
- The roster remains fixed; activation is selected by an objective risk matrix.
- `grilling` owns product intent; the cycle context freezes technical
  decisions; `product-domain` derives acceptance criteria and escalates
  ambiguities.
- Role coverage is dependency-driven, not a global phase barrier.
- Initial role assignments and the final reviewer use fresh sessions; local
  repairs reuse the owner session when safe.
- One writer owns each path; cross-cutting work has an explicit integration
  owner.
- QA owns product behavior; reliability owns operational and release checks;
  final review audits evidence and risk deltas.
- Handoffs use a compact schema with derived clearance and conditional next
  owner; parallel results flow through phase packets.
- Contexts and redacted reports are per-cycle artifacts under
  `.saturation/cycles/<cycle_id>/`.
- Evidence is referenced by stable IDs; evals run in CI/governance and are not
  runtime launch gates.
- Material product, scope, cost, infrastructure, data, risk, quality-profile,
  or acceptance changes start a new cycle.

## Role activation

- `lead`: implicit in the main session.
- `architect-data`: active for contracts, data, persistence, migrations,
  integrations, compatibility, or cross-module structure.
- `implementation`: active for the approved skill and evaluator changes.
- `security-privacy-ip`: active for prompt boundaries, sensitive-data rules,
  dependencies, assets, licenses, or permissions.
- `qa-harness`: active as the executable-change validation gate.
- `reliability-release`: active for reproducibility, artifacts, persistence,
  release and operational behavior.
- `final-reviewer`: active after integration in a fresh independent session.
- `product-domain`: `not_applicable`; no product workflow or business rule is
  being changed.
- `experience-fidelity`: `not_applicable`; no product UI or interaction is
  being changed.

## Gate registry

- `scope`: only approved saturation skill, contracts, evaluators, tests, and
  cycle artifacts change.
- `contract-consistency`: role, handoff, routing, state, evidence, and
  persistence contracts agree.
- `python-tests`: all evaluator tests pass.
- `markdown-quality`: Markdown remains clear and `git diff --check` passes.
- `review`: an independent final reviewer finds no release-blocking defect or
  unresolved contract contradiction.

## Approved references and constraints

- Applicable guides: `code_styleguides/general.md`,
  `code_styleguides/prompting.md`, and `code_styleguides/python.md`.
- Preserve the existing root `.saturation/context.md` unchanged.
- No network or external effects.
- Keep the cycle context immutable after this freeze; promotions use a
  redacted append-only decision record and do not mutate this file.
