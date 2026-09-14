import subprocess
import sys
import unittest
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
TRACES_DIR = EVALS_DIR / "traces"
sys.path.insert(0, str(EVALS_DIR))
import grader  # noqa: E402


class GraderTests(unittest.TestCase):
    def grade(self, name):
        return grader.grade_file(TRACES_DIR / name)

    def test_complete_is_accept_100_a(self):
        result = self.grade("complete.json")
        self.assertEqual((result["decision"], result["score"], result["grade"]), ("ACCEPT", 100, "A"))

    def test_all_regressions_are_rejected_with_exact_targets(self):
        expected = {
            "incomplete_handoff.json": ["handoff_payload"],
            "missing_freeze.json": ["context_freeze"],
            "missing_reverify.json": ["repair_reverify"],
            "out_of_scope_write.json": ["write_scope"],
            "premature_completion.json": ["completion_gates"],
            "reviewer_not_readonly.json": ["write_scope", "readonly_review"],
            "wrong_tool_order.json": ["tool_order"],
        }
        for name, criteria in expected.items():
            with self.subTest(name=name):
                result = self.grade(name)
                self.assertEqual(result["decision"], "REJECT")
                self.assertEqual(result["failed_criteria"], criteria)

    def test_invalid_schema_scores_zero(self):
        result = grader.grade_trace({"schema_version": 999}, "invalid")
        self.assertEqual(result["score"], 0)
        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["decision"], "REJECT")

    def test_cli_passes_and_prints_summary(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(EVALS_DIR / "report.py"), "--traces", str(TRACES_DIR)],
            cwd=EVALS_DIR.parents[4],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("SUMMARY: PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
