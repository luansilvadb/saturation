"""Versioned, deterministic TDD contract checks for saturation traces."""

from __future__ import annotations

import copy
import hashlib
import json
import posixpath
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import prompt_contract


SCHEMA_VERSION = 4
TDD_POLICY_VERSION = "tdd-v1"
TDD_CRITERION = ("tdd_workflow", "test-first red/green workflow")
TDD_CLASSIFICATIONS = {"required", "exempt"}
TDD_EXEMPTION_KINDS = {"documentation_only", "metadata_only"}
TDD_MODES = {"initial", "repair"}
TDD_RUN_KINDS = (
    "baseline",
    "red",
    "green",
    "regression",
    "verifier_regression",
)
TDD_PHASE_FOR_RUN = {
    "baseline": "baseline",
    "red": "red",
    "green": "green",
    "regression": "regression",
    "verifier_regression": "verifier_regression",
}
TDD_EVENT_KINDS = {
    "test_first",
    "tdd_test",
    "tdd_gate",
    "tdd_trace_persisted",
}
TDD_TOOL_PHASES = {
    "baseline",
    "test_first",
    "red",
    "tdd_gate",
    "green",
    "regression",
    "verifier_regression",
    "persist_trace",
}
COMMAND_FIELDS = (
    "argv",
    "cwd",
    "timeout_seconds",
    "network",
    "side_effects",
)
RUN_FIELDS = (
    "run_id",
    "kind",
    "source_id",
    "command",
    "exit_code",
    "status",
    "discovered_test_ids",
    "failed_test_ids",
    "failure_reason",
    "evidence",
)
ARTIFACT_FIELDS = ("id", "path", "kind", "immutable_after_red")
TEST_FIELDS = ("id", "runner_id", "path")
ACCEPTANCE_FIELDS = ("acceptance_id", "test_ids")
CYCLE_FIELDS = (
    "cycle_id",
    "mode",
    "target_gap",
    "owner_actor_id",
    "test_first_actor_id",
    "test_first_handoff_id",
    "test_first_event_id",
    "gate_event_id",
    "implementation_event_id",
    "test_artifact_ids",
    "test_ids",
    "baseline_run_id",
    "red_run_id",
    "green_run_id",
    "regression_run_id",
    "acceptance_map",
    "tests_locked_after_red",
)
TDD_FIELDS = (
    "classification",
    "exemption",
    "base_revision",
    "initial_worktree",
    "commands",
    "test_artifacts",
    "test_ids",
    "acceptance_map",
    "cycles",
    "runs",
    "verifier_run_id",
    "persisted_trace",
    "redaction",
)
DECLARATION_FIELDS = (
    "policy_version",
    "required_for",
    "exemptions",
    "run_kinds",
    "command_fields",
    "run_fields",
    "artifact_fields",
    "test_fields",
    "acceptance_fields",
    "cycle_fields",
)
PERSISTED_TRACE_FIELDS = ("path", "sha256", "status", "source_id")
REDACTION_FIELDS = ("status", "secrets", "pii")
SHELL_META = re.compile(r"[;&|<>`$()\r\n]")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ids(value: Any) -> List[str]:
    values = _list(value)
    if any(not _nonempty(item) for item in values):
        return []
    return [item for item in values if isinstance(item, str)]


def _normal_path(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.replace("\\", "/")
    if not value or value.startswith("/") or (len(value) > 1 and value[1] == ":"):
        return None
    normalized = posixpath.normpath(value)
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        return None
    return normalized[2:] if normalized.startswith("./") else normalized


def _inside(path: Any, root: str) -> bool:
    normalized = _normal_path(path)
    return bool(normalized and (normalized == root or normalized.startswith(root + "/")))


def _source_maps(trace: Mapping[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    events = {
        item.get("event_id"): item
        for item in _list(trace.get("events"))
        if isinstance(item, dict) and _nonempty(item.get("event_id"))
    }
    calls = {
        item.get("call_id"): item
        for item in _list(trace.get("tool_calls"))
        if isinstance(item, dict) and _nonempty(item.get("call_id"))
    }
    return events, calls


def _source_sequence(source: Mapping[str, Any]) -> int:
    value = source.get("sequence")
    return value if isinstance(value, int) and not isinstance(value, bool) else 10**9


def _call_event(events: Mapping[str, Dict[str, Any]], call: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    event_id = call.get("event_ref")
    event = events.get(event_id) if isinstance(event_id, str) else None
    return event if isinstance(event, dict) else None


def _actor(trace: Mapping[str, Any], actor_id: Any) -> Dict[str, Any]:
    actors = trace.get("actors")
    value = actors.get(actor_id) if isinstance(actors, dict) and isinstance(actor_id, str) else None
    return value if isinstance(value, dict) else {}


def _evidence_map(trace: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        item.get("evidence_id"): item
        for item in _list(trace.get("evidence"))
        if isinstance(item, dict) and _nonempty(item.get("evidence_id"))
    }


def _expected_declaration() -> Dict[str, Any]:
    return {
        "policy_version": TDD_POLICY_VERSION,
        "required_for": ["implementation", "repair"],
        "exemptions": sorted(TDD_EXEMPTION_KINDS),
        "run_kinds": list(TDD_RUN_KINDS),
        "command_fields": list(COMMAND_FIELDS),
        "run_fields": list(RUN_FIELDS),
        "artifact_fields": list(ARTIFACT_FIELDS),
        "test_fields": list(TEST_FIELDS),
        "acceptance_fields": list(ACCEPTANCE_FIELDS),
        "cycle_fields": list(CYCLE_FIELDS),
    }


def _contract_errors(trace: Mapping[str, Any]) -> List[str]:
    contract = _mapping(trace.get("trace_contract"))
    errors: List[str] = []
    if set(contract) != {"version", "causal_links", "handoff", "verifier", "prompt", "tdd"}:
        errors.append("trace_contract must contain the fixed v4 declarations")
    if contract.get("version") != SCHEMA_VERSION:
        errors.append("trace_contract.version must be 4")
    if contract.get("causal_links") != "bidirectional":
        errors.append("trace_contract.causal_links must be bidirectional")

    handoff = _mapping(contract.get("handoff"))
    expected_handoff = {
        "input_fields": ["context", "assignment", "state", "input", "output", "error", "stop", "evidence", "fresh_session"],
        "assignment_fields": ["id", "owner_actor_id", "read_scope", "write_scope"],
        "output_fields": ["status", "event_ref", "changed_paths", "verification_evidence", "unresolved_risks", "evidence"],
        "error_fields": ["code", "message", "retryable", "escalate", "evidence"],
    }
    if handoff != expected_handoff:
        errors.append("trace_contract.handoff is not the fixed v3 handoff contract")

    verifier = _mapping(contract.get("verifier"))
    if set(verifier) != {"dimensions", "criteria"}:
        errors.append("trace_contract.verifier must contain only dimensions and criteria")
    else:
        dimensions = verifier.get("dimensions")
        optional = [
            item
            for item in ("behavior", "error_handling", "task_completion")
            if item in _ids(dimensions)
        ]
        expected_dimensions = ["completeness", "clarity", "consistency", "testability"] + optional
        if dimensions != expected_dimensions:
            errors.append("trace_contract.verifier.dimensions are not canonical")
        expected_criteria = [
            "context_freeze",
            "tool_order",
            "session_freshness",
            "write_scope",
            "handoff_payload",
            "readonly_review",
            "evidence",
            "repair_reverify",
            "completion_gates",
            "escalation",
            "prompt_contract",
            TDD_CRITERION[0],
        ]
        if verifier.get("criteria") != expected_criteria:
            errors.append("trace_contract.verifier.criteria are not canonical v4 criteria")

    if contract.get("tdd") != _expected_declaration():
        errors.append("trace_contract.tdd is not the canonical tdd-v1 declaration")
    return errors


def _declaration_valid(trace: Mapping[str, Any]) -> bool:
    return not _contract_errors(trace)


def _validate_command(command: Any, expected: Optional[Mapping[str, Any]] = None) -> bool:
    if not isinstance(command, dict) or set(command) != set(COMMAND_FIELDS):
        return False
    argv = command.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or any(not _nonempty(item) or SHELL_META.search(item) for item in argv)
    ):
        return False
    cwd = _normal_path(command.get("cwd"))
    if cwd is None and command.get("cwd") != ".":
        return False
    timeout = command.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 0 < timeout <= 3600:
        return False
    if command.get("network") is not False or command.get("side_effects") != "none":
        return False
    return expected is None or dict(command) == dict(expected)


def _valid_commands(tdd: Mapping[str, Any]) -> bool:
    commands = _mapping(tdd.get("commands"))
    return (
        set(commands) == {"target", "regression"}
        and _validate_command(commands.get("target"))
        and _validate_command(commands.get("regression"))
        and commands.get("target") != commands.get("regression")
    )


def _valid_initial_worktree(tdd: Mapping[str, Any]) -> bool:
    worktree = _mapping(tdd.get("initial_worktree"))
    return (
        set(worktree) == {"head", "status", "overlap"}
        and _nonempty(worktree.get("head"))
        and worktree.get("status") == "clean"
        and worktree.get("overlap") is False
    )


def _valid_artifacts(tdd: Mapping[str, Any], trace: Mapping[str, Any]) -> bool:
    artifacts = _list(tdd.get("test_artifacts"))
    allowed = [
        root
        for root in _list(trace.get("allowed_write_roots"))
        if isinstance(root, str) and root != ".saturation/runs"
    ]
    ids = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != set(ARTIFACT_FIELDS):
            return False
        if not _nonempty(artifact.get("id")) or artifact.get("id") in ids:
            return False
        ids.add(artifact.get("id"))
        if not _nonempty(_normal_path(artifact.get("path"))) or not any(
            _inside(artifact.get("path"), root) for root in allowed
        ):
            return False
        if not _nonempty(artifact.get("kind")) or artifact.get("immutable_after_red") is not True:
            return False
    return bool(artifacts)


def _valid_tests(tdd: Mapping[str, Any], artifact_paths: set) -> bool:
    tests = _list(tdd.get("test_ids"))
    ids = set()
    for test in tests:
        if not isinstance(test, dict) or set(test) != set(TEST_FIELDS):
            return False
        if not _nonempty(test.get("id")) or test.get("id") in ids:
            return False
        ids.add(test.get("id"))
        if not _nonempty(test.get("runner_id")) or test.get("path") not in artifact_paths:
            return False
    return bool(tests)


def _valid_acceptance_map(tdd: Mapping[str, Any], test_ids: set) -> bool:
    mapping = _list(tdd.get("acceptance_map"))
    if not mapping:
        return False
    seen = set()
    mapped_test_ids = set()
    for entry in mapping:
        if not isinstance(entry, dict) or set(entry) != set(ACCEPTANCE_FIELDS):
            return False
        acceptance_id = entry.get("acceptance_id")
        ids = _ids(entry.get("test_ids"))
        if not _nonempty(acceptance_id) or acceptance_id in seen or not ids or not set(ids) <= test_ids:
            return False
        seen.add(acceptance_id)
        mapped_test_ids.update(ids)
    return mapped_test_ids == test_ids


def _valid_exemption(trace: Mapping[str, Any], tdd: Mapping[str, Any], evidence: Mapping[str, Dict[str, Any]]) -> bool:
    classification = tdd.get("classification")
    exemption = tdd.get("exemption")
    if classification == "required":
        return exemption is None
    if classification != "exempt" or not isinstance(exemption, dict):
        return False
    if set(exemption) != {"kind", "reason", "alternative", "approved_by_actor_id", "evidence"}:
        return False
    actor = _actor(trace, exemption.get("approved_by_actor_id"))
    refs = _ids(exemption.get("evidence"))
    return (
        exemption.get("kind") in TDD_EXEMPTION_KINDS
        and _nonempty(exemption.get("reason"))
        and _nonempty(exemption.get("alternative"))
        and actor.get("role") in {"orchestrator", "user"}
        and refs
        and set(refs) <= set(evidence)
    )


def _run_map(tdd: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        run.get("run_id"): run
        for run in _list(tdd.get("runs"))
        if isinstance(run, dict) and _nonempty(run.get("run_id"))
    }


def _valid_run(
    trace: Mapping[str, Any],
    run: Any,
    commands: Mapping[str, Any],
    test_ids: set,
    evidence: Mapping[str, Dict[str, Any]],
) -> bool:
    if not isinstance(run, dict) or set(run) != set(RUN_FIELDS):
        return False
    kind = run.get("kind")
    if kind not in TDD_RUN_KINDS or not _nonempty(run.get("run_id")):
        return False
    expected_command = commands.get("target") if kind in {"red", "green"} else commands.get("regression")
    if not _validate_command(run.get("command"), expected_command):
        return False
    exit_code = run.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        return False
    discovered = _ids(run.get("discovered_test_ids"))
    failed = _ids(run.get("failed_test_ids"))
    refs = _ids(run.get("evidence"))
    if not discovered or not set(discovered) <= test_ids or not set(failed) <= set(discovered):
        return False
    if not refs or not set(refs) <= set(evidence):
        return False
    if kind == "red":
        if run.get("status") != "fail" or exit_code == 0 or not failed:
            return False
        if run.get("failure_reason") != "missing_behavior" or set(failed) != set(discovered):
            return False
    else:
        if run.get("status") != "pass" or exit_code != 0 or failed or run.get("failure_reason") is not None:
            return False
    sources, calls = _source_maps(trace)
    source = calls.get(run.get("source_id"))
    if not isinstance(source, dict) or source.get("phase") != TDD_PHASE_FOR_RUN[kind]:
        return False
    event = _call_event(sources, source)
    payload = _mapping(event.get("payload")) if isinstance(event, dict) else {}
    if (
        event is None
        or event.get("kind") != "tdd_test"
        or payload.get("run_id") != run.get("run_id")
        or payload.get("tdd_kind") != kind
        or payload.get("tool_call_ref") != source.get("call_id")
    ):
        return False
    if source.get("writes"):
        return False
    return True


def _valid_runs(
    trace: Mapping[str, Any],
    tdd: Mapping[str, Any],
    test_ids: set,
    evidence: Mapping[str, Dict[str, Any]],
) -> bool:
    runs = _list(tdd.get("runs"))
    run_ids = [run.get("run_id") for run in runs if isinstance(run, dict)]
    commands = _mapping(tdd.get("commands"))
    kinds = {
        run.get("kind")
        for run in runs
        if isinstance(run, dict)
    }
    return (
        len(runs) == len(set(run_ids))
        and set(run_ids) == set(_run_map(tdd))
        and {"baseline", "red", "green", "regression", "verifier_regression"} <= kinds
        and all(_valid_run(trace, run, commands, test_ids, evidence) for run in runs)
    )


def _cycle_map(tdd: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        cycle.get("cycle_id"): cycle
        for cycle in _list(tdd.get("cycles"))
        if isinstance(cycle, dict) and _nonempty(cycle.get("cycle_id"))
    }


def _valid_cycle_count(cycles: Mapping[str, Dict[str, Any]]) -> bool:
    values = list(cycles.values())
    return (
        bool(values)
        and sum(item.get("mode") == "initial" for item in values) == 1
        and sum(item.get("mode") == "repair" for item in values) <= 3
        and len(values) <= 4
    )


def _valid_cycle(
    trace: Mapping[str, Any],
    tdd: Mapping[str, Any],
    cycle: Any,
    runs: Mapping[str, Dict[str, Any]],
    artifacts: Mapping[str, Dict[str, Any]],
    tests: Mapping[str, Dict[str, Any]],
) -> bool:
    if not isinstance(cycle, dict) or set(cycle) != set(CYCLE_FIELDS):
        return False
    mode = cycle.get("mode")
    if mode not in TDD_MODES or not _nonempty(cycle.get("cycle_id")):
        return False
    if mode == "initial" and cycle.get("target_gap") is not None:
        return False
    if mode == "repair" and not _nonempty(cycle.get("target_gap")):
        return False
    artifact_ids = _ids(cycle.get("test_artifact_ids"))
    cycle_test_ids = _ids(cycle.get("test_ids"))
    if not artifact_ids or not set(artifact_ids) <= set(artifacts):
        return False
    if not cycle_test_ids or not set(cycle_test_ids) <= set(tests):
        return False
    if not cycle.get("tests_locked_after_red") is True:
        return False
    for run_id in ("baseline_run_id", "red_run_id", "green_run_id", "regression_run_id"):
        if cycle.get(run_id) not in runs:
            return False
    if not _valid_acceptance_map({"acceptance_map": cycle.get("acceptance_map")}, set(cycle_test_ids)):
        return False

    events, calls = _source_maps(trace)
    handoff = events.get(cycle.get("test_first_handoff_id"))
    test_first = events.get(cycle.get("test_first_event_id"))
    gate = events.get(cycle.get("gate_event_id"))
    implementation = events.get(cycle.get("implementation_event_id"))
    if not all(isinstance(item, dict) for item in (handoff, test_first, gate, implementation)):
        return False
    state = _mapping(_mapping(handoff).get("payload")).get("state")
    if (
        handoff.get("kind") != "handoff"
        or _mapping(state).get("phase") != "test_first"
        or handoff.get("to_actor_id") != cycle.get("test_first_actor_id")
        or _mapping(_mapping(_mapping(handoff).get("payload")).get("output")).get("event_ref") != test_first.get("event_id")
    ):
        return False
    if test_first.get("kind") != "test_first" or test_first.get("actor_id") != cycle.get("test_first_actor_id"):
        return False
    artifact_paths = {artifacts[item]["path"] for item in artifact_ids}
    test_first_payload = _mapping(test_first.get("payload"))
    test_first_call = calls.get(test_first_payload.get("tool_call_ref"), {})
    assignments = {
        item.get("assignment_id"): item
        for item in _list(trace.get("assignments"))
        if isinstance(item, dict) and _nonempty(item.get("assignment_id"))
    }
    test_assignment = assignments.get(test_first.get("assignment_id"), {})
    if (
        set(_list(test_first.get("writes"))) != artifact_paths
        or not isinstance(test_first_call, dict)
        or test_first_call.get("phase") != "test_first"
        or test_first_call.get("actor_id") != cycle.get("test_first_actor_id")
        or set(_list(test_first_call.get("writes"))) != artifact_paths
        or not isinstance(test_assignment, dict)
        or test_assignment.get("owner_actor_id") != cycle.get("test_first_actor_id")
        or set(_list(test_assignment.get("write_scope"))) != artifact_paths
        or test_first_payload.get("handoff_ref") != cycle.get("test_first_handoff_id")
        or test_first_payload.get("cycle_id") != cycle.get("cycle_id")
        or test_first_payload.get("red_run_id") != cycle.get("red_run_id")
        or set(_list(test_first_payload.get("test_artifact_paths"))) != artifact_paths
    ):
        return False
    gate_payload = _mapping(gate.get("payload"))
    gate_call = calls.get(gate_payload.get("tool_call_ref"), {})
    if (
        gate.get("kind") != "tdd_gate"
        or gate_payload.get("status") != "pass"
        or gate_payload.get("cycle_id") != cycle.get("cycle_id")
        or gate_payload.get("red_run_id") != cycle.get("red_run_id")
        or not isinstance(gate_call, dict)
        or gate_call.get("phase") != "tdd_gate"
        or gate_call.get("actor_id") != gate.get("actor_id")
        or gate_call.get("writes")
    ):
        return False
    expected_kind = "implementation" if mode == "initial" else "repair"
    if implementation.get("kind") != expected_kind or implementation.get("actor_id") != cycle.get("owner_actor_id"):
        return False
    if set(_list(implementation.get("writes"))) & artifact_paths:
        return False

    run_sequences = {}
    for field in ("baseline_run_id", "red_run_id", "green_run_id", "regression_run_id"):
        run_id = cycle.get(field)
        run = runs.get(run_id)
        if isinstance(run, dict) and run.get("source_id") in calls:
            run_sequences[run_id] = _source_sequence(calls[run["source_id"]])
    ordered = [
        run_sequences.get(cycle.get("baseline_run_id"), 10**9),
        _source_sequence(test_first),
        run_sequences.get(cycle.get("red_run_id"), 10**9),
        _source_sequence(gate),
        _source_sequence(implementation),
        run_sequences.get(cycle.get("green_run_id"), 10**9),
        run_sequences.get(cycle.get("regression_run_id"), 10**9),
    ]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        return False
    owner = _actor(trace, cycle.get("owner_actor_id"))
    test_owner = _actor(trace, cycle.get("test_first_actor_id"))
    if owner.get("role") != "implementer" or test_owner.get("role") != "implementer":
        return False
    if owner.get("logical_owner_id") != test_owner.get("logical_owner_id"):
        return False
    if owner.get("session_id") == test_owner.get("session_id"):
        return False
    red_sequence = run_sequences.get(cycle.get("red_run_id"))
    if red_sequence is None or not _test_paths_locked(trace, artifact_paths, red_sequence):
        return False
    return True


def _test_paths_locked(trace: Mapping[str, Any], paths: set, red_sequence: int) -> bool:
    for item in _list(trace.get("events")) + _list(trace.get("tool_calls")):
        if not isinstance(item, dict) or _source_sequence(item) <= red_sequence:
            continue
        if set(_list(item.get("writes"))) & paths:
            return False
    return True


def _valid_verifier_run(trace: Mapping[str, Any], tdd: Mapping[str, Any], runs: Mapping[str, Dict[str, Any]]) -> bool:
    run = runs.get(tdd.get("verifier_run_id"))
    if not isinstance(run, dict) or run.get("kind") != "verifier_regression":
        return False
    _, calls = _source_maps(trace)
    call = calls.get(run.get("source_id"), {})
    actor = _actor(trace, call.get("actor_id"))
    return (
        actor.get("role") == "verifier"
        and call.get("mode") == "read_only"
        and not _list(call.get("writes"))
        and run.get("status") == "pass"
    )


def _valid_persistence(trace: Mapping[str, Any], tdd: Mapping[str, Any]) -> bool:
    record = tdd.get("persisted_trace")
    if not isinstance(record, dict) or set(record) != set(PERSISTED_TRACE_FIELDS):
        return False
    if not _inside(record.get("path"), ".saturation/runs") or record.get("status") != "finalized":
        return False
    if not isinstance(record.get("sha256"), str) or not SHA256.fullmatch(record["sha256"]):
        return False
    events, calls = _source_maps(trace)
    call = calls.get(record.get("source_id"))
    event = _call_event(events, call) if isinstance(call, dict) else None
    payload = _mapping(event.get("payload")) if isinstance(event, dict) else {}
    return (
        isinstance(call, dict)
        and call.get("phase") == "persist_trace"
        and call.get("writes") == [record.get("path")]
        and isinstance(event, dict)
        and event.get("kind") == "tdd_trace_persisted"
        and payload.get("tool_call_ref") == call.get("call_id")
        and payload.get("persisted_path") == record.get("path")
        and _trace_hash(trace) == record.get("sha256")
    )


def _trace_hash(trace: Mapping[str, Any]) -> str:
    value = copy.deepcopy(dict(trace))
    persisted = _mapping(_mapping(value.get("tdd")).get("persisted_trace"))
    if persisted:
        persisted["sha256"] = ""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _valid_redaction(tdd: Mapping[str, Any]) -> bool:
    redaction = tdd.get("redaction")
    return (
        isinstance(redaction, dict)
        and set(redaction) == set(REDACTION_FIELDS)
        and redaction.get("status") == "applied"
        and redaction.get("secrets") == "redacted"
        and redaction.get("pii") == "redacted"
    )


def _valid_barrier(trace: Mapping[str, Any], cycles: Mapping[str, Dict[str, Any]], runs: Mapping[str, Dict[str, Any]]) -> bool:
    events, calls = _source_maps(trace)
    for cycle in cycles.values():
        gate = events.get(cycle.get("gate_event_id"), {})
        implementation = events.get(cycle.get("implementation_event_id"), {})
        red = runs.get(cycle.get("red_run_id"), {})
        red_call = calls.get(red.get("source_id"), {})
        if not all(isinstance(item, dict) for item in (gate, implementation, red_call)):
            return False
        if not (_source_sequence(red_call) < _source_sequence(gate) < _source_sequence(implementation)):
            return False
        gate_sequence = _source_sequence(gate)
        for item in list(events.values()) + list(calls.values()):
            if _source_sequence(red_call) < _source_sequence(item) < gate_sequence:
                if item.get("kind") in {"implementation", "repair"} or item.get("phase") in {"implement", "repair"}:
                    return False
    return bool(cycles)


def _valid_test_first_prompt(trace: Mapping[str, Any]) -> bool:
    prompts = [
        item
        for item in _list(trace.get("prompts"))
        if isinstance(item, dict) and item.get("phase") == "test_first"
    ]
    if len(prompts) != 1:
        return False
    prompt = prompts[0]
    events, calls = _source_maps(trace)
    target_event = events.get(prompt.get("target_event_id"), {})
    target_call = calls.get(prompt.get("target_call_id"), {})
    return (
        prompt.get("output_contract_id") == "test_first.v1"
        and _nonempty(prompt.get("target_event_id"))
        and _nonempty(prompt.get("target_call_id"))
        and target_event.get("kind") == "test_first"
        and target_call.get("phase") == "test_first"
    )


def validate_v4_trace(trace: Any) -> List[str]:
    """Return structural v4 errors without turning semantic TDD gaps into schema errors."""

    if not isinstance(trace, dict):
        return ["root must be an object"]
    errors: List[str] = []
    if trace.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 4")
    from grader import legacy_projection, validate_trace

    legacy_errors = validate_trace(legacy_projection(trace))
    errors.extend("legacy: " + error for error in legacy_errors)
    errors.extend(_contract_errors(trace))
    tdd = trace.get("tdd")
    if not isinstance(tdd, dict) or set(tdd) != set(TDD_FIELDS):
        errors.append("tdd must contain the exact tdd-v1 fields")
    return errors


def grade_tdd(trace: Mapping[str, Any]) -> Dict[str, Any]:
    """Grade the hard TDD workflow criterion for a v4 trace."""

    from grader import _result

    tdd = _mapping(trace.get("tdd"))
    evidence = _evidence_map(trace)
    artifacts = {
        item.get("id"): item
        for item in _list(tdd.get("test_artifacts"))
        if isinstance(item, dict) and _nonempty(item.get("id"))
    }
    tests = {
        item.get("id"): item
        for item in _list(tdd.get("test_ids"))
        if isinstance(item, dict) and _nonempty(item.get("id"))
    }
    runs = _run_map(tdd)
    cycles = _cycle_map(tdd)
    artifact_paths = {item.get("path") for item in artifacts.values()}
    prompt_errors = prompt_contract.validate_prompt_catalog(trace)
    required = tdd.get("classification") == "required"
    red_green_ok = (
        bool(cycles)
        and all(
            runs.get(cycle.get("red_run_id"), {}).get("status") == "fail"
            and runs.get(cycle.get("green_run_id"), {}).get("status") == "pass"
            for cycle in cycles.values()
        )
        if required
        else not cycles and not _list(tdd.get("runs"))
    )
    checks = [
        ("declaration", _declaration_valid(trace), "v4 trace and tdd-v1 declarations must be canonical"),
        ("classification", tdd.get("classification") in TDD_CLASSIFICATIONS, "testability must be required or an approved exemption"),
        ("baseline", _valid_initial_worktree(tdd) if required else True, "baseline must start from a clean, non-overlapping worktree"),
        ("commands", _valid_commands(tdd) if required else True, "target and regression commands must be structured and side-effect-free"),
        ("artifacts", _valid_artifacts(tdd, trace) if required else True, "test artifacts must be persisted inside the declared write roots"),
        ("test_ids", _valid_tests(tdd, artifact_paths) if required else True, "test IDs must map to persisted artifacts"),
        ("acceptance_map", _valid_acceptance_map(tdd, set(tests)) if required else True, "every behavioral acceptance criterion needs mapped tests"),
        ("exemption", _valid_exemption(trace, tdd, evidence), "exemptions must be typed, justified, and independently authorized"),
        ("runs", _valid_runs(trace, tdd, set(tests), evidence) if required else not _list(tdd.get("runs")), "test runs must have observable commands, statuses, and evidence"),
        ("retry_limit", _valid_cycle_count(cycles) if required else True, "implementation cycles allow at most three repair retries"),
        ("cycle", bool(cycles) and all(_valid_cycle(trace, tdd, cycle, runs, artifacts, tests) for cycle in cycles.values()) if required else not cycles, "each implementation cycle must link test-first, gate, implementation, and runs"),
        ("red_green", red_green_ok, "red must expose missing behavior and green must pass afterward"),
        ("barrier", _valid_barrier(trace, cycles, runs) if required else True, "test-first and implementation must be separated by the red gate"),
        ("verifier", _valid_verifier_run(trace, tdd, runs) if required else True, "verifier must independently execute the regression command"),
        ("prompt", not prompt_errors and _valid_test_first_prompt(trace) if required else not prompt_errors, "test_first.v1 prompt must be valid and linked"),
        ("persistence", _valid_persistence(trace, tdd), "the finalized trace must be persisted and hash-verifiable"),
        ("redaction", _valid_redaction(tdd), "persisted evidence must record secret and PII redaction"),
        ("verifier_criterion", _verifier_tdd_evidence(trace), "verifier evidence must explicitly cover tdd_workflow"),
    ]
    return _result(TDD_CRITERION[0], TDD_CRITERION[1], checks)


def _verifier_tdd_evidence(trace: Mapping[str, Any]) -> bool:
    events, _ = _source_maps(trace)
    verifications = [event for event in events.values() if event.get("kind") == "verify"]
    if not verifications:
        return False
    verifier = _mapping(_mapping(verifications[-1]).get("payload")).get("verifier")
    entry = _mapping(_mapping(verifier).get("criteria")).get(TDD_CRITERION[0])
    return bool(
        isinstance(entry, dict)
        and entry.get("result") == "pass"
        and _nonempty(entry.get("claim"))
        and _ids(entry.get("evidence"))
    )


def metrics(trace: Mapping[str, Any]) -> Dict[str, Any]:
    tdd = _mapping(trace.get("tdd"))
    classification = tdd.get("classification")
    if classification not in TDD_CLASSIFICATIONS:
        return {"status": "invalid"}
    cycles = _list(tdd.get("cycles"))
    runs = _list(tdd.get("runs"))
    return {
        "status": classification,
        "cycles": len(cycles),
        "initial_cycles": sum(item.get("mode") == "initial" for item in cycles if isinstance(item, dict)),
        "repair_cycles": sum(item.get("mode") == "repair" for item in cycles if isinstance(item, dict)),
        "valid_red": sum(item.get("kind") == "red" and item.get("status") == "fail" for item in runs if isinstance(item, dict)),
        "valid_green": sum(item.get("kind") == "green" and item.get("status") == "pass" for item in runs if isinstance(item, dict)),
        "waivers": int(classification == "exempt"),
        "blocked": sum(item.get("status") == "blocked" for item in runs if isinstance(item, dict)),
        "retries": max(0, len(cycles) - 1),
    }
