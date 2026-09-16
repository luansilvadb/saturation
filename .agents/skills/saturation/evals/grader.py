"""Evaluate redacted saturation observations for CI and governance."""

from __future__ import annotations

import argparse
import copy
import json
import posixpath
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import team_contract


CYCLE_ROOT = team_contract.CYCLE_ROOT
CONTEXT_PATH = f"{CYCLE_ROOT}/<cycle_id>/context.md"
REPORT_PATH = f"{CYCLE_ROOT}/<cycle_id>/report.json"
PASS_STATUSES = frozenset({"pass"})
SKIP_STATUSES = frozenset({"skip", "not_applicable"})
INTEGRATION_STATUSES = frozenset({"complete"})
PHASE_PACKET_STATUSES = frozenset(
    {"complete", "needs_repair", "blocked", "not_applicable"}
)
BOUND_EVENT_KINDS = frozenset(
    {
        "context_frozen",
        "activation_matrix",
        "assignment",
        "check",
        "integrated",
        "report",
        "report_written",
        "durable_path",
        "phase_packet",
        "phase_packet_created",
    }
)
_COMMON_EVENT_FIELDS = frozenset(
    {"kind", "cycle_id", "evidence_id", "evidence_ids"}
)
_EVENT_FIELDS = {
    "context_frozen": frozenset(
        {
            "path",
            "frozen",
            "base_revision",
            "workspace",
            "isolation",
            "risk_matrix_id",
            "dependency_graph_id",
            "gate_registry_id",
        }
    ),
    "activation_matrix": frozenset(
        {"mode", "roles", "activation_matrix", "matrix"}
    ),
    "assignment": frozenset(
        {
            "assignment_id",
            "agent_id",
            "role",
            "session_id",
            "fresh_session",
            "assignment_type",
            "repair",
            "phase",
            "owner_session_id",
            "owner_assignment_id",
            "read_scope",
            "write_scope",
            "style_guides",
            "style_guides_status",
            "style_guide_status",
        }
    ),
    "check": frozenset({"name", "status", "applicable", "reason"}),
    "integrated": frozenset(
        {"status", "changed_paths", "integration_owner"}
    ),
    "report": frozenset({"path"}),
    "report_written": frozenset({"path"}),
    "durable_path": frozenset({"path"}),
    "phase_packet": frozenset(
        {
            "version",
            "packet_id",
            "phase_packet_id",
            "upstream_assignment_ids",
            "assignment_ids",
            "dependency_state",
            "changed_paths",
            "next_owner",
            "integration_owner",
            "owner",
            "status",
        }
    ),
    "phase_packet_created": frozenset(
        {
            "version",
            "packet_id",
            "phase_packet_id",
            "upstream_assignment_ids",
            "assignment_ids",
            "dependency_state",
            "changed_paths",
            "next_owner",
            "integration_owner",
            "owner",
            "status",
        }
    ),
}
_CYCLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _redacted_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Project an observation onto the non-sensitive contract fields."""

    kind = event.get("kind")
    allowed = _COMMON_EVENT_FIELDS | _EVENT_FIELDS.get(kind, frozenset())
    return {key: value for key, value in event.items() if key in allowed}


class RunObserver:
    """Collect runtime events in memory for an evaluator or diagnostic view."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, kind: str, **payload: Any) -> None:
        """Record one event without serializing or persisting it.

        Args:
            kind: Stable event kind.
            **payload: Redacted event metadata.

        Raises:
            ValueError: If ``kind`` is empty.
        """

        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("event kind must be a non-empty string")
        if team_contract.contains_forbidden_field(payload):
            raise ValueError("event payload contains a forbidden field")
        event = dict(payload)
        event["kind"] = kind
        self._events.append(_redacted_event(event))

    def snapshot(self) -> list[dict[str, Any]]:
        """Return a detached snapshot suitable for ``evaluate_events``.

        Returns:
            A deep copy of the recorded events.
        """

        return copy.deepcopy(self._events)


def _normal_path(value: Any) -> str | None:
    """Normalize a repository-relative path and reject absolute escapes."""

    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("\\", "/")
    if candidate.startswith("/") or (
        len(candidate) > 1 and candidate[1] == ":"
    ):
        return None
    normalized = posixpath.normpath(candidate)
    if normalized == ".." or normalized.startswith("../"):
        return None
    return normalized


def _paths(value: Any, *, allow_empty: bool = True) -> list[str] | None:
    """Validate a list of repository-relative paths."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    values = list(value)
    if not allow_empty and not values:
        return None
    normalized: list[str] = []
    for item in values:
        path = _normal_path(item)
        if path is None:
            return None
        normalized.append(path)
    return normalized


def _valid_cycle_id(value: Any) -> bool:
    """Return whether a cycle ID is safe for a path component."""

    return isinstance(value, str) and bool(_CYCLE_ID_RE.fullmatch(value))


def _context_cycle(path: Any) -> str | None:
    """Extract a cycle ID from a canonical context path."""

    normalized = _normal_path(path)
    if normalized is None:
        return None
    parts = normalized.split("/")
    if len(parts) != 4 or parts[:2] != CYCLE_ROOT.split("/"):
        return None
    if parts[3] != "context.md" or not _valid_cycle_id(parts[2]):
        return None
    return parts[2]


def _cycle_artifact(path: Any, cycle_id: Any) -> bool:
    """Return whether a path is an allowed artifact for one cycle."""

    return team_contract.is_per_cycle_artifact(path, cycle_id)


def _contains(scope: str, path: str) -> bool:
    """Return whether a scope contains a path."""

    if scope == ".":
        return True
    root = scope.rstrip("/")
    return path == root or path.startswith(root + "/")


def _overlap(left: str, right: str) -> bool:
    """Return whether two repository scopes overlap."""

    return _contains(left, right) or _contains(right, left)


def _internal_artifact(path: str) -> bool:
    """Identify saturation files that need an explicit per-cycle allowance."""

    return path == ".saturation" or path.startswith(".saturation/")


def _stable_ids(value: Any, field: str) -> tuple[list[str], list[str]]:
    """Validate a singular or plural list of stable opaque IDs."""

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = list(value)
    else:
        return [], [f"{field} must contain stable identifiers"]

    identifiers: list[str] = []
    errors: list[str] = []
    for identifier in values:
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"{field} must contain non-empty identifiers")
            continue
        identifiers.append(identifier.strip())
    if len(set(identifiers)) != len(identifiers):
        errors.append(f"{field} must not contain duplicates")
    return identifiers, errors


def _event_ids(
    event: Mapping[str, Any], label: str
) -> tuple[list[str], list[str]]:
    """Collect optional evidence IDs from an event."""

    identifiers: list[str] = []
    errors: list[str] = []
    for field in ("evidence_id", "evidence_ids"):
        if field not in event:
            continue
        values, value_errors = _stable_ids(event[field], f"{label}.{field}")
        identifiers.extend(values)
        errors.extend(value_errors)
    if len(set(identifiers)) != len(identifiers):
        errors.append(f"{label} evidence IDs must not repeat")
    return identifiers, errors


def _result(
    checks: Mapping[str, Mapping[str, Any]],
    errors: Sequence[str],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the stable CI/governance evaluator result."""

    issue_list = list(errors)
    status = "pass" if not issue_list and all(
        value.get("status") == "pass" for value in checks.values()
    ) else "fail"
    return {
        "status": status,
        "scope": "ci_governance",
        "launch_gate": False,
        "checks": {key: dict(value) for key, value in checks.items()},
        "metrics": dict(metrics),
        "errors": issue_list,
    }


def _activation_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Extract the matrix envelope from an activation event."""

    if "matrix" in event:
        source = event["matrix"]
    elif "activation_matrix" in event:
        source = event["activation_matrix"]
    elif "roles" in event:
        source = event["roles"]
    else:
        source = {
            key: value
            for key, value in event.items()
            if key not in {"kind", "mode", "cycle_id"}
        }
    if isinstance(source, Mapping) and any(
        key in source for key in ("roles", "activation_matrix", "matrix")
    ):
        payload = dict(source)
        if "mode" not in payload and "mode" in event:
            payload["mode"] = event["mode"]
        return payload
    return {"mode": event.get("mode"), "roles": source}


def _style_guides_valid(
    assignment: Mapping[str, Any], index: int, errors: list[str]
) -> bool:
    """Validate applicable or explicitly not-applicable style guides."""

    raw_guides = assignment.get("style_guides")
    style_status = assignment.get(
        "style_guides_status", assignment.get("style_guide_status")
    )
    if raw_guides == "not_applicable":
        raw_guides = []
        style_status = "not_applicable"
    elif isinstance(raw_guides, Mapping):
        if style_status is None:
            style_status = raw_guides.get("status")
        raw_guides = raw_guides.get(
            "paths", raw_guides.get("guides", [])
        )
    if style_status is None:
        style_status = "applicable"
    if style_status not in {"applicable", "not_applicable"}:
        errors.append(f"assignment {index} has an invalid style guide status")
        return False

    guides = _paths(raw_guides, allow_empty=True)
    if guides is None:
        errors.append(f"assignment {index} has invalid style_guides")
        return False
    if style_status == "not_applicable":
        if guides:
            errors.append(
                f"assignment {index} cannot list guides as not_applicable"
            )
        return not guides
    if not guides or any("code_styleguides/" not in guide for guide in guides):
        errors.append(f"assignment {index} must name relevant code_styleguides")
        return False
    return True


def _assignment_is_repair(assignment: Mapping[str, Any]) -> bool:
    """Return whether an assignment is an explicitly local repair."""

    assignment_type = assignment.get("assignment_type")
    return (
        assignment.get("repair") is True
        or assignment_type in {"repair", "local_repair"}
        or assignment.get("phase") == "repair"
    )


def _assignment_cycle_id(
    assignment: Mapping[str, Any], cycle_id: str | None
) -> str | None:
    """Read and validate an optional assignment cycle ID."""

    value = assignment.get("cycle_id")
    if value is None:
        return cycle_id
    if not _valid_cycle_id(value):
        return None
    return value


def evaluate_events(
    events: Any,
    *,
    cycle_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate a redacted event sequence for CI/governance.

    The evaluator checks orchestration evidence rather than product release
    readiness.  It accepts optional evidence IDs and phase packets, and never
    reads or writes a run directory or decides whether a product may launch.

    Args:
        events: Event sequence supplied by an in-memory observation hook.
        cycle_id: Optional cycle ID supplied by an observation wrapper.

    Returns:
        A deterministic evaluator result with ``launch_gate`` set to ``False``.
    """

    errors: list[str] = []
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return _result(
            {},
            ["events must be a sequence of event objects"],
            {"events": 0},
        )

    parsed: list[Mapping[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            errors.append("event %d is not an object" % index)
            continue
        kind = event.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            errors.append("event %d has no valid kind" % index)
            continue
        if team_contract.contains_forbidden_field(event):
            errors.append(
                "event %d contains a forbidden private or sensitive field"
                % index
            )
        parsed.append(_redacted_event(event))

    contexts = [event for event in parsed if event.get("kind") == "context_frozen"]
    if cycle_id is not None and not _valid_cycle_id(cycle_id):
        errors.append("cycle_id must be a safe non-empty identifier")
        cycle_id = None
    for context in contexts:
        path_cycle_id = _context_cycle(context.get("path"))
        if path_cycle_id is None:
            continue
        if cycle_id is None:
            cycle_id = path_cycle_id
        elif cycle_id != path_cycle_id:
            errors.append("context paths must belong to one cycle")
        event_cycle_id = context.get("cycle_id")
        if event_cycle_id is not None and event_cycle_id != path_cycle_id:
            errors.append("context cycle_id does not match its path")
    context_metadata_ok = len(contexts) == 1
    if context_metadata_ok:
        context = contexts[0]
        for field in ("base_revision", "workspace"):
            if not isinstance(context.get(field), str) or not context[field].strip():
                context_metadata_ok = False
                errors.append("context_frozen needs " + field)
        if context.get("isolation") not in {"isolated", "exclusive_lease"}:
            context_metadata_ok = False
            errors.append(
                "context_frozen needs isolated or exclusive_lease isolation"
            )
        context_evidence, context_evidence_errors = _stable_ids(
            context.get("evidence_ids"), "context_frozen.evidence_ids"
        )
        errors.extend(context_evidence_errors)
        for field in (
            "risk_matrix_id",
            "dependency_graph_id",
            "gate_registry_id",
        ):
            evidence_id = context.get(field)
            if not isinstance(evidence_id, str) or not evidence_id.strip():
                context_metadata_ok = False
                errors.append("context_frozen needs " + field)
            elif evidence_id.strip() not in context_evidence:
                context_metadata_ok = False
                errors.append(
                    "context_frozen " + field + " needs a matching evidence_id"
                )
    context_ok = (
        len(contexts) == 1
        and cycle_id is not None
        and _context_cycle(contexts[0].get("path")) == cycle_id
        and contexts[0].get("frozen") is True
        and context_metadata_ok
    )
    if not context_ok:
        errors.append("exactly one frozen per-cycle context event is required")

    for index, event in enumerate(parsed):
        if event.get("kind") not in BOUND_EVENT_KINDS:
            continue
        event_cycle_id = event.get("cycle_id")
        if not _valid_cycle_id(event_cycle_id):
            errors.append("event %d needs a valid cycle_id" % index)
        elif cycle_id is not None and event_cycle_id != cycle_id:
            errors.append("event %d belongs to a different cycle" % index)

    evidence_ids: set[str] = set()
    for index, event in enumerate(parsed):
        event_values, event_errors = _event_ids(event, f"event {index}")
        evidence_ids.update(event_values)
        errors.extend(event_errors)

    activation_events = [
        event for event in parsed if event.get("kind") == "activation_matrix"
    ]
    activation_ok = len(activation_events) == 1
    activation_roles: dict[str, str] = {}
    if not activation_events:
        errors.append("exactly one activation_matrix event is required")
    elif len(activation_events) > 1:
        errors.append("activation_matrix events must be unique")
    else:
        activation_event = activation_events[0]
        activation_payload = _activation_payload(activation_event)
        if not isinstance(activation_event.get("mode"), str):
            activation_ok = False
            errors.append("activation_matrix needs a mode")
        matrix_errors = team_contract.validate_activation_matrix(
            activation_payload
        )
        if matrix_errors:
            activation_ok = False
            errors.extend(matrix_errors)
        activation_roles = team_contract.activation_matrix_roles(
            activation_payload
        )
        matrix_values, matrix_id_errors = _event_ids(
            activation_event, "activation_matrix"
        )
        evidence_ids.update(matrix_values)
        errors.extend(matrix_id_errors)

    assignments = [event for event in parsed if event.get("kind") == "assignment"]
    assignment_ids: set[str] = set()
    session_ids: set[str] = set()
    write_scopes: list[tuple[str, str]] = []
    assignment_write_scopes: dict[str, list[str]] = {}
    assignment_ok = bool(assignments)
    style_ok = bool(assignments)
    assignment_roles: dict[str, str] = {}

    for index, assignment in enumerate(assignments):
        assignment_id = assignment.get("assignment_id")
        session_id = assignment.get("session_id")
        is_repair = _assignment_is_repair(assignment)
        if not isinstance(assignment_id, str) or not assignment_id.strip():
            assignment_ok = False
            errors.append("assignment %d has no valid assignment_id" % index)
        elif assignment_id in assignment_ids:
            assignment_ok = False
            errors.append("assignment IDs must be unique")
        else:
            assignment_ids.add(assignment_id)

        role = assignment.get("agent_id", assignment.get("role"))
        if role is None:
            assignment_ok = False
            errors.append("assignment %d needs a non-lead role" % index)
        else:
            if not isinstance(role, str) or not role.strip():
                assignment_ok = False
                errors.append("assignment %d has an invalid role" % index)
            elif role not in team_contract.ROLE_CONTRACTS:
                assignment_ok = False
                errors.append("assignment %d has an unknown role" % index)
            elif role == team_contract.LEAD_ROLE:
                assignment_ok = False
                errors.append("the lead must not be a delegated assignment")
            else:
                role = role.strip()
                if role in assignment_roles and not is_repair:
                    assignment_ok = False
                    errors.append(
                        "initial assignments must be unique per role: " + role
                    )
                assignment_roles[role] = assignment_id
                if activation_roles and activation_roles.get(role) != "active":
                    assignment_ok = False
                    errors.append(
                        "assignment role is not active in the activation matrix: "
                        + role
                    )

        if not isinstance(session_id, str) or not session_id.strip():
            assignment_ok = False
            errors.append("assignment %d has no valid session_id" % index)
        else:
            session_id = session_id.strip()

        fresh_session = assignment.get("fresh_session")
        if type(fresh_session) is not bool:
            assignment_ok = False
            errors.append("assignment %d needs boolean fresh_session" % index)
        elif not is_repair and fresh_session is not True:
            assignment_ok = False
            errors.append("assignment %d must use a fresh session" % index)
        elif role == "final-reviewer" and fresh_session is not True:
            assignment_ok = False
            errors.append("final-reviewer assignments must use a fresh session")

        if isinstance(session_id, str) and session_id in session_ids:
            can_reuse = is_repair and fresh_session is False
            if not can_reuse:
                assignment_ok = False
                errors.append("delegated sessions must be unique")
            elif assignment.get("owner_session_id") not in {
                None,
                session_id,
            }:
                assignment_ok = False
                errors.append("repair must identify its reused owner session")
        elif isinstance(session_id, str):
            session_ids.add(session_id)
            if is_repair and fresh_session is False:
                assignment_ok = False
                errors.append("repair must reuse an existing owner session")

        if is_repair and assignment.get("owner_assignment_id") is not None:
            owner_id = assignment.get("owner_assignment_id")
            if owner_id not in assignment_ids:
                assignment_ok = False
                errors.append("repair owner_assignment_id must name prior work")

        reads = _paths(assignment.get("read_scope"), allow_empty=False)
        writes = _paths(assignment.get("write_scope"), allow_empty=True)
        if reads is None:
            assignment_ok = False
            errors.append("assignment %d has an invalid read_scope" % index)
        elif any(scope == "." for scope in reads):
            assignment_ok = False
            errors.append(
                "assignment %d read_scope cannot be the whole repository" % index
            )
        if writes is None:
            assignment_ok = False
            errors.append("assignment %d has an invalid write_scope" % index)
        elif any(
            scope == "." or _internal_artifact(scope) for scope in writes
        ):
            assignment_ok = False
            errors.append(
                "assignment %d write_scope must use concrete product paths" % index
            )
        elif isinstance(assignment_id, str):
            assignment_write_scopes[assignment_id] = writes
            for scope in writes:
                write_scopes.append((assignment_id, scope))

        if not _style_guides_valid(assignment, index, errors):
            style_ok = False

        assignment_values, assignment_id_errors = _event_ids(
            assignment, f"assignment {index}"
        )
        evidence_ids.update(assignment_values)
        errors.extend(assignment_id_errors)
        assignment_cycle_id = _assignment_cycle_id(assignment, cycle_id)
        if assignment.get("cycle_id") is not None and assignment_cycle_id is None:
            assignment_ok = False
            errors.append("assignment cycle_id is invalid")
        elif assignment_cycle_id != cycle_id:
            assignment_ok = False
            errors.append("assignment belongs to a different cycle")

    if activation_roles:
        for role, status in activation_roles.items():
            if role == team_contract.LEAD_ROLE or status != "active":
                continue
            if role not in assignment_roles:
                assignment_ok = False
                errors.append(
                    "active role has no delegated assignment: " + role
                )

    scope_ok = assignment_ok
    for index, (assignment_id, left) in enumerate(write_scopes):
        for other_id, right in write_scopes[index + 1 :]:
            if assignment_id != other_id and _overlap(left, right):
                scope_ok = False
                errors.append("write scopes overlap: %s and %s" % (left, right))

    check_events = [event for event in parsed if event.get("kind") == "check"]
    check_statuses: list[str] = []
    verification_ok = bool(check_events)
    for index, check in enumerate(check_events):
        status = check.get("status")
        if not isinstance(status, str):
            verification_ok = False
            errors.append("check %d has no status" % index)
            continue
        normalized_status = status.strip().lower()
        check_statuses.append(normalized_status)
        if normalized_status not in PASS_STATUSES | SKIP_STATUSES:
            verification_ok = False
            errors.append("check %d did not pass: %s" % (index, status))
        elif (
            normalized_status == "skip"
            and check.get("applicable", True) is not False
        ):
            verification_ok = False
            errors.append("check %d cannot skip an applicable gate" % index)
        check_values, check_id_errors = _event_ids(check, f"check {index}")
        evidence_ids.update(check_values)
        errors.extend(check_id_errors)
    if check_events and not any(
        status in PASS_STATUSES for status in check_statuses
    ) and any(status not in SKIP_STATUSES for status in check_statuses):
        verification_ok = False
        errors.append("checks without a pass must all be not_applicable or skip")
    if not check_events:
        errors.append("at least one verification check is required")

    integrations = [event for event in parsed if event.get("kind") == "integrated"]
    integration_ok = (
        len(integrations) == 1
        and integrations[0].get("status") in INTEGRATION_STATUSES
    )
    if not integration_ok:
        errors.append("exactly one successful final integration is required")

    integration_index = next(
        (
            index
            for index, event in enumerate(parsed)
            if event.get("kind") == "integrated"
        ),
        None,
    )
    final_reviewer_indices = [
        index
        for index, event in enumerate(parsed)
        if event.get("kind") == "assignment"
        and event.get("agent_id", event.get("role")) == "final-reviewer"
    ]
    final_review_ok = (
        len(final_reviewer_indices) == 1
        and integration_index is not None
        and final_reviewer_indices[0] > integration_index
    )
    if not final_review_ok:
        errors.append(
            "one fresh final-reviewer assignment must follow final integration"
        )

    if len(integrations) == 1:
        integration_owner = integrations[0].get("integration_owner")
        if not isinstance(integration_owner, str) or not integration_owner.strip():
            integration_ok = False
            errors.append("integration needs an explicit integration_owner")
        elif integration_owner != team_contract.LEAD_ROLE and (
            integration_owner not in activation_roles
            or activation_roles.get(integration_owner) != "active"
        ):
            integration_ok = False
            errors.append(
                "integration_owner must be the lead or an active role"
            )

    changed_paths: list[str] = []
    if len(integrations) == 1:
        integration_paths = _paths(
            integrations[0].get("changed_paths"), allow_empty=True
        )
        if integration_paths is None:
            integration_ok = False
            errors.append("integration changed_paths are invalid")
        else:
            changed_paths = integration_paths
            for path in changed_paths:
                if path == ".":
                    integration_ok = False
                    errors.append("integration changed_paths must be concrete")
                    continue
                if _internal_artifact(path):
                    if not _cycle_artifact(path, cycle_id):
                        integration_ok = False
                        errors.append(
                            "integrated saturation path must be per-cycle: "
                            + path
                        )
                    continue
                if not any(_contains(scope, path) for _, scope in write_scopes):
                    integration_ok = False
                    errors.append(
                        "integrated path is outside assignment scopes: " + path
                    )
        integration_values, integration_id_errors = _event_ids(
            integrations[0], "integration"
        )
        evidence_ids.update(integration_values)
        errors.extend(integration_id_errors)

    report_events = [
        event
        for event in parsed
        if event.get("kind") in {"report", "report_written"}
    ]
    report_paths: list[str] = []
    reports_ok = True
    for event in report_events:
        report_path = _normal_path(event.get("path"))
        if report_path is None or not _cycle_artifact(report_path, cycle_id):
            reports_ok = False
            errors.append("report events must use a per-cycle report path")
        else:
            report_paths.append(report_path)
        report_values, report_id_errors = _event_ids(
            event, "report event"
        )
        evidence_ids.update(report_values)
        errors.extend(report_id_errors)

    phase_packets = [
        event
        for event in parsed
        if event.get("kind") in {"phase_packet", "phase_packet_created"}
    ]
    phase_packet_ids: set[str] = set()
    phase_packets_ok = True
    for index, packet in enumerate(phase_packets):
        packet_id = packet.get("phase_packet_id", packet.get("packet_id"))
        if not isinstance(packet_id, str) or not packet_id.strip():
            phase_packets_ok = False
            errors.append("phase packet %d needs a phase_packet_id" % index)
        elif packet_id in phase_packet_ids:
            phase_packets_ok = False
            errors.append("phase packet IDs must be unique")
        else:
            phase_packet_ids.add(packet_id)
        packet_status = packet.get("status")
        if packet_status is not None and packet_status not in PHASE_PACKET_STATUSES:
            phase_packets_ok = False
            errors.append("phase packet %d has a non-canonical status" % index)
        packet_payload = dict(packet)
        if "packet_id" not in packet_payload and isinstance(packet_id, str):
            packet_payload["packet_id"] = packet_id
        packet_errors = team_contract.validate_phase_packet(
            packet_payload, cycle_id
        )
        if packet_errors:
            phase_packets_ok = False
            errors.extend(
                "phase packet %d: %s" % (index, error)
                for error in packet_errors
            )
        upstream_values = packet_payload.get(
            "upstream_assignment_ids", packet_payload.get("assignment_ids", [])
        )
        upstream_assignment_values: list[Any] = []
        if isinstance(upstream_values, Sequence) and not isinstance(
            upstream_values, (str, bytes)
        ):
            upstream_assignment_values = list(upstream_values)
            for assignment_id in upstream_assignment_values:
                if assignment_id not in assignment_ids:
                    phase_packets_ok = False
                    errors.append(
                        "phase packet %d references an unknown assignment: %s"
                        % (index, assignment_id)
                    )
        packet_paths = _paths(
            packet_payload.get("changed_paths"), allow_empty=True
        )
        if packet_paths is not None:
            upstream_scopes = [
                scope
                for assignment_id in upstream_assignment_values
                if assignment_id in assignment_write_scopes
                for scope in assignment_write_scopes[assignment_id]
            ]
            for path in packet_paths:
                if path == ".":
                    phase_packets_ok = False
                    errors.append(
                        "phase packet %d changed_paths must be concrete" % index
                    )
                elif not _internal_artifact(path) and not any(
                    _contains(scope, path) for scope in upstream_scopes
                ):
                    phase_packets_ok = False
                    errors.append(
                        "phase packet %d path is outside assignment scopes: %s"
                        % (index, path)
                    )
        packet_values, packet_id_errors = _event_ids(
            packet, f"phase packet {index}"
        )
        evidence_ids.update(packet_values)
        errors.extend(packet_id_errors)

    durable_paths: list[str] = []
    artifacts_ok = True
    for event in parsed:
        if event.get("kind") != "durable_path":
            continue
        path = _normal_path(event.get("path"))
        if path is None:
            artifacts_ok = False
            errors.append("durable_path event has an invalid path")
            continue
        durable_paths.append(path)
        if _internal_artifact(path) and not _cycle_artifact(path, cycle_id):
            artifacts_ok = False
            errors.append(
                "saturation runtime artifacts must be per-cycle context/report: "
                + path
            )

    checks = {
        "context_frozen": {
            "status": "pass" if context_ok else "fail",
            "detail": cycle_contract_path(cycle_id)
            if context_ok and cycle_id is not None
            else "missing per-cycle context",
        },
        "activation_matrix": {
            "status": "pass" if activation_ok else "fail",
            "detail": len(activation_roles),
        },
        "fresh_sessions": {
            "status": "pass" if assignment_ok else "fail",
            "detail": len(session_ids),
        },
        "disjoint_scopes": {
            "status": "pass" if scope_ok else "fail",
            "detail": len(write_scopes),
        },
        "style_guides": {
            "status": "pass" if style_ok else "fail",
            "detail": "relevant guides named or not_applicable"
            if style_ok
            else "missing or invalid guides",
        },
        "verification": {
            "status": "pass" if verification_ok else "fail",
            "detail": len(check_events),
        },
        "integration": {
            "status": "pass" if integration_ok else "fail",
            "detail": len(changed_paths),
        },
        "final_review": {
            "status": "pass" if final_review_ok else "fail",
            "detail": len(final_reviewer_indices),
        },
        "phase_packets": {
            "status": "pass" if phase_packets_ok else "fail",
            "detail": len(phase_packet_ids),
        },
        "reports": {
            "status": "pass" if reports_ok else "fail",
            "detail": len(report_paths),
        },
        "no_runtime_artifacts": {
            "status": "pass" if artifacts_ok else "fail",
            "detail": len(durable_paths),
        },
    }
    metrics = {
        "events": len(parsed),
        "cycle_id": cycle_id,
        "assignments": len(assignments),
        "sessions": len(session_ids),
        "checks": len(check_events),
        "passed_checks": sum(
            status in PASS_STATUSES for status in check_statuses
        ),
        "changed_paths": len(changed_paths),
        "durable_paths": len(durable_paths),
        "reports": len(report_paths),
        "phase_packets": len(phase_packet_ids),
        "evidence_ids": len(evidence_ids),
        "forbidden_durable_paths": sum(
            _internal_artifact(path)
            and not _cycle_artifact(path, cycle_id)
            for path in durable_paths
        ),
    }
    return _result(checks, errors, metrics)


def cycle_contract_path(cycle_id: str | None) -> str:
    """Return a display path for a cycle or the unbound template."""

    if cycle_id is None:
        return CONTEXT_PATH
    return team_contract.cycle_context_path(cycle_id)


def evaluate_observation(value: Any) -> dict[str, Any]:
    """Evaluate an event list or an observation wrapper.

    The wrapper may carry ``cycle_id`` and an optional top-level activation
    matrix.  These values are converted to in-memory events only.
    """

    if isinstance(value, Mapping):
        events = value.get("events")
        if isinstance(events, Sequence) and not isinstance(events, (str, bytes)):
            normalized_events = list(events)
        else:
            normalized_events = events
        if "activation_matrix" in value:
            if not isinstance(normalized_events, list):
                normalized_events = []
            normalized_events.append(
                {
                    "kind": "activation_matrix",
                    "cycle_id": value.get("cycle_id"),
                    "mode": value.get("mode"),
                    "roles": value["activation_matrix"],
                }
            )
        if "report_path" in value:
            if not isinstance(normalized_events, list):
                normalized_events = []
            normalized_events.append(
                {
                    "kind": "report",
                    "cycle_id": value.get("cycle_id"),
                    "path": value["report_path"],
                }
            )
        return evaluate_events(
            normalized_events,
            cycle_id=value.get("cycle_id"),
        )
    return evaluate_events(value)


def load_observation(path: Path) -> Any:
    """Load an evaluator-owned JSON input without writing files.

    Args:
        path: JSON path supplied by the CI/governance caller.

    Returns:
        Decoded JSON value.

    Raises:
        OSError: If the input cannot be opened.
        json.JSONDecodeError: If the input is not valid JSON.
    """

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_result(result: Mapping[str, Any]) -> str:
    """Format a compact human-readable CI evaluator result."""

    status = str(result.get("status", "fail")).upper()
    metrics = result.get("metrics", {})
    errors = result.get("errors", [])
    summary = "events={events} assignments={assignments} checks={checks}".format(
        events=metrics.get("events", 0),
        assignments=metrics.get("assignments", 0),
        checks=metrics.get("checks", 0),
    )
    if errors:
        return "%s: %s; %s" % (status, errors[0], summary)
    return "%s: %s" % (status, summary)


def _parser() -> argparse.ArgumentParser:
    """Build the evaluator command-line parser."""

    parser = argparse.ArgumentParser(
        description="Evaluate an in-memory saturation governance snapshot."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="JSON input owned by CI/governance; stdin is used when omitted.",
    )
    parser.add_argument("--json", action="store_true", help="print JSON output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the evaluator CLI without creating a report artifact.

    Returns:
        ``0`` for a passing governance evaluation and ``1`` otherwise.
    """

    args = _parser().parse_args(argv)
    try:
        if args.input is not None:
            observation = load_observation(args.input)
        elif not sys.stdin.isatty():
            observation = json.load(sys.stdin)
        else:
            _parser().error(
                "provide an input JSON path or pipe an observation on stdin"
            )
    except (OSError, json.JSONDecodeError) as exc:
        print("input error: %s" % exc, file=sys.stderr)
        return 2

    result = evaluate_observation(observation)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_result(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
