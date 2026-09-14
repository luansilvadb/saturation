# Saturation trace evals

These deterministic, standard-library-only evals grade synthetic workflow traces for the `saturation` skill: frozen context, fresh handoffs, scoped writes, independent review, evidence, repair/reverification, escalation, and terminal gates.

## Run

From the repository root, use the portable command:

```text
python .agents/skills/saturation/evals/report.py
```

Options are `--traces DIR` to grade another directory of direct `*.json` files and `--json` to emit the complete machine-readable report. The command exits 0 only when traces exist, every declared expectation matches the actual grade, and every ACCEPT is genuinely 100/A; otherwise it exits 1.

## Trace contract

Essential top-level fields are `schema_version: 1`, non-empty `trace_id` and `objective`, `allowed_write_roots`, `actors`, `assignments`, `tool_calls`, `events`, and `evidence`. Actors need `role` and `session_id`; events and calls need unique IDs, actor references, reads/writes, and valid kinds/phases. Evidence needs an ID, source ID, kind, and claim. See `grader.py` for the executable schema and behavioral checks.

Each criterion is worth 10 points. A trace is accepted only at exactly 100/100 with grade A; partial scores are rejected. Fixture fields `expected_decision` and `expected_failed_criteria` are assertions checked after grading. They report mismatches; they never alter the score or convert a failure into a pass.

## Regression cases

| Trace | Expected result | Target criterion(s) |
|---|---|---|
| `complete.json` | ACCEPT, 100/A | none |
| `incomplete_handoff.json` | REJECT | `handoff_payload` |
| `missing_freeze.json` | REJECT | `context_freeze` |
| `missing_reverify.json` | REJECT | `repair_reverify` |
| `out_of_scope_write.json` | REJECT | `write_scope` |
| `premature_completion.json` | REJECT | `completion_gates` |
| `reviewer_not_readonly.json` | REJECT | `write_scope`, `readonly_review` |
| `wrong_tool_order.json` | REJECT | `tool_order` |

## Baseline and post-verification

The original requested `agent eval report with graded traces` baseline could not run because the `agent` command is unavailable in this environment. The repo-local equivalent above is the honest replacement; it does not claim that baseline succeeded. After changes, run the report and the focused unittest command below, inspect both exit codes and the final diff, and confirm that the final diff contains only files within the scope of this change (`SKILL.md`, `evals/**`, and the execution context if it is retained). No network, third-party package, or write is required by the tests.
