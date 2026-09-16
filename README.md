# Saturation

Saturation is a Codex skill for delivering polished, launch-ready
implementations through a fixed specialist team. It treats a validated product
intent as a client brief and owns the technical method, integration, quality,
and evidence of the result.

## Core contract

When `$saturation` runs, it:

1. receives the intent, scope, and non-goals from the user or `grilling`;
2. conducts a separate technical-discovery conversation;
3. records the consolidated contract in the frozen per-cycle
   `.saturation/cycles/<cycle_id>/context.md`;
4. delegates to the fixed v1 specialist team through deep, traceable,
   role-specific runtime briefs;
5. implements complete in-scope behavior and does not optimize internal
   tokens or iterations;
6. runs integration, repair, a task-specific harness, and target-environment
   validation;
7. verifies security, privacy, licensing, maintainability, and operations when
   relevant;
8. returns a release candidate with evidence, or an honest blocker.

The skill may choose technical details autonomously. New infrastructure,
paid or usage-billed services, proprietary assets, external commitments,
irreversible actions, and production deployment require explicit approval.

## Context and team boundaries

`grilling` refines what is being built. `saturation` refines how it will be
delivered. The technical briefing is consolidated into the frozen per-cycle
`.saturation/cycles/<cycle_id>/context.md`; prompts, role briefs, traces, and
evaluation data remain ephemeral.

The lead is the only user-facing agent. Specialists work in fresh sessions
with disjoint write scopes, relevant style guides, and only the context and
files needed for their roles. The lead integrates their work and owns the
final quality gate.

## Launch readiness

`launch-ready` means a polished release candidate with complete in-scope
workflows, no known release-blocking or user-impacting defects, passing
applicable harness checks, validation in the declared target environment, and
the necessary release and recovery materials. Essential missing assets,
unapproved compromises, or unavailable applicable checks prevent that status.

The default result is ready for the user to deploy, not an automatic production
change. Defects that violate the original scope remain the responsibility of
the saturation service; new capabilities are new scope.

## Evaluation

The `evals` package checks orchestration hygiene such as frozen context, fresh
sessions, disjoint scopes, relevant guides, checks, final integration, and the
absence of persisted runtime artifacts. It does not certify product quality,
market readiness, legal compliance, or the truth of a launch claim; the lead's
task-specific harness and evidence gate do that.

Run the evaluator suite from the repository root:

```text
python -B .agents/skills/saturation/evals/test_grader.py
```

The evaluator also accepts an in-memory observation snapshot through
`evals/grader.py <file>` or stdin; `evals/README.md` documents the event schema.
That snapshot is an evaluator input, not an artifact produced by `$saturation`.

## Repository layout

```text
.agents/skills/saturation/
├── SKILL.md                    # orchestration behavior
├── agents/                     # role contracts and the shared handoff contract
├── code_styleguides/           # reusable implementation rules
└── evals/
    ├── grader.py               # the single in-memory run evaluator and its CLI
    ├── test_grader.py          # evaluator tests
    └── README.md               # evaluator contract and event schema
.saturation/cycles/<cycle_id>/  # the only durable harness artifacts
```

Prompts, traces, ledgers, hashes, coverage reports, and session history must
not be written under `.saturation/runs/` or otherwise persisted by a normal
run. Existing project tests and product documentation remain ordinary project
files.
