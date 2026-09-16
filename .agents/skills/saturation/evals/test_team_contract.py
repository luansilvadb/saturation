"""Focused tests for the saturation role and handoff contracts."""

from __future__ import annotations

import unittest
from pathlib import Path

import team_contract


SKILL_DIR = Path(__file__).resolve().parents[1]


def _handoff(
    *, status: str = "complete", clearance: bool = True
) -> dict[str, object]:
    return {
        "handoff": {
            "version": "1",
            "assignment_id": "assignment-1",
            "agent_id": "implementation",
            "status": status,
            "summary": "Implemented and verified the assigned change.",
            "changed_paths": ["src/app.py"],
            "checks": [
                {
                    "name": "focused tests",
                    "status": "pass",
                    "evidence": "python -m unittest tests/test_app.py",
                }
            ],
            "open_items": [],
            "next_owner": "lead",
            "clearance": clearance,
        }
    }


class RosterTests(unittest.TestCase):
    """Verify the fixed role library is complete and wired into the skill."""

    def test_fixed_roster_is_valid(self) -> None:
        self.assertEqual(team_contract.validate_roster(SKILL_DIR), [])

    def test_all_nine_role_contracts_are_present(self) -> None:
        self.assertEqual(len(team_contract.ROLE_CONTRACTS), 9)
        for role_id, relative_path in team_contract.ROLE_CONTRACTS.items():
            self.assertEqual(
                team_contract.validate_agent_contract(
                    SKILL_DIR / relative_path, role_id
                ),
                [],
            )


class HandoffTests(unittest.TestCase):
    """Verify the minimal in-memory handoff envelope."""

    def test_complete_handoff_passes(self) -> None:
        self.assertEqual(team_contract.validate_handoff(_handoff()), [])

    def test_repair_handoff_requires_no_clearance(self) -> None:
        errors = team_contract.validate_handoff(
            _handoff(status="needs_repair", clearance=False)
        )
        self.assertEqual(errors, [])

    def test_failed_check_cannot_be_cleared(self) -> None:
        value = _handoff()
        value["handoff"]["checks"] = [
            {"name": "tests", "status": "fail", "evidence": "failure"}
        ]

        errors = team_contract.validate_handoff(value)

        self.assertIn("cleared handoffs cannot contain failed checks", errors)

    def test_private_fields_are_rejected(self) -> None:
        value = _handoff()
        value["handoff"]["scratchpad"] = "private reasoning"

        errors = team_contract.validate_handoff(value)

        self.assertIn(
            "handoff contains a forbidden private or sensitive field", errors
        )

    def test_internal_paths_are_rejected(self) -> None:
        value = _handoff()
        value["handoff"]["changed_paths"] = [".saturation/runs/trace.json"]

        errors = team_contract.validate_handoff(value)

        self.assertIn(
            "handoff changed_paths cannot contain saturation runtime files", errors
        )

    def test_broad_changed_path_is_rejected(self) -> None:
        value = _handoff()
        value["handoff"]["changed_paths"] = ["."]

        errors = team_contract.validate_handoff(value)

        self.assertIn("handoff changed_paths must name concrete paths", errors)


class RoutingTests(unittest.TestCase):
    """Verify adaptive modes still account for every fixed role."""

    def test_full_mode_activates_the_complete_roster(self) -> None:
        errors = team_contract.validate_mode_selection(
            "full", list(team_contract.ROLE_CONTRACTS), {}
        )

        self.assertEqual(errors, [])

    def test_full_mode_can_omit_an_inapplicable_conditional_role(self) -> None:
        active = sorted(
            set(team_contract.ROLE_CONTRACTS) - {"experience-fidelity"}
        )
        omitted = {
            "experience-fidelity": "The authorized task has no user-facing surface."
        }

        self.assertEqual(
            team_contract.validate_mode_selection("full", active, omitted), []
        )

    def test_hotfix_can_omit_conditional_roles_with_reasons(self) -> None:
        active = sorted(team_contract.MODE_MINIMUM_ROLES["hotfix"])
        omitted = {
            role: "No UI, security boundary, architecture, or release impact."
            for role in set(team_contract.ROLE_CONTRACTS) - set(active)
        }

        self.assertEqual(
            team_contract.validate_mode_selection("hotfix", active, omitted), []
        )

    def test_missing_required_role_is_rejected(self) -> None:
        active = [
            role
            for role in team_contract.MODE_MINIMUM_ROLES["hotfix"]
            if role != "qa-harness"
        ]
        omitted = {
            role: "Omitted for test"
            for role in set(team_contract.ROLE_CONTRACTS) - set(active)
        }

        errors = team_contract.validate_mode_selection("hotfix", active, omitted)

        self.assertTrue(any("missing required roles" in error for error in errors))

    def test_three_same_failures_trip_the_breaker(self) -> None:
        self.assertFalse(team_contract.should_trip_circuit_breaker(2))
        self.assertTrue(team_contract.should_trip_circuit_breaker(3))
        self.assertTrue(team_contract.should_trip_circuit_breaker(4))


if __name__ == "__main__":
    unittest.main()
