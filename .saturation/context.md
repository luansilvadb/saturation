# Saturation Context

## Objective

Reduce redundant prose in the `Saturation Governance` part of the saturation
skill while preserving its safety, scope, persistence, quality, and evaluation
invariants.

## Scope

- Edit only the six `Saturation Governance` sections in
  `.agents/skills/saturation/SKILL.md`:
  `Persistence boundary`, `Context and trust`, `Scoped subagents`,
  `Quality actions`, `Evaluation boundary`, and `Safety and escalation`.
- Keep the behavior and intent of each retained invariant.
- Keep `Lifecycle`, `Core promise`, `Final delivery`, `evals/`,
  `code_styleguides/`, `README.md`, and `agents/openai.yaml` unchanged.

## Non-goals

- Do not remove fresh sessions, disjoint scopes, temporary workspaces, frozen
  context, relevant checks, safety escalation, or the no-persistence boundary.
- Do not change evaluator implementation, tests, graphify outputs, or unrelated
  user changes.
- Do not add prompt, trace, ledger, or evaluation artifacts.

## Acceptance criteria

- The six sections are shorter and retain their agreed compact contracts.
- The other skill sections and support files are unchanged.
- Markdown remains clear and consistent with the local style guides.
- `git diff --check` passes.
- All 35 existing evaluator tests pass.

## Constraints

- Preserve the existing modification in `graphify-out/cache/last_query_stamp`.
- Use no network or external effects.
- Apply only the approved final diff to the primary workspace.
- Keep `.saturation/context.md` as the sole durable orchestration artifact.

## Decisions

- `Evaluation boundary` keeps a short in-memory-only contract and points to
  `evals/README.md` for details.
- `Persistence boundary` becomes one concise paragraph.
- `Scoped subagents`, `Quality actions`, `Context and trust`, and `Safety and
  escalation` retain their essential guardrails in compact prose.
- This pass does not regenerate `graphify-out`.

## References

- `.agents/skills/saturation/SKILL.md`
- `.agents/skills/saturation/code_styleguides/general.md`
- `.agents/skills/saturation/code_styleguides/prompting.md`
- `.agents/skills/saturation/evals/README.md`
