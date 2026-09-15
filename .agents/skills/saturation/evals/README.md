# Saturation evals

The evaluator measures whether saturation produces a dependable implementation
without making the normal runtime persist orchestration data. It consumes an
in-memory observation snapshot and returns a result; any JSON file used by the
CLI is an evaluator-owned input, never a file created by `/saturation`.

## What is measured

The focused evaluator checks only useful invariants:

- the task context is frozen at `.saturation/context.md`;
- delegated assignments use fresh sessions;
- write scopes do not overlap;
- relevant `code_styleguides` are supplied;
- applicable checks pass;
- only an approved final integration reaches the workspace;
- no saturation runtime artifact is persisted.

TDD, review, repair, verification, and coverage can be represented as `check`
events. The evaluator does not force every task to use every action.

## Observation hook

The runtime may use `RunObserver` from `grader.py`:

```python
observer = RunObserver()
observer.record("context_frozen", path=".saturation/context.md", frozen=True)
events = observer.snapshot()
result = evaluate_events(events)
```

The event list stays in memory. The useful event kinds are:

- `context_frozen` with `path` and `frozen`;
- `assignment` with `assignment_id`, `session_id`, `fresh_session`, scopes, and
  `style_guides`;
- `check` with a name and `pass`, `skip`, or `not_applicable` status;
- `integrated` with `complete` status and final changed paths;
- `durable_path` when an observer wants to assert what reached disk.

The hook is optional and one-way. `saturation` owns emission of this small,
neutral event vocabulary; `evals` owns validation, metrics, and comparisons.
Observation payloads are redacted metadata only: statuses, opaque IDs,
normalized repository-relative scopes, guide names, and changed paths. They do
not carry prompts, transcripts, tool output, secrets, credentials, unnecessary
PII, or private reasoning.

The evaluator may ignore additive event kinds and fields. Breaking changes to
the event contract require an explicit version and tests, while the normal
runtime must remain independent of persisted evaluator schemas.

## Run the tests

From the repository root:

```text
python -B .agents/skills/saturation/evals/test_grader.py
python -B .agents/skills/saturation/evals/test_quality_comparison.py
python -B .agents/skills/saturation/evals/test_quality_comparison_edges.py
python -B .agents/skills/saturation/evals/test_quality_comparison_missing_branches.py
python -B .agents/skills/saturation/evals/test_quality_comparison_numeric_edges.py
```

The optional `quality_comparison.py` module evaluates explicitly versioned,
paired outcomes for harness experiments. `reasoning_scaffold.py` provides a
bounded internal routing aid. Neither module is part of the product run's
persistence contract.

## CLI

Evaluate an evaluator-owned JSON snapshot from a path or stdin:

```text
python -B .agents/skills/saturation/evals/report.py observation.json
type observation.json | python -B .agents/skills/saturation/evals/report.py --json
```

The command prints the result and never writes a report. A failed evaluation
returns a non-zero exit code.

## Boundary

Do not add prompt contracts, PCP budgets, trace schemas, run directories,
evidence ledgers, or persisted handoffs to this evaluator. If a future metric
needs richer data, add an in-memory event or an evaluator-owned experiment
input without changing the normal `/saturation` output.
