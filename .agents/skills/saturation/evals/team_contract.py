"""Validate the versioned saturation team and its canonical handoffs."""

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

LEAD_ROLE = "lead"

REQUIRED_HEADINGS = (
    "## Mission",
    "## Inputs",
    "## Deliverables",
    "## Boundaries",
    "## Required checks",
    "## Escalation",
    "## Handoff",
)

# The lead is the main session and is therefore not an assignment in any
# mode. The roster still contains the lead so every role has a contract.
MODE_MINIMUM_ROLES = {
    "full": frozenset(
        {
            "product-domain",
            "architect-data",
            "implementation",
            "qa-harness",
            "final-reviewer",
        }
    ),
    "hotfix": frozenset(
        {
            "product-domain",
            "implementation",
            "qa-harness",
            "final-reviewer",
        }
    ),
    "refactor": frozenset(
        {
            "architect-data",
            "implementation",
            "qa-harness",
            "reliability-release",
            "final-reviewer",
        }
    ),
}

ACTIVATION_STATUSES = frozenset(
    {"active", "implicit", "not_applicable"}
)
HANDOFF_REQUIRED_FIELDS = (
    "version",
    "cycle_id",
    "assignment_id",
    "agent_id",
    "status",
    "summary",
    "changed_paths",
    "checks",
    "open_items",
)
HANDOFF_OPTIONAL_FIELDS = (
    "next_owner",
    "clearance",
    "evidence_id",
    "evidence_ids",
    "phase_packet_id",
    "phase_packet_ids",
)
HANDOFF_ALLOWED_FIELDS = frozenset(
    HANDOFF_REQUIRED_FIELDS + HANDOFF_OPTIONAL_FIELDS
)
HANDOFF_CHECK_FIELDS = frozenset(
    {"name", "status", "applicable", "reason", "evidence_id", "evidence_ids"}
)
HANDOFF_OPEN_ITEM_FIELDS = frozenset({"item", "reason", "owner"})
PHASE_PACKET_FIELDS = frozenset(
    {
        "kind",
        "version",
        "cycle_id",
        "packet_id",
        "phase_packet_id",
        "upstream_assignment_ids",
        "assignment_ids",
        "dependency_state",
        "changed_paths",
        "evidence_id",
        "evidence_ids",
        "next_owner",
        "integration_owner",
        "owner",
        "status",
    }
)
ACTIVATION_ROW_FIELDS = frozenset(
    {"status", "activation", "reason", "evidence_id", "evidence_ids"}
)
HANDOFF_STATUSES = frozenset(
    {"complete", "needs_repair", "blocked", "not_applicable"}
)
CHECK_STATUSES = frozenset({"pass", "fail", "skip", "not_applicable"})
CLEARING_HANDOFF_STATUSES = frozenset({"complete", "not_applicable"})
FORBIDDEN_FIELD_FRAGMENTS = (
    "chain_of_thought",
    "scratchpad",
    "private_reasoning",
    "credential",
    "secret",
    "prompt",
    "trace",
)

CYCLE_ROOT = ".saturation/cycles"
_CYCLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _nonempty_string(value: Any) -> bool:
    """Return whether a value is a non-empty string."""

    return isinstance(value, str) and bool(value.strip())


def _safe_repo_path(value: Any) -> str | None:
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


def _valid_cycle_id(value: Any) -> bool:
    """Return whether a cycle identifier is safe for a path component."""

    return isinstance(value, str) and bool(_CYCLE_ID_RE.fullmatch(value))


def cycle_context_path(cycle_id: str) -> str:
    """Build the canonical context path for a cycle.

    Args:
        cycle_id: Safe, opaque cycle identifier.

    Returns:
        Repository-relative path to the cycle context.

    Raises:
        ValueError: If ``cycle_id`` is not a safe path component.
    """

    if not _valid_cycle_id(cycle_id):
        raise ValueError("cycle_id must be a safe non-empty identifier")
    return f"{CYCLE_ROOT}/{cycle_id}/context.md"


def _is_report_filename(filename: str) -> bool:
    """Return whether a basename denotes a redacted cycle report."""

    return (
        filename == "report"
        or filename.startswith("report.")
        or filename.startswith("evidence-report.")
    )


def cycle_report_path(cycle_id: str, filename: str = "report.json") -> str:
    """Build a canonical per-cycle report path.

    Args:
        cycle_id: Safe, opaque cycle identifier.
        filename: Report filename, normally ``report.json`` or ``report.md``.

    Returns:
        Repository-relative path to the cycle report.

    Raises:
        ValueError: If either path component is unsafe or not report-like.
    """

    if not _valid_cycle_id(cycle_id):
        raise ValueError("cycle_id must be a safe non-empty identifier")
    if (
        not _nonempty_string(filename)
        or "/" in filename
        or "\\" in filename
        or not _is_report_filename(filename)
    ):
        raise ValueError("filename must be a report filename")
    return f"{CYCLE_ROOT}/{cycle_id}/{filename}"


def is_per_cycle_artifact(path: Any, cycle_id: Any = None) -> bool:
    """Return whether a path is an allowed context or report artifact.

    Args:
        path: Repository-relative path to inspect.
        cycle_id: Optional cycle ID that the path must belong to.

    Returns:
        ``True`` for a cycle context or redacted cycle report path.
    """

    normalized = _safe_repo_path(path)
    if normalized is None:
        return False
    parts = normalized.split("/")
    if len(parts) != 4 or parts[:2] != CYCLE_ROOT.split("/"):
        return False
    path_cycle_id = parts[2]
    if not _valid_cycle_id(path_cycle_id):
        return False
    if cycle_id is not None and path_cycle_id != cycle_id:
        return False
    return parts[3] == "context.md" or _is_report_filename(parts[3])


def _validate_sequence(value: Any, field: str) -> tuple[list[Any], list[str]]:
    """Validate a sequence-valued contract field."""

    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return [], [f"{field} must be a sequence"]
    return list(value), []


def _identifier_values(value: Any, field: str) -> tuple[list[str], list[str]]:
    """Validate one or more stable opaque identifiers."""

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = list(value)
    else:
        return [], [f"{field} must contain stable identifiers"]

    errors: list[str] = []
    identifiers: list[str] = []
    for identifier in values:
        if not _nonempty_string(identifier):
            errors.append(f"{field} must contain non-empty identifiers")
            continue
        identifiers.append(identifier.strip())
    if len(set(identifiers)) != len(identifiers):
        errors.append(f"{field} must not contain duplicates")
    return identifiers, errors


def _record_evidence(
    value: Mapping[str, Any], field_prefix: str
) -> tuple[list[str], list[str]]:
    """Read singular or plural evidence IDs from a mapping."""

    identifiers: list[str] = []
    errors: list[str] = []
    for field in ("evidence_id", "evidence_ids"):
        if field not in value:
            continue
        values, value_errors = _identifier_values(
            value[field], f"{field_prefix}.{field}"
        )
        identifiers.extend(values)
        errors.extend(value_errors)
    if len(set(identifiers)) != len(identifiers):
        errors.append(f"{field_prefix} evidence IDs must not repeat")
    return identifiers, errors


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
    """Return whether nested contract data names private or sensitive data."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str):
                normalized = key.lower().replace("-", "_")
                if any(
                    fragment in normalized
                    for fragment in FORBIDDEN_FIELD_FRAGMENTS
                ):
                    return True
            if _contains_forbidden_field(nested):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_forbidden_field(item) for item in value)
    return False


def contains_forbidden_field(value: Any) -> bool:
    """Return whether redacted contract data contains a forbidden field.

    This public wrapper lets the in-memory observation evaluator apply
    the same privacy boundary as handoff validation without duplicating the
    field-name policy.
    """

    return _contains_forbidden_field(value)


def _unsupported_fields(
    value: Mapping[str, Any], allowed: frozenset[str], label: str
) -> list[str]:
    """Return violations for fields outside a redacted contract shape."""

    unsupported = [field for field in value if field not in allowed]
    return [
        f"{label} contains unsupported field: {field}"
        for field in sorted(unsupported, key=str)
    ]


def _matrix_source(
    value: Any, mode_override: Any = None
) -> tuple[Any, Any, list[str]]:
    """Extract mode and role rows from supported matrix envelopes."""

    errors: list[str] = []
    mode = mode_override
    source = value
    if isinstance(value, Mapping):
        if mode is None:
            mode = value.get("mode")
        for key in ("roles", "activation_matrix", "matrix"):
            if key in value:
                source = value[key]
                break
    if isinstance(source, Mapping):
        rows: list[tuple[Any, Any]] = list(source.items())
    elif isinstance(source, Sequence) and not isinstance(source, (str, bytes)):
        rows = []
        for index, row in enumerate(source):
            if not isinstance(row, Mapping):
                errors.append(f"activation matrix row {index} must be an object")
                continue
            role = row.get("role_id", row.get("role", row.get("agent_id")))
            rows.append((role, row))
    else:
        rows = []
        errors.append("activation matrix roles must be a mapping or sequence")
    return mode, rows, errors


def _matrix_entries(
    value: Any, mode_override: Any = None
) -> tuple[Any, dict[str, Mapping[str, Any]], list[str]]:
    """Normalize matrix rows while retaining validation errors."""

    mode, rows, errors = _matrix_source(value, mode_override)
    entries: dict[str, Mapping[str, Any]] = {}
    for role_value, row_value in rows:
        if not _nonempty_string(role_value):
            errors.append("activation matrix rows need a role ID")
            continue
        role = role_value.strip()
        if role in entries:
            errors.append(f"activation matrix repeats role: {role}")
            continue
        if isinstance(row_value, str):
            row: Mapping[str, Any] = {"status": row_value}
        elif isinstance(row_value, Mapping):
            row = row_value
        else:
            errors.append(f"activation matrix row is invalid: {role}")
            continue
        entries[role] = row
    return mode, entries, errors


def _validate_activation_matrix(
    value: Any,
    mode_override: Any = None,
    *,
    require_evidence: bool = True,
) -> list[str]:
    """Validate a normalized activation matrix."""

    mode, entries, errors = _matrix_entries(value, mode_override)
    if mode is not None and (
        not isinstance(mode, str) or mode not in MODE_MINIMUM_ROLES
    ):
        errors.append(f"mode must be one of {sorted(MODE_MINIMUM_ROLES)}")

    unknown_roles = set(entries) - set(ROLE_CONTRACTS)
    for role in sorted(unknown_roles):
        errors.append(f"activation matrix contains unknown role: {role}")
    missing_roles = set(ROLE_CONTRACTS) - set(entries)
    if missing_roles:
        errors.append(
            "activation matrix must account for every role: "
            + ", ".join(sorted(missing_roles))
        )

    statuses: dict[str, Any] = {}
    for role, row in entries.items():
        errors.extend(
            _unsupported_fields(
                row, ACTIVATION_ROW_FIELDS, f"activation matrix role {role}"
            )
        )
        status = row.get("status", row.get("activation"))
        statuses[role] = status
        if status not in ACTIVATION_STATUSES:
            errors.append(
                f"activation matrix role {role} has an invalid status"
            )
            continue
        if role == LEAD_ROLE and status != "implicit":
            errors.append("lead activation must be implicit")
        if role != LEAD_ROLE and status == "implicit":
            errors.append(f"only lead may use implicit activation: {role}")

        reason = row.get("reason")
        evidence_ids, evidence_errors = _record_evidence(
            row, f"activation matrix role {role}"
        )
        errors.extend(evidence_errors)
        if status in {"implicit", "not_applicable"}:
            if not _nonempty_string(reason):
                errors.append(
                    f"activation matrix role {role} needs a reason"
                )
            if require_evidence and not evidence_ids:
                errors.append(
                    f"activation matrix role {role} needs evidence IDs"
                )

    if isinstance(mode, str) and mode in MODE_MINIMUM_ROLES:
        missing_required = {
            role
            for role in MODE_MINIMUM_ROLES[mode]
            if statuses.get(role) != "active"
        }
        if missing_required:
            errors.append(
                "mode is missing active roles: "
                + ", ".join(sorted(missing_required))
            )
    return errors


def validate_activation_matrix(
    matrix_or_mode: Any, matrix: Any = None
) -> list[str]:
    """Validate an objective risk-based role activation matrix.

    The canonical shape is a mapping with optional ``mode`` and a ``roles``
    mapping. Each role has ``status`` set to ``active``, ``implicit`` (only
    for the main-session lead), or ``not_applicable``. Omitted roles need a
    reason and stable evidence IDs. A two-argument ``(mode, matrix)`` form is
    accepted for in-memory callers.

    Args:
        matrix_or_mode: Matrix envelope, or the mode in two-argument form.
        matrix: Matrix rows when ``matrix_or_mode`` is a mode.

    Returns:
        A list of contract violations.
    """

    if isinstance(matrix_or_mode, str) and matrix is not None:
        return _validate_activation_matrix(matrix, matrix_or_mode)
    if isinstance(matrix, str):
        return _validate_activation_matrix(matrix_or_mode, matrix)
    return _validate_activation_matrix(matrix_or_mode)


def activation_matrix_roles(value: Any) -> dict[str, str]:
    """Return role statuses from a matrix for evaluator linkage checks."""

    _, entries, _ = _matrix_entries(value)
    result: dict[str, str] = {}
    for role, row in entries.items():
        status = row.get("status", row.get("activation"))
        if isinstance(status, str):
            result[role] = status
    return result


def _check_evidence_valid(check: Mapping[str, Any]) -> bool:
    """Return whether a check contains at least one stable evidence ID."""

    evidence_ids, errors = _record_evidence(check, "check")
    return bool(evidence_ids) and not errors


def derive_handoff_clearance(value: Any) -> bool:
    """Derive clearance from canonical status, checks, and open items.

    Args:
        value: A complete handoff envelope or its inner payload.

    Returns:
        ``True`` only for a complete or accepted not-applicable result with
        valid evidence and no failed or applicable skipped checks.
    """

    payload = value.get("handoff") if isinstance(value, Mapping) else None
    if isinstance(payload, Mapping):
        candidate = payload
    elif isinstance(value, Mapping):
        candidate = value
    else:
        return False

    if candidate.get("status") not in CLEARING_HANDOFF_STATUSES:
        return False
    if candidate.get("clearance") is True:
        return False
    if not _valid_cycle_id(candidate.get("cycle_id")):
        return False
    open_items = candidate.get("open_items")
    if not isinstance(open_items, Sequence) or isinstance(
        open_items, (str, bytes)
    ) or list(open_items):
        return False
    checks = candidate.get("checks")
    if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)):
        return False
    if not checks:
        return False
    for check in checks:
        if not isinstance(check, Mapping):
            return False
        status = check.get("status")
        if status not in {"pass", "skip", "not_applicable"}:
            return False
        if status == "skip" and check.get("applicable", True) is not False:
            return False
        if not _check_evidence_valid(check):
            return False
    return True


def _validate_handoff_paths(
    changed_paths: Any, status: Any
) -> tuple[list[str], list[str]]:
    """Validate concrete non-runtime handoff paths."""

    errors: list[str] = []
    paths, path_errors = _validate_sequence(
        changed_paths, "handoff changed_paths"
    )
    errors.extend(path_errors)
    normalized_paths: list[str] = []
    for path in paths:
        normalized = _safe_repo_path(path)
        if normalized is None:
            errors.append("handoff changed_paths must be repository-relative")
            continue
        if normalized == ".":
            errors.append("handoff changed_paths must name concrete paths")
            continue
        if normalized == ".saturation" or normalized.startswith(".saturation/"):
            errors.append(
                "handoff changed_paths may only use per-cycle context/report"
            )
        normalized_paths.append(normalized)
    if status == "not_applicable" and normalized_paths:
        errors.append("not_applicable handoffs cannot change product paths")
    return normalized_paths, errors


def validate_handoff(value: Any) -> list[str]:
    """Validate one compact canonical handoff envelope."""

    errors: list[str] = []
    if not isinstance(value, Mapping):
        return ["handoff must be an object"]
    payload = value.get("handoff")
    if not isinstance(payload, Mapping):
        return ["handoff object is required"]
    if _contains_forbidden_field(payload):
        errors.append("handoff contains a forbidden private or sensitive field")
    errors.extend(
        _unsupported_fields(payload, HANDOFF_ALLOWED_FIELDS, "handoff")
    )

    for field in HANDOFF_REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"handoff is missing {field}")

    if payload.get("version") != "1":
        errors.append("handoff version must be 1")
    if not _valid_cycle_id(payload.get("cycle_id")):
        errors.append("handoff cycle_id must be a safe non-empty identifier")
    for field in ("assignment_id", "agent_id", "summary"):
        if not _nonempty_string(payload.get(field)):
            errors.append(f"handoff {field} must be a non-empty string")
    if payload.get("agent_id") == LEAD_ROLE:
        errors.append("lead does not return a specialist handoff")
    elif (
        _nonempty_string(payload.get("agent_id"))
        and payload.get("agent_id") not in ROLE_CONTRACTS
    ):
        errors.append("handoff agent_id must name a known specialist role")

    status = payload.get("status")
    if status not in HANDOFF_STATUSES:
        errors.append(f"handoff status must be one of {sorted(HANDOFF_STATUSES)}")

    _, path_errors = _validate_handoff_paths(payload.get("changed_paths"), status)
    errors.extend(path_errors)

    checks, check_errors = _validate_sequence(
        payload.get("checks"), "handoff checks"
    )
    errors.extend(check_errors)
    if not checks:
        errors.append("handoff checks must not be empty")
    failed_check = False
    for index, check in enumerate(checks):
        if not isinstance(check, Mapping):
            errors.append(f"handoff check {index} must be an object")
            continue
        errors.extend(
            _unsupported_fields(
                check, HANDOFF_CHECK_FIELDS, f"handoff check {index}"
            )
        )
        if not _nonempty_string(check.get("name")):
            errors.append(f"handoff check {index} has no name")
        check_status = check.get("status")
        if check_status not in CHECK_STATUSES:
            errors.append(f"handoff check {index} has an invalid status")
        if check_status == "fail":
            failed_check = True
        if check_status == "skip" and check.get("applicable", True) is not False:
            errors.append(
                f"handoff check {index} cannot skip an applicable check"
            )
        evidence_ids, evidence_errors = _record_evidence(
            check, f"handoff check {index}"
        )
        if not evidence_ids:
            errors.append(f"handoff check {index} needs evidence_id")
        errors.extend(evidence_errors)

    open_items, open_errors = _validate_sequence(
        payload.get("open_items"), "handoff open_items"
    )
    errors.extend(open_errors)
    for index, item in enumerate(open_items):
        if not isinstance(item, Mapping):
            errors.append(f"handoff open item {index} must be an object")
            continue
        errors.extend(
            _unsupported_fields(
                item, HANDOFF_OPEN_ITEM_FIELDS, f"handoff open item {index}"
            )
        )
        for field in ("item", "reason", "owner"):
            if not _nonempty_string(item.get(field)):
                errors.append(f"handoff open item {index} needs {field}")

    if status in {"needs_repair", "blocked"}:
        if not _nonempty_string(payload.get("next_owner")):
            errors.append(f"{status} handoff needs a next_owner")
        elif payload.get("next_owner") not in ROLE_CONTRACTS:
            errors.append("handoff next_owner must name a known role or lead")
        if not open_items:
            errors.append(f"{status} handoffs need an open item")
    elif "next_owner" in payload:
        errors.append(
            "next_owner is only valid for needs_repair or blocked handoffs"
        )

    if status == "complete" and open_items:
        errors.append("complete handoffs cannot contain open items")
    if status in CLEARING_HANDOFF_STATUSES and failed_check:
        errors.append("cleared handoffs cannot contain failed checks")

    for field in ("phase_packet_id", "phase_packet_ids"):
        if field in payload:
            _, identifier_errors = _identifier_values(
                payload[field], f"handoff {field}"
            )
            errors.extend(identifier_errors)

    if "clearance" in payload:
        if type(payload["clearance"]) is not bool:
            errors.append("handoff clearance must be boolean when supplied")
        elif payload["clearance"] is True:
            errors.append("roles cannot self-authorize clearance")
    return errors


def validate_phase_packet(
    value: Any, cycle_id: str | None = None
) -> list[str]:
    """Validate an in-memory packet that joins parallel role results.

    Args:
        value: Packet or ``{"phase_packet": packet}`` mapping.
        cycle_id: Optional cycle ID that the packet must use.

    Returns:
        A list of packet contract violations.
    """

    if not isinstance(value, Mapping):
        return ["phase_packet must be an object"]
    packet_value = value.get("phase_packet", value)
    if not isinstance(packet_value, Mapping):
        return ["phase_packet object is required"]
    packet = packet_value
    errors: list[str] = []
    errors.extend(
        _unsupported_fields(packet, PHASE_PACKET_FIELDS, "phase_packet")
    )
    if _contains_forbidden_field(packet):
        errors.append(
            "phase_packet contains a forbidden private or sensitive field"
        )
    if packet.get("version") != "1":
        errors.append("phase_packet version must be 1")
    packet_cycle_id = packet.get("cycle_id")
    if not _valid_cycle_id(packet_cycle_id):
        errors.append("phase_packet cycle_id must be a safe identifier")
    if cycle_id is not None and packet_cycle_id != cycle_id:
        errors.append("phase_packet cycle_id does not match the current cycle")
    if not _nonempty_string(packet.get("packet_id")):
        errors.append("phase_packet needs a packet_id")

    upstream = packet.get(
        "upstream_assignment_ids", packet.get("assignment_ids")
    )
    upstream_values, upstream_errors = _validate_sequence(
        upstream, "phase_packet upstream_assignment_ids"
    )
    errors.extend(upstream_errors)
    if not upstream_values:
        errors.append("phase_packet needs upstream assignment IDs")
    for assignment_id in upstream_values:
        if not _nonempty_string(assignment_id):
            errors.append("phase_packet assignment IDs must be non-empty")
    normalized_upstream = [
        value.strip()
        for value in upstream_values
        if _nonempty_string(value)
    ]
    if len(normalized_upstream) != len(set(normalized_upstream)):
        errors.append("phase_packet assignment IDs must not repeat")

    if "status" in packet and packet["status"] not in HANDOFF_STATUSES:
        errors.append("phase_packet status must be a canonical role status")

    dependency_state = packet.get("dependency_state")
    if not isinstance(dependency_state, (Mapping, str)) or (
        isinstance(dependency_state, str)
        and not dependency_state.strip()
    ):
        errors.append("phase_packet needs dependency_state")

    changed_paths, path_errors = _validate_sequence(
        packet.get("changed_paths"), "phase_packet changed_paths"
    )
    errors.extend(path_errors)
    for path in changed_paths:
        normalized = _safe_repo_path(path)
        if normalized is None or normalized == ".":
            errors.append("phase_packet changed_paths must be concrete paths")
        elif normalized.startswith(".saturation"):
            errors.append("phase_packet changed_paths cannot be runtime paths")

    packet_evidence = packet.get("evidence_ids", packet.get("evidence_id"))
    evidence_ids, evidence_errors = _identifier_values(
        packet_evidence, "phase_packet evidence_ids"
    )
    errors.extend(evidence_errors)
    if not evidence_ids:
        errors.append("phase_packet needs evidence_ids")

    owners = [
        packet.get("next_owner"),
        packet.get("integration_owner"),
        packet.get("owner"),
    ]
    if not any(_nonempty_string(owner) for owner in owners):
        errors.append("phase_packet needs a next or integration owner")
    for owner in owners:
        if _nonempty_string(owner) and owner not in ROLE_CONTRACTS:
            errors.append("phase_packet owner must name a known role or lead")
    return errors


def validate_mode_selection(
    mode: Any,
    active_roles: Any,
    omitted_roles: Any = None,
) -> list[str]:
    """Validate mode routing, including the legacy list adapter.

    New callers should pass a complete activation matrix as ``active_roles``.
    The old ``active_roles`` plus ``omitted_roles`` form remains accepted as a
    compatibility adapter, but the lead is always represented as implicit.
    """

    if omitted_roles is None:
        if isinstance(active_roles, Mapping):
            envelope = dict(active_roles)
            envelope.setdefault("mode", mode)
            return validate_activation_matrix(envelope)
        if isinstance(active_roles, Sequence) and not isinstance(
            active_roles, (str, bytes)
        ):
            active_values = list(active_roles)
            matrix: dict[str, Any] = {}
            active_set = set(active_values)
            for role in ROLE_CONTRACTS:
                if role == LEAD_ROLE:
                    matrix[role] = {
                        "status": "implicit",
                        "reason": "The lead is the main session.",
                    }
                elif role in active_set:
                    matrix[role] = {"status": "active"}
                else:
                    matrix[role] = {
                        "status": "not_applicable",
                        "reason": "Not selected by this compatibility call.",
                    }
            return _validate_activation_matrix(
                {"mode": mode, "roles": matrix},
                require_evidence=False,
            )
        return validate_activation_matrix({"mode": mode, "roles": active_roles})

    active, active_errors = _validate_sequence(active_roles, "active_roles")
    errors = list(active_errors)
    active_values = [role for role in active if isinstance(role, str)]
    if len(active_values) != len(active) or len(set(active_values)) != len(
        active_values
    ):
        errors.append("active_roles must contain unique role IDs")
    if not isinstance(omitted_roles, Mapping):
        errors.append("omitted_roles must map role IDs to reasons")
        omitted: dict[str, Any] = {}
    else:
        omitted = dict(omitted_roles)

    matrix: dict[str, Any] = {}
    for role in active_values:
        matrix[role] = {
            "status": "implicit" if role == LEAD_ROLE else "active",
            **(
                {"reason": "The lead is the main session."}
                if role == LEAD_ROLE
                else {}
            ),
        }
    for role, reason in omitted.items():
        matrix[role] = {"status": "not_applicable", "reason": reason}
    for role in ROLE_CONTRACTS:
        if role not in matrix:
            matrix[role] = {
                "status": "not_applicable",
                "reason": "Not selected by this compatibility call.",
            }
    errors.extend(
        _validate_activation_matrix(
            {"mode": mode, "roles": matrix},
            require_evidence=False,
        )
    )
    return errors


def should_trip_circuit_breaker(same_failure_count: Any) -> bool:
    """Return whether the three-failure limit has been reached."""

    return type(same_failure_count) is int and same_failure_count >= 3
