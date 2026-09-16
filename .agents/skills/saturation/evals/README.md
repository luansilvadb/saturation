# Saturation evals

These evaluators are CI and governance tooling for the saturation skill. They
inspect a redacted, in-memory observation and return a reproducible result;
they do not decide whether a product is ready to launch. Product quality,
target-environment validation, security, privacy, licensing, operations, and
the truth of a `launch-ready` claim remain the responsibility of the lead and
the task-specific harness.

A failed evaluator is a CI/governance signal. Its CLI may return a non-zero
exit code so CI can report the issue, but the evaluator is not a runtime launch
gate and never returns `launch-ready`.

## Contract measured

`grader.py` is the single evaluator. It checks orchestration evidence only:

- exactly one frozen context for the current cycle;
- a complete objective activation matrix for the fixed nine-role roster, with
  `implementation`, `qa-harness`, and `final-reviewer` active in every mode;
- delegated non-lead assignments bound to the current cycle, fresh initial
  sessions, and safe local repair session reuse;
- disjoint write scopes;
- applicable `code_styleguides`, or an explicit `not_applicable` style-guide
  status when the list is empty;
- canonical check and integration statuses;
- a compact canonical handoff with derived clearance, a conditional
  `next_owner`, and no private fields;
- a single fresh final-reviewer assignment after integration;
- the three-failure circuit breaker;
- optional stable evidence IDs and phase packets;
- per-cycle context/report artifacts only; and
- a successful final integration within the declared scopes.

The lead is part of the fixed roster but is the main session: it has an
`implicit` matrix row and no required assignment or specialist handoff.

## Per-cycle paths

The current cycle context is:

```text
.saturation/cycles/<cycle_id>/context.md
```

An optional redacted report uses a sibling path such as:

```text
.saturation/cycles/<cycle_id>/report.json
```

General `.saturation` runtime artifacts are not valid substitutes. The
evaluator never writes these paths.

## Activation matrix

Record one matrix event for every observation. The mode must be one of the
three routing modes, and every role must occur exactly once:

```python
observer.record(
    "activation_matrix",
    cycle_id="cycle-001",
    mode="refactor",
    roles={
        "lead": {
            "status": "implicit",
            "reason": "The lead is the main session.",
            "evidence_ids": ["EV-ACT-001"],
        },
        "architect-data": {"status": "active"},
        "implementation": {"status": "active"},
        "qa-harness": {"status": "active"},
        "reliability-release": {"status": "active"},
        "final-reviewer": {"status": "active"},
        "product-domain": {
            "status": "not_applicable",
            "reason": "No product workflow changes.",
            "evidence_ids": ["EV-ACT-002"],
        },
        "experience-fidelity": {
            "status": "not_applicable",
            "reason": "No user-facing surface changes.",
            "evidence_ids": ["EV-ACT-003"],
        },
        "security-privacy-ip": {
            "status": "not_applicable",
            "reason": "No security or asset boundary changes.",
            "evidence_ids": ["EV-ACT-004"],
        },
    },
)
```

The matrix is a governance record, not a replacement for the role contracts.
Conditional roles may be `not_applicable` only with a concise reason and
stable evidence IDs. The lead is implicit rather than active.

## Observation hook

The runtime may use `RunObserver` from `grader.py`:

```python
observer = RunObserver()
observer.record(
    "context_frozen",
    cycle_id="cycle-001",
    path=".saturation/cycles/cycle-001/context.md",
    frozen=True,
    base_revision="a2b3b38",
    workspace="cycle-001-isolated",
    isolation="isolated",
    risk_matrix_id="EV-RISK-001",
    dependency_graph_id="EV-DEPENDENCY-001",
    gate_registry_id="EV-GATES-001",
    evidence_ids=[
        "EV-RISK-001",
        "EV-DEPENDENCY-001",
        "EV-GATES-001",
    ],
)
events = observer.snapshot()
result = evaluate_events(events)
```

Useful event kinds and their redacted fields are:

- `context_frozen` with `cycle_id`, per-cycle `path`, `frozen`, base revision,
  workspace isolation, and evidence IDs for the risk matrix, dependency graph,
  and gate registry;
- `activation_matrix` with `cycle_id`, `mode`, and one row for each fixed role;
- `assignment` with `cycle_id`, a non-lead `agent_id`, `assignment_id`,
  `session_id`, `fresh_session`, scopes, and `style_guides`;
- `check` with `cycle_id` and canonical `pass`, `skip`, or `not_applicable`
  status;
- `integrated` with `cycle_id`, an explicit `integration_owner`, canonical
  `complete` status, and final changed paths;
- optional `evidence`/`evidence_registered` and `phase_packet` events; and
- `report` or `durable_path`, each bound to the current cycle, for a per-cycle
  report/context assertion.

Assignments marked as local repairs may reuse their owner's session when
`fresh_session` is `False`; initial assignments and the final reviewer must
use fresh sessions. Empty style-guide lists are valid only when accompanied
by `style_guides_status="not_applicable"` (the shorthand
`style_guides="not_applicable"` is also accepted).

Evidence payloads contain opaque IDs such as `EV-ACT-001`, not prompts,
transcripts, tool output, secrets, credentials, unnecessary PII, or private
reasoning. Additive event kinds and fields remain ignored unless they use one
of the explicitly validated contracts above. Breaking changes need an
explicit version and tests.

## CLI

Evaluate a CI-owned JSON snapshot from a path or stdin:

```text
python -B .agents/skills/saturation/evals/grader.py observation.json
type observation.json | python -B .agents/skills/saturation/evals/grader.py --json
```

The command prints the governance result and never writes a report. Its exit
code is a CI signal only.

## Boundary

Keep this evaluator free of prompt contracts, token budgets, trace schemas,
run directories, evidence ledgers, and persisted handoffs. If a future metric
needs richer data, add a redacted in-memory event or an evaluator-owned
experiment input without changing the normal saturation output.
