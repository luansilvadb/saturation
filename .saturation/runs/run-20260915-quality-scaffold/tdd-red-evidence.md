# TDD red evidence

- `evidence_id`: `EV-TDD-RED-QUALITY`
- `command`: `python -B .agents/skills/saturation/evals/test_quality_comparison.py`
- `exit_code`: `1`
- `discovered_tests`: `13`
- `failed_tests`: `13`
- `failure_class`: `missing_behavior`
- `setup_failure`: `false`
- `implementation_present_at_red`: `false`
- `test_artifact_locked_after_red`: `true`

The target tests were discovered and failed because the scaffold and
comparison modules were absent. No raw model output, oracle content, or
private reasoning was persisted.
