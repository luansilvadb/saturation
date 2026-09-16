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
4. delegates to the fixed specialist team through role-specific runtime briefs;
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
delivered. The technical briefing and every decision approved during the run are
recorded in the frozen per-cycle `.saturation/cycles/<cycle_id>/context.md`,
which is the single record for that cycle; prompts, role briefs, traces, and run
data remain ephemeral.

The lead is the main session and the only user-facing agent. Eight specialist
contracts in `agents/` carry the specialist work in disjoint write scopes with
the style guides their roles need. `final-reviewer`, `qa-harness`, and
`security-privacy-ip` always work in fresh sessions, because their independence
is the evidence; other specialists may reuse a session when the runtime is
constrained, and the reuse is recorded in the cycle context. The lead integrates
their work and owns the final quality gate.

## Launch readiness

`launch-ready` means a polished release candidate with complete in-scope
workflows, no known release-blocking or user-impacting defects, passing
applicable harness checks, validation in the declared target environment, and
the necessary release and recovery materials. Essential missing assets,
unapproved compromises, or unavailable applicable checks prevent that status.

The default result is ready for the user to deploy, not an automatic production
change. Defects that violate the original scope remain the responsibility of
the saturation service; new capabilities are new scope.

## Verification status

This repository ships prose contracts and has **no automated check**. An earlier
`evals/` package and its GitHub Actions workflow were removed: the evaluator
inspected orchestration events that only its own test suite produced, so it
validated itself rather than the skill, and nothing outside this repository
consumed its output.

Nothing here validates a change to `SKILL.md`, the role contracts, the handoff
contract, or the style guides. Editing them is a manual review responsibility,
and the quality bar is enforced at run time by the gates in `SKILL.md` and the
task-specific harness of each cycle.

## Repository layout

```text
.agents/skills/saturation/
├── SKILL.md                    # orchestration behavior, role roster, lead duties
├── agents/                     # eight role contracts and the handoff contract
└── code_styleguides/           # reusable implementation rules
.saturation/cycles/<cycle_id>/  # the only durable harness artifacts
```

Prompts, traces, ledgers, hashes, coverage reports, and session history must
not be written under `.saturation/runs/` or otherwise persisted by a normal
run. Existing project tests and product documentation remain ordinary project
files.
