# Saturation

Saturation is a Codex skill for implementing work with fresh, scoped
subagents. It keeps the coordination sophisticated inside the harness while
keeping the user's repository focused on the actual product code and tests.

## Core contract

When `/saturation` runs, it:

1. reads the request and the repository;
2. creates or refreshes `.saturation/context.md` with the frozen task intent;
3. derives disjoint assignments in memory;
4. delegates each assignment to a clean session with the relevant
   `code_styleguides`;
5. performs useful quality actions such as tests, TDD, review, repair, and
   verification internally;
6. works in a temporary isolated workspace and integrates only the approved
   final diff;
7. returns the finished result.

The only orchestration artifact kept in the product repository is:

```text
.saturation/context.md
```

Prompts, traces, handoffs, ledgers, hashes, coverage reports, and session
history are transient. They must not be required for a normal run or written
under `.saturation/runs/`. Project tests remain ordinary project files.

## Context

`context.md` is a short, human-readable contract containing the objective,
scope, non-goals, acceptance criteria, constraints, decisions, and relevant
guide references. It is frozen during a run. It is not a trace, status board,
prompt catalog, or metrics report.

## Subagent boundaries

Every delegated session receives only the context, repository paths, and style
rules relevant to its assignment. Write scopes do not overlap. Sessions do not
share conversational history. Their operational prompts and handoffs remain
in memory.

The primary workspace is protected from partial writes. A failed or interrupted
run discards its temporary workspace and starts again from the frozen context.

## Quality and evaluation

TDD, review, repair, independent verification, and coverage are available
quality actions. They improve confidence but do not create a persistence
ceremony. Their temporary results can be exposed through an in-memory
observation hook.

The `evals` package owns metrics and comparisons. It observes saturation runs
without making the normal runtime write prompts, traces, or reports to the
product repository. Evaluation fixtures and reports belong to the evaluator,
not to a product run.

Run the focused evaluator tests with:

```text
python -B .agents/skills/saturation/evals/test_grader.py
python -B .agents/skills/saturation/evals/test_quality_comparison.py
python -B .agents/skills/saturation/evals/test_quality_comparison_edges.py
python -B .agents/skills/saturation/evals/test_quality_comparison_missing_branches.py
python -B .agents/skills/saturation/evals/test_quality_comparison_numeric_edges.py
```

The evaluator also accepts an in-memory observation snapshot through
`evals/report.py --input <file>`. That file is an evaluator input, not an
artifact produced by `/saturation`.

## Repository layout

```text
.agents/skills/saturation/
├── SKILL.md                    # orchestration behavior
├── agents/openai.yaml          # display metadata and default prompt
├── code_styleguides/           # reusable implementation rules
└── evals/
    ├── grader.py               # in-memory run evaluator
    ├── report.py               # evaluator CLI adapter
    ├── test_grader.py          # evaluator tests
    ├── reasoning_scaffold.py   # optional internal routing aid
    └── quality_comparison.py   # optional outcome comparison
.saturation/context.md          # the only durable harness artifact
```

## Design principles

- Keep the implementation core small and the quality actions reusable.
- Prefer clean sessions, explicit scopes, and relevant style guidance.
- Keep internal orchestration state ephemeral.
- Let `evals` measure the harness without defining the product workflow.
- Preserve unrelated user changes and never broaden a task silently.
- Expose a concise final delivery rather than internal ceremony.
