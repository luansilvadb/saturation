# Saturation

Saturation is a Codex skill for orchestrating implementation work through fresh, scoped subagents. It turns the current session context into a frozen execution contract and guides the work through implementation, independent review, repair, verification, and promotion.

## What it provides

- A repeatable workflow for complex implementation tasks.
- Explicit scopes, assignments, handoffs, and evidence.
- Fresh sessions for implementation, review, and verification.
- Adversarial, read-only review before promotion.
- A deterministic evaluation suite for catching workflow regressions.
- A canonical prompt policy with modular composition, PCP complexity budgets,
  quality gates, and traceable prompt evidence.

## Workflow

1. Read the modular prompt and code-style guides, then freeze the active
   context in `.saturation/context.md` before delegation.
2. Split the work into disjoint assignments with explicit read and write scopes.
3. Compose, lint, and record each operational prompt before dispatch.
4. Implement the assignments in fresh sessions and return structured handoffs.
5. Review the result and its prompts with a fresh, adversarial, read-only reviewer.
6. Repair every material gap and verify the repair independently.
7. Promote the result only after the final review and all completion gates pass.

Scope changes, conflicts, real-world effects, and unresolved blockers must be escalated instead of being silently absorbed.

Assignments may read and write explicitly scoped product paths; the synthetic
trace fixtures use a narrower, self-contained read boundary only for testing.

## At a glance

The frozen context and style guide feed the orchestration rules. Work then moves through fresh implementation, review, repair, verification, and promotion sessions. The evaluation suite grades the observable trace of that workflow.

```mermaid
flowchart TD
    C[".saturation/context.md<br/>Frozen run context"] --> S["SKILL.md<br/>Orchestration rules"]
    G["code_styleguides/prompting.md<br/>general.md<br/>language modules"] --> S
    M["agents/openai.yaml<br/>Metadata and default prompt"] --> S

    S --> F["Freeze context"]
    F --> A["Disjoint assignments"]
    A --> I["Fresh implementation sessions"]
    I --> R["Fresh adversarial read-only review"]
    R --> P{"Material gaps?"}
    P -- "Yes" --> X["Repair"]
    X --> V["Fresh independent verification"]
    P -- "No" --> V
    V --> Q{"All gates pass?"}
    Q -- "No" --> X
    Q -- "Yes" --> PR["Final review"]
    PR --> PM["Promote"]

    E["evals/report.py"] --> GR["evals/grader.py"]
    T["evals/test_grader.py"] --> GR
    TR["evals/traces/*.json"] --> GR
    RB["evals/rubric.json"] --> GR
```

## Repository layout

```text
.agents/skills/saturation/
├── SKILL.md                    # Core skill instructions
├── agents/openai.yaml          # Display metadata and default prompt
├── code_styleguides/
│   ├── README.md               # Module index and selection order
│   ├── prompting.md            # Prompt construction and prompt trace policy
│   ├── general.md              # Cross-language structural design
│   └── <language>.md           # Language-specific guidance
└── evals/
    ├── prompt_contract.py      # Prompt contract and PCP validator
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
python .agents/skills/saturation/evals/prompt_contract.py --trace .agents/skills/saturation/evals/traces/complete.json --root .
python .agents/skills/saturation/evals/report.py
python .agents/skills/saturation/evals/test_grader.py
```

The report grades the checked-in synthetic traces and exits successfully only
when the valid trace reaches 110/A and every regression fixture is rejected for
its intended reason. Use `--json` for machine-readable output or `--traces DIR`
to grade another directory of direct JSON trace files. Prompt-aware traces use
schema v3 and include rendered prompt evidence, strict module manifests, PCP,
and quality gates. The prompt validator can independently verify the canonical
prompt contract and module hashes; the report also emits descriptive PCP,
strategy, gate, attempt, and repair metrics that do not alter acceptance.

## Contributing

- Keep the evaluator deterministic and dependency-free.
- Preserve the lifecycle gates: freeze, implement, review, repair, verify, and promote.
- Keep reviewers and verifiers fresh and read-only.
- Update the rubric, fixtures, and focused tests together when changing the trace contract.
- Run both evaluation commands before submitting a change.
- Do not mutate `.saturation/context.md` after it has been frozen for a run.
