# Objective

Review the completed quality-scaffold implementation for correctness and
scope compliance.

# Context

Run `run-20260915-quality-scaffold` is implementing a future, versioned
comparison path and a deterministic bounded scaffold. The parent context at
`.saturation/context.md` is immutable. No quality improvement may be claimed
without real paired benchmark outcomes.

# Scope

Read only these paths: `.agents/skills/saturation/evals/reasoning_scaffold.py`,
`.agents/skills/saturation/evals/quality_comparison.py`, the three
`test_quality_comparison*.py` files, the run coverage adapter and report, the
run context, and the related README/workflow/policy diffs.

# Constraints

Do not edit files, do not inspect or infer hidden chain-of-thought, do not
access external services, and do not read benchmark oracles. Check that the
new path is standard-library only, versioned, deterministic, oracle-isolated,
and does not change v3/v4/v5 behavior.

# Strategy

Perform an independent adversarial review of contract boundaries, decision
logic, malformed input handling, evidence redaction, and test/coverage claims.

# Deliverable

Return a concise finding list with severity, file/line, evidence, and a
recommended repair. If no issue remains, state that explicitly and list the
checks performed.

# Verification

Inspect the current worktree and run only read-only, bounded checks if useful.
Do not change the worktree or persist raw secrets, oracle data, or private
reasoning.

# Handoff

Give the parent agent the findings; the parent owns all repairs and gates.

# Output Contract

Use identifiers `REVIEW-P-004`, `FINDING-*`, and `CHECK-*`. Do not include
private chain-of-thought; provide conclusions and concise evidence only.
