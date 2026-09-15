# Saturation Context

Status: FROZEN

## Objective

Keep `/saturation` small and dependable: freeze the user's intent, delegate
bounded work to clean subagents, apply the relevant code style guides, verify
the implementation internally, and integrate only the final diff.

## Scope

- simplify the saturation skill and its internal prompt guidance;
- keep fresh scoped subagents and useful quality actions;
- move runtime observation and metrics to `evals`;
- make delegated writes transactional and temporary;
- simplify the evaluator and remove prompt/trace protocol baggage;
- remove generated run artifacts from the repository.

## Non-goals

- removing TDD, review, repair, verification, or coverage as available actions;
- removing ordinary product tests;
- exposing internal session details to the user;
- adding a new persistence layer for orchestration state;
- changing unrelated skills or user work.

## Acceptance criteria

- `.saturation/context.md` is the only durable harness artifact in the project;
- no normal `/saturation` run requires or creates prompts, traces, ledgers,
  evidence files, hashes, or run directories;
- subagents use fresh sessions, disjoint scopes, relevant style guides, and a
  temporary workspace;
- only an approved final diff reaches the primary workspace;
- `evals` can observe internal events and own its metrics without coupling the
  runtime to persisted trace schemas;
- documentation and tests describe the simplified contract consistently.

## Constraints

- keep the evaluator dependency-free and deterministic;
- preserve unrelated user changes;
- do not use network access or external effects for validation;
- do not persist prompt text, session history, or private reasoning;
- use normal project test locations for tests that intentionally belong to the
  product.

## Decisions

- orchestration state is ephemeral and a failed run restarts from this context;
- `evals` observes and measures; `saturation` executes and integrates;
- historical prompt/trace contracts are not active runtime requirements;
- the final user-facing result is concise and focused on the delivered code.

## References

- `.agents/skills/saturation/SKILL.md`
- `.agents/skills/saturation/code_styleguides/prompting.md`
- `.agents/skills/saturation/evals/README.md`
