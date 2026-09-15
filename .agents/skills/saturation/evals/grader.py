"""Evaluate ephemeral saturation observations without writing project files."""

from __future__ import annotations

import argparse
import copy
import json
import posixpath
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


CONTEXT_PATH = ".saturation/context.md"
PASS_STATUSES = frozenset({"pass", "passed", "ok", "complete", "success"})
SKIP_STATUSES = frozenset({"skip", "skipped", "not_applicable"})


class RunObserver:
    """Collect runtime events in memory for an evaluator or a diagnostic view."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, kind: str, **payload: Any) -> None:
        """Record one event without serializing or persisting it."""

        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("event kind must be a non-empty string")
        event = dict(payload)
        event["kind"] = kind
        self._events.append(event)

    def snapshot(self) -> list[dict[str, Any]]:
        """Return a detached snapshot suitable for ``evaluate_events``."""

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
    """Identify saturation files other than the one allowed context file."""

    return path == ".saturation" or path.startswith(".saturation/")


def _result(
    checks: Mapping[str, Mapping[str, Any]],
    errors: Sequence[str],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the stable evaluator result."""

    issue_list = list(errors)
    status = "pass" if not issue_list and all(
        value.get("status") == "pass" for value in checks.values()
    ) else "fail"
    return {
        "status": status,
        "checks": {key: dict(value) for key, value in checks.items()},
        "metrics": dict(metrics),
        "errors": issue_list,
    }


def evaluate_events(events: Any) -> dict[str, Any]:
    """Evaluate a runtime event sequence supplied by the in-memory hook.

    The evaluator checks only useful execution invariants: a frozen context,
    fresh sessions, disjoint scopes, style-guide use, successful checks, a
    valid final integration, and the absence of persisted saturation files.
    It never reads or writes a run directory.
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
        parsed.append(event)

    contexts = [event for event in parsed if event.get("kind") == "context_frozen"]
    context_ok = (
        len(contexts) == 1
        and _normal_path(contexts[0].get("path")) == CONTEXT_PATH
        and contexts[0].get("frozen") is True
    )
    if not context_ok:
        errors.append("exactly one frozen .saturation/context.md event is required")

    assignments = [event for event in parsed if event.get("kind") == "assignment"]
    assignment_ids: set[str] = set()
    session_ids: set[str] = set()
    write_scopes: list[tuple[str, str]] = []
    assignment_ok = bool(assignments)
    style_ok = bool(assignments)

    for index, assignment in enumerate(assignments):
        assignment_id = assignment.get("assignment_id")
        session_id = assignment.get("session_id")
        if not isinstance(assignment_id, str) or not assignment_id.strip():
            assignment_ok = False
            errors.append("assignment %d has no valid assignment_id" % index)
        elif assignment_id in assignment_ids:
            assignment_ok = False
            errors.append("assignment IDs must be unique")
        else:
            assignment_ids.add(assignment_id)

        if not isinstance(session_id, str) or not session_id.strip():
            assignment_ok = False
            errors.append("assignment %d has no valid session_id" % index)
        elif session_id in session_ids:
            assignment_ok = False
            errors.append("delegated sessions must be unique")
        else:
            session_ids.add(session_id)

        if assignment.get("fresh_session") is not True:
            assignment_ok = False
            errors.append("assignment %d must use a fresh session" % index)

        reads = _paths(assignment.get("read_scope"), allow_empty=False)
        writes = _paths(assignment.get("write_scope"), allow_empty=True)
        if reads is None:
            assignment_ok = False
            errors.append("assignment %d has an invalid read_scope" % index)
        if writes is None:
            assignment_ok = False
            errors.append("assignment %d has an invalid write_scope" % index)
        else:
            for scope in writes:
                write_scopes.append((str(assignment_id), scope))

        guides = _paths(assignment.get("style_guides"), allow_empty=False)
        if guides is None or any("code_styleguides/" not in guide for guide in guides):
            style_ok = False
            errors.append("assignment %d must name relevant code_styleguides" % index)

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
    if check_events and not any(status in PASS_STATUSES for status in check_statuses):
        verification_ok = False
        errors.append("at least one verification check must pass")
    if not check_events:
        errors.append("at least one verification check is required")

    integrations = [event for event in parsed if event.get("kind") == "integrated"]
    integration_ok = (
        len(integrations) == 1
        and isinstance(integrations[0].get("status"), str)
        and integrations[0]["status"].strip().lower() in PASS_STATUSES
    )
    if not integration_ok:
        errors.append("exactly one successful final integration is required")

    changed_paths: list[str] = []
    if len(integrations) == 1:
        integration_paths = _paths(integrations[0].get("changed_paths"), allow_empty=True)
        if integration_paths is None:
            integration_ok = False
            errors.append("integration changed_paths are invalid")
        else:
            changed_paths = integration_paths
            for path in changed_paths:
                if path == CONTEXT_PATH:
                    continue
                if not any(_contains(scope, path) for _, scope in write_scopes):
                    integration_ok = False
                    errors.append("integrated path is outside assignment scopes: %s" % path)

    durable_paths: list[str] = []
    for event in parsed:
        if event.get("kind") != "durable_path":
            continue
        path = _normal_path(event.get("path"))
        if path is None:
            errors.append("durable_path event has an invalid path")
            continue
        durable_paths.append(path)

    forbidden_durable_paths = [
        path for path in durable_paths if _internal_artifact(path) and path != CONTEXT_PATH
    ]
    artifacts_ok = not forbidden_durable_paths
    if forbidden_durable_paths:
        errors.append(
            "saturation runtime artifacts must not persist: "
            + ", ".join(forbidden_durable_paths)
        )

    checks = {
        "context_frozen": {
            "status": "pass" if context_ok else "fail",
            "detail": CONTEXT_PATH if context_ok else "missing frozen context",
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
            "detail": "relevant guides named" if style_ok else "missing guides",
        },
        "verification": {
            "status": "pass" if verification_ok else "fail",
            "detail": len(check_events),
        },
        "integration": {
            "status": "pass" if integration_ok else "fail",
            "detail": len(changed_paths),
        },
        "no_runtime_artifacts": {
            "status": "pass" if artifacts_ok else "fail",
            "detail": len(forbidden_durable_paths),
        },
    }
    metrics = {
        "events": len(parsed),
        "assignments": len(assignments),
        "sessions": len(session_ids),
        "checks": len(check_events),
        "passed_checks": sum(status in PASS_STATUSES for status in check_statuses),
        "changed_paths": len(changed_paths),
        "durable_paths": len(durable_paths),
        "forbidden_durable_paths": len(forbidden_durable_paths),
    }
    return _result(checks, errors, metrics)


def evaluate_observation(value: Any) -> dict[str, Any]:
    """Evaluate either an event list or ``{"events": [...]}`` snapshot."""

    if isinstance(value, Mapping):
        return evaluate_events(value.get("events"))
    return evaluate_events(value)


def load_observation(path: Path) -> Any:
    """Load an evaluator-owned JSON input; this function never writes files."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_result(result: Mapping[str, Any]) -> str:
    """Format a compact human-readable evaluator result."""

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
    parser = argparse.ArgumentParser(
        description="Evaluate an ephemeral saturation observation snapshot."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="JSON input owned by evals; stdin is used when omitted.",
    )
    parser.add_argument("--json", action="store_true", help="print JSON output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the evaluator CLI without creating a report artifact."""

    args = _parser().parse_args(argv)
    try:
        if args.input is not None:
            observation = load_observation(args.input)
        elif not sys.stdin.isatty():
            observation = json.load(sys.stdin)
        else:
            _parser().error("provide an input JSON path or pipe an observation on stdin")
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
