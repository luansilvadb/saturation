# Saturation Context

Status: FROZEN

## Run

- `run_id`: `run-20260915-quality-scaffold`
- `trace_id`: `trace-quality-scaffold-20260915`
- `parent_context`: `.saturation/context.md`

The parent context belongs to an earlier completed objective and is immutable.
This run uses this run-scoped context and must not replace or edit the parent
context.

## Objective

Add a versioned, deterministic evaluation path for improving the correctness
of delegated implementation and repair work. The candidate intervention is a
short, structured reasoning scaffold selected by the orchestrator only for
tasks with observable dependency or repair signals. Do not request, store, or
disclose hidden chain-of-thought.

## Scope

- `.agents/skills/saturation/SKILL.md`
- `.agents/skills/saturation/code_styleguides/prompting.md`
- `.agents/skills/saturation/evals/reasoning_scaffold.py`
- `.agents/skills/saturation/evals/quality_comparison.py`
- `.agents/skills/saturation/evals/test_quality_comparison.py`
- `.agents/skills/saturation/evals/README.md`
- `README.md`
- `.github/workflows/tests.yml`
- `.saturation/runs/run-20260915-quality-scaffold/`

This run may add only the new policy, evaluator, tests, workflow invocation,
documentation, and its own redacted evidence artifacts. Existing v3, v4, and
v5 trace fixtures and their workflow grading scores remain unchanged.

## Non-goals

- Do not add provider calls, external effects, or a production rollout.
- Do not expose or persist private chain-of-thought or raw benchmark oracles.
- Do not use tokens, PCP, or same-version workflow scores as quality claims.
- Do not change the current trace rubric, schema v3/v4/v5 compatibility, or
  the existing frozen parent context.
- Do not claim a measured quality improvement without real paired outcome data.

## Quality

- The current evaluator and all existing fixtures retain their decisions and
  scores.
- The new comparison contract requires distinct baseline and candidate
  versions, immutable task and oracle versions, controlled environment
  metadata, at least three repetitions per task and variant, task-level macro
  aggregation, a pre-registered 0.05 minimum lift, and a paired uncertainty
  interval.
- Candidate promotion is rejected for any critical regression, candidate
  workflow-gate failure, invalid oracle data, or missing required observation.
- The scaffold classifier is deterministic, orchestrator-owned, evidence
  backed, and escalates ambiguity that requires a user decision.
- All new executable code has test-first red/green evidence and instrumented
  line and branch coverage.

## Constraints

- Keep the evaluator dependency-free and standard-library only.
- Preserve machine-readable identifiers, paths, and current schema contracts.
- Use repository-relative POSIX paths in artifacts and traces.
- Keep operational prompt and handoff scaffolding in English.
- Keep benchmark oracle content outside agent scopes and recorded artifacts.
- Keep new quality comparison results separate from the existing workflow
  grade; descriptive telemetry remains non-decisive there.
- Use immutable version identifiers and never edit an already persisted result.

## Decisions

- The primary outcome is independent behavioral correctness of delegated
  implementation and repair tasks.
- The first benchmark excludes documentation, metadata-only, and external
  effect tasks.
- The first candidate is an adaptive structured scaffold for implementers and
  repairers, not a global zero-shot CoT instruction.
- Activation signals are interdependent acceptance branches, cross-module or
  data-flow dependency, and repair after a material failure.
- Comparison uses the same task suite, oracle, model, configuration,
  toolchain, clean workspace, and three repetitions per variant.
- A task passes only when all mandatory independent acceptance checks pass.
- A candidate needs at least a five-percentage-point macro task-pass lift and
  no critical regression; otherwise the result is not an improvement.
- Benchmark tasks and oracles are immutable versions owned by the harness
  maintainer; rollout is out of scope for this run.

## Principles

- Measure outcomes, not reasoning prose or token counts.
- Prefer concise, verifiable decision summaries over hidden reasoning traces.
- Keep the baseline and candidate comparable and the oracle independent.
- Make failure, uncertainty, and invalid evidence explicit.
- Preserve backward compatibility while versioning new comparison behavior.

## Verification Criteria

- New tests fail first for missing scaffold and comparison behavior, then pass
  after implementation.
- The scaffold classifier activates only on the three approved signals,
  returns `direct` otherwise, and returns `escalate` for user decisions.
- The comparison validator rejects same-version, missing-oracle,
  insufficient-repetition, malformed-run, and critical-regression inputs.
- A valid paired comparison computes task-level macro pass rates, delta,
  deterministic paired uncertainty, and the correct decision.
- Existing prompt-contract validators, report, focused tests, and CI commands
  remain successful.
- Instrumented line and branch coverage meets the configured threshold for
  all new executable modules.
- Evidence and integrity artifacts are persisted under this run directory,
  redacted, and linked to the new context without changing the parent context.
