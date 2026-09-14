"""Deterministic, dependency-free grading for saturation workflow traces."""

from __future__ import annotations

import argparse
import json
import math
import posixpath
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import prompt_contract


SCHEMA_VERSION = 3
CURRENT_SCHEMA_VERSION = 3
SUPPORTED_SCHEMA_VERSIONS = {CURRENT_SCHEMA_VERSION}
EXPECTED_WRITE_ROOT = ".agents/skills/saturation/evals"
CONTEXT_PATH = ".saturation/context.md"
EXPECTED_READ_ROOTS = (
    CONTEXT_PATH,
    ".agents/skills/saturation/code_styleguides",
    EXPECTED_WRITE_ROOT,
)
EVENT_KINDS = {
    "context_frozen",
    "inspection",
    "handoff",
    "implementation",
    "review",
    "repair",
    "verify",
    "promotion",
    "completion_gate",
}
TOOL_PHASES = {
    "freeze_context",
    "inspect",
    "implement",
    "review",
    "repair",
    "verify",
    "promote",
    "completion_gate",
}
EVIDENCE_KINDS = {
    "read",
    "handoff",
    "diff",
    "review",
    "verification",
    "promotion",
    "gate",
    "test",
}
RISK_KINDS = {"scope_conflict", "quality_change", "data_effect", "blocker"}
READ_ONLY_ROLES = {"reviewer", "verifier"}

# Schema v3 fixes the handoff, verifier, prompt, sequence, and reverse-link contracts;
# missing fields cannot be mistaken for a successful delivery or verification.
HANDOFF_INPUT_FIELDS = ("context", "assignment", "state", "input", "output", "error", "stop", "evidence", "fresh_session")
HANDOFF_ASSIGNMENT_FIELDS = ("id", "owner_actor_id", "read_scope", "write_scope")
HANDOFF_OUTPUT_FIELDS = (
    "status",
    "event_ref",
    "changed_paths",
    "verification_evidence",
    "unresolved_risks",
    "evidence",
)
HANDOFF_ERROR_FIELDS = ("code", "message", "retryable", "escalate", "evidence")
HANDOFF_OUTPUT_STATUSES = {"complete", "needs_repair", "blocked"}
HANDOFF_PHASES = {
    "freeze_context",
    "inspect",
    "implement",
    "review",
    "final_review",
    "repair",
    "verify",
    "promote",
    "completion_gate",
}
HANDOFF_STATE_STATUSES = {"ready", "running", "needs_repair", "verified", "blocked"}
HANDOFF_STATE_DECISIONS = {
    "continue",
    "repair",
    "verify",
    "promote",
    "escalate",
    "complete",
    "reject",
}
BASE_VERIFIER_DIMENSIONS = ("completeness", "clarity", "consistency", "testability")
OPTIONAL_VERIFIER_DIMENSIONS = ("behavior", "error_handling", "task_completion")
VERIFIER_DIMENSIONS = BASE_VERIFIER_DIMENSIONS + OPTIONAL_VERIFIER_DIMENSIONS
VERIFIER_RESULTS = {"pass", "fail", "not_applicable"}

EVENT_TOOL_PHASES = {
    "context_frozen": "freeze_context",
    "inspection": "inspect",
    "implementation": "implement",
    "review": "review",
    "repair": "repair",
    "verify": "verify",
    "promotion": "promote",
    "completion_gate": "completion_gate",
}
TOOL_PHASE_ROLES = {
    "freeze_context": "orchestrator",
    "inspect": "orchestrator",
    "implement": "implementer",
    "review": "reviewer",
    "repair": "repairer",
    "verify": "verifier",
    "promote": "orchestrator",
    "completion_gate": "orchestrator",
}
HANDOFF_TARGET_KINDS = {
    "freeze_context": "context_frozen",
    "inspect": "inspection",
    "implement": "implementation",
    "review": "review",
    "final_review": "review",
    "repair": "repair",
    "verify": "verify",
    "promote": "promotion",
    "completion_gate": "completion_gate",
}
EVIDENCE_SOURCE_KINDS = {
    "read": {"context_frozen", "inspection", "freeze_context", "inspect"},
    "handoff": {"handoff"},
    "diff": {"implementation", "repair", "promotion", "implement", "repair", "promote"},
    "review": {"review"},
    "verification": {"verify"},
    "promotion": {"promotion", "promote"},
    "gate": {"completion_gate"},
    "test": {"inspection", "verify", "inspect", "verification"},
}

CRITERIA = (
    ("context_freeze", "frozen context before delegation"),
    ("tool_order", "tool-call order"),
    ("session_freshness", "session identity and freshness"),
    ("write_scope", "write scopes and promotion"),
    ("handoff_payload", "complete handoff payload"),
    ("readonly_review", "independent, adversarial, read-only review"),
    ("evidence", "evidence linked to observable actions"),
    ("repair_reverify", "repair and reverification"),
    ("completion_gates", "completion gates"),
    ("escalation", "conflict and blocker escalation"),
    ("prompt_contract", "prompt composition and trace contract"),
)
MAX_SCORE = len(CRITERIA) * 10


def load_trace(path: Path) -> Dict[str, Any]:
    """Load one JSON trace without resolving includes or using external state."""

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("trace root must be an object")
    return value


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_ids(value: Any, *, nonempty: bool = False) -> List[str]:
    values = _list(value)
    result = [item for item in values if isinstance(item, str)]
    if nonempty and (not isinstance(value, list) or len(result) != len(values)):
        return []
    if nonempty and any(not item.strip() for item in result):
        return []
    return result


def _id_set(value: Any) -> set:
    return set(_string_ids(value, nonempty=True))


def _strict_contract(trace: Dict[str, Any]) -> bool:
    return trace.get("schema_version") == CURRENT_SCHEMA_VERSION


def _contract(trace: Dict[str, Any]) -> Dict[str, Any]:
    return _mapping(trace.get("trace_contract"))


def _actor(trace: Dict[str, Any], actor_id: Any) -> Dict[str, Any]:
    actors = trace.get("actors", {})
    value = actors.get(actor_id, {}) if isinstance(actors, dict) else {}
    return value if isinstance(value, dict) else {}


def _role(trace: Dict[str, Any], actor_id: Any) -> str:
    return str(_actor(trace, actor_id).get("role", ""))


def _session(trace: Dict[str, Any], actor_id: Any) -> str:
    return str(_actor(trace, actor_id).get("session_id", ""))


def _events(trace: Dict[str, Any], kind: Optional[str] = None) -> List[Tuple[int, Dict[str, Any]]]:
    result = []
    for index, event in enumerate(_list(trace.get("events"))):
        if isinstance(event, dict) and (kind is None or event.get("kind") == kind):
            result.append((index, event))
    return result


def _tools(trace: Dict[str, Any], phase: Optional[str] = None) -> List[Tuple[int, Dict[str, Any]]]:
    result = []
    for index, call in enumerate(_list(trace.get("tool_calls"))):
        if isinstance(call, dict) and (phase is None or call.get("phase") == phase):
            result.append((index, call))
    return result


def _id_map(items: Iterable[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    result = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(key)
        if isinstance(value, str):
            result[value] = item
    return result


def _normal_path(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.replace("\\", "/")
    if not value or value.startswith("/") or (len(value) > 1 and value[1] == ":"):
        return None
    normalized = posixpath.normpath(value)
    if normalized in ("", ".") or normalized == ".." or normalized.startswith("../"):
        return None
    return normalized[2:] if normalized.startswith("./") else normalized


def _inside(path: Any, root: str = EXPECTED_WRITE_ROOT) -> bool:
    normalized = _normal_path(path)
    return bool(normalized and (normalized == root or normalized.startswith(root + "/")))


def _check_scope(paths: Any, root: str = EXPECTED_WRITE_ROOT) -> bool:
    return isinstance(paths, list) and all(_inside(path, root) for path in paths)


def _check_read_scope(paths: Any) -> bool:
    """Require unique, normalized read roots inside context or evals."""

    if not isinstance(paths, list) or len(paths) != len(set(_string_ids(paths))):
        return False
    return all(
        _normal_path(path) == path
        and any(_inside(path, root) for root in EXPECTED_READ_ROOTS)
        for path in paths
    )


def _declared_verifier_dimensions(trace: Dict[str, Any]) -> List[str]:
    dimensions = _mapping(_contract(trace).get("verifier")).get("dimensions")
    return _string_ids(dimensions, nonempty=True)


def _source_map(trace: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result = {}
    for item in _list(trace.get("events")) + _list(trace.get("tool_calls")):
        if isinstance(item, dict):
            item_id = item.get("event_id", item.get("call_id"))
            if isinstance(item_id, str):
                result[item_id] = item
    return result


def _event_map(trace: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return _id_map(_list(trace.get("events")), "event_id")


def _call_map(trace: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return _id_map(_list(trace.get("tool_calls")), "call_id")


def _source_position(trace: Dict[str, Any], source_id: Any) -> Optional[int]:
    """Return an event-order position for an observable source when possible."""

    for index, event in _events(trace):
        if event.get("event_id") == source_id:
            return index
    for _, call in _tools(trace):
        if call.get("call_id") != source_id:
            continue
        event_ref = call.get("event_ref")
        if isinstance(event_ref, str):
            for index, event in _events(trace):
                if event.get("event_id") == event_ref:
                    return index
        linked = _linked_call_event(trace, call)
        if linked is not None:
            return linked[0]
        return None
    return None


def _evidence_position(trace: Dict[str, Any], evidence_id: Any) -> Optional[int]:
    for record in _list(trace.get("evidence")):
        if isinstance(record, dict) and record.get("evidence_id") == evidence_id:
            return _source_position(trace, record.get("source_id"))
    return None


def _linked_call_event(
    trace: Dict[str, Any], call: Dict[str, Any]
) -> Optional[Tuple[int, Dict[str, Any]]]:
    """Find the event causally paired with a tool call."""

    event_ref = call.get("event_ref")
    if isinstance(event_ref, str):
        for index, event in _events(trace):
            if event.get("event_id") == event_ref:
                return index, event
        return None
    call_id = call.get("call_id")
    if not isinstance(call_id, str):
        return None
    matches = [
        (index, event)
        for index, event in _events(trace)
        if _payload(event).get("tool_call_ref") == call_id
    ]
    return matches[0] if len(matches) == 1 else None


def _contract_declaration_errors(trace: Dict[str, Any]) -> List[str]:
    """Validate the fixed v3 declaration without inspecting event semantics."""

    if "trace_contract" not in trace:
        return ["schema_version 3 requires trace_contract"]
    declaration = trace.get("trace_contract")
    if not isinstance(declaration, dict):
        return ["trace_contract must be an object"]

    errors: List[str] = []
    if set(declaration) != {"version", "causal_links", "handoff", "verifier", "prompt"}:
        errors.append("trace_contract must contain the fixed v3 declarations")
    if declaration.get("version") != CURRENT_SCHEMA_VERSION:
        errors.append("trace_contract.version must be 3")
    if declaration.get("causal_links") != "bidirectional":
        errors.append("trace_contract.causal_links must be bidirectional")

    handoff = declaration.get("handoff")
    if not isinstance(handoff, dict):
        errors.append("trace_contract.handoff must be an object")
    else:
        expected_handoff = {
            "input_fields": list(HANDOFF_INPUT_FIELDS),
            "assignment_fields": list(HANDOFF_ASSIGNMENT_FIELDS),
            "output_fields": list(HANDOFF_OUTPUT_FIELDS),
            "error_fields": list(HANDOFF_ERROR_FIELDS),
        }
        if set(handoff) != set(expected_handoff):
            errors.append("trace_contract.handoff must contain only the fixed contract fields")
        for field, expected in expected_handoff.items():
            if handoff.get(field) != expected:
                errors.append("trace_contract.handoff.%s is not the fixed contract" % field)

    verifier = declaration.get("verifier")
    if not isinstance(verifier, dict):
        errors.append("trace_contract.verifier must be an object")
    else:
        dimensions = verifier.get("dimensions")
        optional = [
            dimension
            for dimension in OPTIONAL_VERIFIER_DIMENSIONS
            if dimension in _string_ids(dimensions)
        ]
        expected_dimensions = list(BASE_VERIFIER_DIMENSIONS) + optional
        expected_criteria = [criterion_id for criterion_id, _ in CRITERIA]
        if set(verifier) != {"dimensions", "criteria"}:
            errors.append("trace_contract.verifier must contain only dimensions and criteria")
        if dimensions != expected_dimensions:
            errors.append("trace_contract.verifier.dimensions must contain the base dimensions followed by declared optional dimensions")
        if verifier.get("criteria") != expected_criteria:
            errors.append("trace_contract.verifier.criteria are not the rubric criteria")
    errors.extend(
        "prompt declaration: " + error
        for error in prompt_contract.validate_prompt_declaration(declaration.get("prompt"))
    )
    return errors


def validate_trace(trace: Any) -> List[str]:
    """Return structural errors; behavioral defects are deliberately graded below."""

    errors: List[str] = []
    if not isinstance(trace, dict):
        return ["root must be an object"]
    schema_version = trace.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append("schema_version must be 3")
    elif schema_version == CURRENT_SCHEMA_VERSION or "trace_contract" in trace:
        errors.extend(_contract_declaration_errors(trace))
    for key in ("trace_id", "objective"):
        if not _nonempty_string(trace.get(key)):
            errors.append("missing non-empty %s" % key)
    if not isinstance(trace.get("allowed_write_roots"), list):
        errors.append("allowed_write_roots must be a list")
    actors = trace.get("actors")
    if not isinstance(actors, dict) or not actors:
        errors.append("actors must be a non-empty object")
    else:
        for actor_id, actor in actors.items():
            if not _nonempty_string(actor_id) or not isinstance(actor, dict):
                errors.append("each actor needs an id and object")
                continue
            if not _nonempty_string(actor.get("role")):
                errors.append("actor %s has no role" % actor_id)
            if not _nonempty_string(actor.get("session_id")):
                errors.append("actor %s has no session_id" % actor_id)

    assignments = trace.get("assignments")
    assignment_ids = set()
    if not isinstance(assignments, list) or not assignments:
        errors.append("assignments must be a non-empty list")
        assignments = []
    for assignment in assignments:
        if not isinstance(assignment, dict):
            errors.append("assignment must be an object")
            continue
        assignment_id = assignment.get("assignment_id")
        if not _nonempty_string(assignment_id):
            errors.append("assignment missing assignment_id")
        elif assignment_id in assignment_ids:
            errors.append("duplicate assignment_id %s" % assignment_id)
        else:
            assignment_ids.add(assignment_id)
        owner_actor_id = assignment.get("owner_actor_id")
        if not isinstance(owner_actor_id, str) or owner_actor_id not in actors if isinstance(actors, dict) else True:
            errors.append("assignment has unknown owner_actor_id")
        if set(assignment) != {"assignment_id", "owner_actor_id", "read_scope", "write_scope"}:
            errors.append("assignment %s must contain the exact assignment contract" % assignment_id)
        if not isinstance(assignment.get("read_scope"), list):
            errors.append("assignment %s read_scope must be a list" % assignment_id)
        if not isinstance(assignment.get("write_scope"), list):
            errors.append("assignment %s write_scope must be a list" % assignment_id)

    events = trace.get("events")
    if not isinstance(events, list) or not events:
        errors.append("events must be a non-empty list")
        events = []
    item_ids = set()
    for event in events:
        if not isinstance(event, dict):
            errors.append("event must be an object")
            continue
        event_id = event.get("event_id")
        if not _nonempty_string(event_id):
            errors.append("event missing event_id")
        elif event_id in item_ids:
            errors.append("duplicate trace item id %s" % event_id)
        else:
            item_ids.add(event_id)
        if not isinstance(event.get("kind"), str) or event.get("kind") not in EVENT_KINDS:
            errors.append("event %s has unknown kind" % event_id)
        event_actor_id = event.get("actor_id")
        if not isinstance(event_actor_id, str) or event_actor_id not in actors if isinstance(actors, dict) else True:
            errors.append("event %s has unknown actor_id" % event_id)
        for field in ("reads", "writes"):
            if not isinstance(event.get(field), list):
                errors.append("event %s %s must be a list" % (event_id, field))
        if "payload" in event and not isinstance(event.get("payload"), dict):
            errors.append("event %s payload must be an object" % event_id)
        if "evidence" in event and not isinstance(event.get("evidence"), list):
            errors.append("event %s evidence must be a list" % event_id)

    calls = trace.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        errors.append("tool_calls must be a non-empty list")
        calls = []
    for call in calls:
        if not isinstance(call, dict):
            errors.append("tool call must be an object")
            continue
        call_id = call.get("call_id")
        if not _nonempty_string(call_id):
            errors.append("tool call missing call_id")
        elif call_id in item_ids:
            errors.append("duplicate trace item id %s" % call_id)
        else:
            item_ids.add(call_id)
        if not isinstance(call.get("phase"), str) or call.get("phase") not in TOOL_PHASES:
            errors.append("tool call %s has unknown phase" % call_id)
        call_actor_id = call.get("actor_id")
        if not isinstance(call_actor_id, str) or call_actor_id not in actors if isinstance(actors, dict) else True:
            errors.append("tool call %s has unknown actor_id" % call_id)
        for field in ("name", "mode"):
            if not _nonempty_string(call.get(field)):
                errors.append("tool call %s missing %s" % (call_id, field))
        for field in ("reads", "writes"):
            if not isinstance(call.get(field), list):
                errors.append("tool call %s %s must be a list" % (call_id, field))

    evidence = trace.get("evidence")
    if not isinstance(evidence, list):
        errors.append("evidence must be a list")
    else:
        evidence_ids = set()
        for record in evidence:
            if not isinstance(record, dict):
                errors.append("evidence record must be an object")
                continue
            record_id = record.get("evidence_id")
            if not _nonempty_string(record_id) or record_id in evidence_ids:
                errors.append("evidence ids must be non-empty and unique")
            elif isinstance(record_id, str):
                evidence_ids.add(record_id)
            if not _nonempty_string(record.get("source_id")):
                errors.append("evidence %s has no source_id" % record_id)
            if not isinstance(record.get("kind"), str) or record.get("kind") not in EVIDENCE_KINDS:
                errors.append("evidence %s has unknown kind" % record_id)
            if not _nonempty_string(record.get("claim")):
                errors.append("evidence %s has no claim" % record_id)
            if "paths" in record and not isinstance(record.get("paths"), list):
                errors.append("evidence %s paths must be a list" % record_id)

    for field in ("risks", "escalations"):
        if field in trace and not isinstance(trace.get(field), list):
            errors.append("%s must be a list" % field)
    return errors


def _result(criterion_id: str, label: str, checks: Sequence[Tuple[str, bool, str]]) -> Dict[str, Any]:
    passed = sum(1 for _, ok, _ in checks if ok)
    earned = (10 * passed) // len(checks) if checks else 0
    status = "pass" if passed == len(checks) else ("partial" if passed else "fail")
    failures = [detail for _, ok, detail in checks if not ok]
    return {
        "id": criterion_id,
        "label": label,
        "max_points": 10,
        "earned_points": earned,
        "status": status,
        "summary": "ok" if not failures else "; ".join(failures),
        "checks": [
            {"id": check_id, "passed": ok, "detail": detail}
            for check_id, ok, detail in checks
        ],
    }


def _failed_result(criterion_id: str, label: str, reason: str) -> Dict[str, Any]:
    return _result(criterion_id, label, [("schema", False, reason)])


def _payload(event: Dict[str, Any]) -> Dict[str, Any]:
    value = event.get("payload", {})
    return value if isinstance(value, dict) else {}


def _gaps(event: Optional[Dict[str, Any]]) -> List[str]:
    if not event:
        return []
    payload = _payload(event)
    values = payload.get("gap_ids", payload.get("material_gaps", []))
    return [value for value in _list(values) if isinstance(value, str) and value]


def _linked_call(trace: Dict[str, Any], event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    call_id = _payload(event).get("tool_call_ref")
    if not isinstance(call_id, str):
        return None
    return _call_map(trace).get(call_id)


def _event_tool_links(trace: Dict[str, Any]) -> Tuple[bool, str]:
    """Require one causally compatible tool call for every operational event."""

    event_map = _event_map(trace)
    call_map = _call_map(trace)
    strict = _strict_contract(trace)
    event_refs: Dict[str, List[str]] = {}
    ok = True
    detail = "event and tool calls must have exact phase, actor, and assignment links"

    for event in event_map.values():
        kind = event.get("kind")
        phase = EVENT_TOOL_PHASES.get(kind)
        if phase is None:
            continue
        ref = _payload(event).get("tool_call_ref")
        call = call_map.get(ref) if isinstance(ref, str) else None
        compatible = bool(call) and call.get("phase") == phase
        compatible = compatible and call.get("actor_id") == event.get("actor_id")
        compatible = compatible and call.get("assignment_id") == event.get("assignment_id")
        compatible = compatible and call.get("reads") == event.get("reads")
        compatible = compatible and call.get("writes") == event.get("writes")
        if compatible:
            event_refs.setdefault(ref, []).append(event.get("event_id"))
        else:
            ok = False

    for call in call_map.values():
        phase = call.get("phase")
        if phase == "inspect" and not strict and "event_ref" not in call:
            # The v1 fixtures contain an inspection call but no inspection
            # event.  It remains grandfathered; all workflow-changing calls
            # still need an exact reverse link in v1.
            continue
        if phase not in TOOL_PHASE_ROLES:
            ok = False
            continue
        event_ref = call.get("event_ref")
        linked_event: Optional[Dict[str, Any]] = (
            event_map.get(event_ref) if isinstance(event_ref, str) and event_ref else None
        )
        if linked_event is None:
            ok = False
            continue
        if (
            linked_event.get("event_id") not in event_refs.get(call.get("call_id"), [])
            or linked_event.get("actor_id") != call.get("actor_id")
            or linked_event.get("kind") not in EVENT_TOOL_PHASES
            or EVENT_TOOL_PHASES.get(linked_event.get("kind")) != phase
            or linked_event.get("assignment_id") != call.get("assignment_id")
            or linked_event.get("reads") != call.get("reads")
            or linked_event.get("writes") != call.get("writes")
        ):
            ok = False

    if any(len(refs) != 1 for refs in event_refs.values()):
        ok = False
    return ok, detail


def _handoff_input(event: Dict[str, Any]) -> Dict[str, Any]:
    return _payload(event)


def _handoff_has_explicit_contract(event: Dict[str, Any]) -> bool:
    payload = _payload(event)
    return any(field in payload for field in ("input", "output", "error"))


def _next_handoff_target(
    trace: Dict[str, Any], index: int, event: Dict[str, Any]
) -> Optional[Tuple[int, Dict[str, Any]]]:
    input_payload = _handoff_input(event)
    state = _mapping(input_payload.get("state"))
    target_kind = HANDOFF_TARGET_KINDS.get(state.get("phase"))
    target_actor = event.get("to_actor_id")
    if target_kind is None or not isinstance(target_actor, str):
        return None
    candidates = [
        (candidate_index, candidate)
        for candidate_index, candidate in _events(trace)
        if candidate_index > index
        and candidate.get("kind") == target_kind
        and candidate.get("actor_id") == target_actor
    ]
    return candidates[0] if candidates else None


def _handoff_contract_values(
    trace: Dict[str, Any], index: int, event: Dict[str, Any]
) -> Tuple[Dict[str, Any], Any, Any, Optional[Tuple[int, Dict[str, Any]]], bool]:
    """Return the declared input/output/error and resolved target."""

    payload = _payload(event)
    explicit = _handoff_has_explicit_contract(event)
    input_payload = _handoff_input(event)
    target = _next_handoff_target(trace, index, event)
    output = payload.get("output")
    error = payload.get("error")
    return input_payload, output, error, target, explicit


def _valid_handoff_input(
    trace: Dict[str, Any], event: Dict[str, Any], input_payload: Any, evidence_ids: set
) -> bool:
    if not isinstance(input_payload, dict):
        return False
    if any(field not in input_payload for field in ("context", "assignment", "state", "input", "output", "error", "stop", "evidence", "fresh_session")):
        return False
    context = _mapping(input_payload.get("context"))
    assignment = _mapping(input_payload.get("assignment"))
    state = _mapping(input_payload.get("state"))
    task_input = _mapping(input_payload.get("input"))
    evidence = _string_ids(input_payload.get("evidence"), nonempty=True)
    registered_assignment = _id_map(
        _list(trace.get("assignments")), "assignment_id"
    ).get(assignment.get("id"), {})
    return (
        set(input_payload) == set(HANDOFF_INPUT_FIELDS)
        and set(context) == {"path", "frozen"}
        and context.get("path") == CONTEXT_PATH
        and context.get("frozen") is True
        and set(assignment) == set(HANDOFF_ASSIGNMENT_FIELDS)
        and assignment
        == {
            "id": registered_assignment.get("assignment_id"),
            "owner_actor_id": registered_assignment.get("owner_actor_id"),
            "read_scope": registered_assignment.get("read_scope"),
            "write_scope": registered_assignment.get("write_scope"),
        }
        and set(state) == {"phase", "status", "decision"}
        and state.get("phase") in HANDOFF_PHASES
        and state.get("status") in HANDOFF_STATE_STATUSES
        and state.get("decision") in HANDOFF_STATE_DECISIONS
        and set(task_input) == {"objective", "scope", "acceptance", "constraints"}
        and _nonempty_string(task_input.get("objective"))
        and all(
            _string_ids(task_input.get(key), nonempty=True) == task_input.get(key)
            for key in ("scope", "acceptance", "constraints")
        )
        and input_payload.get("fresh_session") is True
        and bool(evidence)
        and set(evidence) <= evidence_ids
    )


def _valid_handoff_error(error: Any, evidence_ids: set) -> bool:
    if error is None:
        return True
    if not isinstance(error, dict):
        return False
    if set(error) != set(HANDOFF_ERROR_FIELDS):
        return False
    return (
        _nonempty_string(error.get("code"))
        and _nonempty_string(error.get("message"))
        and isinstance(error.get("retryable"), bool)
        and isinstance(error.get("escalate"), bool)
        and bool(_string_ids(error.get("evidence"), nonempty=True))
        and set(_string_ids(error.get("evidence"), nonempty=True)) <= evidence_ids
    )


def _valid_handoff_stop(stop: Any, evidence_ids: set) -> bool:
    if stop is None:
        return True
    if not isinstance(stop, dict) or set(stop) != {"required", "reason", "evidence"}:
        return False
    refs = _string_ids(stop.get("evidence"), nonempty=True)
    return (
        stop.get("required") is True
        and _nonempty_string(stop.get("reason"))
        and bool(refs)
        and set(refs) <= evidence_ids
    )


def _valid_handoff_output(
    trace: Dict[str, Any],
    event: Dict[str, Any],
    output: Any,
    error: Any,
    target: Optional[Tuple[int, Dict[str, Any]]],
    evidence_ids: set,
    explicit: bool,
) -> bool:
    if not isinstance(output, dict):
        return False
    if set(output) != set(HANDOFF_OUTPUT_FIELDS):
        return False
    output_evidence = _string_ids(output.get("evidence"), nonempty=True)
    if not output_evidence or not set(output_evidence) <= evidence_ids:
        return False
    verification_evidence = _string_ids(
        output.get("verification_evidence"), nonempty=True
    )
    if (
        verification_evidence != output.get("verification_evidence")
        or not set(verification_evidence) <= evidence_ids
    ):
        return False
    changed_paths = _string_ids(output.get("changed_paths"), nonempty=True)
    unresolved_risks = _string_ids(output.get("unresolved_risks"), nonempty=True)
    if (
        changed_paths != output.get("changed_paths")
        or unresolved_risks != output.get("unresolved_risks")
        or any(_normal_path(path) != path for path in changed_paths)
    ):
        return False
    if target is None or output.get("event_ref") != target[1].get("event_id"):
        return False
    if changed_paths != _list(target[1].get("writes")):
        return False
    status = output.get("status")
    if status not in HANDOFF_OUTPUT_STATUSES:
        return False
    if set(output_evidence) - set(_string_ids(event.get("evidence"), nonempty=True)):
        return False
    if status == "complete":
        return error is None and not unresolved_risks
    if status == "needs_repair":
        return error is None and bool(unresolved_risks)
    return (
        isinstance(error, dict)
        and _valid_handoff_error(error, evidence_ids)
        and bool(unresolved_risks)
    )


def _lifecycle_phase(
    trace: Dict[str, Any], item: Dict[str, Any], review_number: Dict[str, int]
) -> Optional[str]:
    """Resolve an event/call to its phase in the merged lifecycle."""

    if "event_id" in item:
        kind = item.get("kind")
        if kind == "handoff":
            phase = _mapping(_payload(item).get("state")).get("phase")
            return phase if phase in HANDOFF_PHASES else None
        if kind == "review":
            handoff = _event_map(trace).get(_payload(item).get("handoff_ref"), {})
            phase = _mapping(_payload(handoff).get("state")).get("phase")
            if phase in {"review", "final_review"}:
                return phase
            number = review_number.setdefault("event", 0)
            review_number["event"] = number + 1
            return "review" if number == 0 else "final_review"
        return {
            "context_frozen": "freeze",
            "inspection": "inspect",
            "implementation": "implement",
            "repair": "repair",
            "verify": "verify",
            "promotion": "promote",
            "completion_gate": "completion_gate",
        }.get(kind)
    phase = item.get("phase")
    if phase == "freeze_context":
        return "freeze"
    if phase == "review":
        event = _event_map(trace).get(item.get("event_ref"), {})
        handoff = _event_map(trace).get(_payload(event).get("handoff_ref"), {})
        handoff_phase = _mapping(_payload(handoff).get("state")).get("phase")
        if handoff_phase in {"review", "final_review"}:
            return handoff_phase
        number = review_number.setdefault("call", 0)
        review_number["call"] = number + 1
        return "review" if number == 0 else "final_review"
    return phase if phase in {
        "inspect", "implement", "repair", "verify", "promote", "completion_gate"
    } else None


def _sequence_is_causal(trace: Dict[str, Any]) -> bool:
    """Validate one unique, phase-causal timeline shared by all trace items."""

    events = [item for item in _list(trace.get("events")) if isinstance(item, dict)]
    calls = [item for item in _list(trace.get("tool_calls")) if isinstance(item, dict)]
    values = [item.get("sequence") for item in events + calls]
    if (
        not values
        or any(not isinstance(value, int) or isinstance(value, bool) for value in values)
        or len(values) != len(set(values))
    ):
        return False
    if any(
        left.get("sequence") >= right.get("sequence")
        for items in (events, calls)
        for left, right in zip(items, items[1:])
    ):
        return False
    merged = sorted(events + calls, key=lambda item: item["sequence"])
    ranks = {
        "freeze": 0,
        "inspect": 1,
        "implement": 2,
        "review": 3,
        "repair": 4,
        "verify": 5,
        "final_review": 6,
        "promote": 7,
        "completion_gate": 8,
    }
    review_number: Dict[str, int] = {}
    phases = [_lifecycle_phase(trace, item, review_number) for item in merged]
    if any(phase not in ranks for phase in phases):
        return False
    if any(ranks[left] > ranks[right] for left, right in zip(phases, phases[1:])):
        return False
    for event in events:
        call = _linked_call(trace, event)
        if call is not None and call.get("sequence") >= event.get("sequence"):
            return False
    for index, handoff in _events(trace, "handoff"):
        target = _next_handoff_target(trace, index, handoff)
        if target is None or handoff.get("sequence") >= target[1].get("sequence"):
            return False
    return True


def _grade_context(trace: Dict[str, Any]) -> Dict[str, Any]:
    freezes = _events(trace, "context_frozen")
    handoffs = _events(trace, "handoff")
    freeze = freezes[0][1] if freezes else {}
    freeze_index = freezes[0][0] if freezes else 10**9
    first_handoff = handoffs[0][0] if handoffs else 10**9
    payload = _payload(freeze)
    calls = _list(trace.get("tool_calls"))
    first_call = calls[0] if calls and isinstance(calls[0], dict) else {}
    all_writes = [path for item in _list(trace.get("events")) + calls
                  if isinstance(item, dict) for path in _list(item.get("writes"))]
    checks = [
        ("one_freeze", len(freezes) == 1, "exactly one context_frozen event is required"),
        ("orchestrator", _role(trace, freeze.get("actor_id")) == "orchestrator", "freeze must be by orchestrator"),
        ("frozen_payload", payload.get("context_path") == CONTEXT_PATH and payload.get("frozen") is True,
         "context path must be .saturation/context.md and frozen=true"),
        ("read_only", CONTEXT_PATH in _list(freeze.get("reads")) and not _list(freeze.get("writes")),
         "freeze must read the context and write nothing"),
        ("before_delegation", payload.get("before_delegation") is True and freeze_index < first_handoff,
         "freeze must precede the first handoff"),
        ("first_tool", first_call.get("phase") == "freeze_context" and first_call.get("mode") == "read_only",
         "the first tool call must freeze/read the context"),
        ("context_untouched", CONTEXT_PATH not in all_writes, "frozen context must not be written"),
    ]
    return _result(CRITERIA[0][0], CRITERIA[0][1], checks)


def _positions(calls: List[Any], phase: str) -> List[int]:
    return [i for i, call in enumerate(calls) if isinstance(call, dict) and call.get("phase") == phase]


def _grade_order(trace: Dict[str, Any]) -> Dict[str, Any]:
    calls = _list(trace.get("tool_calls"))
    freeze = _positions(calls, "freeze_context")
    inspect = _positions(calls, "inspect")
    implement = _positions(calls, "implement")
    reviews = _positions(calls, "review")
    repair = _positions(calls, "repair")
    verify = _positions(calls, "verify")
    promote = _positions(calls, "promote")
    first = lambda values: values[0] if values else 10**9
    last = lambda values: values[-1] if values else -1
    checks = [
        ("unified_sequence", _sequence_is_causal(trace), "event and tool sequences must be unique and strictly causal"),
        ("starts_freeze", bool(freeze) and freeze[0] == 0, "tool calls must start with freeze_context"),
        ("inspect_after_freeze", bool(inspect) and first(inspect) > first(freeze), "inspect must follow freeze_context"),
        ("implement_after_inspect", bool(implement) and first(implement) > first(inspect), "implement must follow inspect"),
        ("review_after_implement", bool(reviews) and first(reviews) > first(implement), "initial review must follow implementation"),
        ("repair_after_review", bool(repair) and first(repair) > first(reviews), "repair must follow the initial review"),
        ("verify_after_repair", bool(verify) and first(verify) > first(repair), "verify must follow repair"),
        ("final_review_after_verify", len(reviews) >= 2 and last(reviews) > first(verify), "final review must follow verify"),
        ("promote_after_final_review", bool(promote) and first(promote) > last(reviews), "promotion must follow final review"),
        ("promotion_last", bool(promote) and (promote[-1] == len(calls) - 1 or (promote[-1] == len(calls) - 2 and calls[-1].get("phase") == "completion_gate")), "promotion must immediately precede the completion gate"),
    ]
    return _result(CRITERIA[1][0], CRITERIA[1][1], checks)


def _grade_sessions(trace: Dict[str, Any]) -> Dict[str, Any]:
    actors = trace.get("actors", {})
    session_owners: Dict[str, set] = {}
    for actor_id, actor in actors.items() if isinstance(actors, dict) else []:
        if isinstance(actor, dict):
            session_owners.setdefault(actor.get("session_id"), set()).add(actor_id)
    impl = _events(trace, "implementation")
    repair = _events(trace, "repair")
    reviews = _events(trace, "review")
    verify = _events(trace, "verify")
    promotion = _events(trace, "promotion")
    writer_sessions = {
        _session(trace, event.get("actor_id"))
        for _, event in impl + repair + promotion
    }
    review_sessions = [_session(trace, event.get("actor_id")) for _, event in reviews]
    verify_session = _session(trace, verify[0][1].get("actor_id")) if verify else ""
    expected_roles = {
        "context_frozen": "orchestrator",
        "inspection": "orchestrator",
        "implementation": "implementer",
        "review": "reviewer",
        "repair": "repairer",
        "verify": "verifier",
        "promotion": "orchestrator",
        "completion_gate": "orchestrator",
    }
    role_ok = all(
        _role(trace, event.get("actor_id")) == expected_roles.get(event.get("kind"), "")
        for _, event in _events(trace)
        if event.get("kind") in expected_roles
    )
    handoff_targets_ok = True
    fresh_flags_ok = True
    assignments = _id_map(_list(trace.get("assignments")), "assignment_id")
    for _, event in _events(trace, "handoff"):
        target_id = event.get("to_actor_id")
        assignment_id = _payload(event).get("assignment", {}).get("id") if isinstance(_payload(event).get("assignment"), dict) else None
        assignment = assignments.get(assignment_id, {})
        handoff_targets_ok = handoff_targets_ok and target_id == assignment.get("owner_actor_id")
        fresh_flags_ok = fresh_flags_ok and _payload(event).get("fresh_session") is True
    checks = [
        ("actor_identity", bool(actors) and all(_nonempty_string(v.get("session_id")) for v in actors.values()), "every actor needs a stable session identity"),
        ("session_not_shared", all(len(owners) == 1 for owners in session_owners.values()), "one session cannot impersonate multiple actors"),
        ("writer_freshness", len(writer_sessions) >= 3 and _session(trace, impl[0][1].get("actor_id")) != _session(trace, repair[0][1].get("actor_id")) if impl and repair else False, "implementation, repair, and promotion need fresh writer sessions"),
        ("review_freshness", len(review_sessions) >= 2 and len(set(review_sessions)) == len(review_sessions) and not (set(review_sessions) & writer_sessions), "review sessions must be fresh and separate from writers"),
        ("verify_freshness", bool(verify_session) and verify_session not in writer_sessions and verify_session not in set(review_sessions), "verifier needs an independent fresh session"),
        ("role_identity", role_ok, "event actors must keep their declared roles"),
        ("handoff_identity", handoff_targets_ok and fresh_flags_ok, "handoffs must target the declared fresh-session owner"),
    ]
    return _result(CRITERIA[2][0], CRITERIA[2][1], checks)


def _grade_scope(trace: Dict[str, Any]) -> Dict[str, Any]:
    roots = trace.get("allowed_write_roots")
    assignments = _id_map(_list(trace.get("assignments")), "assignment_id")
    event_items = _list(trace.get("events"))
    call_items = _list(trace.get("tool_calls"))
    assignment_scopes_ok = all(
        isinstance(item, dict) and _check_scope(item.get("write_scope"))
        for item in _list(trace.get("assignments"))
    )
    assignment_read_scopes_ok = all(
        isinstance(item, dict) and _check_read_scope(item.get("read_scope"))
        for item in _list(trace.get("assignments"))
    )
    event_reads = [path for item in event_items if isinstance(item, dict) for path in _list(item.get("reads"))]
    call_reads = [path for item in call_items if isinstance(item, dict) for path in _list(item.get("reads"))]
    event_paths = [path for item in event_items if isinstance(item, dict) for path in _list(item.get("writes"))]
    call_paths = [path for item in call_items if isinstance(item, dict) for path in _list(item.get("writes"))]
    event_assignment_ok = True
    owner_ok = True
    for item in event_items:
        if not isinstance(item, dict) or not item.get("writes"):
            continue
        assignment = assignments.get(item.get("assignment_id"), {})
        event_assignment_ok = event_assignment_ok and bool(assignment) and all(
            any(_inside(path, scope) for scope in _list(assignment.get("write_scope")))
            for path in item.get("writes", [])
        )
        owner_ok = owner_ok and assignment.get("owner_actor_id") == item.get("actor_id")
    call_assignment_ok = True
    call_owner_ok = True
    for item in call_items:
        if not isinstance(item, dict) or not item.get("writes"):
            continue
        assignment = assignments.get(item.get("assignment_id"), {})
        call_owner_ok = call_owner_ok and assignment.get("owner_actor_id") == item.get("actor_id")
        call_assignment_ok = call_assignment_ok and bool(assignment) and all(
            any(_inside(path, scope) for scope in _list(assignment.get("write_scope")))
            for path in item.get("writes", [])
        )
    event_read_assignment_ok = True
    event_read_owner_ok = True
    for item in event_items:
        if not isinstance(item, dict) or not item.get("reads"):
            continue
        assignment = assignments.get(item.get("assignment_id"), {})
        event_read_assignment_ok = event_read_assignment_ok and bool(assignment) and all(
            any(_inside(path, scope) for scope in _list(assignment.get("read_scope")))
            for path in item.get("reads", [])
        )
        event_read_owner_ok = event_read_owner_ok and assignment.get("owner_actor_id") == item.get("actor_id")
    call_read_assignment_ok = True
    call_read_owner_ok = True
    for item in call_items:
        if not isinstance(item, dict) or not item.get("reads"):
            continue
        assignment = assignments.get(item.get("assignment_id"), {})
        call_read_assignment_ok = call_read_assignment_ok and bool(assignment) and all(
            any(_inside(path, scope) for scope in _list(assignment.get("read_scope")))
            for path in item.get("reads", [])
        )
        call_read_owner_ok = call_read_owner_ok and assignment.get("owner_actor_id") == item.get("actor_id")
    read_only_ok = all(
        not item.get("writes")
        for item in event_items + call_items
        if isinstance(item, dict) and (
            item.get("kind") in {"context_frozen", "inspection", "review", "verify"}
            or item.get("phase") in {"freeze_context", "review", "verify", "inspect"}
        )
    )
    checks = [
        ("declared_root", roots == [EXPECTED_WRITE_ROOT], "allowed_write_roots must be exactly the evals directory"),
        ("assignment_scopes", assignment_scopes_ok, "assignment scopes must remain inside the evals directory"),
        ("assignment_read_scopes", assignment_read_scopes_ok, "assignment read scopes must be normalized and remain inside context or evals roots"),
        ("event_read_paths", all(any(_inside(path, root) for root in EXPECTED_READ_ROOTS) for path in event_reads), "event reads must stay inside context or evals roots"),
        ("call_read_paths", all(any(_inside(path, root) for root in EXPECTED_READ_ROOTS) for path in call_reads), "tool-call reads must stay inside context or evals roots"),
        ("event_read_assignment", event_read_assignment_ok, "event reads must stay inside their declared assignment read scope"),
        ("call_read_assignment", call_read_assignment_ok, "tool-call reads must stay inside their declared assignment read scope"),
        ("event_read_owner", event_read_owner_ok, "event readers must own their declared assignment"),
        ("call_read_owner", call_read_owner_ok, "tool-call readers must own their declared assignment"),
        ("event_paths", all(_inside(path) for path in event_paths), "event writes must stay inside the evals directory"),
        ("call_paths", all(_inside(path) for path in call_paths), "tool-call writes must stay inside the evals directory"),
        ("event_assignment", event_assignment_ok, "event writes must stay inside their assignment scope"),
        ("call_assignment", call_assignment_ok, "tool-call writes must stay inside their assignment scope"),
        ("call_owner", call_owner_ok, "tool-call actors must own their declared assignment"),
        ("writer_owner", owner_ok, "writers may only write under their assigned scope"),
        ("read_only", read_only_ok, "context, review, verify, and inspect actions cannot write"),
        ("context_scope", all(path != CONTEXT_PATH for path in event_paths + call_paths), "frozen context cannot be written"),
    ]
    return _result(CRITERIA[3][0], CRITERIA[3][1], checks)


def _grade_handoff(trace: Dict[str, Any]) -> Dict[str, Any]:
    handoffs = _events(trace, "handoff")
    assignments = _id_map(_list(trace.get("assignments")), "assignment_id")
    evidence_ids = {
        item.get("evidence_id")
        for item in _list(trace.get("evidence"))
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    target_roles = [_role(trace, event.get("to_actor_id")) for _, event in handoffs]
    contract_values = [
        (index, event, *_handoff_contract_values(trace, index, event))
        for index, event in handoffs
    ]
    inputs = [item[2] for item in contract_values]
    outputs = [item[3] for item in contract_values]
    errors = [item[4] for item in contract_values]
    targets = [item[5] for item in contract_values]
    explicit = [item[6] for item in contract_values]
    input_schema_ok = all(
        _valid_handoff_input(trace, event, input_payload, evidence_ids)
        for (_, event, input_payload, _, _, _, _) in contract_values
    )
    output_schema_ok = all(
        _valid_handoff_output(
            trace,
            event,
            output,
            error,
            target,
            evidence_ids,
            is_explicit,
        )
        for (_, event, _, output, error, target, is_explicit) in contract_values
    )
    error_schema_ok = all(_valid_handoff_error(error, evidence_ids) for error in errors)
    stop_schema_ok = all(
        _valid_handoff_stop(input_payload.get("stop"), evidence_ids)
        for input_payload in inputs
    )
    outcome_coherence_ok = all(
        (
            _mapping(output).get("status") == "complete"
            and error is None
            and input_payload.get("stop") is None
            and not _list(_mapping(output).get("unresolved_risks"))
        )
        or (
            _mapping(output).get("status") == "needs_repair"
            and error is None
            and input_payload.get("stop") is None
            and bool(_list(_mapping(output).get("unresolved_risks")))
        )
        or (
            _mapping(output).get("status") == "blocked"
            and isinstance(error, dict)
            and _mapping(input_payload.get("stop")).get("required") is True
            and bool(_list(_mapping(output).get("unresolved_risks")))
        )
        for (_, _, input_payload, output, error, _, _) in contract_values
    )
    local_output_evidence_ok = all(
        all(
            next(
                (
                    record.get("source_id") == event.get("event_id")
                    and record.get("kind") == "handoff"
                    for record in _list(trace.get("evidence"))
                    if isinstance(record, dict)
                    and record.get("evidence_id") == evidence_id
                ),
                False,
            )
            for evidence_id in _string_ids(_mapping(output).get("evidence"), nonempty=True)
        )
        for (_, event, _, output, _, _, _) in contract_values
    )
    assignment_owner_ok = all(
        assignments.get(_mapping(input_payload.get("assignment")).get("id"), {}).get("owner_actor_id")
        == event.get("to_actor_id")
        for (_, event, input_payload, _, _, _, _) in contract_values
    )
    after_handoff_ok = all(
        target is not None and target[0] > index
        for (index, _, _, _, _, target, _) in contract_values
    )
    strict_backrefs_ok = all(
        not _strict_contract(trace)
        or (
            target is not None
            and _payload(target[1]).get("handoff_ref") == event.get("event_id")
            and sum(
                _payload(candidate).get("handoff_ref") == event.get("event_id")
                for _, candidate in _events(trace)
            ) == 1
        )
        for (_, event, _, _, _, target, _) in contract_values
    )
    input_evidence_order_ok = all(
        all(
            (position := _evidence_position(trace, evidence_id)) is not None
            and position < index
            for evidence_id in _string_ids(input_payload.get("evidence"), nonempty=True)
        )
        for index, _, input_payload, _, _, _, _ in contract_values
    )
    checks = [
        ("count", len(handoffs) >= 5, "the run needs handoffs for implementation, review, repair, verify, and final review"),
        ("orchestrator", all(_role(trace, event.get("actor_id")) == "orchestrator" for _, event in handoffs), "handoffs must be emitted by the orchestrator"),
        ("target_roles", target_roles[:5] == ["implementer", "reviewer", "repairer", "verifier", "reviewer"], "handoff targets must follow the workflow"),
        ("required_fields", all(
            (set(("context", "assignment", "state", "input", "output", "error", "stop", "evidence", "fresh_session")) <= set(_payload(event))
             and set(HANDOFF_OUTPUT_FIELDS) <= set(_mapping(_payload(event).get("output")))
             and "error" in _payload(event))
            if _strict_contract(trace)
            else set(HANDOFF_INPUT_FIELDS) <= set(_payload(event))
            for _, event in handoffs
        ), "every handoff needs the fixed input, output, and error contract"),
        ("input_schema", input_schema_ok, "handoff input must carry typed context, assignment, state, evidence, and freshness"),
        ("output_schema", output_schema_ok, "handoff output must be a typed delivery linked to its target event"),
        ("error_schema", error_schema_ok, "handoff errors must use code, message, and recoverable fields"),
        ("stop_schema", stop_schema_ok, "handoff stops must carry a typed required reason and registered evidence"),
        ("outcome_coherence", outcome_coherence_ok, "handoff output, error, and stop states must agree"),
        ("output_evidence", local_output_evidence_ok, "handoff output evidence must be sourced from that handoff"),
        ("context", all(_mapping(input_payload.get("context")).get("path") == CONTEXT_PATH and _mapping(input_payload.get("context")).get("frozen") is True for input_payload in inputs), "handoffs must carry the frozen context"),
        ("assignment", all(_mapping(input_payload.get("assignment")).get("id") in assignments for input_payload in inputs), "handoffs must name a declared assignment"),
        ("assignment_owner", assignment_owner_ok, "handoff assignment owner must equal its target actor"),
        ("state", all(isinstance(_mapping(input_payload.get("state")), dict) and _nonempty_string(_mapping(input_payload.get("state")).get("phase")) for input_payload in inputs), "handoffs must carry current state"),
        ("evidence", all(set(_string_ids(input_payload.get("evidence"), nonempty=True)) <= evidence_ids and _string_ids(input_payload.get("evidence"), nonempty=True) for input_payload in inputs), "handoffs must carry linked evidence"),
        ("evidence_order", input_evidence_order_ok, "handoff input evidence must come from an earlier observable action"),
        ("fresh", all(input_payload.get("fresh_session") is True for input_payload in inputs), "delegated sessions must be marked fresh"),
        ("target_event", after_handoff_ok, "handoff output must point to the next target action"),
        ("target_backref", strict_backrefs_ok, "target action must point back to the handoff that caused it"),
        ("after_freeze", bool(handoffs) and handoffs[0][0] > (_events(trace, "context_frozen")[0][0] if _events(trace, "context_frozen") else 10**9), "handoffs must follow context freeze"),
    ]
    return _result(CRITERIA[4][0], CRITERIA[4][1], checks)


def _grade_review(trace: Dict[str, Any]) -> Dict[str, Any]:
    reviews = _events(trace, "review")
    assignments = _id_map(_list(trace.get("assignments")), "assignment_id")
    writer_sessions = {
        _session(trace, event.get("actor_id"))
        for _, event in _events(trace)
        if event.get("kind") in {"implementation", "repair", "promotion"}
    }
    linked_ok = True
    for _, event in reviews:
        call = _linked_call(trace, event)
        linked_ok = linked_ok and bool(call) and call.get("phase") == "review" and call.get("mode") == "read_only" and not call.get("writes") and call.get("actor_id") == event.get("actor_id")
    final = reviews[-1][1] if reviews else {}
    final_index = reviews[-1][0] if reviews else -1
    verify_indices = [index for index, _ in _events(trace, "verify")]
    final_payload = _payload(final)
    checks = [
        ("two_reviews", len(reviews) >= 2, "a repair cycle needs an initial and a final review"),
        ("reviewer_role", all(_role(trace, event.get("actor_id")) == "reviewer" for _, event in reviews), "review events must be performed by reviewers"),
        ("read_set", all(_list(event.get("reads")) and not _list(event.get("writes")) for _, event in reviews), "reviewers must read evidence and write nothing"),
        ("readonly_flag", all(_payload(event).get("read_only") is True for _, event in reviews), "review must declare read_only=true"),
        ("adversarial", all(_payload(event).get("adversarial") is True for _, event in reviews), "review must declare adversarial=true"),
        ("tool_link", linked_ok, "each review must link to a read-only review tool call"),
        ("review_scope", all(_list(assignments.get(event.get("assignment_id"), {}).get("write_scope")) == [] for _, event in reviews), "review assignments must have an empty write scope"),
        ("initial_gap", bool(_gaps(reviews[0][1])) if reviews else False, "initial review must record a material gap"),
        ("final_clear", bool(verify_indices) and final_index > verify_indices[-1] and not _gaps(final) and final_payload.get("resolved") is True, "latest review must be clear after verification"),
        ("fresh_adversary", all(_session(trace, event.get("actor_id")) not in writer_sessions for _, event in reviews), "review sessions must be independent from writers"),
    ]
    return _result(CRITERIA[5][0], CRITERIA[5][1], checks)


def _source_kind_matches(record: Dict[str, Any], source: Dict[str, Any]) -> bool:
    source_kind = source.get("kind")
    if source_kind is None:
        source_kind = source.get("phase")
    return source_kind in EVIDENCE_SOURCE_KINDS.get(record.get("kind"), set())


def _source_is_causal(trace: Dict[str, Any], source_id: Any) -> bool:
    events = _event_map(trace)
    calls = _call_map(trace)
    if source_id in calls:
        return _linked_call_event(trace, calls[source_id]) is not None
    source = events.get(source_id)
    if source is None:
        return False
    if source.get("kind") in EVENT_TOOL_PHASES:
        linked = _linked_call(trace, source)
        return linked is not None and _linked_call_event(trace, linked) is not None
    return source.get("kind") in {"handoff", "completion_gate"}


def _verifier_evidence_status(
    trace: Dict[str, Any]
) -> Tuple[bool, bool, bool]:
    """Return (observable, multidimensional, per_criterion) verifier status."""

    records = {
        item.get("evidence_id"): item
        for item in _list(trace.get("evidence"))
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    verifications = _events(trace, "verify")
    if not verifications:
        return False, False, False

    verify_ids = {event.get("event_id") for _, event in verifications}
    observable_records = [
        item
        for item in records.values()
        if item.get("kind") == "verification"
        and item.get("source_id") in verify_ids
        and _source_is_causal(trace, item.get("source_id"))
    ]
    observable = bool(observable_records) and any(
        record.get("evidence_id") in _id_set(event.get("evidence"))
        for record in observable_records
        for _, event in verifications
        if record.get("source_id") == event.get("event_id")
    )
    if not _strict_contract(trace):
        # The v1 fixture has one typed verification record and gap coverage;
        # that is the compatibility projection of the stronger v2 contract.
        return observable, observable, observable

    verify = verifications[-1][1]
    verifier = _mapping(_payload(verify).get("verifier"))
    dimensions = verifier.get("dimensions")
    criteria = verifier.get("criteria")
    if not isinstance(dimensions, dict) or not isinstance(criteria, dict):
        return observable, False, False

    dimension_record_ids: List[str] = []
    dimensions_ok = True
    declared_dimensions = _declared_verifier_dimensions(trace)
    for dimension in declared_dimensions:
        entry = _mapping(dimensions.get(dimension))
        refs = _string_ids(entry.get("evidence"), nonempty=True)
        applicable = entry.get("applicable")
        expected_result = "pass" if applicable is True else "not_applicable"
        dimensions_ok = dimensions_ok and (
            set(entry) == {"id", "applicable", "result", "claim", "evidence"}
            and entry.get("id") == dimension
            and isinstance(applicable, bool)
            and (dimension not in BASE_VERIFIER_DIMENSIONS or applicable is True)
            and entry.get("result") == expected_result
            and _nonempty_string(entry.get("claim"))
            and bool(refs)
        )
        for evidence_id in refs:
            record = records.get(evidence_id, {})
            dimensions_ok = dimensions_ok and (
                record.get("kind") == "verification"
                and record.get("source_id") == verify.get("event_id")
                and record.get("dimension") == dimension
                and record.get("applicable") is applicable
                and record.get("result") == expected_result
            )
        dimension_record_ids.extend(refs)
    dimensions_ok = dimensions_ok and len(dimension_record_ids) == len(set(dimension_record_ids))

    criterion_record_ids: List[str] = []
    criteria_ok = True
    for criterion_id, _ in CRITERIA:
        entry = _mapping(criteria.get(criterion_id))
        refs = _string_ids(entry.get("evidence"), nonempty=True)
        criteria_ok = criteria_ok and (
            set(entry) == {"result", "claim", "evidence"}
            and entry.get("result") == "pass"
            and _nonempty_string(entry.get("claim"))
            and bool(refs)
        )
        for evidence_id in refs:
            record = records.get(evidence_id, {})
            criteria_ok = criteria_ok and (
                record.get("kind") == "verification"
                and record.get("source_id") == verify.get("event_id")
                and record.get("criterion_id") == criterion_id
                and record.get("result") == "pass"
            )
        criterion_record_ids.extend(refs)
    criteria_ok = criteria_ok and len(criterion_record_ids) == len(set(criterion_record_ids))
    # Keep the v2 gate explicit and deterministic: every declared item must
    # have a unique, verifier-sourced pass record with its matching label.
    dimension_refs = [ref for name in declared_dimensions for ref in _string_ids(_mapping(dimensions.get(name)).get("evidence"), nonempty=True)]
    criterion_refs = [ref for name, _ in CRITERIA for ref in _string_ids(_mapping(criteria.get(name)).get("evidence"), nonempty=True)]
    all_refs = dimension_refs + criterion_refs
    distinct_refs = len(all_refs) == len(set(all_refs))
    return (
        observable,
        dimensions_ok
        and set(dimensions) == set(declared_dimensions)
        and len(dimension_refs) == len(declared_dimensions)
        and distinct_refs,
        criteria_ok
        and set(criteria) == {name for name, _ in CRITERIA}
        and len(criterion_refs) == len(CRITERIA)
        and distinct_refs,
    )


def _event_evidence_links(trace: Dict[str, Any]) -> bool:
    """Ensure each observable event has local evidence and valid references."""

    records = {
        item.get("evidence_id"): item
        for item in _list(trace.get("evidence"))
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    ok = True
    for _, event in _events(trace):
        refs = _string_ids(event.get("evidence"), nonempty=True)
        if not refs or not set(refs) <= set(records):
            ok = False
            continue
        source_ids = {event.get("event_id")}
        linked = _linked_call(trace, event)
        if linked is not None:
            source_ids.add(linked.get("call_id"))
        if event.get("kind") == "completion_gate":
            reviews = _events(trace, "review")
            verifications = _events(trace, "verify")
            promotions = _events(trace, "promotion")
            terminal_sources = [
                reviews[-1][1] if reviews else {},
                verifications[-1][1] if verifications else {},
                promotions[-1][1] if promotions else {},
                event,
            ]
            source_ids = set()
            for source in terminal_sources:
                source_ids.add(source.get("event_id"))
                source_call = _linked_call(trace, source)
                if source_call is not None:
                    source_ids.add(source_call.get("call_id"))
        if any(records[ref].get("source_id") not in source_ids for ref in refs):
            ok = False
    return ok


def _grade_evidence(trace: Dict[str, Any]) -> Dict[str, Any]:
    records = [item for item in _list(trace.get("evidence")) if isinstance(item, dict)]
    record_map = {item.get("evidence_id"): item for item in records}
    sources = _source_map(trace)
    lifecycle = _events(trace)
    refs_ok = all(
        all(ref in record_map for ref in _list(event.get("evidence")))
        for _, event in lifecycle
        if "evidence" in event
    )
    paths_ok = True
    source_kinds_ok = True
    causal_sources_ok = True
    for record in records:
        source = sources.get(record.get("source_id"), {})
        available = set(_list(source.get("reads")) + _list(source.get("writes")))
        paths_ok = paths_ok and all(path in available for path in _list(record.get("paths")))
        source_kinds_ok = source_kinds_ok and _source_kind_matches(record, source)
        causal_sources_ok = causal_sources_ok and _source_is_causal(trace, record.get("source_id"))
    causal_links_ok, _ = _event_tool_links(trace)
    verifier_observable, verifier_dimensions, verifier_criteria = _verifier_evidence_status(trace)
    used_evidence = set()
    for event_index, event in lifecycle:
        used_evidence.update(_id_set(event.get("evidence")))
        if event.get("kind") == "handoff":
            input_payload, output, _, _, _ = _handoff_contract_values(trace, event_index, event)
            used_evidence.update(_id_set(input_payload.get("evidence")))
            used_evidence.update(_id_set(_mapping(output).get("evidence")))
        if event.get("kind") == "verify":
            verifier = _mapping(_payload(event).get("verifier"))
            for group in (verifier.get("dimensions"), verifier.get("criteria")):
                if isinstance(group, dict):
                    for entry in group.values():
                        used_evidence.update(_id_set(_mapping(entry).get("evidence")))
        if event.get("kind") == "completion_gate":
            # v1 gates already have a terminal evidence record whose source is
            # the gate itself, even though the gate payload links its three
            # decision inputs.  Preserve that representation while still
            # requiring every other registry entry to be referenced.
            used_evidence.update(
                record_id
                for record_id, record in record_map.items()
                if record.get("source_id") == event.get("event_id")
            )
    for escalation in _list(trace.get("escalations")):
        if isinstance(escalation, dict):
            used_evidence.update(_id_set(escalation.get("evidence")))
    for record in _list(trace.get("prompts")) + _list(trace.get("prompt_attempts")):
        if not isinstance(record, dict):
            continue
        used_evidence.update(_id_set(record.get("selection_evidence")))
        used_evidence.update(_id_set(record.get("evidence")))
        for gate in _mapping(record.get("quality_gates")).values():
            used_evidence.update(_id_set(_mapping(gate).get("evidence")))
        exception = _mapping(_mapping(record.get("complexity")).get("exception"))
        used_evidence.update(_id_set(exception.get("evidence")))
    for event in _list(trace.get("events")):
        if isinstance(event, dict):
            used_evidence.update(_id_set(_mapping(_payload(event).get("prompt_review")).get("evidence")))
    all_records_used = set(record_map) <= used_evidence
    required = {
        "read": any(item.get("kind") == "read" for item in records),
        "handoff": any(item.get("kind") == "handoff" for item in records),
        "diff": any(item.get("kind") == "diff" for item in records),
        "review": sum(item.get("kind") == "review" for item in records) >= 2,
        "verification": any(item.get("kind") == "verification" for item in records),
        "promotion": any(item.get("kind") == "promotion" for item in records),
        "gate": any(item.get("kind") == "gate" for item in records),
    }
    gate = _events(trace, "completion_gate")
    gate_refs = _id_set(gate[-1][1].get("evidence")) if gate else set()
    gate_kinds = {record_map[ref].get("kind") for ref in gate_refs if ref in record_map}
    checks = [
        ("registry", bool(records) and len(record_map) == len(records), "evidence registry must be non-empty and unique"),
        ("sources", all(item.get("source_id") in sources for item in records), "every evidence item needs an existing source"),
        ("claims", all(_nonempty_string(item.get("claim")) and item.get("kind") in EVIDENCE_KINDS for item in records), "evidence needs a typed claim"),
        ("event_refs", refs_ok, "actions must reference registered evidence"),
        ("paths", paths_ok, "evidence paths must be observable in the source action"),
        ("source_kinds", source_kinds_ok, "evidence kind must match the observable source action"),
        ("causal_sources", causal_sources_ok, "evidence sources must belong to the causal event/tool sequence"),
        ("causal_links", causal_links_ok, "operational events and tool calls need exact causal links"),
        ("event_observability", _event_evidence_links(trace), "every observable event needs local linked evidence"),
        ("registry_usage", all_records_used, "registered evidence cannot be orphaned"),
        ("required_kinds", all(required.values()), "read, handoff, diff, review, verification, promotion, and gate evidence are required"),
        ("gate_links", {"review", "verification", "promotion"} <= gate_kinds, "completion gate must link final review, verification, and promotion"),
        ("verifier_observable", verifier_observable, "verification must be backed by evidence sourced from the verifier event"),
        ("verifier_dimensions", verifier_dimensions, "verifier evidence must exactly cover every declared quality dimension"),
        ("verifier_criteria", verifier_criteria, "verifier evidence must cover every rubric criterion"),
    ]
    return _result(CRITERIA[6][0], CRITERIA[6][1], checks)


def _grade_repair(trace: Dict[str, Any]) -> Dict[str, Any]:
    implementations = _events(trace, "implementation")
    reviews = _events(trace, "review")
    repairs = _events(trace, "repair")
    verifications = _events(trace, "verify")
    initial = reviews[0][1] if reviews else None
    final = reviews[-1][1] if reviews else None
    repair = repairs[0][1] if repairs else None
    verify = verifications[0][1] if verifications else None
    gaps = set(_gaps(initial))
    repair_payload = _payload(repair) if repair else {}
    verify_payload = _payload(verify) if verify else {}
    verifier_observable, verifier_dimensions, verifier_criteria = _verifier_evidence_status(trace)
    order_ok = bool(implementations and reviews and repairs and verifications and reviews[-1][0] > verifications[0][0])
    checks = [
        ("implementation", bool(implementations), "implementation is required"),
        ("initial_review", bool(reviews) and bool(gaps), "initial review must expose material gaps"),
        ("repair_order", bool(repairs and reviews and repairs[0][0] > reviews[0][0]), "repair must follow the initial review"),
        ("resolves", bool(gaps) and gaps <= _id_set(repair_payload.get("resolves")), "repair must name every reviewed gap"),
        ("repair_write", bool(repair and _list(repair.get("writes"))), "repair must produce a scoped write"),
        ("verify_order", bool(verifications and repairs and verifications[0][0] > repairs[0][0]), "verification must follow repair"),
        ("rechecks", bool(gaps) and gaps <= _id_set(verify_payload.get("rechecks")), "verification must recheck every repaired gap"),
        ("verify_pass", bool(verify) and verify_payload.get("result") == "pass" and verify_payload.get("independent") is True, "verification must independently pass"),
        ("verify_readonly", bool(verify) and not _list(verify.get("writes")) and _linked_call(trace, verify) is not None, "verification must be read-only and linked to its call"),
        ("verifier_evidence", verifier_observable, "verification flags must be backed by observable verifier evidence"),
        ("verifier_dimensions", verifier_dimensions, "verification must provide evidence for every quality dimension"),
        ("verifier_criteria", verifier_criteria, "verification must provide evidence for every rubric criterion"),
        ("final_review", order_ok and not _gaps(final) and _payload(final).get("resolved") is True if final else False, "latest review must have no material gaps"),
    ]
    return _result(CRITERIA[7][0], CRITERIA[7][1], checks)


def _grade_completion(trace: Dict[str, Any]) -> Dict[str, Any]:
    gates = _events(trace, "completion_gate")
    reviews = _events(trace, "review")
    verifications = _events(trace, "verify")
    promotions = _events(trace, "promotion")
    gate = gates[-1][1] if gates else {}
    payload = _payload(gate)
    required_flags = ("context_frozen", "scope_checked", "independent_review", "latest_review_clear", "verification_passed", "promotion_reviewed", "no_unresolved_blocker")
    final_review_ok = bool(reviews) and not _gaps(reviews[-1][1]) and _payload(reviews[-1][1]).get("resolved") is True
    verify_ok = bool(verifications) and _payload(verifications[-1][1]).get("result") == "pass"
    promotion_ok = bool(promotions) and _payload(promotions[-1][1]).get("approved") is True and promotions[-1][0] > (reviews[-1][0] if reviews else 10**9)
    linked_call = _linked_call(trace, gate) if gate else None
    evidence_records = {
        item.get("evidence_id"): item
        for item in _list(trace.get("evidence"))
        if isinstance(item, dict)
    }
    decision_evidence = _id_set(payload.get("evidence"))
    decision_kinds = {
        evidence_records[reference].get("kind")
        for reference in decision_evidence
        if reference in evidence_records
    }
    checks = [
        ("one_gate", len(gates) == 1, "exactly one terminal completion gate is required"),
        ("terminal_event", bool(gates) and gates[-1][0] == len(_list(trace.get("events"))) - 1, "completion gate must be terminal"),
        ("orchestrator_readonly", bool(gate) and _role(trace, gate.get("actor_id")) == "orchestrator" and not _list(gate.get("writes")), "gate must be an orchestrator read-only decision"),
        ("tool_link", bool(linked_call) and linked_call.get("phase") == "completion_gate" and linked_call.get("mode") == "read_only", "gate must link its completion tool call"),
        ("decision", payload.get("decision") == "complete", "gate decision must be complete"),
        ("flags", all(payload.get(flag) is True for flag in required_flags), "all completion gate flags must be true"),
        ("review_clear", final_review_ok, "latest review must be clear"),
        ("verification", verify_ok, "verification must pass"),
        ("promotion", promotion_ok, "scoped promotion must follow final review"),
        ("gate_evidence", bool(gate) and bool(_list(gate.get("evidence"))), "gate must carry evidence"),
        ("decision_evidence", decision_evidence == _id_set(gate.get("evidence")) and {"review", "verification", "promotion", "gate"} <= decision_kinds, "gate payload must link final review, verification, promotion, and its gate record"),
        ("no_blocker", payload.get("no_unresolved_blocker") is True, "unresolved blockers cannot be completed"),
    ]
    return _result(CRITERIA[8][0], CRITERIA[8][1], checks)


def _grade_escalation(trace: Dict[str, Any]) -> Dict[str, Any]:
    risks = [item for item in _list(trace.get("risks")) if isinstance(item, dict) and item.get("requires_escalation") is True]
    escalations = [item for item in _list(trace.get("escalations")) if isinstance(item, dict)]
    by_risk = {item.get("risk_id"): item for item in escalations}
    evidence_ids = {item.get("evidence_id") for item in _list(trace.get("evidence")) if isinstance(item, dict)}
    matched = [by_risk.get(risk.get("risk_id")) for risk in risks]
    checks = [
        ("risk_types", all(risk.get("kind") in RISK_KINDS for risk in risks), "risky changes must use a recognized escalation kind"),
        ("all_escalated", all(item is not None for item in matched), "every scope, quality, data/effect, or blocker risk needs escalation"),
        ("decision", all(item and item.get("decision") in {"ask_user", "stop", "resolved", "approved"} for item in matched), "escalation must stop, ask, or resolve the risk"),
        ("evidence", all(item and set(_list(item.get("evidence"))) <= evidence_ids and _list(item.get("evidence")) for item in matched), "escalation decisions need evidence"),
        ("no_unresolved", not any(item and item.get("decision") == "unresolved" for item in matched), "unresolved risks cannot be silently completed"),
    ]
    return _result(CRITERIA[9][0], CRITERIA[9][1], checks)


def _prompt_error_subset(errors: Sequence[str], *terms: str) -> List[str]:
    return [error for error in errors if any(term in error for term in terms)]


def _grade_prompt_contract(trace: Dict[str, Any]) -> Dict[str, Any]:
    """Grade the observable prompt contract without judging prose semantics."""

    errors = prompt_contract.validate_prompt_catalog(trace)

    def clean(terms: Sequence[str]) -> bool:
        return not _prompt_error_subset(errors, *terms)

    checks = [
        ("declaration", clean(("prompt declaration",)), "prompt policy declaration must be v3 and canonical"),
        ("catalog", clean(("prompt record", "prompt attempt", "prompt IDs", "attempt IDs", "prompts must", "prompt_attempts must")), "prompt catalogs and exact record fields must be present"),
        ("coverage", clean(("no dispatched prompt record", "each handoff", "handoff_event_id")), "each prompted handoff must have one prompt"),
        ("causal_links", clean(("target event", "target call", "prompt actor", "target tool call", "prompt_id")), "prompt, event, call, actor, and handoff links must agree"),
        ("rendered_structure", clean(("rendered_prompt", "headings", "section", "sentinel", "hidden reasoning")), "rendered prompts must have canonical structure and trust boundaries"),
        ("modules", clean(("module",)), "module manifests must be ordered, known, and hashed"),
        ("strategy", clean(("strategy",)), "strategies and conditional details must be valid"),
        ("output_contract", clean(("output_contract_id",)), "phase output contract IDs must match"),
        ("complexity", clean(("complexity",)), "PCP arithmetic, thresholds, and exceptions must be valid"),
        ("quality_gates", clean(("quality gate",)), "all pre-dispatch quality gates must pass"),
        ("security", clean(("sensitive", "sanitization", "secret", "PII")), "prompt text must be sanitized"),
        ("attempt_lineage", clean(("attempt", "prompt_family")), "blocked attempt lineage must be bounded and linked"),
        ("review_coverage", clean(("review",)), "reviewers must cover prompts and attempts"),
        ("hash", clean(("sha256",)), "prompt hashes must match canonical text"),
        ("complete", not errors, "all prompt contract checks must pass"),
    ]
    return _result(CRITERIA[10][0], CRITERIA[10][1], checks)


def _metric_number(value: Any) -> Optional[float]:
    """Convert a numeric PCP value to a stable JSON number."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else round(number, 3)


def _percentile(values: Sequence[float], fraction: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return _metric_number(ordered[rank])


def _prompt_metrics(trace: Any) -> Dict[str, Any]:
    """Return descriptive prompt metrics; these never change the grade."""

    trace = trace if isinstance(trace, dict) else {}
    prompts = [item for item in _list(trace.get("prompts")) if isinstance(item, dict)]
    attempts = [item for item in _list(trace.get("prompt_attempts")) if isinstance(item, dict)]
    pcp_values: List[float] = []
    warning_count = 0
    exception_count = 0
    strategy_counts: Dict[str, int] = {}
    gate_failures: Dict[str, int] = {}
    chain_aggregates: Dict[str, Dict[str, Any]] = {}

    for record in prompts:
        total = _metric_number(_mapping(record.get("complexity")).get("total"))
        if total is not None:
            pcp_values.append(float(total))
            if total >= float(prompt_contract.PCP_WARNING_THRESHOLD):
                warning_count += 1
        if _mapping(record.get("complexity")).get("exception") is not None:
            exception_count += 1
        strategy = record.get("strategy")
        if isinstance(strategy, str):
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        gates = _mapping(record.get("quality_gates"))
        for gate_id, gate in gates.items():
            if isinstance(gate, dict) and gate.get("status") == "fail":
                gate_failures[gate_id] = gate_failures.get(gate_id, 0) + 1
        details = _mapping(record.get("strategy_details"))
        chain_id = details.get("chain_id")
        if strategy == "chained" and isinstance(chain_id, str) and chain_id:
            aggregate = chain_aggregates.setdefault(
                chain_id,
                {"prompt_count": 0, "pcp_total": 0, "max_pcp": None},
            )
            aggregate["prompt_count"] += 1
            if total is not None:
                aggregate["pcp_total"] = _metric_number(aggregate["pcp_total"] + total) or 0
                aggregate["max_pcp"] = (
                    total
                    if aggregate["max_pcp"] is None
                    else max(aggregate["max_pcp"], total)
                )

    repair_count = sum(
        1
        for event in _list(trace.get("events"))
        if isinstance(event, dict) and event.get("kind") == "repair"
    )
    average = _metric_number(sum(pcp_values) / len(pcp_values)) if pcp_values else None
    return {
        "prompt_count": len(prompts),
        "attempt_count": len(attempts),
        "repair_count": repair_count,
        "pcp": {
            "total": _metric_number(sum(pcp_values)) if pcp_values else 0,
            "average": average,
            "max": _metric_number(max(pcp_values)) if pcp_values else None,
            "p50": _percentile(pcp_values, 0.50),
            "p95": _percentile(pcp_values, 0.95),
            "warnings": warning_count,
            "exceptions": exception_count,
        },
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "gate_failures": dict(sorted(gate_failures.items())),
        "chain_aggregates": dict(sorted(chain_aggregates.items())),
    }


def _aggregate_prompt_metrics(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate additive report metrics without affecting expectations."""

    prompt_count = 0
    attempt_count = 0
    repair_count = 0
    pcp_total = 0.0
    pcp_values: List[float] = []
    warnings = 0
    exceptions = 0
    strategy_counts: Dict[str, int] = {}
    gate_failures: Dict[str, int] = {}
    for result in results:
        metrics = _mapping(result.get("metrics"))
        prompt_count += int(metrics.get("prompt_count", 0))
        attempt_count += int(metrics.get("attempt_count", 0))
        repair_count += int(metrics.get("repair_count", 0))
        pcp = _mapping(metrics.get("pcp"))
        warnings += int(pcp.get("warnings", 0))
        exceptions += int(pcp.get("exceptions", 0))
        maximum = pcp.get("max")
        if isinstance(maximum, (int, float)):
            pcp_values.extend(
                [float(maximum)] * int(metrics.get("prompt_count", 0))
            )
        total = pcp.get("total")
        if isinstance(total, (int, float)):
            pcp_total += float(total)
        else:
            average = pcp.get("average")
            if isinstance(average, (int, float)):
                pcp_total += float(average) * int(metrics.get("prompt_count", 0))
        for key, value in _mapping(metrics.get("strategy_counts")).items():
            if isinstance(value, int):
                strategy_counts[key] = strategy_counts.get(key, 0) + value
        for key, value in _mapping(metrics.get("gate_failures")).items():
            if isinstance(value, int):
                gate_failures[key] = gate_failures.get(key, 0) + value
    return {
        "trace_count": len(results),
        "prompt_count": prompt_count,
        "attempt_count": attempt_count,
        "repair_count": repair_count,
        "pcp_total": _metric_number(pcp_total),
        "pcp_average": _metric_number(pcp_total / prompt_count) if prompt_count else None,
        "pcp_max": _metric_number(max(pcp_values)) if pcp_values else None,
        "pcp_warnings": warnings,
        "pcp_exceptions": exceptions,
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "gate_failures": dict(sorted(gate_failures.items())),
    }


def grade_trace(trace: Dict[str, Any], source: str = "") -> Dict[str, Any]:
    errors = validate_trace(trace)
    if errors:
        criteria = [_failed_result(cid, label, "schema: " + ", ".join(errors)) for cid, label in CRITERIA]
        return {
            "trace_id": trace.get("trace_id", source) if isinstance(trace, dict) else source,
            "source": source,
            "schema_valid": False,
            "schema_errors": errors,
            "score": 0,
            "max_score": MAX_SCORE,
            "grade": "D",
            "decision": "REJECT",
            "criteria": criteria,
            "failed_criteria": [item["id"] for item in criteria],
            "metrics": _prompt_metrics(trace),
        }
    criteria = [
        _grade_context(trace),
        _grade_order(trace),
        _grade_sessions(trace),
        _grade_scope(trace),
        _grade_handoff(trace),
        _grade_review(trace),
        _grade_evidence(trace),
        _grade_repair(trace),
        _grade_completion(trace),
        _grade_escalation(trace),
        _grade_prompt_contract(trace),
    ]
    score = sum(item["earned_points"] for item in criteria)
    accepted = score == MAX_SCORE and all(item["status"] == "pass" for item in criteria)
    grade = "A" if accepted else ("B" if score >= MAX_SCORE * 0.9 else ("C" if score >= MAX_SCORE * 0.75 else "D"))
    return {
        "trace_id": trace.get("trace_id", source),
        "source": source,
        "schema_valid": True,
        "schema_errors": [],
        "score": score,
        "max_score": MAX_SCORE,
        "grade": grade,
        "decision": "ACCEPT" if accepted else "REJECT",
        "criteria": criteria,
        "failed_criteria": [item["id"] for item in criteria if item["status"] != "pass"],
        "metrics": _prompt_metrics(trace),
    }


def grade_file(path: Path) -> Dict[str, Any]:
    try:
        return grade_trace(load_trace(path), str(path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "trace_id": str(path),
            "source": str(path),
            "schema_valid": False,
            "schema_errors": [str(exc)],
            "score": 0,
            "max_score": MAX_SCORE,
            "grade": "D",
            "decision": "REJECT",
            "criteria": [_failed_result(cid, label, "load: " + str(exc)) for cid, label in CRITERIA],
            "failed_criteria": [cid for cid, _ in CRITERIA],
            "metrics": _prompt_metrics({}),
        }


def format_result(result: Dict[str, Any], expected: str = "") -> str:
    expectation = (" expected=" + expected) if expected else ""
    lines = [
        "%s | %s | score %d/%d | grade %s%s"
        % (result.get("decision"), result.get("trace_id"), result.get("score", 0), result.get("max_score", MAX_SCORE), result.get("grade", "D"), expectation),
    ]
    if not result.get("schema_valid"):
        lines.append("  schema: INVALID - " + "; ".join(result.get("schema_errors", [])))
    for criterion in result.get("criteria", []):
        lines.append("  %-20s %2d/10 %-7s %s" % (
            criterion["id"], criterion["earned_points"], criterion["status"], criterion["summary"]))
    if result.get("failed_criteria"):
        lines.append("  failed: " + ", ".join(result["failed_criteria"]))
    return "\n".join(lines)


DEFAULT_TRACES_DIR = Path(__file__).resolve().parent / "traces"
EXPECTED_DECISIONS = {"ACCEPT", "REJECT"}
CRITERION_IDS = {criterion_id for criterion_id, _ in CRITERIA}


def discover_traces(directory: Optional[Path] = None) -> List[Path]:
    """Return direct JSON trace files in deterministic name order."""

    traces_dir = Path(directory) if directory is not None else DEFAULT_TRACES_DIR
    return sorted(
        (path for path in traces_dir.glob("*.json") if path.is_file()),
        key=lambda path: path.name,
    )


def _expectation(trace: Optional[Dict[str, Any]], result: Dict[str, Any]) -> Dict[str, Any]:
    """Check optional fixture expectations without changing the actual grade."""

    trace = trace if isinstance(trace, dict) else {}
    has_decision = "expected_decision" in trace
    has_failed = "expected_failed_criteria" in trace
    expected_decision = trace.get("expected_decision")
    expected_failed = trace.get("expected_failed_criteria")
    failures: List[str] = []

    if has_decision:
        if not isinstance(expected_decision, str) or expected_decision not in EXPECTED_DECISIONS:
            failures.append("expected_decision must be ACCEPT or REJECT")
            effective_decision = None
        else:
            effective_decision = expected_decision
    elif has_failed and isinstance(expected_failed, list) and not expected_failed:
        effective_decision = "ACCEPT"
    elif has_failed and isinstance(expected_failed, list):
        effective_decision = "REJECT"
    else:
        effective_decision = "ACCEPT"

    if has_failed:
        if not isinstance(expected_failed, list):
            failures.append("expected_failed_criteria must be a list")
        elif any(not isinstance(item, str) or not item.strip() for item in expected_failed):
            failures.append("expected_failed_criteria must contain non-empty strings")
        elif len(set(expected_failed)) != len(expected_failed):
            failures.append("expected_failed_criteria must not contain duplicates")
        elif not set(expected_failed) <= CRITERION_IDS:
            failures.append("expected_failed_criteria contains an unknown criterion")
        elif set(expected_failed) != set(result.get("failed_criteria", [])):
            failures.append(
                "expected_failed_criteria does not match the actual failed criteria"
            )

    if effective_decision is not None and result.get("decision") != effective_decision:
        failures.append(
            "expected decision %s, got %s"
            % (effective_decision, result.get("decision", "REJECT"))
        )

    # An ACCEPT result is always required to be a complete max/A result.  Keep
    # this check independent from expectation metadata so expected failures
    # cannot turn a partial or inconsistent pass into a successful run.
    if result.get("decision") == "ACCEPT" and (
        result.get("score") != result.get("max_score") or result.get("grade") != "A"
    ):
        failures.append("an acceptable trace must have the maximum score and grade A")

    return {
        "expected_decision": expected_decision if has_decision else None,
        "expected_failed_criteria": expected_failed if has_failed else None,
        "effective_expected_decision": effective_decision,
        "passed": not failures,
        "failures": failures,
    }


def _grade_case(path: Path) -> Dict[str, Any]:
    """Grade one file and attach expectation status for CLI reporting."""

    trace: Optional[Dict[str, Any]] = None
    try:
        trace = load_trace(path)
        result = grade_trace(trace, str(path))
    except (OSError, ValueError, json.JSONDecodeError):
        result = grade_file(path)
    result = dict(result)
    result["expectation"] = _expectation(trace, result)
    return result


def _report_payload(traces_dir: Path, results: List[Dict[str, Any]], error: str = "") -> Dict[str, Any]:
    checks = [
        bool(results),
        not error,
        all(result.get("expectation", {}).get("passed") is True for result in results),
        all(
            result.get("decision") != "ACCEPT"
            or (result.get("score") == result.get("max_score") and result.get("grade") == "A")
        for result in results
        ),
    ]
    payload: Dict[str, Any] = {
        "ok": all(checks),
        "trace_directory": str(traces_dir),
        "count": len(results),
        "results": results,
        "metrics": _aggregate_prompt_metrics(results),
    }
    if error:
        payload["error"] = error
    return payload


def _format_report(payload: Dict[str, Any]) -> str:
    lines = [
        "TRACE DIRECTORY: %s" % payload["trace_directory"],
        "TRACES: %d" % payload["count"],
    ]
    metrics = _mapping(payload.get("metrics"))
    lines.append(
        "METRICS: prompts=%d attempts=%d pcp_avg=%s pcp_max=%s warnings=%d exceptions=%d repairs=%d"
        % (
            metrics.get("prompt_count", 0),
            metrics.get("attempt_count", 0),
            metrics.get("pcp_average"),
            metrics.get("pcp_max"),
            metrics.get("pcp_warnings", 0),
            metrics.get("pcp_exceptions", 0),
            metrics.get("repair_count", 0),
        )
    )
    if payload.get("error"):
        lines.append("ERROR: " + payload["error"])
    for result in payload.get("results", []):
        expectation = result.get("expectation", {})
        expected = expectation.get("effective_expected_decision") or ""
        lines.append(format_result(result, expected=expected))
        if expectation.get("failures"):
            lines.append("  expectation: FAIL - " + "; ".join(expectation["failures"]))
        else:
            lines.append("  expectation: PASS")
    status = "PASS" if payload.get("ok") else "FAIL"
    lines.append("SUMMARY: %s" % status)
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Grade saturation JSON traces from a directory."
    )
    parser.add_argument(
        "--traces",
        type=Path,
        metavar="DIR",
        help="directory containing *.json traces (default: evals/traces)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit the complete report as JSON",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the trace grader and return a process exit status."""

    args = _parser().parse_args(argv)
    traces_dir = args.traces if args.traces is not None else DEFAULT_TRACES_DIR
    error = ""
    results: List[Dict[str, Any]] = []

    try:
        if not traces_dir.exists():
            error = "trace directory does not exist: %s" % traces_dir
        elif not traces_dir.is_dir():
            error = "trace path is not a directory: %s" % traces_dir
        else:
            paths = discover_traces(traces_dir)
            if not paths:
                error = "no *.json traces found in: %s" % traces_dir
            else:
                results = [_grade_case(path) for path in paths]
    except OSError as exc:
        error = "cannot inspect trace directory %s: %s" % (traces_dir, exc)

    payload = _report_payload(traces_dir, results, error)
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(_format_report(payload))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
