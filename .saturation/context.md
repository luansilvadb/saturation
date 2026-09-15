# Saturation Context

Status: FROZEN

## Objective

Update the saturation prompt/harness evaluation policy so the current
prompt/harness version does not measure or infer a quality increase or
decrease. Quality deltas may be measured only by a future, explicitly
versioned prompt/harness comparison with real outcome data. Preserve the
current deterministic workflow grade and descriptive token telemetry.

## Scope

- `.agents/skills/saturation/SKILL.md`
- `.agents/skills/saturation/code_styleguides/prompting.md`
- `.agents/skills/saturation/evals/README.md`
- `.agents/skills/saturation/evals/grader.py`
- `.agents/skills/saturation/evals/token_metrics.py`
- `.agents/skills/saturation/evals/test_grader.py`
- `README.md`

Changes must remain limited to policy, documentation, evaluator behavior, and
focused tests needed to enforce the deferral rule. Do not add provider calls,
benchmark claims, or external effects. Preserve unrelated user work already
present in the working tree.

## Quality

- The current schema and workflow acceptance behavior remain deterministic and
  unchanged for existing fixtures.
- No current-version report, metric, or test claims that tokens caused a
  quality improvement or regression.
- A future comparison is clearly distinguished from a same-version trace and
  cannot be considered available without explicit version identities and real
  outcome observations.
- Documentation and tests state the limitation unambiguously.

## Constraints

- Keep machine-readable contract keys, identifiers, enum values, and paths
  unchanged unless a versioned contract extension is required.
- Do not invent benchmark measurements or use token counts as a proxy for
  quality.
- Token telemetry remains descriptive and must not affect dispatch or the
  110-point workflow grade.
- Keep the evaluator dependency-free and compatible with the existing Python
  standard-library implementation.
- Operational prompts, handoffs, reports, and artifacts are written in
  English; user requirements may be quoted as data.
- Frozen context is immutable after this point.

## Decisions

- Interpret “next version of the prompt/harness” as an explicit future
  versioned comparison, not another execution of the current v3 harness.
- Treat quality increase/decrease as unavailable in the current version unless
  both a baseline and candidate version plus observed outcome data are part of
  a future contract.
- Keep current trace grading focused on observable workflow correctness;
  forward-looking quality comparison is a separate, non-decisive concern until
  its contract is versioned.

## Principles

- Measure only what the current contract can identify and observe.
- Separate descriptive cost/token telemetry from quality claims.
- Preserve immutable prompt records and avoid retroactive interpretation.
- Prefer an explicit deferred status over an inferred quality delta.

## Verification Criteria

- Existing complete and regression fixtures retain their expected decisions and
  scores.
- Tests cover the absence/deferment of current-version quality comparison and
  reject or ignore unsupported same-version quality claims according to the
  chosen contract behavior.
- Any future-version comparison path is gated by explicit version identities
  and observed outcomes, if such a path is added.
- `prompt_contract.py`, `report.py`, and `test_grader.py` complete
  successfully, with no unresolved risks.
