"""Validate the versioned saturation team and its ephemeral handoffs."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROLE_CONTRACTS = {
    "lead": "agents/lead.md",
    "product-domain": "agents/product-domain.md",
    "architect-data": "agents/architect-data.md",
    "implementation": "agents/implementation.md",
    "experience-fidelity": "agents/experience-fidelity.md",
    "security-privacy-ip": "agents/security-privacy-ip.md",
    "qa-harness": "agents/qa-harness.md",
    "reliability-release": "agents/reliability-release.md",
    "final-reviewer": "agents/final-reviewer.md",
}

REQUIRED_HEADINGS = (
    "## Mission",
    "## Inputs",
    "## Deliverables",
    "## Boundaries",
    "## Required checks",
    "## Escalation",
    "## Handoff",
)

MODE_MINIMUM_ROLES = {
    "full": frozenset(
        {
            "lead",
            "product-domain",
            "architect-data",
            "implementation",
            "qa-harness",
            "final-reviewer",
        }
    ),
    "hotfix": frozenset(
        {
            "lead",
            "product-domain",
            "implementation",
            "qa-harness",
            "final-reviewer",
        }
    ),
    "refactor": frozenset(
        {
            "lead",
            "architect-data",
            "implementation",
            "qa-harness",
            "reliability-release",
            "final-reviewer",
        }
    ),
}

HANDOFF_REQUIRED_FIELDS = (
    "version",
    "assignment_id",
    "agent_id",
    "status",
    "summary",
    "changed_paths",
    "checks",
    "open_items",
    "next_owner",
    "clearance",
)
HANDOFF_STATUSES = frozenset(
    {"complete", "needs_repair", "blocked", "not_applicable"}
)
CHECK_STATUSES = frozenset({"pass", "fail", "skip", "not_applicable"})
FORBIDDEN_FIELD_FRAGMENTS = (
    "chain_of_thought",
    "scratchpad",
    "private_reasoning",
    "credential",
    "secret",
    "prompt",
    "trace",
)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _safe_repo_path(value: Any) -> str | None:
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


def _validate_sequence(value: Any, field: str) -> tuple[list[Any], list[str]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return [], [f"{field} must be a sequence"]
    return list(value), []


def validate_agent_contract(path: Path, role_id: str) -> list[str]:
    """Validate one role contract without executing or modifying it."""

    errors: list[str] = []
    if not path.is_file():
        return [f"missing role contract: {path.as_posix()}"]
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path.as_posix()}: {exc}"]

    expected_title = f"# Agent contract: {role_id}"
    if not content.startswith(expected_title + "\n"):
        errors.append(f"{path.as_posix()} has the wrong contract title")
    if f"**Role ID:** `{role_id}`" not in content:
        errors.append(f"{path.as_posix()} has no matching role ID")
    for heading in REQUIRED_HEADINGS:
        if heading not in content:
            errors.append(f"{path.as_posix()} is missing {heading}")
    if "agents/handoff-contract.md" not in content:
        errors.append(f"{path.as_posix()} must reference the handoff contract")
    if "TODO" in content or "[placeholder]" in content.lower():
        errors.append(f"{path.as_posix()} contains an unresolved placeholder")
    return errors


def validate_roster(skill_dir: Path) -> list[str]:
    """Validate the fixed role library and its explicit skill wiring."""

    errors: list[str] = []
    agents_dir = skill_dir / "agents"
    if not agents_dir.is_dir():
        return [f"missing agents directory: {agents_dir.as_posix()}"]

    for role_id, relative_path in ROLE_CONTRACTS.items():
        errors.extend(
            validate_agent_contract(skill_dir / relative_path, role_id)
        )

    handoff_path = agents_dir / "handoff-contract.md"
    if not handoff_path.is_file():
        errors.append("missing agents/handoff-contract.md")
    else:
        handoff = handoff_path.read_text(encoding="utf-8")
        for heading in ("## Envelope", "## Rules", "## Validation"):
            if heading not in handoff:
                errors.append(f"handoff contract is missing {heading}")

    expected_markdown = set(ROLE_CONTRACTS.values()) | {
        "agents/handoff-contract.md"
    }
    actual_markdown = {
        path.relative_to(skill_dir).as_posix()
        for path in agents_dir.glob("*.md")
    }
    for unexpected in sorted(actual_markdown - expected_markdown):
        errors.append(f"unexpected role markdown file: {unexpected}")

    skill_path = skill_dir / "SKILL.md"
    if not skill_path.is_file():
        errors.append("missing SKILL.md")
    else:
        skill = skill_path.read_text(encoding="utf-8")
        if len(skill.splitlines()) >= 500:
            errors.append("SKILL.md must remain under 500 lines")
        required_wiring = (
            "agents/handoff-contract.md",
            "full",
            "hotfix",
            "refactor",
            "clearance",
            "fresh session",
        )
        for marker in required_wiring:
            if marker not in skill:
                errors.append(f"SKILL.md is missing roster wiring: {marker}")
        for relative_path in ROLE_CONTRACTS.values():
            if relative_path not in skill:
                errors.append(f"SKILL.md does not name {relative_path}")

    metadata_path = agents_dir / "openai.yaml"
    if not metadata_path.is_file():
        errors.append("missing agents/openai.yaml metadata")
    else:
        metadata = metadata_path.read_text(encoding="utf-8")
        for marker in (
            "interface:",
            "display_name:",
            "short_description:",
            "default_prompt:",
        ):
            if marker not in metadata:
                errors.append(f"agents/openai.yaml is missing {marker}")
        short_description = re.search(
            r'^\s*short_description:\s*"([^"]*)"\s*$',
            metadata,
            flags=re.MULTILINE,
        )
        if short_description and not 25 <= len(short_description.group(1)) <= 64:
            errors.append("short_description must be between 25 and 64 characters")
        default_prompt = re.search(
            r'^\s*default_prompt:\s*"([^"]*)"\s*$',
            metadata,
            flags=re.MULTILINE,
        )
        if default_prompt and "$saturation" not in default_prompt.group(1):
            errors.append("default_prompt must mention $saturation")
    return errors


def _contains_forbidden_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str):
                normalized = key.lower().replace("-", "_")
                if any(fragment in normalized for fragment in FORBIDDEN_FIELD_FRAGMENTS):
                    return True
            if _contains_forbidden_field(nested):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_forbidden_field(item) for item in value)
    return False


def validate_handoff(value: Any) -> list[str]:
    """Validate one in-memory handoff envelope."""

    errors: list[str] = []
    if not isinstance(value, Mapping):
        return ["handoff must be an object"]
    payload = value.get("handoff")
    if not isinstance(payload, Mapping):
        return ["handoff object is required"]
    if _contains_forbidden_field(payload):
        errors.append("handoff contains a forbidden private or sensitive field")

    for field in HANDOFF_REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"handoff is missing {field}")

    if payload.get("version") != "1":
        errors.append("handoff version must be 1")
    for field in ("assignment_id", "agent_id", "summary", "next_owner"):
        if not _nonempty_string(payload.get(field)):
            errors.append(f"handoff {field} must be a non-empty string")

    status = payload.get("status")
    if status not in HANDOFF_STATUSES:
        errors.append(f"handoff status must be one of {sorted(HANDOFF_STATUSES)}")

    changed_paths, path_errors = _validate_sequence(
        payload.get("changed_paths"), "handoff changed_paths"
    )
    errors.extend(path_errors)
    normalized_paths: list[str] = []
    for path in changed_paths:
        normalized = _safe_repo_path(path)
        if normalized is None:
            errors.append("handoff changed_paths must be repository-relative")
            continue
        if normalized == ".":
            errors.append("handoff changed_paths must name concrete paths")
            continue
        if normalized == ".saturation" or normalized.startswith(".saturation/"):
            errors.append("handoff changed_paths cannot contain saturation runtime files")
        normalized_paths.append(normalized)
    if status == "not_applicable" and normalized_paths:
        errors.append("not_applicable handoffs cannot change product paths")

    checks, check_errors = _validate_sequence(payload.get("checks"), "handoff checks")
    errors.extend(check_errors)
    if not checks:
        errors.append("handoff checks must not be empty")
    failed_check = False
    for index, check in enumerate(checks):
        if not isinstance(check, Mapping):
            errors.append(f"handoff check {index} must be an object")
            continue
        if not _nonempty_string(check.get("name")):
            errors.append(f"handoff check {index} has no name")
        check_status = check.get("status")
        if check_status not in CHECK_STATUSES:
            errors.append(f"handoff check {index} has an invalid status")
        if check_status == "fail":
            failed_check = True
        if not _nonempty_string(check.get("evidence")):
            errors.append(f"handoff check {index} needs observable evidence")

    open_items, open_errors = _validate_sequence(
        payload.get("open_items"), "handoff open_items"
    )
    errors.extend(open_errors)
    for index, item in enumerate(open_items):
        if not isinstance(item, Mapping):
            errors.append(f"handoff open item {index} must be an object")
            continue
        for field in ("item", "reason", "owner"):
            if not _nonempty_string(item.get(field)):
                errors.append(f"handoff open item {index} needs {field}")

    clearance = payload.get("clearance")
    if type(clearance) is not bool:
        errors.append("handoff clearance must be boolean")
    if status in {"needs_repair", "blocked"} and clearance is True:
        errors.append("repair or blocked handoffs cannot have clearance")
    if status in {"complete", "not_applicable"} and failed_check:
        errors.append("cleared handoffs cannot contain failed checks")
    if status in {"complete", "not_applicable"} and clearance is not True:
        errors.append("complete or accepted not_applicable handoffs need clearance")
    return errors


def validate_mode_selection(
    mode: Any,
    active_roles: Any,
    omitted_roles: Any,
) -> list[str]:
    """Ensure mode routing accounts for the complete fixed roster."""

    errors: list[str] = []
    if not isinstance(mode, str) or mode not in MODE_MINIMUM_ROLES:
        return [f"mode must be one of {sorted(MODE_MINIMUM_ROLES)}"]

    active, active_errors = _validate_sequence(active_roles, "active_roles")
    errors.extend(active_errors)
    active_values = [role for role in active if isinstance(role, str)]
    if len(active_values) != len(active) or len(set(active_values)) != len(active_values):
        errors.append("active_roles must contain unique role IDs")
    active_set = set(active_values)
    unknown_active = active_set - set(ROLE_CONTRACTS)
    if unknown_active:
        errors.append("active_roles contains unknown roles")

    if not isinstance(omitted_roles, Mapping):
        errors.append("omitted_roles must map role IDs to reasons")
        omitted: dict[str, Any] = {}
    else:
        omitted = dict(omitted_roles)
    unknown_omitted = set(omitted) - set(ROLE_CONTRACTS)
    if unknown_omitted:
        errors.append("omitted_roles contains unknown roles")
    if active_set & set(omitted):
        errors.append("a role cannot be active and omitted")

    accounted = active_set | set(omitted)
    missing = set(ROLE_CONTRACTS) - accounted
    if missing:
        errors.append("every fixed role needs an active or omitted decision")
    for role, reason in omitted.items():
        if not _nonempty_string(reason):
            errors.append(f"omitted role {role} needs a concise reason")

    missing_required = MODE_MINIMUM_ROLES[mode] - active_set
    if missing_required:
        errors.append("mode is missing required roles: " + ", ".join(sorted(missing_required)))
    return errors


def should_trip_circuit_breaker(same_failure_count: Any) -> bool:
    """Return whether the three-failure limit has been reached."""

    return type(same_failure_count) is int and same_failure_count >= 3
