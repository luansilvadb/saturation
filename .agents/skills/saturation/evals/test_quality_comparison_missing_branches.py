"""Focused regression checks for previously unvisited rejection branches."""

from __future__ import annotations

import importlib
import unittest

from test_quality_comparison import _comparison


class MissingBranchTests(unittest.TestCase):
    """Keep non-mapping and non-string input boundaries executable."""

    def test_non_mapping_signals_are_rejected(self):
        module = importlib.import_module("reasoning_scaffold")

        with self.assertRaises(ValueError):
            module.classify_activation(None, ["EV-BRANCH-001"])

    def test_non_string_comparison_id_is_rejected(self):
        module = importlib.import_module("quality_comparison")
        comparison = _comparison()
        comparison["comparison_id"] = None

        self.assertTrue(module.validate_comparison(comparison))


if __name__ == "__main__":
    unittest.main()
