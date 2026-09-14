# Saturation evaluation run context

## Objective

Create deterministic, trace-graded regression evals for the `saturation` skill
that detect workflow regressions across tool calls and agent handoffs. Rewrite
the skill more compactly with semantically precise, action-oriented wording;
the shorter version must preserve or improve the existing quality bar.

## Scope

- `.agents/skills/saturation/SKILL.md`: the skill instructions only.
- `.agents/skills/saturation/evals/**`: a dependency-free trace schema, rubric,
  fixtures, grader/report command, and focused tests/documentation.
- `.saturation/context.md`: this frozen orchestration context.

Do not change the blueprint, unrelated skills, metadata, or add a full runner.
Use synthetic local traces; do not call external services or models.

## Quality bar

The skill must state observable contracts with an actor, action, trigger, and
evidence/stop condition. Preserve these invariants: freeze context before
delegation; use fresh sessions; isolate assignments and promotion; review with
a fresh read-only adversary; carry context, assignment, state, and evidence in
handoffs; repeat implement → review → repair → verify until the latest review
has no material gaps; escalate real conflicts, scope/quality changes,
data/effect operations, and blockers. Prefer positive, specific instructions;
retain a safety boundary whenever positive wording alone would make a contract
ambiguous.

## Constraints and decisions

- Never weaken a gate, remove an assertion, hide an error, tune against hidden
  labels, or remove a failing case.
- Keep the evaluator deterministic and standard-library-only so it runs in this
  repository with the available Python executable.
- Grade event ordering, actor/session identity, handoff payloads, write scopes,
  read-only review, evidence linkage, repair/reverification, and terminal
  completion gates—not just final prose.
- Keep representative failing traces and report both their failed criterion and
  score; a passing report must prove that the negative fixtures are rejected.

## Baseline evidence

The initial audit found no `AGENTS.md`, `CLAUDE.md`, `PLAN.md`, issue, log,
dataset, rubric, judge, or regression report in the working tree. The exact
command `agent eval report with graded traces` failed because `agent` is not
installed. Python, Node, and `uv` are available; no `pytest` command was found.
The required fresh-session probe returned `READY` and was closed.

## Verification

Provide a repo-local equivalent at:

```text
python .agents/skills/saturation/evals/report.py
```

It must emit a graded report, pass the valid trace, reject every regression
fixture for its intended reason, and run focused unit tests without network or
third-party dependencies. Record honest before/after evidence and the final
diff; do not claim the unavailable `agent` command succeeded.

## Frozen handoff rule

This file is immutable for this run. Every subagent receives this path plus its
disjoint assignment and must report changed paths, evidence, and unresolved
risks. The orchestrator reviews and integrates only scoped, independently
reviewed changes.
