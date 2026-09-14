# Saturation

Saturation is a Codex skill for orchestrating implementation work through fresh, scoped subagents. It turns the current session context into a frozen execution contract and guides the work through implementation, independent review, repair, verification, and promotion.

## What it provides

- A repeatable workflow for complex implementation tasks.
- Explicit scopes, assignments, handoffs, and evidence.
- Fresh sessions for implementation, review, and verification.
- Adversarial, read-only review before promotion.
- A deterministic evaluation suite for catching workflow regressions.

## Workflow

1. Freeze the active context in `.saturation/context.md` before delegation.
2. Split the work into disjoint assignments with explicit read and write scopes.
3. Implement the assignments in fresh sessions and return structured handoffs.
4. Review the result with a fresh, adversarial, read-only reviewer.
5. Repair every material gap and verify the repair independently.
6. Promote the result only after the final review and all completion gates pass.

Scope changes, conflicts, real-world effects, and unresolved blockers must be escalated instead of being silently absorbed.

## Repository layout

```text
.agents/skills/saturation/
├── SKILL.md                    # Core skill instructions
├── agents/openai.yaml          # Display metadata and default prompt
├── code_styleguides/SKILL.md   # Coding guidance used by the skill
└── evals/
    ├── grader.py               # Trace schema and behavioral grader
    ├── report.py               # Portable command-line entry point
    ├── rubric.json             # Grading criteria and fixture matrix
    ├── test_grader.py          # Focused unit tests
    └── traces/                 # Valid and regression trace fixtures
.saturation/context.md          # Frozen orchestration context for a run
```

## Use the skill

In a Codex session, invoke the skill with:

```text
/saturation
```

The skill reads the current session context, freezes it in `.saturation/context.md`, and uses that file as the source of truth for the delegated work.

## Run the evaluation suite

The evaluation suite uses only the Python standard library. From the repository root, run:

```text
python .agents/skills/saturation/evals/report.py
python .agents/skills/saturation/evals/test_grader.py
```

The report grades the checked-in synthetic traces and exits successfully only when the valid trace reaches 100/A and every regression fixture is rejected for its intended reason. Use `--json` for machine-readable output or `--traces DIR` to grade another directory of direct JSON trace files.

## Contributing

- Keep the evaluator deterministic and dependency-free.
- Preserve the lifecycle gates: freeze, implement, review, repair, verify, and promote.
- Keep reviewers and verifiers fresh and read-only.
- Update the rubric, fixtures, and focused tests together when changing the trace contract.
- Run both evaluation commands before submitting a change.
- Do not mutate `.saturation/context.md` after it has been frozen for a run.
