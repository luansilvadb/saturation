"""Deterministic, dependency-free grading for saturation workflow traces."""

from __future__ import annotations

import argparse
import json
import posixpath
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = 1
EXPECTED_WRITE_ROOT = ".agents/skills/saturation/evals"
CONTEXT_PATH = ".saturation/context.md"
EVENT_KINDS = {
    "context_frozen",
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

CRITERIA = (
    ("context_freeze", "contexto congelado antes da delegação"),
    ("tool_order", "ordem dos tool calls"),
    ("session_freshness", "identidade e frescor das sessões"),
    ("write_scope", "escopos de escrita e promoção"),
    ("handoff_payload", "payload completo de handoff"),
    ("readonly_review", "revisão independente, adversarial e read-only"),
    ("evidence", "evidências ligadas a ações observáveis"),
    ("repair_reverify", "reparo e reverificação"),
    ("completion_gates", "gates de conclusão"),
    ("escalation", "escalada de conflitos e bloqueios"),
)


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


def _source_map(trace: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result = {}
    for item in _list(trace.get("events")) + _list(trace.get("tool_calls")):
        if isinstance(item, dict):
            item_id = item.get("event_id", item.get("call_id"))
            if isinstance(item_id, str):
                result[item_id] = item
    return result


def validate_trace(trace: Any) -> List[str]:
    """Return structural errors; behavioral defects are deliberately graded below."""

    errors: List[str] = []
    if not isinstance(trace, dict):
        return ["root must be an object"]
    if trace.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
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
        if assignment.get("owner_actor_id") not in actors if isinstance(actors, dict) else True:
            errors.append("assignment has unknown owner_actor_id")
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
        if event.get("kind") not in EVENT_KINDS:
            errors.append("event %s has unknown kind" % event_id)
        if event.get("actor_id") not in actors if isinstance(actors, dict) else True:
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
        if call.get("phase") not in TOOL_PHASES:
            errors.append("tool call %s has unknown phase" % call_id)
        if call.get("actor_id") not in actors if isinstance(actors, dict) else True:
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
            evidence_ids.add(record_id)
            if not _nonempty_string(record.get("source_id")):
                errors.append("evidence %s has no source_id" % record_id)
            if record.get("kind") not in EVIDENCE_KINDS:
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
    for _, call in _tools(trace):
        if call.get("call_id") == call_id:
            return call
    return None


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
        ("starts_freeze", bool(freeze) and freeze[0] == 0, "tool calls must start with freeze_context"),
        ("inspect_after_freeze", bool(inspect) and first(inspect) > first(freeze), "inspect must follow freeze_context"),
        ("implement_after_inspect", bool(implement) and first(implement) > first(inspect), "implement must follow inspect"),
        ("review_after_implement", bool(reviews) and first(reviews) > first(implement), "initial review must follow implementation"),
        ("repair_after_review", bool(repair) and first(repair) > first(reviews), "repair must follow the initial review"),
        ("verify_after_repair", bool(verify) and first(verify) > first(repair), "verify must follow repair"),
        ("final_review_after_verify", len(reviews) >= 2 and last(reviews) > first(verify), "final review must follow verify"),
        ("promote_after_final_review", bool(promote) and first(promote) > last(reviews), "promotion must follow final review"),
        ("promotion_last", bool(promote) and promote[-1] == len(calls) - 1, "promotion must be the final tool call"),
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
    for item in call_items:
        if not isinstance(item, dict) or not item.get("writes"):
            continue
        assignment = assignments.get(item.get("assignment_id"), {})
        call_assignment_ok = call_assignment_ok and bool(assignment) and all(
            any(_inside(path, scope) for scope in _list(assignment.get("write_scope")))
            for path in item.get("writes", [])
        )
    read_only_ok = all(
        not item.get("writes")
        for item in event_items + call_items
        if isinstance(item, dict) and (
            item.get("kind") in {"context_frozen", "review", "verify"}
            or item.get("phase") in {"freeze_context", "review", "verify", "inspect"}
        )
    )
    checks = [
        ("declared_root", roots == [EXPECTED_WRITE_ROOT], "allowed_write_roots must be exactly the evals directory"),
        ("assignment_scopes", assignment_scopes_ok, "assignment scopes must remain inside the evals directory"),
        ("event_paths", all(_inside(path) for path in event_paths), "event writes must stay inside the evals directory"),
        ("call_paths", all(_inside(path) for path in call_paths), "tool-call writes must stay inside the evals directory"),
        ("event_assignment", event_assignment_ok, "event writes must stay inside their assignment scope"),
        ("call_assignment", call_assignment_ok, "tool-call writes must stay inside their assignment scope"),
        ("writer_owner", owner_ok, "writers may only write under their assigned scope"),
        ("read_only", read_only_ok, "context, review, verify, and inspect actions cannot write"),
        ("context_scope", all(path != CONTEXT_PATH for path in event_paths + call_paths), "frozen context cannot be written"),
    ]
    return _result(CRITERIA[3][0], CRITERIA[3][1], checks)


def _grade_handoff(trace: Dict[str, Any]) -> Dict[str, Any]:
    handoffs = _events(trace, "handoff")
    assignments = _id_map(_list(trace.get("assignments")), "assignment_id")
    evidence_ids = {item.get("evidence_id") for item in _list(trace.get("evidence")) if isinstance(item, dict)}
    target_roles = [_role(trace, event.get("to_actor_id")) for _, event in handoffs]
    checks = [
        ("count", len(handoffs) >= 5, "the run needs handoffs for implementation, review, repair, verify, and final review"),
        ("orchestrator", all(_role(trace, event.get("actor_id")) == "orchestrator" for _, event in handoffs), "handoffs must be emitted by the orchestrator"),
        ("target_roles", target_roles[:5] == ["implementer", "reviewer", "repairer", "verifier", "reviewer"], "handoff targets must follow the workflow"),
        ("required_fields", all(set(("context", "assignment", "state", "evidence", "fresh_session")) <= set(_payload(event)) for _, event in handoffs), "every handoff needs context, assignment, state, evidence, and freshness"),
        ("context", all((_payload(event).get("context", {}) or {}).get("path") == CONTEXT_PATH and (_payload(event).get("context", {}) or {}).get("frozen") is True for _, event in handoffs), "handoffs must carry the frozen context"),
        ("assignment", all(((_payload(event).get("assignment", {}) or {}).get("id") in assignments) for _, event in handoffs), "handoffs must name a declared assignment"),
        ("state", all(isinstance(_payload(event).get("state"), dict) and _nonempty_string(_payload(event).get("state", {}).get("phase")) for _, event in handoffs), "handoffs must carry current state"),
        ("evidence", all(set(_list(_payload(event).get("evidence"))) <= evidence_ids and _list(_payload(event).get("evidence")) for _, event in handoffs), "handoffs must carry linked evidence"),
        ("fresh", all(_payload(event).get("fresh_session") is True for _, event in handoffs), "delegated sessions must be marked fresh"),
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
    for record in records:
        source = sources.get(record.get("source_id"), {})
        available = set(_list(source.get("reads")) + _list(source.get("writes")))
        paths_ok = paths_ok and all(path in available for path in _list(record.get("paths")))
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
    gate_refs = set(_list(gate[-1][1].get("evidence"))) if gate else set()
    gate_kinds = {record_map[ref].get("kind") for ref in gate_refs if ref in record_map}
    checks = [
        ("registry", bool(records) and len(record_map) == len(records), "evidence registry must be non-empty and unique"),
        ("sources", all(item.get("source_id") in sources for item in records), "every evidence item needs an existing source"),
        ("claims", all(_nonempty_string(item.get("claim")) and item.get("kind") in EVIDENCE_KINDS for item in records), "evidence needs a typed claim"),
        ("event_refs", refs_ok, "actions must reference registered evidence"),
        ("paths", paths_ok, "evidence paths must be observable in the source action"),
        ("required_kinds", all(required.values()), "read, handoff, diff, review, verification, promotion, and gate evidence are required"),
        ("gate_links", {"review", "verification", "promotion"} <= gate_kinds, "completion gate must link final review, verification, and promotion"),
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
    order_ok = bool(implementations and reviews and repairs and verifications and reviews[-1][0] > verifications[0][0])
    checks = [
        ("implementation", bool(implementations), "implementation is required"),
        ("initial_review", bool(reviews) and bool(gaps), "initial review must expose material gaps"),
        ("repair_order", bool(repairs and reviews and repairs[0][0] > reviews[0][0]), "repair must follow the initial review"),
        ("resolves", bool(gaps) and gaps <= set(_list(repair_payload.get("resolves"))), "repair must name every reviewed gap"),
        ("repair_write", bool(repair and _list(repair.get("writes"))), "repair must produce a scoped write"),
        ("verify_order", bool(verifications and repairs and verifications[0][0] > repairs[0][0]), "verification must follow repair"),
        ("rechecks", bool(gaps) and gaps <= set(_list(verify_payload.get("rechecks"))), "verification must recheck every repaired gap"),
        ("verify_pass", bool(verify) and verify_payload.get("result") == "pass" and verify_payload.get("independent") is True, "verification must independently pass"),
        ("verify_readonly", bool(verify) and not _list(verify.get("writes")) and _linked_call(trace, verify) is not None, "verification must be read-only and linked to its call"),
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
    checks = [
        ("one_gate", len(gates) == 1, "exactly one terminal completion gate is required"),
        ("terminal_event", bool(gates) and gates[-1][0] == len(_list(trace.get("events"))) - 1, "completion gate must be terminal"),
        ("orchestrator_readonly", bool(gate) and _role(trace, gate.get("actor_id")) == "orchestrator" and not _list(gate.get("writes")), "gate must be an orchestrator read-only decision"),
        ("decision", payload.get("decision") == "complete", "gate decision must be complete"),
        ("flags", all(payload.get(flag) is True for flag in required_flags), "all completion gate flags must be true"),
        ("review_clear", final_review_ok, "latest review must be clear"),
        ("verification", verify_ok, "verification must pass"),
        ("promotion", promotion_ok, "scoped promotion must follow final review"),
        ("gate_evidence", bool(gate) and bool(_list(gate.get("evidence"))), "gate must carry evidence"),
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
            "max_score": 100,
            "grade": "D",
            "decision": "REJECT",
            "criteria": criteria,
            "failed_criteria": [item["id"] for item in criteria],
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
    ]
    score = sum(item["earned_points"] for item in criteria)
    accepted = score == 100 and all(item["status"] == "pass" for item in criteria)
    grade = "A" if accepted else ("B" if score >= 90 else ("C" if score >= 75 else "D"))
    return {
        "trace_id": trace.get("trace_id", source),
        "source": source,
        "schema_valid": True,
        "schema_errors": [],
        "score": score,
        "max_score": 100,
        "grade": grade,
        "decision": "ACCEPT" if accepted else "REJECT",
        "criteria": criteria,
        "failed_criteria": [item["id"] for item in criteria if item["status"] != "pass"],
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
            "max_score": 100,
            "grade": "D",
            "decision": "REJECT",
            "criteria": [_failed_result(cid, label, "load: " + str(exc)) for cid, label in CRITERIA],
            "failed_criteria": [cid for cid, _ in CRITERIA],
        }


def format_result(result: Dict[str, Any], expected: str = "") -> str:
    expectation = (" expected=" + expected) if expected else ""
    lines = [
        "%s | %s | score %d/%d | grade %s%s"
        % (result.get("decision"), result.get("trace_id"), result.get("score", 0), result.get("max_score", 100), result.get("grade", "D"), expectation),
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

    # An ACCEPT result is always required to be a complete 100/A result.  Keep
    # this check independent from expectation metadata so expected failures
    # cannot turn a partial or inconsistent pass into a successful run.
    if result.get("decision") == "ACCEPT" and (
        result.get("score") != 100 or result.get("grade") != "A"
    ):
        failures.append("an acceptable trace must have score 100 and grade A")

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
            or (result.get("score") == 100 and result.get("grade") == "A")
            for result in results
        ),
    ]
    payload: Dict[str, Any] = {
        "ok": all(checks),
        "trace_directory": str(traces_dir),
        "count": len(results),
        "results": results,
    }
    if error:
        payload["error"] = error
    return payload


def _format_report(payload: Dict[str, Any]) -> str:
    lines = [
        "TRACE DIRECTORY: %s" % payload["trace_directory"],
        "TRACES: %d" % payload["count"],
    ]
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
