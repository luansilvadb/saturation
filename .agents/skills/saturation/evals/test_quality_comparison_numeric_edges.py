"""Numeric and evidence identifier boundary regressions."""

from __future__ import annotations

import importlib
import unittest

from test_quality_comparison import _comparison, _signals


class NumericEdgeTests(unittest.TestCase):
    """Ensure malformed finite-number and evidence inputs fail safely."""

    def test_empty_evidence_identifier_is_rejected(self):
        module = importlib.import_module("reasoning_scaffold")

        with self.assertRaises(ValueError):
            module.classify_activation(_signals(), ["EV-"])

    def test_overflowing_observation_is_rejected_without_an_exception(self):
        module = importlib.import_module("quality_comparison")
        comparison = _comparison()
        comparison["tasks"][0]["candidate"][0]["latency_ms"] = 10**1000

        self.assertTrue(module.validate_comparison(comparison))

    def test_overflowing_registered_lift_is_rejected_without_an_exception(self):
        module = importlib.import_module("quality_comparison")
        comparison = _comparison()
        comparison["pre_registration"]["minimum_lift"] = 10**1000

        self.assertTrue(module.validate_comparison(comparison))


if __name__ == "__main__":
    unittest.main()
