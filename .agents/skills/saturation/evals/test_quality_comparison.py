"""Test-first contract checks for scaffold routing and quality comparison."""

from __future__ import annotations

import copy
import importlib
import unittest
from typing import Any, Dict, List, Optional


def _load_module(name: str) -> Any:
    """Load a future module and turn absence into a missing-behavior failure."""

    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        raise AssertionError("missing behavior: %s is not implemented" % name) from exc


def _signals(**overrides: bool) -> Dict[str, bool]:
    """Return the canonical scaffold signal set."""

    value = {
        "interdependent_acceptance": False,
        "cross_module_dependency": False,
        "material_repair": False,
        "requires_user_decision": False,
    }
    value.update(overrides)
    return value


def _run(
    run_id: str,
    passed: bool,
    *,
    workflow_passed: bool = True,
    critical_regressions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build one observed task run."""

    return {
        "run_id": run_id,
        "passed": passed,
        "workflow_passed": workflow_passed,
        "critical_regressions": critical_regressions or [],
        "latency_ms": 100,
        "input_tokens": 200,
    }


def _task(
    number: int,
    baseline_passed: bool = False,
    candidate_passed: bool = True,
) -> Dict[str, Any]:
    """Build a task with three paired repetitions per variant."""

    return {
        "task_id": "TASK-%03d" % number,
        "stratum": "python/bugfix/medium",
        "baseline": [
            _run("B-%03d-%d" % (number, index), baseline_passed)
            for index in range(1, 4)
        ],
        "candidate": [
            _run("C-%03d-%d" % (number, index), candidate_passed)
            for index in range(1, 4)
        ],
    }


def _comparison(tasks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Build a valid, fully pre-registered comparison."""

    return {
        "policy_version": "quality-comparison-v1",
        "comparison_id": "CMP-QUALITY-001",
        "baseline_version": "harness-v5",
        "candidate_version": "harness-v6",
        "task_suite_version": "tasks-v1",
        "oracle_version": "oracle-v1",
        "environment": {
            "model": "model-under-test",
            "configuration_digest": "config-digest-001",
            "toolchain_digest": "toolchain-digest-001",
        },
        "pre_registration": {
            "repetitions": 3,
            "minimum_lift": 0.05,
            "aggregation": "macro_task_mean",
            "uncertainty": {
                "method": "paired_bootstrap_v1",
                "level": 0.95,
                "samples": 1000,
                "seed": 0,
            },
            "critical_regression_policy": "candidate_zero",
        },
        "tasks": tasks or [_task(index) for index in range(1, 5)],
    }


class ScaffoldTests(unittest.TestCase):
    """Verify deterministic, evidence-backed scaffold routing."""

    def test_direct_without_activation_signal(self):
        module = _load_module("reasoning_scaffold")
        result = module.classify_activation(_signals(), ["EV-CLASS-001"])

        self.assertEqual(result["policy_version"], "reasoning-scaffold-v1")
        self.assertEqual(result["decision"], "direct")
        self.assertEqual(result["trigger_codes"], [])
        self.assertEqual(result["scaffold_fields"], [])

    def test_activation_uses_canonical_trigger_order(self):
        module = _load_module("reasoning_scaffold")
        result = module.classify_activation(
            _signals(
                material_repair=True,
                interdependent_acceptance=True,
                cross_module_dependency=True,
            ),
            ["EV-CLASS-002"],
        )

        self.assertEqual(result["decision"], "activate")
        self.assertEqual(
            result["trigger_codes"],
            [
                "interdependent_acceptance",
                "cross_module_dependency",
                "material_repair",
            ],
        )
        self.assertEqual(
            result["scaffold_fields"],
            [
                "intended_behavior",
                "assumptions",
                "invariants_and_risks",
                "planned_checks",
                "evidence_refs",
            ],
        )

    def test_user_decision_escalates_instead_of_activating(self):
        module = _load_module("reasoning_scaffold")
        result = module.classify_activation(
            _signals(
                cross_module_dependency=True,
                requires_user_decision=True,
            ),
            ["EV-CLASS-003"],
        )

        self.assertEqual(result["decision"], "escalate")
        self.assertEqual(result["trigger_codes"], ["user_decision_required"])
        self.assertEqual(result["scaffold_fields"], [])

    def test_instructions_are_bounded_and_private(self):
        module = _load_module("reasoning_scaffold")
        instructions = module.scaffold_instructions().lower()

        for field in (
            "intended_behavior",
            "assumptions",
            "invariants_and_risks",
            "planned_checks",
            "evidence_refs",
        ):
            self.assertIn(field, instructions)
        self.assertIn("hidden chain-of-thought", instructions)
        self.assertIn("private scratchpad", instructions)


class QualityComparisonTests(unittest.TestCase):
    """Verify the independent, versioned outcome comparison contract."""

    def test_valid_comparison_computes_macro_rates_and_improvement(self):
        module = _load_module("quality_comparison")
        comparison = _comparison()

        self.assertEqual(module.validate_comparison(comparison), [])
        result = module.evaluate_comparison(comparison)

        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["decision"], "improved")
        self.assertEqual(result["baseline_pass_rate"], 0.0)
        self.assertEqual(result["candidate_pass_rate"], 1.0)
        self.assertEqual(result["delta"], 1.0)
        self.assertEqual(
            result["uncertainty"]["method"], "paired_bootstrap_v1"
        )

    def test_rates_are_task_level_macro_averages(self):
        module = _load_module("quality_comparison")
        comparison = _comparison(
            [
                _task(1, baseline_passed=True, candidate_passed=False),
                _task(2, baseline_passed=False, candidate_passed=True),
            ]
        )

        result = module.evaluate_comparison(comparison)

        self.assertEqual(result["baseline_pass_rate"], 0.5)
        self.assertEqual(result["candidate_pass_rate"], 0.5)
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(result["decision"], "no_meaningful_improvement")

    def test_same_versions_are_rejected_by_validation(self):
        module = _load_module("quality_comparison")
        comparison = _comparison()
        comparison["candidate_version"] = comparison["baseline_version"]

        errors = module.validate_comparison(comparison)

        self.assertTrue(errors)
        self.assertTrue(any("version" in error for error in errors))

    def test_missing_oracle_version_is_rejected(self):
        module = _load_module("quality_comparison")
        comparison = _comparison()
        comparison.pop("oracle_version")

        self.assertTrue(module.validate_comparison(comparison))

    def test_fewer_than_three_repetitions_are_rejected(self):
        module = _load_module("quality_comparison")
        comparison = _comparison()
        comparison["pre_registration"]["repetitions"] = 2
        for task in comparison["tasks"]:
            task["baseline"] = task["baseline"][:2]
            task["candidate"] = task["candidate"][:2]

        errors = module.validate_comparison(comparison)

        self.assertTrue(errors)
        self.assertTrue(any("repetition" in error for error in errors))

    def test_malformed_run_is_rejected(self):
        module = _load_module("quality_comparison")
        comparison = _comparison()
        comparison["tasks"][0]["candidate"][0]["passed"] = "yes"

        self.assertTrue(module.validate_comparison(comparison))

    def test_candidate_critical_regression_rejects_comparison(self):
        module = _load_module("quality_comparison")
        comparison = _comparison()
        comparison["tasks"][0]["candidate"][0]["critical_regressions"] = [
            "out_of_scope_write"
        ]

        result = module.evaluate_comparison(comparison)

        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("out_of_scope_write", result["critical_regressions"])

    def test_candidate_workflow_failure_rejects_comparison(self):
        module = _load_module("quality_comparison")
        comparison = _comparison()
        comparison["tasks"][0]["candidate"][0]["workflow_passed"] = False

        result = module.evaluate_comparison(comparison)

        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["decision"], "rejected")

    def test_below_margin_positive_result_is_inconclusive(self):
        module = _load_module("quality_comparison")
        tasks = [_task(index, False, index == 1) for index in range(1, 22)]

        result = module.evaluate_comparison(_comparison(tasks))

        self.assertGreater(result["delta"], 0.0)
        self.assertLess(result["delta"], 0.05)
        self.assertEqual(result["decision"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
