"""Adversarial edge coverage for the future comparison contracts."""

from __future__ import annotations

import copy
import importlib
import unittest
from typing import Any, Callable, Dict, List

from test_quality_comparison import _comparison, _run, _signals, _task


def _load_module(name: str) -> Any:
    """Load one implementation module for edge-case coverage."""

    return importlib.import_module(name)


class ScaffoldEdgeTests(unittest.TestCase):
    """Exercise malformed inputs and every scaffold routing boundary."""

    def test_malformed_signal_and_evidence_inputs_are_rejected(self):
        module = _load_module("reasoning_scaffold")
        cases = [
            ({}, ["EV-EDGE-001"]),
            (_signals(interdependent_acceptance=1), ["EV-EDGE-002"]),
            (_signals(), "EV-EDGE-003"),
            (_signals(), []),
            (_signals(), ["BAD-EDGE-004"]),
            (_signals(), ["EV-EDGE-005", "EV-EDGE-005"]),
            (_signals(), None),
        ]

        for index, (signals, evidence) in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):
                    module.classify_activation(signals, evidence)


class QualityComparisonEdgeTests(unittest.TestCase):
    """Exercise validation failures not needed by the primary contract tests."""

    def _assert_invalid(self, comparison: Any) -> None:
        module = _load_module("quality_comparison")
        self.assertTrue(module.validate_comparison(comparison))

    def _cases(self) -> List[Any]:
        """Build independent malformed comparisons for validation coverage."""

        cases: List[Any] = [None, {}, {"policy_version": "wrong"}]

        def add(mutator: Callable[[Dict[str, Any]], None]) -> None:
            comparison = copy.deepcopy(_comparison())
            mutator(comparison)
            cases.append(comparison)

        add(lambda value: value.update(policy_version="wrong"))
        add(lambda value: value.update(comparison_id=""))
        add(lambda value: value.update(baseline_version=""))
        add(lambda value: value.update(candidate_version=""))
        add(
            lambda value: value.update(
                candidate_version=value["baseline_version"]
            )
        )
        add(lambda value: value.update(task_suite_version=""))
        add(lambda value: value.update(oracle_version=""))
        add(lambda value: value.update(environment=None))
        add(lambda value: value.update(environment={}))
        add(
            lambda value: value["environment"].update(model="")
        )
        add(lambda value: value.update(pre_registration=None))
        add(lambda value: value["pre_registration"].update(repetitions=2))
        add(
            lambda value: value["pre_registration"].update(
                minimum_lift=None
            )
        )
        add(
            lambda value: value["pre_registration"].update(
                minimum_lift="0.05"
            )
        )
        add(
            lambda value: value["pre_registration"].update(
                aggregation="sample_mean"
            )
        )
        add(
            lambda value: value["pre_registration"].update(
                critical_regression_policy="allow"
            )
        )
        add(
            lambda value: value["pre_registration"].update(
                uncertainty=None
            )
        )
        add(
            lambda value: value["pre_registration"]["uncertainty"].update(
                method="other"
            )
        )
        add(
            lambda value: value["pre_registration"]["uncertainty"].update(
                level=0
            )
        )
        add(
            lambda value: value["pre_registration"]["uncertainty"].update(
                samples=0
            )
        )
        add(
            lambda value: value["pre_registration"]["uncertainty"].update(
                seed=-1
            )
        )
        add(lambda value: value.update(tasks=None))
        add(lambda value: value.update(tasks=[]))
        add(lambda value: value.update(tasks=[{}]))
        add(
            lambda value: value["tasks"].extend(
                [copy.deepcopy(value["tasks"][0])]
            )
        )
        add(lambda value: value["tasks"][0].update(task_id=""))
        add(lambda value: value["tasks"][0].update(stratum=""))
        add(lambda value: value["tasks"][0].update(baseline=None))
        add(lambda value: value["tasks"][0].update(candidate=None))
        add(
            lambda value: value["tasks"][0]["candidate"].pop()
        )
        add(
            lambda value: value["tasks"][0]["candidate"].__setitem__(
                0, {}
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                run_id=""
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                passed=1
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                workflow_passed=1
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                critical_regressions=["unknown"]
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                critical_regressions=[
                    "out_of_scope_write",
                    "out_of_scope_write",
                ]
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                latency_ms=-1
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                input_tokens=1.5
            )
        )
        add(
            lambda value: value["tasks"][0]["candidate"][0].update(
                run_id=value["tasks"][0]["baseline"][0]["run_id"]
            )
        )
        return cases

    def test_malformed_contract_cases_are_rejected(self):
        for index, comparison in enumerate(self._cases()):
            with self.subTest(case=index):
                self._assert_invalid(comparison)

    def test_optional_observations_and_baseline_gate_are_reported(self):
        module = _load_module("quality_comparison")
        comparison = _comparison(
            [
                _task(1, baseline_passed=True, candidate_passed=False),
                _task(2, baseline_passed=True, candidate_passed=False),
            ]
        )
        for task in comparison["tasks"]:
            for variant in ("baseline", "candidate"):
                for run in task[variant]:
                    run["latency_ms"] = None
                    run["input_tokens"] = None
        comparison["tasks"][0]["baseline"][0]["workflow_passed"] = False

        result = module.evaluate_comparison(comparison)

        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["reason"], "baseline workflow gate failure detected"
        )
        self.assertIsNone(result["observations"]["baseline_latency_ms_average"])
        self.assertIsNone(
            result["observations"]["candidate_input_tokens_average"]
        )

    def test_percentile_covers_singleton_and_interpolation(self):
        module = _load_module("quality_comparison")

        self.assertEqual(module._percentile([1.0], 0.5), 1.0)
        self.assertEqual(module._percentile([0.0, 1.0], 0.25), 0.25)


if __name__ == "__main__":
    unittest.main()
