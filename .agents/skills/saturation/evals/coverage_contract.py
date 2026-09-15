"""Versioned, language-agnostic coverage checks for saturation traces."""

from __future__ import annotations

import math
import posixpath
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = 5
COVERAGE_POLICY_VERSION = "coverage-v1"
COVERAGE_CRITERION = ("coverage_workflow", "instrumented line and branch coverage")
COVERAGE_METRICS = ("line", "branch")
MINIMUM_THRESHOLDS = {"line": 80.0, "branch": 80.0}

COVERAGE_FIELDS = (
    "policy_version",
    "required_for",
    "metrics",
    "thresholds",
    "adapter",
    "source_paths",
    "command",
    "report",
    "target_run",
    "verifier_run",
)
ADAPTER_FIELDS = ("id", "language", "tool", "version")
REPORT_FIELDS = ("path", "format", "immutable_after_run")
RUN_FIELDS = ("run_id", "source_id", "status", "metrics", "evidence")
COMMAND_FIELDS = (
    "argv",
    "cwd",
    "timeout_seconds",
    "network",
    "side_effects",
)
SHELL_META = re.compile(r"[;&|<>`$()\r\n]")


def expected_declaration() -> Dict[str, Any]:
    """Return the canonical trace_contract.coverage declaration."""

    return {
        "policy_version": COVERAGE_POLICY_VERSION,
        "required_for": ["implementation", "repair"],
        "metrics": list(COVERAGE_METRICS),
        "minimum_thresholds": dict(MINIMUM_THRESHOLDS),
        "adapter_fields": list(ADAPTER_FIELDS),
        "report_fields": list(REPORT_FIELDS),
        "run_fields": list(RUN_FIELDS),
        "command_fields": list(COMMAND_FIELDS),
    }


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


def _normal_root(value: Any) -> Optional[str]:
    if value == ".":
        return "."
    return _normal_path(value)


def _inside(path: Any, root: Any) -> bool:
    normalized = _normal_path(path)
    normalized_root = _normal_root(root)
    if not normalized or not normalized_root:
        return False
    return normalized_root == "." or normalized == normalized_root or normalized.startswith(normalized_root + "/")


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


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


def _call_event(events: Mapping[str, Dict[str, Any]], call: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    event_id = call.get("event_ref")
    event = events.get(event_id) if isinstance(event_id, str) else None
    return event if isinstance(event, dict) else None


def _source_sequence(source: Mapping[str, Any]) -> int:
    value = source.get("sequence")
    return value if isinstance(value, int) and not isinstance(value, bool) else 10**9


def _evidence_map(trace: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        item.get("evidence_id"): item
        for item in _list(trace.get("evidence"))
        if isinstance(item, dict) and _nonempty(item.get("evidence_id"))
    }


def _valid_command(command: Any) -> bool:
    if not isinstance(command, dict) or set(command) != set(COMMAND_FIELDS):
        return False
    argv = command.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or any(not _nonempty(item) or SHELL_META.search(item) for item in argv)
    ):
        return False
    cwd = command.get("cwd")
    if cwd != "." and _normal_path(cwd) is None:
        return False
    timeout = command.get("timeout_seconds")
    return (
        isinstance(timeout, int)
        and not isinstance(timeout, bool)
        and 0 < timeout <= 3600
        and command.get("network") is False
        and command.get("side_effects") == "none"
    )


def _valid_metrics(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(COVERAGE_METRICS)
        and all(_number(value.get(metric)) is not None and 0 <= value[metric] <= 100 for metric in COVERAGE_METRICS)
    )


def _valid_thresholds(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(COVERAGE_METRICS)
        and all(
            _number(value.get(metric)) is not None
            and MINIMUM_THRESHOLDS[metric] <= value[metric] <= 100
            for metric in COVERAGE_METRICS
        )
    )


def _allowed_report_path(trace: Mapping[str, Any], path: Any) -> bool:
    roots = [
        root
        for root in _list(trace.get("allowed_write_roots"))
        if isinstance(root, str) and root != ".saturation/runs"
    ]
    return bool(_normal_path(path) and any(_inside(path, root) for root in roots))


def _valid_executable_policy(trace: Mapping[str, Any], coverage: Mapping[str, Any]) -> bool:
    if (
        coverage.get("policy_version") != COVERAGE_POLICY_VERSION
        or coverage.get("required_for") != ["implementation", "repair"]
        or coverage.get("metrics") != list(COVERAGE_METRICS)
        or not _valid_thresholds(coverage.get("thresholds"))
        or not _valid_command(coverage.get("command"))
    ):
        return False

    adapter = coverage.get("adapter")
    if not isinstance(adapter, dict) or set(adapter) != set(ADAPTER_FIELDS):
        return False
    if any(not _nonempty(adapter.get(field)) for field in ADAPTER_FIELDS):
        return False

    source_paths = _list(coverage.get("source_paths"))
    if not source_paths or len(set(source_paths)) != len(source_paths):
        return False
    if any(_normal_path(path) is None for path in source_paths):
        return False

    report = coverage.get("report")
    if (
        not isinstance(report, dict)
        or set(report) != set(REPORT_FIELDS)
        or not _allowed_report_path(trace, report.get("path"))
        or not _nonempty(report.get("format"))
        or report.get("immutable_after_run") is not True
    ):
        return False

    return True


def _tdd_runs(trace: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    runs = {
        run.get("run_id"): run
        for run in _list(_mapping(trace.get("tdd")).get("runs"))
        if isinstance(run, dict) and _nonempty(run.get("run_id"))
    }
    target = next((run for run in runs.values() if run.get("kind") == "regression"), {})
    verifier = next((run for run in runs.values() if run.get("kind") == "verifier_regression"), {})
    return target, verifier


def _valid_coverage_run(
    trace: Mapping[str, Any],
    run: Any,
    expected_tdd_run: Mapping[str, Any],
    kind: str,
    report_path: str,
    source_paths: Sequence[str],
    thresholds: Mapping[str, Any],
    evidence: Mapping[str, Dict[str, Any]],
) -> bool:
    if not isinstance(run, dict) or set(run) != set(RUN_FIELDS):
        return False
    if (
        run.get("run_id") != expected_tdd_run.get("run_id")
        or run.get("source_id") != expected_tdd_run.get("source_id")
        or run.get("status") != "pass"
        or not _valid_metrics(run.get("metrics"))
        or not _ids(run.get("evidence"))
        or not set(_ids(run.get("evidence"))) <= set(evidence)
    ):
        return False
    if any(run["metrics"][metric] < thresholds[metric] for metric in COVERAGE_METRICS):
        return False

    events, calls = _source_maps(trace)
    source = calls.get(run.get("source_id"))
    event = _call_event(events, source) if isinstance(source, dict) else None
    if not isinstance(source, dict) or not isinstance(event, dict):
        return False
    expected_phase = "regression" if kind == "target" else "verifier_regression"
    expected_mode = "coverage" if kind == "target" else "read_only"
    if (
        source.get("phase") != expected_phase
        or source.get("mode") != expected_mode
        or event.get("kind") != "tdd_test"
        or event.get("reads") != source.get("reads")
        or event.get("writes") != source.get("writes")
    ):
        return False
    payload = _mapping(event.get("payload"))
    if (
        payload.get("run_id") != expected_tdd_run.get("run_id")
        or payload.get("tdd_kind") != expected_tdd_run.get("kind")
        or payload.get("tool_call_ref") != source.get("call_id")
    ):
        return False

    normalized_sources = {_normal_path(path) for path in source_paths}
    if not normalized_sources <= {_normal_path(path) for path in _list(source.get("reads"))}:
        return False
    normalized_report = _normal_path(report_path)
    if kind == "target":
        if source.get("writes") != [report_path]:
            return False
    elif source.get("writes"):
        return False
    if kind == "verifier" and normalized_report not in {
        _normal_path(path) for path in _list(source.get("reads"))
    }:
        return False
    if kind == "target" and not normalized_report:
        return False
    return True


def _valid_evidence_paths(
    trace: Mapping[str, Any],
    run: Mapping[str, Any],
    report_path: str,
    source_paths: Sequence[str],
) -> bool:
    records = _evidence_map(trace)
    expected_paths = {_normal_path(report_path)} | {_normal_path(path) for path in source_paths}
    for evidence_id in _ids(run.get("evidence")):
        record = records.get(evidence_id)
        if not isinstance(record, dict) or record.get("source_id") != run.get("source_id"):
            return False
        if record.get("kind") not in {"test", "verification"}:
            return False
        if not expected_paths <= {_normal_path(path) for path in _list(record.get("paths"))}:
            return False
    return True


def _valid_coverage(trace: Mapping[str, Any]) -> bool:
    coverage = trace.get("coverage")
    tdd = _mapping(trace.get("tdd"))
    if tdd.get("classification") == "exempt":
        return coverage is None
    if tdd.get("classification") != "required" or not isinstance(coverage, dict):
        return False
    if not _valid_executable_policy(trace, coverage):
        return False

    target_tdd, verifier_tdd = _tdd_runs(trace)
    target = _mapping(coverage.get("target_run"))
    verifier = _mapping(coverage.get("verifier_run"))
    report_path = coverage["report"]["path"]
    source_paths = coverage["source_paths"]
    thresholds = coverage["thresholds"]
    evidence = _evidence_map(trace)
    return (
        _valid_coverage_run(trace, target, target_tdd, "target", report_path, source_paths, thresholds, evidence)
        and _valid_coverage_run(trace, verifier, verifier_tdd, "verifier", report_path, source_paths, thresholds, evidence)
        and _valid_evidence_paths(trace, target, report_path, source_paths)
        and _valid_evidence_paths(trace, verifier, report_path, source_paths)
        and _source_sequence(_source_maps(trace)[1].get(target.get("source_id"), {}))
        < _source_sequence(_source_maps(trace)[1].get(verifier.get("source_id"), {}))
    )


def validate_v5_trace(trace: Any) -> List[str]:
    """Return structural v5 errors; coverage behavior is graded separately."""

    if not isinstance(trace, dict):
        return ["root must be an object"]

    from tdd_contract import validate_tdd_trace

    errors = validate_tdd_trace(
        trace,
        schema_version=SCHEMA_VERSION,
        contract_extensions={"coverage": expected_declaration()},
        extra_criteria=[COVERAGE_CRITERION[0]],
    )
    if "coverage" not in trace:
        errors.append("coverage must be present in schema v5")
    elif trace.get("coverage") is not None:
        coverage = trace.get("coverage")
        if not isinstance(coverage, dict) or set(coverage) != set(COVERAGE_FIELDS):
            errors.append("coverage must contain the exact coverage-v1 fields")
    elif _mapping(trace.get("tdd")).get("classification") != "exempt":
        errors.append("coverage may be null only for an approved exemption")
    return errors


def _verifier_criterion_evidence(trace: Mapping[str, Any]) -> bool:
    verifications = [
        event
        for event in _list(trace.get("events"))
        if isinstance(event, dict) and event.get("kind") == "verify"
    ]
    if not verifications:
        return False
    verifier = _mapping(_mapping(verifications[-1].get("payload")).get("verifier"))
    entry = _mapping(verifier.get("criteria")).get(COVERAGE_CRITERION[0])
    return bool(
        isinstance(entry, dict)
        and entry.get("result") == "pass"
        and _nonempty(entry.get("claim"))
        and _ids(entry.get("evidence"))
    )


def grade_coverage(trace: Mapping[str, Any]) -> Dict[str, Any]:
    """Grade the required instrumented coverage workflow for schema v5."""

    from grader import _result

    coverage = trace.get("coverage")
    tdd = _mapping(trace.get("tdd"))
    exempt = tdd.get("classification") == "exempt"
    checks = [
        (
            "declaration",
            _mapping(trace.get("trace_contract")).get("coverage") == expected_declaration(),
            "coverage-v1 declaration must be canonical",
        ),
        (
            "classification",
            exempt or tdd.get("classification") == "required",
            "coverage is required for implementation and repair work",
        ),
        (
            "policy",
            exempt or (isinstance(coverage, dict) and _valid_executable_policy(trace, coverage)),
            "coverage policy must require line and branch metrics with a valid adapter",
        ),
        (
            "thresholds",
            exempt or (
                isinstance(coverage, dict)
                and _valid_thresholds(coverage.get("thresholds"))
                and all(coverage["thresholds"][metric] >= MINIMUM_THRESHOLDS[metric] for metric in COVERAGE_METRICS)
            ),
            "line and branch thresholds must meet the minimum policy",
        ),
        (
            "command",
            exempt or (
                isinstance(coverage, dict)
                and _valid_command(coverage.get("command"))
                and coverage.get("command") == _mapping(_mapping(trace.get("tdd")).get("commands")).get("regression")
            ),
            "coverage must use the declared instrumented regression command",
        ),
        (
            "source_paths",
            exempt or (isinstance(coverage, dict) and bool(_list(coverage.get("source_paths")))),
            "coverage must name executable source paths",
        ),
        (
            "report",
            exempt or (
                isinstance(coverage, dict)
                and isinstance(coverage.get("report"), dict)
                and _allowed_report_path(trace, _mapping(coverage.get("report")).get("path"))
                and _mapping(coverage.get("report")).get("immutable_after_run") is True
            ),
            "a persisted immutable coverage report is required",
        ),
        (
            "target_run",
            exempt or _valid_coverage(trace),
            "the implementation must generate passing instrumented coverage",
        ),
        (
            "verifier_run",
            exempt or _valid_coverage(trace),
            "the verifier must independently validate passing coverage",
        ),
        (
            "verifier_criterion",
            _verifier_criterion_evidence(trace),
            "verifier evidence must explicitly cover coverage_workflow",
        ),
    ]
    return _result(COVERAGE_CRITERION[0], COVERAGE_CRITERION[1], checks)


def metrics(trace: Mapping[str, Any]) -> Dict[str, Any]:
    coverage = trace.get("coverage")
    tdd = _mapping(trace.get("tdd"))
    if tdd.get("classification") == "exempt":
        return {"status": "exempt", "reports": 0}
    if not isinstance(coverage, dict):
        return {"status": "invalid", "reports": 0}
    target = _mapping(coverage.get("target_run"))
    verifier = _mapping(coverage.get("verifier_run"))
    return {
        "status": "required" if _valid_coverage(trace) else "invalid",
        "adapter": _mapping(coverage.get("adapter")).get("id"),
        "language": _mapping(coverage.get("adapter")).get("language"),
        "line": target.get("metrics", {}).get("line"),
        "branch": target.get("metrics", {}).get("branch"),
        "verifier_line": verifier.get("metrics", {}).get("line"),
        "verifier_branch": verifier.get("metrics", {}).get("branch"),
        "line_threshold": _mapping(coverage.get("thresholds")).get("line"),
        "branch_threshold": _mapping(coverage.get("thresholds")).get("branch"),
        "reports": int(isinstance(coverage.get("report"), dict)),
    }
