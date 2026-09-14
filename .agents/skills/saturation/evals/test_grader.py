import copy
import subprocess
import sys
import unittest
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
TRACES_DIR = EVALS_DIR / "traces"
sys.path.insert(0, str(EVALS_DIR))
import grader  # noqa: E402


class GraderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.complete = grader.load_trace(TRACES_DIR / "complete.json")

    def grade(self, name):
        return grader.grade_file(TRACES_DIR / name)

    def fixture(self, name):
        return grader.load_trace(TRACES_DIR / name)

    def mutate(self, mutation):
        trace = copy.deepcopy(self.complete)
        mutation(trace)
        return grader.grade_trace(trace, "mutation")

    def assert_failed(self, mutation, expected):
        result = self.mutate(mutation)
        self.assertEqual(result["decision"], "REJECT")
        self.assertEqual(result["failed_criteria"], expected)

    @staticmethod
    def event(trace, event_id):
        return next(
            event for event in trace["events"] if event["event_id"] == event_id
        )

    @staticmethod
    def call(trace, call_id):
        return next(
            call for call in trace["tool_calls"] if call["call_id"] == call_id
        )

    def test_complete_is_accept_100_a(self):
        result = self.grade("complete.json")
        self.assertEqual(
            (result["decision"], result["score"], result["grade"]),
            ("ACCEPT", 100, "A"),
        )

    def test_all_regressions_are_rejected_with_exact_targets(self):
        fixtures = [
            path for path in grader.discover_traces(TRACES_DIR)
            if path.name != "complete.json"
        ]
        self.assertGreaterEqual(len(fixtures), 10)
        for path in fixtures:
            with self.subTest(name=path.name):
                trace = grader.load_trace(path)
                result = grader.grade_trace(trace, str(path))
                self.assertEqual(result["decision"], trace["expected_decision"])
                self.assertEqual(
                    result["failed_criteria"],
                    trace["expected_failed_criteria"],
                )

    def test_rubric_mirrors_grader_checks_and_fixture_matrix(self):
        rubric = grader.load_trace(EVALS_DIR / "rubric.json")
        result = grader.grade_trace(copy.deepcopy(self.complete), "rubric-check")
        actual_checks = {
            criterion["id"]: [check["id"] for check in criterion["checks"]]
            for criterion in result["criteria"]
        }
        declared_checks = {
            criterion["id"]: criterion["checks"]
            for criterion in rubric["criteria"]
        }
        self.assertEqual(declared_checks, actual_checks)

        declared_matrix = {
            row["trace"]: (row["decision"], row["failed_criteria"])
            for row in rubric["regression_matrix"]
        }
        fixture_matrix = {
            path.name: (
                trace["expected_decision"],
                trace["expected_failed_criteria"],
            )
            for path in grader.discover_traces(TRACES_DIR)
            for trace in [grader.load_trace(path)]
        }
        self.assertEqual(declared_matrix, fixture_matrix)

    def test_fixture_incomplete_handoff_has_missing_stop(self):
        trace = self.fixture("incomplete_handoff.json")
        self.assertNotIn("stop", self.event(trace, "E-002")["payload"])

    def test_fixture_missing_freeze_has_false_freeze_flags(self):
        payload = self.event(
            self.fixture("missing_freeze.json"), "E-001"
        )["payload"]
        self.assertIs(payload["frozen"], False)
        self.assertIs(payload["before_delegation"], False)

    def test_fixture_missing_handoff_contract_has_no_typed_input(self):
        payload = self.event(
            self.fixture("missing_handoff_contract.json"), "E-006"
        )["payload"]
        self.assertNotIn("input", payload)

    def test_fixture_missing_reverify_has_no_gap_recheck(self):
        payload = self.event(
            self.fixture("missing_reverify.json"), "E-009"
        )["payload"]
        self.assertEqual(payload["rechecks"], [])

    def test_fixture_missing_verifier_entries_omits_named_coverage(self):
        verifier = self.event(
            self.fixture("missing_verifier_dimension_criterion.json"), "E-009"
        )["payload"]["verifier"]
        self.assertNotIn("clarity", verifier["dimensions"])
        self.assertNotIn("tool_order", verifier["criteria"])

    def test_fixture_missing_declared_optional_dimension_omits_behavior(self):
        trace = self.fixture("missing_declared_optional_dimension.json")
        self.assertIn("behavior", trace["trace_contract"]["verifier"]["dimensions"])
        verifier = self.event(trace, "E-009")["payload"]["verifier"]
        self.assertNotIn("behavior", verifier["dimensions"])

    def test_fixture_out_of_read_scope_targets_skill_file(self):
        trace = self.fixture("out_of_read_scope.json")
        path = ".agents/skills/saturation/SKILL.md"
        self.assertIn(path, self.event(trace, "E-003")["reads"])
        self.assertIn(path, self.call(trace, "C-003")["reads"])
        assignment = next(
            item for item in trace["assignments"]
            if item["assignment_id"] == "A-impl"
        )
        self.assertNotIn(path, assignment["read_scope"])

    def test_fixture_out_of_scope_write_targets_skill_file(self):
        trace = self.fixture("out_of_scope_write.json")
        path = ".agents/skills/saturation/SKILL.md"
        self.assertIn(path, self.event(trace, "E-007")["writes"])
        self.assertIn(path, self.call(trace, "C-005")["writes"])

    def test_fixture_premature_completion_has_failed_verify_flag(self):
        payload = self.event(
            self.fixture("premature_completion.json"), "E-013"
        )["payload"]
        self.assertIs(payload["verification_passed"], False)

    def test_fixture_reviewer_not_readonly_writes_review_notes(self):
        trace = self.fixture("reviewer_not_readonly.json")
        path = ".agents/skills/saturation/evals/review-notes.json"
        self.assertEqual(self.call(trace, "C-004")["mode"], "write")
        self.assertIn(path, self.call(trace, "C-004")["writes"])
        self.assertIn(path, self.event(trace, "E-005")["writes"])

    def test_fixture_unrelated_evidence_has_wrong_gate_source(self):
        trace = self.fixture("unrelated_evidence_tool_link.json")
        record = next(
            item for item in trace["evidence"]
            if item["evidence_id"] == "EV-013"
        )
        self.assertEqual(record["kind"], "gate")
        self.assertEqual(record["source_id"], "C-008")

    def test_fixture_wrong_tool_order_places_implement_before_inspect(self):
        trace = self.fixture("wrong_tool_order.json")
        call_ids = [call["call_id"] for call in trace["tool_calls"]]
        self.assertLess(call_ids.index("C-003"), call_ids.index("C-002"))

    def test_missing_implementation_link(self):
        def mutation(trace):
            self.event(trace, "E-003")["payload"]["tool_call_ref"] = "C-missing"

        self.assert_failed(mutation, ["evidence"])

    def test_unrelated_handoff_evidence_source(self):
        def mutation(trace):
            handoff = self.event(trace, "E-004")
            handoff["payload"]["output"]["evidence"] = ["EV-005"]
            handoff["evidence"] = ["EV-005"]

        self.assert_failed(mutation, ["handoff_payload", "evidence"])

    def test_tool_actor_mismatch(self):
        def mutation(trace):
            self.call(trace, "C-004")["actor_id"] = "rev2"

        self.assert_failed(mutation, ["write_scope", "readonly_review", "evidence"])

    def test_tool_assignment_mismatch(self):
        def mutation(trace):
            self.call(trace, "C-004")["assignment_id"] = "A-review2"

        self.assert_failed(mutation, ["write_scope", "evidence"])

    def test_tool_reads_mismatch(self):
        def mutation(trace):
            self.call(trace, "C-003")["reads"] = []

        self.assert_failed(mutation, ["evidence"])

    def test_read_outside_declared_assignment_scope(self):
        def mutation(trace):
            path = ".agents/skills/saturation/SKILL.md"
            self.event(trace, "E-003")["reads"].append(path)
            self.call(trace, "C-003")["reads"].append(path)

        self.assert_failed(mutation, ["write_scope"])

    def test_tool_writes_mismatch(self):
        def mutation(trace):
            self.call(trace, "C-003")["writes"].append(
                ".agents/skills/saturation/evals/grader.py"
            )

        self.assert_failed(mutation, ["evidence"])

    def test_tool_wrong_event_ref(self):
        def mutation(trace):
            self.call(trace, "C-003")["event_ref"] = "E-007"

        self.assert_failed(mutation, ["evidence"])

    def test_missing_tool_event_ref_rejects_without_reverse_link_inference(self):
        def mutation(trace):
            del self.call(trace, "C-003")["event_ref"]

        self.assert_failed(mutation, ["evidence"])

    def test_duplicate_handoff_reverse_link(self):
        def mutation(trace):
            self.event(trace, "E-005")["payload"]["handoff_ref"] = "E-002"

        self.assert_failed(mutation, ["handoff_payload"])

    def test_missing_verifier_dimension(self):
        def mutation(trace):
            verifier = self.event(trace, "E-009")["payload"]["verifier"]
            del verifier["dimensions"]["clarity"]

        self.assert_failed(mutation, ["evidence", "repair_reverify"])

    def test_missing_declared_optional_verifier_dimension(self):
        def mutation(trace):
            verifier = self.event(trace, "E-009")["payload"]["verifier"]
            del verifier["dimensions"]["behavior"]

        self.assert_failed(mutation, ["evidence", "repair_reverify"])

    def test_declared_optional_dimension_can_be_evidenced_not_applicable(self):
        trace = copy.deepcopy(self.complete)
        entry = self.event(trace, "E-009")["payload"]["verifier"]["dimensions"]["error_handling"]
        entry["applicable"] = False
        entry["result"] = "not_applicable"
        record = next(
            item for item in trace["evidence"]
            if item["evidence_id"] == "EV-ver-error_handling"
        )
        record["applicable"] = False
        record["result"] = "not_applicable"
        result = grader.grade_trace(trace, "optional-not-applicable")
        self.assertEqual(
            (result["decision"], result["score"], result["grade"]),
            ("ACCEPT", 100, "A"),
        )

    def test_missing_verifier_criterion(self):
        def mutation(trace):
            verifier = self.event(trace, "E-009")["payload"]["verifier"]
            del verifier["criteria"]["tool_order"]

        self.assert_failed(mutation, ["evidence", "repair_reverify"])

    def test_malformed_handoff_output(self):
        def mutation(trace):
            output = self.event(trace, "E-006")["payload"]["output"]
            output["status"] = "unknown"

        self.assert_failed(mutation, ["handoff_payload"])

    def test_malformed_handoff_error(self):
        def mutation(trace):
            payload = self.event(trace, "E-006")["payload"]
            payload["error"] = {"code": "broken"}

        self.assert_failed(mutation, ["handoff_payload"])

    def test_malformed_handoff_stop(self):
        def mutation(trace):
            payload = self.event(trace, "E-006")["payload"]
            payload["stop"] = {"required": True, "reason": "blocked"}

        self.assert_failed(mutation, ["handoff_payload"])

    def test_duplicate_sequence_rejects_order(self):
        def mutation(trace):
            self.event(trace, "E-003")["sequence"] = self.event(
                trace, "E-002"
            )["sequence"]

        self.assert_failed(mutation, ["tool_order"])

    def test_noncausal_linked_sequence_rejects_order(self):
        def mutation(trace):
            implementation = self.event(trace, "E-003")
            implementation["sequence"] = self.call(trace, "C-003")["sequence"] - 1

        self.assert_failed(mutation, ["tool_order"])

    def test_cross_array_lifecycle_violation_rejects_order(self):
        def mutation(trace):
            ordered_ids = [
                "C-001", "E-001", "C-002", "E-inspect", "E-002", "C-003",
                "C-004", "E-003", "E-004", "E-005", "E-006", "C-005",
                "E-007", "E-008", "C-006", "E-009", "E-010", "C-007",
                "E-011", "C-008", "E-012", "C-gate", "E-013",
            ]
            items = {
                item.get("event_id", item.get("call_id")): item
                for item in trace["events"] + trace["tool_calls"]
            }
            for sequence, item_id in enumerate(ordered_ids, start=1):
                items[item_id]["sequence"] = sequence
            for collection in (trace["events"], trace["tool_calls"]):
                sequences = [item["sequence"] for item in collection]
                self.assertEqual(sequences, sorted(sequences))

        self.assert_failed(mutation, ["tool_order"])

    def test_event_rejects_unrelated_registered_evidence(self):
        def mutation(trace):
            self.event(trace, "E-005")["evidence"].append("EV-003")

        self.assert_failed(mutation, ["evidence"])

    def test_invalid_schema_scores_zero(self):
        result = grader.grade_trace({"schema_version": 999}, "invalid")
        self.assertEqual(result["score"], 0)
        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["decision"], "REJECT")

    def test_cli_passes_and_prints_summary(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(EVALS_DIR / "report.py"),
                "--traces",
                str(TRACES_DIR),
            ],
            cwd=EVALS_DIR.parents[4],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("SUMMARY: PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
