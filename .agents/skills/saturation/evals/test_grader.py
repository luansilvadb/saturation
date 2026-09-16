"""Focused tests for the in-memory saturation governance evaluator."""

from __future__ import annotations

import copy
import unittest

import grader


CYCLE_ID = "cycle-001"
CONTEXT_PATH = ".saturation/cycles/cycle-001/context.md"
REPORT_PATH = ".saturation/cycles/cycle-001/report.json"


def _activation_matrix() -> dict[str, object]:
    """Return a complete refactor activation matrix."""

    return {
        "mode": "refactor",
        "roles": {
            "lead": {
                "status": "implicit",
                "reason": "The lead is the main session.",
                "evidence_ids": ["EV-ACT-LEAD"],
            },
            "product-domain": {
                "status": "not_applicable",
                "reason": "No product workflow changes.",
                "evidence_ids": ["EV-ACT-PRODUCT"],
            },
            "architect-data": {"status": "active"},
            "implementation": {"status": "active"},
            "experience-fidelity": {
                "status": "not_applicable",
                "reason": "No user-facing surface changes.",
                "evidence_ids": ["EV-ACT-EXPERIENCE"],
            },
            "security-privacy-ip": {
                "status": "not_applicable",
                "reason": "No security or asset boundary changes.",
                "evidence_ids": ["EV-ACT-SECURITY"],
            },
            "qa-harness": {"status": "active"},
            "reliability-release": {"status": "active"},
            "final-reviewer": {"status": "active"},
        },
    }


def _assignment(
    assignment_id: str,
    role: str,
    session_id: str,
    write_scope: list[str],
) -> dict[str, object]:
    """Build one fresh specialist assignment."""

    return {
        "kind": "assignment",
        "cycle_id": CYCLE_ID,
        "assignment_id": assignment_id,
        "agent_id": role,
        "session_id": session_id,
        "fresh_session": True,
        "read_scope": [
            CONTEXT_PATH,
            "src",
            ".agents/skills/saturation/code_styleguides/general.md",
        ],
        "write_scope": write_scope,
        "style_guides": [
            ".agents/skills/saturation/code_styleguides/general.md"
        ],
    }


def _events() -> list[dict[str, object]]:
    """Return a valid observation for the active non-lead roles."""

    return [
        {
            "kind": "context_frozen",
            "cycle_id": CYCLE_ID,
            "path": CONTEXT_PATH,
            "frozen": True,
            "base_revision": "a2b3b38",
            "workspace": "cycle-001-isolated",
            "isolation": "isolated",
            "risk_matrix_id": "EV-RISK-001",
            "dependency_graph_id": "EV-DEPENDENCY-001",
            "gate_registry_id": "EV-GATES-001",
            "evidence_ids": [
                "EV-CONTEXT-001",
                "EV-RISK-001",
                "EV-DEPENDENCY-001",
                "EV-GATES-001",
            ],
        },
        {
            "kind": "activation_matrix",
            "cycle_id": CYCLE_ID,
            **_activation_matrix(),
        },
        _assignment(
            "architect",
            "architect-data",
            "S-architect-1",
            ["src/architecture"],
        ),
        _assignment(
            "implementation",
            "implementation",
            "S-implementation-1",
            ["src/core"],
        ),
        _assignment(
            "qa",
            "qa-harness",
            "S-qa-1",
            ["tests/qa"],
        ),
        _assignment(
            "reliability",
            "reliability-release",
            "S-reliability-1",
            ["ops/release"],
        ),
        {"kind": "check", "cycle_id": CYCLE_ID, "name": "tests", "status": "pass"},
        {"kind": "check", "cycle_id": CYCLE_ID, "name": "review", "status": "pass"},
        {
            "kind": "phase_packet",
            "version": "1",
            "phase_packet_id": "PP-VALIDATION-001",
            "packet_id": "PP-VALIDATION-001",
            "cycle_id": CYCLE_ID,
            "upstream_assignment_ids": ["implementation", "qa"],
            "dependency_state": "ready",
            "changed_paths": ["src/core/sim.ts", "tests/qa/test_sim.py"],
            "integration_owner": "lead",
            "status": "complete",
            "evidence_ids": ["EV-PACKET-001"],
        },
        {
            "kind": "evidence",
            "evidence_id": "EV-EVIDENCE-001",
        },
        {
            "kind": "integrated",
            "cycle_id": CYCLE_ID,
            "status": "complete",
            "integration_owner": "lead",
            "changed_paths": [
                "src/architecture/decision.md",
                "src/core/sim.ts",
                "tests/qa/test_sim.py",
                "ops/release/checklist.md",
            ],
            "evidence_ids": ["EV-INTEGRATION-001"],
        },
        _assignment(
            "review",
            "final-reviewer",
            "S-review-1",
            [],
        ),
        {"kind": "report", "cycle_id": CYCLE_ID, "path": REPORT_PATH},
        {"kind": "durable_path", "cycle_id": CYCLE_ID, "path": CONTEXT_PATH},
        {"kind": "durable_path", "cycle_id": CYCLE_ID, "path": REPORT_PATH},
        {"kind": "durable_path", "cycle_id": CYCLE_ID, "path": "src/core/sim.ts"},
    ]


def _event(events: list[dict[str, object]], kind: str) -> dict[str, object]:
    """Return the first event with a requested kind."""

    return next(event for event in events if event.get("kind") == kind)


class ObserverTests(unittest.TestCase):
    """Verify that runtime observations stay detached and in memory."""

    def test_observer_returns_a_detached_snapshot(self) -> None:
        observer = grader.RunObserver()
        observer.record(
            "context_frozen", path=CONTEXT_PATH, frozen=True
        )

        snapshot = observer.snapshot()
        snapshot[0]["path"] = "changed"

        self.assertEqual(observer.snapshot()[0]["path"], CONTEXT_PATH)

    def test_empty_event_kind_is_rejected(self) -> None:
        observer = grader.RunObserver()

        with self.assertRaises(ValueError):
            observer.record("", value=True)

    def test_forbidden_event_fields_are_rejected(self) -> None:
        observer = grader.RunObserver()

        with self.assertRaises(ValueError):
            observer.record("evidence", secret="must not be retained")


class GraderTests(unittest.TestCase):
    """Verify governance invariants without a runtime launch decision."""

    def test_complete_observation_passes(self) -> None:
        result = grader.evaluate_events(_events())

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["scope"], "ci_governance")
        self.assertFalse(result["launch_gate"])
        self.assertEqual(result["metrics"]["assignments"], 5)
        self.assertEqual(result["metrics"]["forbidden_durable_paths"], 0)
        self.assertEqual(result["metrics"]["reports"], 1)
        self.assertEqual(result["metrics"]["phase_packets"], 1)
        self.assertGreater(result["metrics"]["evidence_ids"], 0)
        self.assertEqual(result["errors"], [])

    def test_mapping_snapshot_is_supported(self) -> None:
        result = grader.evaluate_observation(
            {"cycle_id": CYCLE_ID, "events": _events()}
        )

        self.assertEqual(result["status"], "pass")

    def test_top_level_matrix_and_report_are_supported(self) -> None:
        events = [
            event
            for event in _events()
            if event.get("kind") not in {"activation_matrix", "report"}
        ]
        result = grader.evaluate_observation(
            {
                "cycle_id": CYCLE_ID,
                "mode": "refactor",
                "activation_matrix": _activation_matrix()["roles"],
                "report_path": REPORT_PATH,
                "events": events,
            }
        )

        self.assertEqual(result["status"], "pass")

    def test_lead_is_implicit_and_needs_no_assignment(self) -> None:
        events = _events()

        self.assertFalse(
            any(
                event.get("agent_id") == "lead"
                for event in events
                if event.get("kind") == "assignment"
            )
        )
        self.assertEqual(grader.evaluate_events(events)["status"], "pass")

    def test_additive_event_kinds_and_fields_are_ignored(self) -> None:
        events = _events()
        events[0]["future_field"] = "ignored"
        events.insert(2, {"kind": "future_metric", "value": 1})

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "pass")

    def test_runtime_artifacts_are_rejected_when_persisted(self) -> None:
        events = _events()
        events.append(
            {"kind": "durable_path", "path": ".saturation/runs/trace.json"}
        )

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(
            result["checks"]["no_runtime_artifacts"]["status"], "fail"
        )
        self.assertEqual(result["metrics"]["forbidden_durable_paths"], 1)

    def test_unbound_canonical_events_are_rejected(self) -> None:
        events = _events()
        _event(events, "check").pop("cycle_id")

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertTrue(
            any("needs a valid cycle_id" in error for error in result["errors"])
        )

    def test_whole_repository_scopes_are_rejected(self) -> None:
        events = _events()
        assignment = next(
            event
            for event in events
            if event.get("kind") == "assignment"
            and event.get("agent_id") == "implementation"
        )
        assignment["read_scope"] = ["."]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["disjoint_scopes"]["status"], "fail")

    def test_final_review_must_follow_integration(self) -> None:
        events = _events()
        review = next(
            event
            for event in events
            if event.get("kind") == "assignment"
            and event.get("agent_id") == "final-reviewer"
        )
        events.remove(review)
        events.insert(2, review)

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["final_review"]["status"], "fail")

    def test_phase_packet_must_match_assignments_and_contract(self) -> None:
        events = _events()
        packet = _event(events, "phase_packet")
        packet["upstream_assignment_ids"] = ["missing-assignment"]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["phase_packets"]["status"], "fail")

    def test_phase_packet_paths_must_belong_to_upstream_assignments(self) -> None:
        events = _events()
        packet = _event(events, "phase_packet")
        packet["upstream_assignment_ids"] = ["implementation"]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["phase_packets"]["status"], "fail")

    def test_root_context_is_not_a_current_cycle_artifact(self) -> None:
        events = _events()
        _event(events, "context_frozen")["path"] = ".saturation/context.md"

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertIn("per-cycle context", result["errors"][0])

    def test_context_requires_execution_metadata(self) -> None:
        events = _events()
        _event(events, "context_frozen").pop("gate_registry_id")

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["context_frozen"]["status"], "fail")

    def test_other_cycle_report_is_rejected(self) -> None:
        events = _events()
        _event(events, "report")["path"] = (
            ".saturation/cycles/other-cycle/report.json"
        )

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["reports"]["status"], "fail")

    def test_reused_session_is_rejected_for_initial_assignment(self) -> None:
        events = _events()
        assignments = [
            event for event in events if event.get("kind") == "assignment"
        ]
        assignments[1]["session_id"] = assignments[0]["session_id"]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["fresh_sessions"]["status"], "fail")

    def test_local_repair_may_reuse_the_owner_session(self) -> None:
        events = _events()
        events.append(
            {
                "kind": "assignment",
                "cycle_id": CYCLE_ID,
                "assignment_id": "implementation-repair",
                "agent_id": "implementation",
                "session_id": "S-implementation-1",
                "fresh_session": False,
                "repair": True,
                "owner_assignment_id": "implementation",
                "read_scope": [CONTEXT_PATH, "src/core"],
                "write_scope": [],
                "style_guides_status": "not_applicable",
                "style_guides": [],
            }
        )

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "pass")

    def test_overlapping_write_scopes_are_rejected(self) -> None:
        events = _events()
        assignments = [
            event for event in events if event.get("kind") == "assignment"
        ]
        assignments[1]["write_scope"] = ["src"]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["disjoint_scopes"]["status"], "fail")

    def test_empty_style_guides_can_be_not_applicable(self) -> None:
        events = _events()
        assignment = next(
            event
            for event in events
            if event.get("kind") == "assignment"
            and event.get("agent_id") == "architect-data"
        )
        assignment["style_guides"] = []
        assignment["style_guides_status"] = "not_applicable"

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "pass")

    def test_empty_style_guides_without_status_are_rejected(self) -> None:
        events = _events()
        assignment = next(
            event
            for event in events
            if event.get("kind") == "assignment"
            and event.get("agent_id") == "architect-data"
        )
        assignment["style_guides"] = []

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["style_guides"]["status"], "fail")

    def test_failed_check_is_rejected(self) -> None:
        events = _events()
        checks = [
            event for event in events if event.get("kind") == "check"
        ]
        checks[0]["status"] = "fail"

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["verification"]["status"], "fail")

    def test_noncanonical_check_status_is_rejected(self) -> None:
        events = _events()
        _event(events, "check")["status"] = "passed"

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")

    def test_applicable_skip_is_rejected(self) -> None:
        events = _events()
        _event(events, "check")["status"] = "skip"

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["verification"]["status"], "fail")

    def test_all_checks_not_applicable_are_governance_valid(self) -> None:
        events = _events()
        for event in events:
            if event.get("kind") == "check":
                event["status"] = "not_applicable"

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["metrics"]["passed_checks"], 0)

    def test_missing_activation_matrix_is_rejected(self) -> None:
        events = [
            event
            for event in _events()
            if event.get("kind") != "activation_matrix"
        ]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(
            result["checks"]["activation_matrix"]["status"], "fail"
        )

    def test_out_of_scope_integration_is_rejected(self) -> None:
        events = _events()
        integrated = _event(events, "integrated")
        integrated["changed_paths"] = ["src/game/renderer.ts"]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["integration"]["status"], "fail")

    def test_invalid_event_input_is_rejected_without_writing(self) -> None:
        result = grader.evaluate_observation(None)

        self.assertEqual(result["status"], "fail")
        self.assertIn("events must be a sequence", result["errors"][0])

    def test_evaluation_does_not_mutate_input(self) -> None:
        events = _events()
        before = copy.deepcopy(events)

        grader.evaluate_events(events)

        self.assertEqual(events, before)


if __name__ == "__main__":
    unittest.main()
