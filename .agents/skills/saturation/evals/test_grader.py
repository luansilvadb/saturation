import copy
import subprocess
import sys
import unittest
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
TRACES_DIR = EVALS_DIR / "traces"
TDD_TRACES_DIR = EVALS_DIR / "traces_v4"
sys.path.insert(0, str(EVALS_DIR))
import grader  # noqa: E402
import prompt_contract  # noqa: E402
import tdd_contract  # noqa: E402
import coverage_contract  # noqa: E402
import token_metrics  # noqa: E402


class GraderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.complete = grader.load_trace(TRACES_DIR / "complete.json")
        cls.complete_v4 = grader.load_trace(TDD_TRACES_DIR / "complete.json")

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

    def test_complete_is_accept_110_a(self):
        result = self.grade("complete.json")
        self.assertEqual(
            (result["decision"], result["score"], result["grade"]),
            ("ACCEPT", 110, "A"),
        )
        self.assertEqual(result["metrics"]["prompt_count"], 5)
        self.assertEqual(result["metrics"]["pcp"]["average"], 3)
        self.assertEqual(result["metrics"]["strategy_counts"], {"direct": 5})

    def test_tdd_workflow(self):
        """The persisted v4 fixture is the executable TDD contract artifact."""

        result = grader.grade_trace(self.complete_v4, "v4-complete")
        self.assertEqual(
            (result["decision"], result["score"], result["max_score"], result["grade"]),
            ("ACCEPT", 120, 120, "A"),
        )
        self.assertEqual(result["metrics"]["tdd"]["valid_red"], 1)
        self.assertEqual(result["metrics"]["tdd"]["valid_green"], 1)

    def tdd_mutate(self, mutation):
        trace = copy.deepcopy(self.complete_v4)
        mutation(trace)
        return grader.grade_trace(trace, "v4-mutation")

    def coverage_trace(self):
        trace = copy.deepcopy(self.complete_v4)
        report_path = ".agents/skills/saturation/evals/coverage-report.json"
        source_path = ".agents/skills/saturation/evals/grader.py"

        trace["schema_version"] = 5
        trace["trace_schema_version"] = 5
        trace["score_max"] = 130
        trace["trace_contract"]["version"] = 5
        trace["trace_contract"]["coverage"] = coverage_contract.expected_declaration()
        trace["trace_contract"]["verifier"]["criteria"].append("coverage_workflow")

        for item in trace["tool_calls"] + trace["events"]:
            if item.get("event_id", item.get("call_id")) == "C-TDD-REG":
                item["writes"] = [report_path]
                item["mode"] = "coverage"
            elif item.get("event_id", item.get("call_id")) == "E-TDD-REG":
                item["writes"] = [report_path]
            elif item.get("event_id", item.get("call_id")) == "C-TDD-VER":
                item["reads"] = list(item["reads"]) + [report_path]
            elif item.get("event_id", item.get("call_id")) == "E-TDD-VER":
                item["reads"] = list(item["reads"]) + [report_path]

        trace["evidence"].extend(
            [
                {
                    "evidence_id": "EV-COV-TARGET",
                    "source_id": "C-TDD-REG",
                    "kind": "test",
                    "claim": "Instrumented target regression reports passing line and branch coverage.",
                    "paths": [source_path, report_path],
                },
                {
                    "evidence_id": "EV-COV-VERIFIER",
                    "source_id": "C-TDD-VER",
                    "kind": "verification",
                    "claim": "An independent verifier confirms the instrumented coverage report.",
                    "paths": [source_path, report_path],
                },
                {
                    "evidence_id": "EV-crit-coverage",
                    "source_id": "E-009",
                    "kind": "verification",
                    "criterion_id": "coverage_workflow",
                    "claim": "Coverage workflow passed independent verification.",
                    "paths": [source_path, report_path],
                },
            ]
        )
        trace["coverage"] = {
            "policy_version": "coverage-v1",
            "required_for": ["implementation", "repair"],
            "metrics": ["line", "branch"],
            "thresholds": {"line": 80, "branch": 80},
            "adapter": {
                "id": "python.coverage",
                "language": "python",
                "tool": "coverage.py",
                "version": "7.6.1",
            },
            "source_paths": [source_path],
            "command": copy.deepcopy(trace["tdd"]["commands"]["regression"]),
            "report": {
                "path": report_path,
                "format": "json",
                "immutable_after_run": True,
            },
            "target_run": {
                "run_id": "RUN-REGRESSION",
                "source_id": "C-TDD-REG",
                "status": "pass",
                "metrics": {"line": 92, "branch": 88},
                "evidence": ["EV-COV-TARGET"],
            },
            "verifier_run": {
                "run_id": "RUN-VERIFIER",
                "source_id": "C-TDD-VER",
                "status": "pass",
                "metrics": {"line": 91, "branch": 87},
                "evidence": ["EV-COV-VERIFIER"],
            },
        }
        verify_event = next(event for event in trace["events"] if event["event_id"] == "E-009")
        verify_event["payload"]["verifier"]["criteria"]["coverage_workflow"] = {
            "result": "pass",
            "claim": "criterion checked",
            "evidence": ["EV-crit-coverage"],
        }
        trace["tdd"]["persisted_trace"]["sha256"] = tdd_contract._trace_hash(trace)
        return trace

    def coverage_mutate(self, mutation):
        trace = self.coverage_trace()
        mutation(trace)
        return grader.grade_trace(trace, "v5-mutation")

    def assert_coverage_rejected(self, mutation):
        result = self.coverage_mutate(mutation)
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn("coverage_workflow", result["failed_criteria"])
        return result

    def test_coverage_workflow(self):
        result = grader.grade_trace(self.coverage_trace(), "v5-complete")
        self.assertEqual(
            (result["decision"], result["score"], result["max_score"], result["grade"]),
            ("ACCEPT", 130, 130, "A"),
        )
        self.assertEqual(result["metrics"]["coverage"]["status"], "required")
        self.assertEqual(result["metrics"]["coverage"]["line"], 92)
        self.assertEqual(result["metrics"]["coverage"]["branch"], 88)

    def test_coverage_requires_line_and_branch_thresholds(self):
        self.assert_coverage_rejected(
            lambda trace: trace["coverage"]["thresholds"].pop("branch")
        )

    def test_coverage_blocks_below_threshold_metrics(self):
        self.assert_coverage_rejected(
            lambda trace: trace["coverage"]["target_run"]["metrics"].update(branch=79)
        )

    def test_coverage_requires_persisted_report(self):
        self.assert_coverage_rejected(
            lambda trace: trace["coverage"]["report"].update(immutable_after_run=False)
        )

    def test_coverage_requires_instrumented_report_write(self):
        def mutation(trace):
            call = self.call(trace, "C-TDD-REG")
            call["writes"] = []

        self.assert_coverage_rejected(mutation)

    def test_coverage_requires_independent_verifier_evidence(self):
        def mutation(trace):
            trace["coverage"]["verifier_run"]["evidence"] = []

        self.assert_coverage_rejected(mutation)

    def test_v5_requires_coverage_block(self):
        trace = self.coverage_trace()
        trace.pop("coverage")
        result = grader.grade_trace(trace, "v5-missing-coverage")
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn("coverage_workflow", result["failed_criteria"])

    def assert_tdd_rejected(self, mutation):
        result = self.tdd_mutate(mutation)
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn("tdd_workflow", result["failed_criteria"])
        return result

    def test_v4_validation_is_non_mutating(self):
        trace = copy.deepcopy(self.complete_v4)
        before = copy.deepcopy(trace)
        self.assertEqual(grader.validate_trace(trace), [])
        self.assertEqual(trace, before)

    def test_red_must_be_a_real_missing_behavior_failure(self):
        def mutation(trace):
            run = next(item for item in trace["tdd"]["runs"] if item["kind"] == "red")
            run.update(status="pass", exit_code=0, failed_test_ids=[], failure_reason=None)

        self.assert_tdd_rejected(mutation)

    def test_red_must_not_be_a_syntax_failure(self):
        def mutation(trace):
            run = next(item for item in trace["tdd"]["runs"] if item["kind"] == "red")
            run["failure_reason"] = "syntax_error"

        self.assert_tdd_rejected(mutation)

    def test_test_artifact_is_locked_after_red(self):
        def mutation(trace):
            event = self.event(trace, "E-003")
            event["writes"].append(".agents/skills/saturation/evals/test_grader.py")

        self.assert_tdd_rejected(mutation)

    def test_tdd_commands_reject_shell_metacharacters(self):
        def mutation(trace):
            trace["tdd"]["commands"]["target"]["argv"].append("&")

        self.assert_tdd_rejected(mutation)

    def test_verifier_must_be_independent(self):
        def mutation(trace):
            trace["actors"]["ver"]["role"] = "implementer"

        self.assert_tdd_rejected(mutation)

    def test_trace_hash_is_an_integrity_gate(self):
        def mutation(trace):
            trace["tdd"]["persisted_trace"]["sha256"] = "0" * 64

        self.assert_tdd_rejected(mutation)

    def test_approved_documentation_exemption_can_skip_the_cycle(self):
        trace = copy.deepcopy(self.complete_v4)
        tdd = trace["tdd"]
        tdd.update(
            classification="exempt",
            exemption={
                "kind": "documentation_only",
                "reason": "The assignment changes only operational documentation.",
                "alternative": "Independent documentation diff review.",
                "approved_by_actor_id": "orch",
                "evidence": ["EV-inspect"],
            },
            commands={},
            test_artifacts=[],
            test_ids=[],
            acceptance_map=[],
            cycles=[],
            runs=[],
            verifier_run_id=None,
        )
        tdd["persisted_trace"]["sha256"] = tdd_contract._trace_hash(trace)
        result = grader.grade_trace(trace, "v4-exempt")
        self.assertEqual(
            (result["decision"], result["score"], result["grade"]),
            ("ACCEPT", 120, "A"),
        )
        self.assertEqual(result["metrics"]["tdd"]["waivers"], 1)

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
        declared_checks = {
            criterion["id"]: criterion["checks"]
            for criterion in rubric["criteria"]
        }
        for trace in (self.complete, self.complete_v4, self.coverage_trace()):
            result = grader.grade_trace(copy.deepcopy(trace), "rubric-check")
            actual_checks = {
                criterion["id"]: [check["id"] for check in criterion["checks"]]
                for criterion in result["criteria"]
            }
            self.assertEqual(
                {criterion_id: declared_checks[criterion_id] for criterion_id in actual_checks},
                actual_checks,
            )

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
        fixture_matrix["traces_v4/complete.json"] = (
            self.complete_v4["expected_decision"],
            self.complete_v4["expected_failed_criteria"],
        )
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

        self.assert_failed(mutation, ["evidence", "prompt_contract"])

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

        self.assert_failed(mutation, ["handoff_payload", "prompt_contract"])

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
            ("ACCEPT", 110, "A"),
        )

    def test_prompt_normalization_and_hash_are_deterministic(self):
        text = "\r\n  ## Role  \r\nvalue\t\r\n\r\n"
        normalized = prompt_contract.normalize_prompt(text)
        self.assertEqual(normalized, "  ## Role\nvalue\n")
        self.assertEqual(
            prompt_contract.prompt_sha256(text),
            prompt_contract.prompt_sha256(normalized),
        )

    def test_complete_reports_estimated_input_tokens_by_phase(self):
        result = self.grade("complete.json")
        tokens = result["metrics"]["tokens"]
        estimated = tokens["estimated"]
        dispatched = estimated["dispatched"]

        self.assertEqual(estimated["estimator"], token_metrics.ESTIMATOR_ID)
        self.assertEqual(
            estimated["measurement_scope"], token_metrics.ESTIMATOR_SCOPE
        )
        self.assertEqual(dispatched["count"], 5)
        self.assertEqual(dispatched["total"], 1960)
        self.assertEqual(
            {
                phase: values["total"]
                for phase, values in dispatched["by_phase"].items()
            },
            {
                "implement": 388,
                "review": 392,
                "repair": 386,
                "verify": 395,
                "final_review": 399,
            },
        )
        self.assertEqual(estimated["attempts"]["total"], 0)
        self.assertEqual(tokens["observed"]["status"], "not_available")

    def test_token_estimator_uses_canonical_utf8_bytes(self):
        text = "\r\n  café\t\r\n"
        normalized = prompt_contract.normalize_prompt(text)
        expected = max(1, (len(normalized.encode("utf-8")) + 3) // 4)
        self.assertEqual(token_metrics.estimate_input_tokens(text), expected)

    def test_extra_prompt_text_changes_tokens_without_changing_quality_grade(self):
        trace = copy.deepcopy(self.complete)
        prompt = trace["prompts"][0]
        prompt["rendered_prompt"] += (
            "This additional quality-preserving note is observable evidence.\n"
        )
        prompt["normalized_sha256"] = prompt_contract.prompt_sha256(
            prompt["rendered_prompt"]
        )

        result = grader.grade_trace(trace, "token-growth")

        self.assertEqual(
            (result["decision"], result["score"], result["grade"]),
            ("ACCEPT", 110, "A"),
        )
        self.assertGreater(
            result["metrics"]["tokens"]["estimated"]["dispatched"]["total"],
            1960,
        )

    def assert_quality_claim_is_deferred(self, direction):
        trace = copy.deepcopy(self.complete)
        trace["evaluation"] = {
            "quality_comparison": {
                "baseline_version": 3,
                "candidate_version": 3,
                "quality_delta": direction,
            }
        }

        result = grader.grade_trace(trace, "same-version-quality-claim")
        comparison = result["metrics"]["quality_comparison"]

        self.assertEqual(
            (result["decision"], result["score"], result["grade"]),
            ("ACCEPT", 110, "A"),
        )
        self.assertEqual(comparison["status"], "deferred")
        self.assertIsNone(comparison["quality_delta"])
        self.assertEqual(
            comparison["reason"],
            grader.QUALITY_COMPARISON_REASON,
        )

    def test_same_version_quality_increase_is_deferred(self):
        self.assert_quality_claim_is_deferred("increase")

    def test_same_version_quality_decrease_is_deferred(self):
        self.assert_quality_claim_is_deferred("decrease")

    def test_observed_token_usage_is_optional_and_model_scoped(self):
        trace = copy.deepcopy(self.complete)
        trace["evaluation"] = {
            "token_usage": {
                "version": 1,
                "records": [
                    {
                        "prompt_id": prompt["prompt_id"],
                        "input_tokens": 1000 + index,
                        "measurement_scope": "api_request",
                        "provider": "test-provider",
                        "model": "test-model",
                        "encoding": "test-encoding",
                    }
                    for index, prompt in enumerate(trace["prompts"])
                ],
            }
        }

        result = grader.grade_trace(trace, "observed-tokens")
        observed = result["metrics"]["tokens"]["observed"]

        self.assertEqual(result["decision"], "ACCEPT")
        self.assertEqual(observed["status"], "available")
        self.assertEqual(observed["measurement_scope"], "api_request")
        self.assertEqual(observed["model"], "test-model")
        self.assertEqual(observed["dispatched"]["total"], 5010)

    def test_invalid_observed_usage_does_not_change_quality_grade(self):
        trace = copy.deepcopy(self.complete)
        trace["evaluation"] = {
            "token_usage": {
                "version": 1,
                "records": [
                    {
                        "prompt_id": trace["prompts"][0]["prompt_id"],
                        "input_tokens": 1000,
                        "measurement_scope": "api_request",
                        "provider": "test-provider",
                        "model": "test-model",
                        "encoding": "test-encoding",
                    }
                ],
            }
        }

        result = grader.grade_trace(trace, "partial-observed-tokens")
        observed = result["metrics"]["tokens"]["observed"]

        self.assertEqual(
            (result["decision"], result["score"], result["grade"]),
            ("ACCEPT", 110, "A"),
        )
        self.assertEqual(observed["status"], "invalid")
        self.assertEqual(len(observed["missing_prompt_ids"]), 4)
        self.assertTrue(observed["errors"])

    def test_attempt_tokens_are_reported_separately(self):
        trace = copy.deepcopy(self.complete)
        trace["prompt_attempts"] = [
            {
                "attempt_id": "A-token-test",
                "handoff_event_id": "E-002",
                "rendered_prompt": trace["prompts"][0]["rendered_prompt"],
            }
        ]

        metrics = grader._prompt_metrics(trace)
        tokens = metrics["tokens"]

        self.assertEqual(tokens["estimated"]["dispatched"]["total"], 1960)
        self.assertEqual(tokens["estimated"]["attempts"]["total"], 388)
        self.assertEqual(
            tokens["estimated"]["attempts"]["by_phase"]["implement"]["total"],
            388,
        )

    def test_prompt_heading_mutation_is_rejected(self):
        def mutation(trace):
            prompt = trace["prompts"][0]
            prompt["rendered_prompt"] = prompt["rendered_prompt"].replace(
                "## Role", "# Role", 1
            )

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_hash_mutation_is_rejected(self):
        def mutation(trace):
            trace["prompts"][0]["normalized_sha256"] = "0" * 64

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_output_contract_must_be_rendered(self):
        def mutation(trace):
            prompt = trace["prompts"][0]
            prompt["rendered_prompt"] = prompt["rendered_prompt"].replace(
                "handoff_ref", "handoff_reference", 1
            )

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_pcp_arithmetic_mutation_is_rejected(self):
        def mutation(trace):
            trace["prompts"][0]["complexity"]["total"] = 4

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_reverse_tool_link_mutation_is_rejected(self):
        def mutation(trace):
            self.call(trace, "C-003")["prompt_id"] = None

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_untrusted_boundary_mutation_is_rejected(self):
        def mutation(trace):
            prompt = trace["prompts"][0]
            prompt["rendered_prompt"] = prompt["rendered_prompt"].replace(
                "[END UNTRUSTED REPOSITORY CONTEXT]",
                "[END UNTRUSTED OTHER CONTEXT]",
                1,
            )

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_strategy_requires_its_quality_gate(self):
        def mutation(trace):
            prompt = trace["prompts"][0]
            prompt["strategy"] = "few_shot"
            prompt["strategy_details"] = {"examples_count": 1}

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_chain_dependency_must_be_observable_and_prior(self):
        def mutation(trace):
            prompt = trace["prompts"][0]
            prompt["strategy"] = "chained"
            prompt["strategy_details"] = {
                "chain_id": "CHAIN-1",
                "step_index": 2,
                "depends_on_prompt_ids": ["P-missing"],
            }

        self.assert_failed(mutation, ["prompt_contract"])

    def test_tool_augmented_prompt_must_match_external_action(self):
        def mutation(trace):
            prompt = trace["prompts"][0]
            prompt["strategy"] = "tool_augmented"
            prompt["strategy_details"] = {"tools": ["other_tool"]}
            prompt["complexity"]["items"].append({
                "id": "pcp-external",
                "kind": "external_dependency",
                "section": "Procedure",
                "description": "Call the observable implementation tool.",
                "count": 1,
            })
            prompt["complexity"]["total"] = 3.5

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_attempt_limit_is_rejected(self):
        source = copy.deepcopy(self.complete["prompts"][0])
        attempts = []
        for index in range(1, 5):
            attempt = {
                "attempt_id": "A-PROMPT-%d" % index,
                "prompt_family_id": "F-001-implement",
                "handoff_event_id": "E-002",
                "previous_attempt_id": None if index == 1 else "A-PROMPT-%d" % (index - 1),
                "rendered_prompt": source["rendered_prompt"],
                "normalized_sha256": source["normalized_sha256"],
                "modules": copy.deepcopy(source["modules"]),
                "language": source["language"],
                "sections": copy.deepcopy(source["sections"]),
                "strategy": source["strategy"],
                "strategy_details": copy.deepcopy(source["strategy_details"]),
                "strategy_reason": source["strategy_reason"],
                "selection_evidence": copy.deepcopy(source["selection_evidence"]),
                "output_contract_id": source["output_contract_id"],
                "complexity": copy.deepcopy(source["complexity"]),
                "quality_gates": copy.deepcopy(source["quality_gates"]),
                "failure_codes": ["G-PROMPT-TEST"],
                "evidence": ["EV-inspect"],
            }
            attempts.append(attempt)

        def mutation(trace):
            trace["prompt_attempts"] = attempts

        self.assert_failed(mutation, ["prompt_contract"])

    def test_prompt_sensitive_values_are_redacted(self):
        raw = "email=user@example.com token=Bearer abcdefghijklmnop"
        self.assertEqual(prompt_contract.scan_sensitive(raw), ["bearer_token", "email"])
        self.assertNotIn("user@example.com", prompt_contract.sanitize_prompt(raw))

    def test_malformed_prompt_values_are_rejected_without_crashing(self):
        for field in ("complexity", "rendered_prompt", "quality_gates"):
            with self.subTest(field=field):
                def mutation(trace, field=field):
                    trace["prompts"][0][field] = []

                self.assert_failed(mutation, ["prompt_contract"])

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

    def test_token_metrics_tolerate_malformed_top_level_lists(self):
        trace = copy.deepcopy(self.complete)
        trace["prompts"] = None
        trace["prompt_attempts"] = None

        result = grader.grade_trace(trace, "malformed-token-input")

        self.assertEqual(result["decision"], "REJECT")
        self.assertEqual(
            result["metrics"]["tokens"]["estimated"]["dispatched"]["total"],
            0,
        )
        self.assertEqual(
            result["metrics"]["tokens"]["estimated"]["attempts"]["total"],
            0,
        )

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
        self.assertIn("TOKENS: ", completed.stdout)
        self.assertIn("QUALITY: comparison=deferred", completed.stdout)

    def test_cli_default_grades_v3_and_v4(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(EVALS_DIR / "report.py"),
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
        self.assertIn("TRACES: 23", completed.stdout)
        self.assertIn("score 120/120", completed.stdout)
        self.assertIn("TDD: cycles=1 red=1 green=1", completed.stdout)


if __name__ == "__main__":
    unittest.main()
