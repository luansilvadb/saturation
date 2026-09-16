"""Focused tests for the saturation role and handoff contracts."""

from __future__ import annotations

import unittest
from pathlib import Path

import team_contract


SKILL_DIR = Path(__file__).resolve().parents[1]
CYCLE_ID = "cycle-001"
CONTEXT_PATH = team_contract.cycle_context_path(CYCLE_ID)
REPORT_PATH = team_contract.cycle_report_path(CYCLE_ID)


def _activation_matrix() -> dict[str, object]:
    """Return a complete matrix for the refactor mode."""

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


def _handoff(
    *,
    status: str = "complete",
    include_clearance: bool = False,
    changed_paths: list[str] | None = None,
) -> dict[str, object]:
    """Build a canonical specialist handoff."""

    payload: dict[str, object] = {
        "handoff": {
            "version": "1",
            "cycle_id": CYCLE_ID,
            "assignment_id": "assignment-1",
            "agent_id": "implementation",
            "status": status,
            "summary": "Implemented and verified the assigned change.",
            "changed_paths": (
                [] if changed_paths is None else changed_paths
            ),
            "checks": [
                {
                    "name": "focused tests",
                    "status": "pass",
                    "evidence_id": "EV-TEST-001",
                }
            ],
            "open_items": [],
        }
    }
    handoff = payload["handoff"]
    if status in {"needs_repair", "blocked"}:
        handoff["open_items"] = [
            {
                "item": "Repair or escalation is pending.",
                "reason": "The result is not clearable yet.",
                "owner": "implementation",
            }
        ]
        handoff["next_owner"] = "implementation"
    if include_clearance:
        handoff["clearance"] = False
    return payload


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

    def test_lead_is_rostered_but_not_a_mode_assignment(self) -> None:
        self.assertIn("lead", team_contract.ROLE_CONTRACTS)
        for roles in team_contract.MODE_MINIMUM_ROLES.values():
            self.assertNotIn("lead", roles)


class HandoffTests(unittest.TestCase):
    """Verify the compact canonical handoff envelope."""

    def test_complete_handoff_derives_clearance_without_a_field(self) -> None:
        value = _handoff()

        self.assertEqual(team_contract.validate_handoff(value), [])
        self.assertTrue(team_contract.derive_handoff_clearance(value))
        self.assertNotIn("clearance", value["handoff"])

    def test_repair_handoff_requires_a_conditional_next_owner(self) -> None:
        value = _handoff(status="needs_repair")

        self.assertEqual(team_contract.validate_handoff(value), [])
        self.assertFalse(team_contract.derive_handoff_clearance(value))

    def test_blocked_handoff_requires_a_conditional_next_owner(self) -> None:
        value = _handoff(status="blocked")

        self.assertEqual(team_contract.validate_handoff(value), [])

    def test_missing_next_owner_is_rejected_for_repair(self) -> None:
        value = _handoff(status="needs_repair")
        del value["handoff"]["next_owner"]

        errors = team_contract.validate_handoff(value)

        self.assertIn("needs a next_owner", errors[0])

    def test_failed_check_cannot_be_cleared(self) -> None:
        value = _handoff(include_clearance=True)
        value["handoff"]["checks"] = [
            {
                "name": "tests",
                "status": "fail",
                "evidence_ids": ["EV-FAIL-001"],
            }
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

    def test_unsupported_handoff_fields_are_rejected(self) -> None:
        value = _handoff()
        value["handoff"]["personal_note"] = "not part of the contract"

        errors = team_contract.validate_handoff(value)

        self.assertIn(
            "handoff contains unsupported field: personal_note", errors
        )

    def test_per_cycle_context_and_report_paths_are_recognized(self) -> None:
        self.assertTrue(
            team_contract.is_per_cycle_artifact(CONTEXT_PATH, CYCLE_ID)
        )
        self.assertTrue(
            team_contract.is_per_cycle_artifact(REPORT_PATH, CYCLE_ID)
        )

    def test_root_context_is_rejected_as_an_internal_path(self) -> None:
        value = _handoff(changed_paths=[".saturation/context.md"])

        errors = team_contract.validate_handoff(value)

        self.assertIn(
            "handoff changed_paths may only use per-cycle context/report",
            errors,
        )

    def test_omitting_assignment_id_is_rejected_by_compact_schema(self) -> None:
        value = _handoff()
        del value["handoff"]["assignment_id"]

        errors = team_contract.validate_handoff(value)

        self.assertIn("handoff is missing assignment_id", errors)

    def test_role_cannot_self_authorize_clearance(self) -> None:
        value = _handoff(include_clearance=True)
        value["handoff"]["clearance"] = True

        errors = team_contract.validate_handoff(value)

        self.assertIn(
            "roles cannot self-authorize clearance", errors
        )

    def test_missing_cycle_id_is_rejected(self) -> None:
        value = _handoff()
        del value["handoff"]["cycle_id"]

        errors = team_contract.validate_handoff(value)

        self.assertIn("handoff is missing cycle_id", errors)

    def test_each_handoff_check_needs_a_stable_evidence_id(self) -> None:
        value = _handoff()
        value["handoff"]["checks"][0].pop("evidence_id")

        errors = team_contract.validate_handoff(value)

        self.assertIn("handoff check 0 needs evidence_id", errors)

    def test_lead_does_not_return_a_specialist_handoff(self) -> None:
        value = _handoff()
        value["handoff"]["agent_id"] = "lead"

        errors = team_contract.validate_handoff(value)

        self.assertIn("lead does not return a specialist handoff", errors)


class RoutingTests(unittest.TestCase):
    """Verify matrix routing accounts for every fixed role."""

    def test_complete_activation_matrix_passes(self) -> None:
        self.assertEqual(
            team_contract.validate_activation_matrix(_activation_matrix()), []
        )

    def test_phase_packet_requires_current_cycle_and_evidence(self) -> None:
        packet = {
            "phase_packet": {
                "version": "1",
                "cycle_id": CYCLE_ID,
                "packet_id": "PP-001",
                "upstream_assignment_ids": ["assignment-1"],
                "dependency_state": "ready",
                "changed_paths": ["src/app.py"],
                "evidence_ids": ["EV-PACKET-001"],
                "integration_owner": "lead",
            }
        }

        self.assertEqual(
            team_contract.validate_phase_packet(packet, CYCLE_ID), []
        )

    def test_phase_packet_mixing_cycles_is_rejected(self) -> None:
        packet = {
            "version": "1",
            "cycle_id": "other-cycle",
            "packet_id": "PP-001",
            "upstream_assignment_ids": ["assignment-1"],
            "dependency_state": "ready",
            "changed_paths": [],
            "evidence_ids": ["EV-PACKET-001"],
            "next_owner": "lead",
        }

        errors = team_contract.validate_phase_packet(packet, CYCLE_ID)

        self.assertIn(
            "phase_packet cycle_id does not match the current cycle", errors
        )

    def test_mode_selection_accepts_the_matrix_form(self) -> None:
        matrix = _activation_matrix()

        self.assertEqual(
            team_contract.validate_mode_selection("refactor", matrix), []
        )

    def test_matrix_can_omit_conditional_roles_with_reason_and_evidence(self) -> None:
        matrix = _activation_matrix()
        matrix["roles"]["experience-fidelity"] = {
            "status": "not_applicable",
            "reason": "The authorized task has no user-facing surface.",
            "evidence_ids": ["EV-OMIT-001"],
        }

        self.assertEqual(
            team_contract.validate_activation_matrix(matrix), []
        )

    def test_matrix_requires_lead_to_be_implicit(self) -> None:
        matrix = _activation_matrix()
        matrix["roles"]["lead"] = {
            "status": "active",
            "reason": "Incorrect delegated lead row.",
        }

        errors = team_contract.validate_activation_matrix(matrix)

        self.assertIn("lead activation must be implicit", errors)

    def test_matrix_requires_evidence_for_not_applicable_roles(self) -> None:
        matrix = _activation_matrix()
        del matrix["roles"]["product-domain"]["evidence_ids"]

        errors = team_contract.validate_activation_matrix(matrix)

        self.assertIn(
            "activation matrix role product-domain needs evidence IDs", errors
        )

    def test_full_mode_legacy_adapter_can_cover_the_roster(self) -> None:
        active = list(team_contract.ROLE_CONTRACTS)

        self.assertEqual(
            team_contract.validate_mode_selection("full", active, {}), []
        )

    def test_hotfix_can_omit_conditional_roles_with_reasons(self) -> None:
        active = sorted(
            set(team_contract.MODE_MINIMUM_ROLES["hotfix"]) | {"lead"}
        )
        omitted = {
            role: "No UI, security boundary, architecture, or release impact."
            for role in set(team_contract.ROLE_CONTRACTS) - set(active)
        }

        self.assertEqual(
            team_contract.validate_mode_selection("hotfix", active, omitted), []
        )

    def test_missing_required_role_is_rejected(self) -> None:
        active = sorted(
            set(team_contract.MODE_MINIMUM_ROLES["hotfix"])
            - {"qa-harness"}
            | {"lead"}
        )
        omitted = {
            role: "Omitted for test"
            for role in set(team_contract.ROLE_CONTRACTS) - set(active)
        }

        errors = team_contract.validate_mode_selection(
            "hotfix", active, omitted
        )

        self.assertTrue(any("missing active roles" in error for error in errors))

    def test_three_same_failures_trip_the_breaker(self) -> None:
        self.assertFalse(team_contract.should_trip_circuit_breaker(2))
        self.assertTrue(team_contract.should_trip_circuit_breaker(3))
        self.assertTrue(team_contract.should_trip_circuit_breaker(4))


if __name__ == "__main__":
    unittest.main()
