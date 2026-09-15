"""Deterministic validation for saturation prompt contracts.

The validator deliberately checks observable structure and arithmetic. It does
not claim to judge semantic prompt quality from prose; that responsibility
belongs to the read-only reviewer and independent verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = 3
TDD_SCHEMA_VERSION = 4
CURRENT_SCHEMA_VERSION = 5
SUPPORTED_SCHEMA_VERSIONS = (SCHEMA_VERSION, TDD_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION)
PROMPT_POLICY_VERSION = "pcp-v1"
PROMPT_SECTIONS = (
    "Role",
    "Objective",
    "Context",
    "Scope",
    "Priorities",
    "Procedure",
    "Output Contract",
    "Verification and Evidence",
    "Failure and Stop Conditions",
)
PROMPT_PHASES = (
    "freeze_context",
    "inspect",
    "implement",
    "review",
    "final_review",
    "repair",
    "verify",
    "promote",
    "completion_gate",
)
PROMPT_PHASES_V4 = (
    "freeze_context",
    "inspect",
    "test_first",
    "implement",
    "review",
    "final_review",
    "repair",
    "verify",
    "promote",
    "completion_gate",
)
PROMPT_STRATEGIES = ("direct", "few_shot", "chained", "tool_augmented")
PROMPT_GATES = (
    "objective",
    "role_authority",
    "relevant_context",
    "scope_permissions",
    "priorities",
    "procedure",
    "output_contract",
    "verification_evidence",
    "failure_stop",
    "consistency_relevance",
    "untrusted_input_boundary",
    "examples",
    "reasoning_guidance",
    "secret_safety",
)
PCP_COSTS = {
    "branch": Decimal("1"),
    "condition": Decimal("1"),
    "exception": Decimal("1"),
    "internal_dependency": Decimal("1"),
    "external_dependency": Decimal("0.5"),
    "obligation": Decimal("1"),
    "sequence": Decimal("1"),
}
PCP_WARNING_THRESHOLD = Decimal("8")
PCP_HARD_LIMIT = Decimal("10")
PCP_BOILERPLATE_EXCLUDED = (
    "headings",
    "examples",
    "inherited_contract",
    "module_manifest",
    "fixed_safety",
)
PROMPT_OUTPUT_CONTRACTS = {
    "context_freeze.v3": (
        "context_path",
        "frozen",
        "before_delegation",
        "tool_call_ref",
    ),
    "inspection.v3": ("tool_call_ref",),
    "handoff.v3": (
        "context",
        "assignment",
        "state",
        "input",
        "output",
        "error",
        "stop",
        "evidence",
        "fresh_session",
    ),
    "implementation.v3": ("tool_call_ref", "handoff_ref"),
    "review.v3": (
        "tool_call_ref",
        "read_only",
        "adversarial",
        "gap_ids",
        "handoff_ref",
    ),
    "repair.v3": ("tool_call_ref", "resolves", "handoff_ref"),
    "verification.v3": (
        "tool_call_ref",
        "rechecks",
        "result",
        "independent",
        "handoff_ref",
        "verifier",
    ),
    "final_review.v3": (
        "tool_call_ref",
        "read_only",
        "adversarial",
        "resolved",
        "gap_ids",
        "handoff_ref",
    ),
    "promotion.v3": ("tool_call_ref", "approved"),
    "completion_gate.v3": (
        "decision",
        "context_frozen",
        "scope_checked",
        "independent_review",
        "latest_review_clear",
        "verification_passed",
        "promotion_reviewed",
        "no_unresolved_blocker",
        "evidence",
        "tool_call_ref",
    ),
}
PROMPT_OUTPUT_CONTRACTS_V4 = {
    "context_freeze.v3": PROMPT_OUTPUT_CONTRACTS["context_freeze.v3"],
    "inspection.v3": PROMPT_OUTPUT_CONTRACTS["inspection.v3"],
    "handoff.v3": PROMPT_OUTPUT_CONTRACTS["handoff.v3"],
    "test_first.v1": (
        "tool_call_ref",
        "handoff_ref",
        "cycle_id",
        "mode",
        "test_artifact_paths",
        "red_run",
    ),
    "implementation.v3": PROMPT_OUTPUT_CONTRACTS["implementation.v3"],
    "review.v3": PROMPT_OUTPUT_CONTRACTS["review.v3"],
    "repair.v3": PROMPT_OUTPUT_CONTRACTS["repair.v3"],
    "verification.v3": PROMPT_OUTPUT_CONTRACTS["verification.v3"],
    "final_review.v3": PROMPT_OUTPUT_CONTRACTS["final_review.v3"],
    "promotion.v3": PROMPT_OUTPUT_CONTRACTS["promotion.v3"],
    "completion_gate.v3": PROMPT_OUTPUT_CONTRACTS["completion_gate.v3"],
}
PROMPT_OUTPUT_CONTRACTS_V5 = PROMPT_OUTPUT_CONTRACTS_V4
PROMPT_OUTPUT_IDS = tuple(PROMPT_OUTPUT_CONTRACTS)
PROMPT_FIELDS = (
    "prompt_id",
    "prompt_family_id",
    "handoff_event_id",
    "target_event_id",
    "target_call_id",
    "actor_id",
    "phase",
    "modules",
    "language",
    "sections",
    "strategy",
    "strategy_details",
    "strategy_reason",
    "selection_evidence",
    "output_contract_id",
    "complexity",
    "quality_gates",
    "rendered_prompt",
    "normalized_sha256",
    "supersedes_attempt_ids",
)
ATTEMPT_FIELDS = (
    "attempt_id",
    "prompt_family_id",
    "handoff_event_id",
    "previous_attempt_id",
    "rendered_prompt",
    "normalized_sha256",
    "modules",
    "language",
    "sections",
    "strategy",
    "strategy_details",
    "strategy_reason",
    "selection_evidence",
    "output_contract_id",
    "complexity",
    "quality_gates",
    "failure_codes",
    "evidence",
)
MODULE_FIELDS = ("path", "sha256")
COMPLEXITY_FIELDS = (
    "items",
    "total",
    "warning_threshold",
    "hard_limit",
    "exception",
)
PCP_ITEM_FIELDS = ("id", "kind", "section", "description", "count")
PCP_EXCEPTION_FIELDS = (
    "reason",
    "impact",
    "alternative",
    "approved_by_actor_id",
    "evidence",
)
GATE_FIELDS = ("status", "claim", "evidence", "reason")
NORMALIZATION_RULE = (
    "unicode_nfc;crlf_to_lf;trim_line_endings;trim_edge_blank_lines;one_final_lf"
)
PROMPT_DECLARATION_FIELDS = (
    "policy_version",
    "sections",
    "strategies",
    "pcp",
    "gates",
    "prompt_fields",
    "attempt_fields",
    "module_fields",
    "output_contracts",
    "normalization",
)
PROMPT_PHASE_CONTRACTS = {
    "freeze_context": "context_freeze.v3",
    "inspect": "inspection.v3",
    "implement": "implementation.v3",
    "review": "review.v3",
    "final_review": "final_review.v3",
    "repair": "repair.v3",
    "verify": "verification.v3",
    "promote": "promotion.v3",
    "completion_gate": "completion_gate.v3",
}
PROMPT_PHASE_CONTRACTS_V4 = {
    **PROMPT_PHASE_CONTRACTS,
    "test_first": "test_first.v1",
}
PROMPT_PHASE_CONTRACTS_V5 = PROMPT_PHASE_CONTRACTS_V4
EVENT_KIND_FOR_PHASE = {
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
EVENT_KIND_FOR_PHASE_V4 = {
    **EVENT_KIND_FOR_PHASE,
    "test_first": "test_first",
}
EVENT_KIND_FOR_PHASE_V5 = EVENT_KIND_FOR_PHASE_V4
TARGET_CALL_PHASE_FOR_PROMPT = {
    "final_review": "review",
}
KNOWN_MODULES = {
    "prompting.md",
    "general.md",
    "cpp.md",
    "csharp.md",
    "dart.md",
    "go.md",
    "html-css.md",
    "java.md",
    "javascript.md",
    "python.md",
    "ruby.md",
    "typescript.md",
}
MODULE_ROOT = ".agents/skills/saturation/code_styleguides/"
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _schema_version(trace: Mapping[str, Any]) -> int:
    value = trace.get("schema_version")
    return value if value in SUPPORTED_SCHEMA_VERSIONS else SCHEMA_VERSION


def _prompt_contracts(version: int) -> Dict[str, Tuple[str, ...]]:
    if version == CURRENT_SCHEMA_VERSION:
        return PROMPT_OUTPUT_CONTRACTS_V5
    if version == TDD_SCHEMA_VERSION:
        return PROMPT_OUTPUT_CONTRACTS_V4
    return PROMPT_OUTPUT_CONTRACTS


def _prompt_phases(version: int) -> Tuple[str, ...]:
    if version == CURRENT_SCHEMA_VERSION:
        return PROMPT_PHASES_V4
    if version == TDD_SCHEMA_VERSION:
        return PROMPT_PHASES_V4
    return PROMPT_PHASES


def _phase_contracts(version: int) -> Dict[str, str]:
    if version == CURRENT_SCHEMA_VERSION:
        return PROMPT_PHASE_CONTRACTS_V5
    if version == TDD_SCHEMA_VERSION:
        return PROMPT_PHASE_CONTRACTS_V4
    return PROMPT_PHASE_CONTRACTS


def _event_kinds_for_phase(version: int) -> Dict[str, str]:
    if version == CURRENT_SCHEMA_VERSION:
        return EVENT_KIND_FOR_PHASE_V5
    if version == TDD_SCHEMA_VERSION:
        return EVENT_KIND_FOR_PHASE_V4
    return EVENT_KIND_FOR_PHASE

_SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    (
        "known_token",
        re.compile(r"\b(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9]{20,})"),
    ),
    (
        "secret_assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9+/_.=-]{8,}"
        ),
    ),
    (
        "connection_string",
        re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@"),
    ),
)
_PII_PATTERNS = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    (
        "phone",
        re.compile(r"(?<![\w])(?:\+\d{1,3}[ -]?)?(?:\(\d{2,4}\)|\d{2,4})[ -]\d{3,4}[ -]\d{4}(?!\w)"),
    ),
    ("national_id", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("card_number", re.compile(r"\b(?:\d[ -]?){13,18}\d\b")),
)
_FORBIDDEN_REASONING_REQUESTS = (
    re.compile(r"(?i)\b(?:show|reveal|provide|print|expose|output|write)\s+(?:your\s+)?(?:hidden\s+|private\s+|full\s+)?(?:chain[- ]of[- ]thought|scratchpad|hidden reasoning)"),
)


def _mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_ids(value: Any, *, nonempty: bool = False) -> List[str]:
    values = _list(value)
    result = [item for item in values if isinstance(item, str)]
    if nonempty and (len(result) != len(values) or any(not item.strip() for item in result)):
        return []
    return result


def _exact_fields(value: Any, expected: Sequence[str]) -> bool:
    return isinstance(value, dict) and set(value) == set(expected)


def _decimal(value: Any) -> Optional[Decimal]:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def normalize_prompt(text: str) -> str:
    """Return the canonical text used for prompt hashing."""

    if not isinstance(text, str):
        raise TypeError("prompt text must be a string")
    value = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [line.rstrip(" \t") for line in value.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "" if not lines else "\n".join(lines) + "\n"


def prompt_sha256(text: str) -> str:
    return hashlib.sha256(normalize_prompt(text).encode("utf-8")).hexdigest()


def scan_sensitive(text: str) -> List[str]:
    """Return category names without returning sensitive matched values."""

    findings: List[str] = []
    for category, pattern in _SECRET_PATTERNS + _PII_PATTERNS:
        if pattern.search(text):
            findings.append(category)
    return findings


def sanitize_prompt(text: str) -> str:
    """Redact high-confidence secrets and PII before recording a prompt."""

    value = text
    for _, pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED_SECRET]", value)
    for _, pattern in _PII_PATTERNS:
        value = pattern.sub("[REDACTED_PII]", value)
    return value


def _prompt_headings(text: str) -> Tuple[List[str], Dict[str, str], List[str]]:
    headings: List[str] = []
    bodies: Dict[str, str] = {}
    errors: List[str] = []
    current: Optional[str] = None
    body: List[str] = []
    fence_char: Optional[str] = None
    fence_length = 0

    def flush() -> None:
        if current is not None:
            bodies[current] = "\n".join(body)

    for line in text.split("\n"):
        stripped = line.lstrip()
        fence_match = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_match:
            marker = fence_match.group(1)
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        if fence_char is not None:
            continue
        heading_match = re.match(r"^## ([^#].*?)\s*$", line)
        if heading_match:
            flush()
            current = heading_match.group(1)
            headings.append(current)
            body = []
        elif current is not None:
            body.append(line)
    flush()
    if fence_char is not None:
        errors.append("unclosed fenced code block")
    return headings, bodies, errors


def validate_rendered_prompt(text: Any) -> List[str]:
    errors: List[str] = []
    if not _nonempty_string(text):
        return ["rendered_prompt must be a non-empty string"]
    headings, bodies, heading_errors = _prompt_headings(text)
    errors.extend(heading_errors)
    if headings != list(PROMPT_SECTIONS):
        errors.append("rendered_prompt headings must be the canonical headings in order")
    for section in PROMPT_SECTIONS:
        if not bodies.get(section, "").strip():
            errors.append("rendered_prompt section %s must be non-empty" % section)

    untrusted_stack: List[str] = []
    for line in text.splitlines():
        begin = re.match(r"^\[BEGIN (UNTRUSTED [A-Z0-9_ -]+)\]$", line.strip())
        end = re.match(r"^\[END (UNTRUSTED [A-Z0-9_ -]+)\]$", line.strip())
        if begin:
            untrusted_stack.append(begin.group(1))
        elif end:
            if not untrusted_stack or untrusted_stack[-1] != end.group(1):
                errors.append("untrusted context sentinels are not properly nested")
            else:
                untrusted_stack.pop()
    if untrusted_stack:
        errors.append("untrusted context sentinel is not closed")
    if "[BEGIN UNTRUSTED " not in text or "[END UNTRUSTED " not in text:
        errors.append("rendered_prompt must delimit untrusted context")

    if any(pattern.search(text) for pattern in _FORBIDDEN_REASONING_REQUESTS):
        errors.append("rendered_prompt must not request manual hidden reasoning")
    findings = scan_sensitive(text)
    if findings:
        errors.append("rendered_prompt contains unsanitized sensitive categories: " + ",".join(findings))
    return errors


def _validate_output_contract_text(
    contract_id: Any,
    text: Any,
    contracts: Optional[Mapping[str, Tuple[str, ...]]] = None,
) -> List[str]:
    """Require the selected machine contract to be visible in the prompt."""

    contracts = contracts or PROMPT_OUTPUT_CONTRACTS
    if not isinstance(contract_id, str) or contract_id not in contracts:
        return ["output_contract_id must name a declared output contract"]
    if not isinstance(text, str):
        return []
    errors: List[str] = []
    if contract_id not in text:
        errors.append("rendered_prompt must name its output_contract_id")
    for field in contracts[contract_id]:
        if not re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(field), text):
            errors.append("rendered_prompt must name output field %s" % field)
    return errors


def validate_modules(value: Any) -> List[str]:
    errors: List[str] = []
    modules = _list(value)
    if not modules:
        return ["modules must be a non-empty list"]
    paths: List[str] = []
    for index, module in enumerate(modules):
        if not _exact_fields(module, MODULE_FIELDS):
            errors.append("module %d must contain exactly path and sha256" % index)
            continue
        path = module.get("path")
        digest = module.get("sha256")
        expected_prefix = MODULE_ROOT
        if not _nonempty_string(path) or not path.startswith(expected_prefix):
            errors.append("module %d path must be repository-relative under code_styleguides" % index)
        else:
            name = path[len(expected_prefix):]
            if name not in KNOWN_MODULES:
                errors.append("module %d names an unknown code-style module" % index)
            paths.append(path)
        if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
            errors.append("module %d sha256 must be lowercase hexadecimal SHA-256" % index)
    if paths:
        expected_first = [MODULE_ROOT + "prompting.md", MODULE_ROOT + "general.md"]
        if paths[:2] != expected_first:
            errors.append("modules must start with prompting.md then general.md")
        if len(paths) != len(set(paths)):
            errors.append("modules must not repeat a path")
        if paths[2:] != sorted(paths[2:]):
            errors.append("language modules must be in stable lexical order")
    return errors


def _validate_strategy(
    strategy: Any,
    reason: Any,
    selection_evidence: Any,
    details: Any,
) -> List[str]:
    errors: List[str] = []
    if strategy not in PROMPT_STRATEGIES:
        errors.append("strategy must be one of the declared strategies")
    if not _nonempty_string(reason):
        errors.append("strategy_reason must be non-empty")
    if not _string_ids(selection_evidence, nonempty=True):
        errors.append("selection_evidence must be a non-empty string list")
    if not isinstance(details, dict):
        return errors + ["strategy_details must be an object"]
    if strategy == "direct" and set(details) != set():
        errors.append("direct strategy_details must be empty")
    elif strategy == "few_shot":
        if set(details) != {"examples_count"} or not isinstance(details.get("examples_count"), int) or isinstance(details.get("examples_count"), bool) or details.get("examples_count") <= 0:
            errors.append("few_shot strategy_details needs examples_count > 0")
    elif strategy == "chained":
        if set(details) != {"chain_id", "step_index", "depends_on_prompt_ids"}:
            errors.append("chained strategy_details has the wrong fields")
        elif (
            not _nonempty_string(details.get("chain_id"))
            or not isinstance(details.get("step_index"), int)
            or isinstance(details.get("step_index"), bool)
            or details.get("step_index") < 1
            or not isinstance(details.get("depends_on_prompt_ids"), list)
            or any(not _nonempty_string(item) for item in details.get("depends_on_prompt_ids"))
            or (details.get("step_index") > 1 and not details.get("depends_on_prompt_ids"))
        ):
            errors.append("chained strategy_details has invalid dependency metadata")
    elif strategy == "tool_augmented":
        tools = details.get("tools")
        if set(details) != {"tools"} or not isinstance(tools, list) or not tools or any(not _nonempty_string(item) for item in tools):
            errors.append("tool_augmented strategy_details needs non-empty tools")
    return errors


def _validate_strategy_semantics(
    record: Mapping[str, Any],
    *,
    allow_failed_gates: bool = False,
) -> List[str]:
    """Check requirements that tie a strategy to observable prompt metadata."""

    errors: List[str] = []
    strategy = record.get("strategy")
    details = _mapping(record.get("strategy_details"))
    gates = _mapping(record.get("quality_gates"))
    if strategy == "few_shot":
        examples_gate = _mapping(gates.get("examples"))
        if examples_gate.get("status") != "pass" and not allow_failed_gates:
            errors.append("few_shot strategy requires a passing examples quality gate")
    elif strategy == "tool_augmented":
        items = _list(_mapping(record.get("complexity")).get("items"))
        if not any(isinstance(item, dict) and item.get("kind") == "external_dependency" for item in items):
            errors.append("tool_augmented strategy requires an external_dependency PCP item")
    return errors


def _validate_complexity(
    value: Any,
    sections: Sequence[str],
    *,
    allow_blocked_overage: bool = False,
) -> List[str]:
    errors: List[str] = []
    if not _exact_fields(value, COMPLEXITY_FIELDS):
        return ["complexity must contain exactly items, total, warning_threshold, hard_limit, and exception"]
    items = value.get("items")
    if not isinstance(items, list):
        errors.append("complexity.items must be a list")
        items = []
    item_ids = set()
    calculated = Decimal("0")
    for index, item in enumerate(items):
        if not _exact_fields(item, PCP_ITEM_FIELDS):
            errors.append("complexity item %d has the wrong fields" % index)
            continue
        item_id = item.get("id")
        if not _nonempty_string(item_id) or item_id in item_ids:
            errors.append("complexity item ids must be non-empty and unique")
        if isinstance(item_id, str):
            item_ids.add(item_id)
        kind = item.get("kind")
        if not isinstance(kind, str) or kind not in PCP_COSTS:
            errors.append("complexity item %s has an unknown kind" % item.get("id"))
            continue
        if item.get("section") not in sections:
            errors.append("complexity item %s must name a canonical section" % item.get("id"))
        if not _nonempty_string(item.get("description")):
            errors.append("complexity item %s needs a description" % item.get("id"))
        count = item.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            errors.append("complexity item %s count must be a positive integer" % item.get("id"))
        else:
            calculated += PCP_COSTS[kind] * count
    total = _decimal(value.get("total"))
    if total is None or total != calculated:
        errors.append("complexity.total must equal the taxonomy-derived total")
        total = calculated if total is None else total
    if _decimal(value.get("warning_threshold")) != PCP_WARNING_THRESHOLD:
        errors.append("complexity.warning_threshold must be 8")
    if _decimal(value.get("hard_limit")) != PCP_HARD_LIMIT:
        errors.append("complexity.hard_limit must be 10")
    exception = value.get("exception")
    if total <= PCP_HARD_LIMIT:
        if exception is not None:
            errors.append("complexity.exception must be null at or below the hard limit")
    elif exception is None:
        if not allow_blocked_overage:
            errors.append("over-limit complexity requires a typed exception")
    elif not _exact_fields(exception, PCP_EXCEPTION_FIELDS):
        errors.append("complexity.exception has the wrong fields")
    else:
        for field in ("reason", "impact", "alternative", "approved_by_actor_id"):
            if not _nonempty_string(exception.get(field)):
                errors.append("complexity.exception.%s must be non-empty" % field)
        if not _string_ids(exception.get("evidence"), nonempty=True):
            errors.append("complexity.exception.evidence must be a non-empty string list")
    return errors


def _validate_gates(value: Any, *, allow_fail: bool = False) -> List[str]:
    errors: List[str] = []
    if not isinstance(value, dict) or set(value) != set(PROMPT_GATES):
        return ["quality_gates must contain exactly the 14 canonical gate IDs"]
    for gate_id in PROMPT_GATES:
        gate = value.get(gate_id)
        if not _exact_fields(gate, GATE_FIELDS):
            errors.append("quality gate %s has the wrong fields" % gate_id)
            continue
        status = gate.get("status")
        if not isinstance(status, str) or status not in {"pass", "fail", "not_applicable"}:
            errors.append("quality gate %s has an invalid status" % gate_id)
        if not _nonempty_string(gate.get("claim")):
            errors.append("quality gate %s needs a claim" % gate_id)
        if not _string_ids(gate.get("evidence"), nonempty=True):
            errors.append("quality gate %s needs non-empty evidence" % gate_id)
        reason = gate.get("reason")
        if status == "pass" and reason is not None:
            errors.append("quality gate %s must use null reason when passing" % gate_id)
        if isinstance(status, str) and status in {"fail", "not_applicable"} and not _nonempty_string(reason):
            errors.append("quality gate %s needs a reason when not passing" % gate_id)
        if status == "not_applicable" and gate_id != "examples":
            errors.append("only examples may be not_applicable")
        if not allow_fail and status != "pass" and not (gate_id == "examples" and status == "not_applicable"):
            errors.append("quality gate %s must pass before dispatch" % gate_id)
    return errors


def validate_prompt_declaration(
    value: Any,
    schema_version: int = SCHEMA_VERSION,
) -> List[str]:
    errors: List[str] = []
    if not _exact_fields(value, PROMPT_DECLARATION_FIELDS):
        return ["trace_contract.prompt has the wrong fields"]
    contracts = _prompt_contracts(schema_version)
    if value.get("policy_version") != PROMPT_POLICY_VERSION:
        errors.append("trace_contract.prompt.policy_version must be pcp-v1")
    if value.get("sections") != list(PROMPT_SECTIONS):
        errors.append("trace_contract.prompt.sections must be canonical")
    if value.get("strategies") != list(PROMPT_STRATEGIES):
        errors.append("trace_contract.prompt.strategies must be canonical")
    pcp = value.get("pcp")
    expected_pcp_fields = {"costs", "warning_threshold", "hard_limit", "boilerplate_excluded"}
    if not _exact_fields(pcp, expected_pcp_fields):
        errors.append("trace_contract.prompt.pcp has the wrong fields")
    else:
        costs = pcp.get("costs")
        if not isinstance(costs, dict) or {key: _decimal(item) for key, item in costs.items()} != PCP_COSTS:
            errors.append("trace_contract.prompt.pcp.costs do not match the taxonomy")
        if _decimal(pcp.get("warning_threshold")) != PCP_WARNING_THRESHOLD:
            errors.append("trace_contract.prompt.pcp.warning_threshold must be 8")
        if _decimal(pcp.get("hard_limit")) != PCP_HARD_LIMIT:
            errors.append("trace_contract.prompt.pcp.hard_limit must be 10")
        if pcp.get("boilerplate_excluded") != list(PCP_BOILERPLATE_EXCLUDED):
            errors.append("trace_contract.prompt.pcp.boilerplate_excluded is not canonical")
    if value.get("gates") != list(PROMPT_GATES):
        errors.append("trace_contract.prompt.gates must be canonical")
    if value.get("prompt_fields") != list(PROMPT_FIELDS):
        errors.append("trace_contract.prompt.prompt_fields are not canonical")
    if value.get("attempt_fields") != list(ATTEMPT_FIELDS):
        errors.append("trace_contract.prompt.attempt_fields are not canonical")
    if value.get("module_fields") != list(MODULE_FIELDS):
        errors.append("trace_contract.prompt.module_fields are not canonical")
    output_contracts = value.get("output_contracts")
    expected_contracts = [
        {"id": contract_id, "required_fields": list(fields)}
        for contract_id, fields in contracts.items()
    ]
    if output_contracts != expected_contracts:
        errors.append("trace_contract.prompt.output_contracts are not canonical")
    if value.get("normalization") != NORMALIZATION_RULE:
        errors.append("trace_contract.prompt.normalization is not canonical")
    return errors


def _event_map(trace: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        item.get("event_id"): item
        for item in _list(trace.get("events"))
        if isinstance(item, dict) and isinstance(item.get("event_id"), str)
    }


def _call_map(trace: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        item.get("call_id"): item
        for item in _list(trace.get("tool_calls"))
        if isinstance(item, dict) and isinstance(item.get("call_id"), str)
    }


def _actor_roles(trace: Mapping[str, Any]) -> Dict[str, str]:
    actors = trace.get("actors", {})
    return {
        actor_id: actor.get("role", "")
        for actor_id, actor in actors.items()
        if isinstance(actor_id, str) and isinstance(actor, dict)
    } if isinstance(actors, dict) else {}


def _handoff_target(trace: Mapping[str, Any], handoff: Mapping[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    output = _mapping(_mapping(handoff).get("payload")).get("output")
    target_event_id = _mapping(output).get("event_ref")
    event = _event_map(trace).get(target_event_id) if isinstance(target_event_id, str) else None
    if not isinstance(event, dict):
        return None, None
    call_id = _mapping(event.get("payload")).get("tool_call_ref")
    return event, _call_map(trace).get(call_id) if isinstance(call_id, str) else None


def _expected_call_phase(phase: str) -> str:
    return TARGET_CALL_PHASE_FOR_PROMPT.get(phase, phase) if isinstance(phase, str) else phase


def _validate_exception_authority(
    complexity: Mapping[str, Any],
    trace: Mapping[str, Any],
    actor_id: str,
) -> List[str]:
    exception = complexity.get("exception")
    total = _decimal(complexity.get("total"))
    if total is None or total <= PCP_HARD_LIMIT or not isinstance(exception, dict):
        return []
    approver = exception.get("approved_by_actor_id")
    roles = _actor_roles(trace)
    if approver == actor_id:
        return ["PCP exception approver must be distinct from prompt actor"]
    if not isinstance(approver, str) or approver not in roles:
        return ["PCP exception approver must be a declared actor"]
    if roles[approver] not in {"orchestrator", "reviewer", "verifier", "user"}:
        return ["PCP exception approver lacks an authority role"]
    return []


def _validate_prompt_record(
    prompt: Any,
    trace: Mapping[str, Any],
    prompt_ids: set,
    handoff_ids: set,
    target_event_ids: set,
    target_call_ids: set,
) -> List[str]:
    errors: List[str] = []
    if not _exact_fields(prompt, PROMPT_FIELDS):
        return ["prompt record must contain the exact versioned prompt fields"]
    version = _schema_version(trace)
    contracts = _prompt_contracts(version)
    phases = _prompt_phases(version)
    phase_contracts = _phase_contracts(version)
    event_kinds = _event_kinds_for_phase(version)
    prompt_id = prompt.get("prompt_id")
    if not _nonempty_string(prompt_id) or prompt_id in prompt_ids:
        errors.append("prompt IDs must be non-empty and unique")
    if isinstance(prompt_id, str):
        prompt_ids.add(prompt_id)
    if not _nonempty_string(prompt.get("prompt_family_id")):
        errors.append("prompt_family_id must be non-empty")
    handoff_id = prompt.get("handoff_event_id")
    event_id = prompt.get("target_event_id")
    call_id = prompt.get("target_call_id")
    if isinstance(handoff_id, str) and handoff_id in handoff_ids:
        errors.append("each handoff may have only one prompt")
    if isinstance(handoff_id, str):
        handoff_ids.add(handoff_id)
    if isinstance(event_id, str) and event_id in target_event_ids:
        errors.append("each target event may have only one prompt")
    if isinstance(event_id, str):
        target_event_ids.add(event_id)
    if isinstance(call_id, str) and call_id in target_call_ids:
        errors.append("each target call may have only one prompt")
    if isinstance(call_id, str):
        target_call_ids.add(call_id)
    if not _nonempty_string(prompt.get("actor_id")):
        errors.append("prompt actor_id must be non-empty")
    phase = prompt.get("phase")
    if phase not in phases:
        errors.append("prompt phase is not supported")
    if isinstance(phase, str) and phase in phase_contracts and prompt.get("output_contract_id") != phase_contracts[phase]:
        errors.append("prompt output_contract_id does not match its phase")
    if prompt.get("language") != "en":
        errors.append("prompt language must be en")
    if prompt.get("sections") != list(PROMPT_SECTIONS):
        errors.append("prompt sections must be canonical")
    errors.extend(validate_modules(prompt.get("modules")))
    errors.extend(validate_rendered_prompt(prompt.get("rendered_prompt")))
    errors.extend(_validate_output_contract_text(prompt.get("output_contract_id"), prompt.get("rendered_prompt"), contracts))
    rendered_prompt = prompt.get("rendered_prompt")
    if isinstance(rendered_prompt, str) and prompt.get("normalized_sha256") != prompt_sha256(rendered_prompt):
        errors.append("prompt normalized_sha256 does not match rendered_prompt")
    errors.extend(_validate_strategy(
        prompt.get("strategy"),
        prompt.get("strategy_reason"),
        prompt.get("selection_evidence"),
        prompt.get("strategy_details", {}),
    ))
    errors.extend(_validate_strategy_semantics(prompt))
    errors.extend(_validate_complexity(prompt.get("complexity"), PROMPT_SECTIONS))
    errors.extend(_validate_gates(prompt.get("quality_gates")))
    errors.extend(_validate_exception_authority(_mapping(prompt.get("complexity")), trace, prompt.get("actor_id", "")))
    superseded = prompt.get("supersedes_attempt_ids")
    if (
        not isinstance(superseded, list)
        or any(not _nonempty_string(item) for item in superseded)
        or len(superseded) != len({item for item in superseded if isinstance(item, str)})
    ):
        errors.append("supersedes_attempt_ids must be a unique string list")

    events = _event_map(trace)
    calls = _call_map(trace)
    handoff = events.get(handoff_id) if isinstance(handoff_id, str) else None
    target_event = events.get(event_id) if isinstance(event_id, str) else None
    target_call = calls.get(call_id) if isinstance(call_id, str) else None
    if not isinstance(handoff, dict) or handoff.get("kind") != "handoff":
        errors.append("prompt handoff_event_id must resolve to a handoff")
    expected_event_kind = event_kinds.get(phase) if isinstance(phase, str) else None
    if not isinstance(target_event, dict) or target_event.get("kind") != expected_event_kind:
        errors.append("prompt target_event_id does not match its phase")
    if not isinstance(target_call, dict) or target_call.get("phase") != _expected_call_phase(phase):
        errors.append("prompt target_call_id does not match its phase")
    if isinstance(handoff, dict):
        payload = _mapping(handoff.get("payload"))
        state = _mapping(payload.get("state"))
        if state.get("phase") != phase:
            errors.append("prompt phase must match its handoff state")
        if _mapping(payload.get("output")).get("event_ref") != event_id:
            errors.append("prompt target_event_id must match handoff output.event_ref")
        if handoff.get("to_actor_id") != prompt.get("actor_id"):
            errors.append("prompt actor must match handoff.to_actor_id")
    if isinstance(target_event, dict):
        target_payload = _mapping(target_event.get("payload"))
        if target_payload.get("handoff_ref") != handoff_id:
            errors.append("target event must point back to handoff_event_id")
        if target_payload.get("tool_call_ref") != call_id:
            errors.append("target event must point to target_call_id")
        if target_event.get("actor_id") != prompt.get("actor_id"):
            errors.append("prompt actor must match target event actor")
    if isinstance(target_call, dict) and target_call.get("prompt_id") != prompt_id:
        errors.append("target tool call must point back to prompt_id")
    if prompt.get("strategy") == "tool_augmented" and isinstance(target_call, dict):
        tools = _list(_mapping(prompt.get("strategy_details")).get("tools"))
        if target_call.get("name") not in tools:
            errors.append("tool_augmented strategy tools must include the target tool call")
    return errors


def _validate_attempt(
    attempt: Any,
    trace: Mapping[str, Any],
    attempt_ids: set,
    prior_by_id: Dict[str, Dict[str, Any]],
) -> List[str]:
    errors: List[str] = []
    if not _exact_fields(attempt, ATTEMPT_FIELDS):
        return ["prompt attempt must contain the exact versioned attempt fields"]
    version = _schema_version(trace)
    contracts = _prompt_contracts(version)
    phase_contracts = _phase_contracts(version)
    attempt_id = attempt.get("attempt_id")
    if not _nonempty_string(attempt_id) or attempt_id in attempt_ids:
        errors.append("attempt IDs must be non-empty and unique")
    if isinstance(attempt_id, str):
        attempt_ids.add(attempt_id)
    if not _nonempty_string(attempt.get("prompt_family_id")):
        errors.append("attempt prompt_family_id must be non-empty")
    if not _nonempty_string(attempt.get("handoff_event_id")):
        errors.append("attempt handoff_event_id must be non-empty")
    previous = attempt.get("previous_attempt_id")
    if previous is not None and not _nonempty_string(previous):
        errors.append("previous_attempt_id must be null or a non-empty ID")
    if previous is not None and (not isinstance(previous, str) or previous not in prior_by_id):
        errors.append("previous_attempt_id must resolve to an earlier attempt")
    if isinstance(previous, str) and previous in prior_by_id and prior_by_id[previous].get("prompt_family_id") != attempt.get("prompt_family_id"):
        errors.append("attempt predecessor must share prompt_family_id")
    errors.extend(validate_modules(attempt.get("modules")))
    errors.extend(validate_rendered_prompt(attempt.get("rendered_prompt")))
    errors.extend(_validate_output_contract_text(attempt.get("output_contract_id"), attempt.get("rendered_prompt"), contracts))
    rendered_prompt = attempt.get("rendered_prompt")
    if isinstance(rendered_prompt, str) and attempt.get("normalized_sha256") != prompt_sha256(rendered_prompt):
        errors.append("attempt normalized_sha256 does not match rendered_prompt")
    if attempt.get("sections") != list(PROMPT_SECTIONS):
        errors.append("attempt sections must be canonical")
    if attempt.get("language") != "en":
        errors.append("attempt language must be en")
    handoff_id = attempt.get("handoff_event_id")
    handoff = _event_map(trace).get(handoff_id) if isinstance(handoff_id, str) else None
    phase = _mapping(_mapping(handoff).get("payload")).get("state")
    phase = _mapping(phase).get("phase")
    if isinstance(phase, str) and phase in phase_contracts and attempt.get("output_contract_id") != phase_contracts[phase]:
        errors.append("attempt output_contract_id does not match its phase")
    errors.extend(_validate_strategy(
        attempt.get("strategy"),
        attempt.get("strategy_reason"),
        attempt.get("selection_evidence"),
        attempt.get("strategy_details", {}),
    ))
    errors.extend(_validate_strategy_semantics(attempt, allow_failed_gates=True))
    errors.extend(_validate_complexity(attempt.get("complexity"), PROMPT_SECTIONS, allow_blocked_overage=True))
    errors.extend(_validate_gates(attempt.get("quality_gates"), allow_fail=True))
    if not _string_ids(attempt.get("failure_codes"), nonempty=True):
        errors.append("blocked attempts need non-empty failure_codes")
    if not _string_ids(attempt.get("evidence"), nonempty=True):
        errors.append("blocked attempts need non-empty evidence")
    handoff = _event_map(trace).get(attempt.get("handoff_event_id")) if isinstance(attempt.get("handoff_event_id"), str) else None
    if not isinstance(handoff, dict) or handoff.get("kind") != "handoff":
        errors.append("attempt handoff_event_id must resolve to a handoff")
    if isinstance(attempt_id, str):
        prior_by_id[attempt_id] = attempt
    return errors


def _validate_prompt_review(trace: Mapping[str, Any], prompt_ids: set, attempt_ids: set) -> List[str]:
    errors: List[str] = []
    reviews = [
        event for event in _list(trace.get("events"))
        if isinstance(event, dict) and event.get("kind") == "review"
    ]
    if not reviews:
        return ["at least one review event is required for prompt_review"]
    warning_ids = {
        prompt.get("prompt_id")
        for prompt in _list(trace.get("prompts"))
        if isinstance(prompt, dict)
        and isinstance(prompt.get("prompt_id"), str)
        and (_decimal(_mapping(prompt.get("complexity")).get("total")) or Decimal("0")) >= PCP_WARNING_THRESHOLD
    }
    for event in reviews:
        review = _mapping(_mapping(event.get("payload")).get("prompt_review"))
        expected_fields = {"prompt_ids", "attempt_ids", "result", "gaps", "warnings_acknowledged", "evidence"}
        if set(review) != expected_fields:
            errors.append("review %s has no exact prompt_review block" % event.get("event_id"))
            continue
        if set(_string_ids(review.get("prompt_ids"), nonempty=True)) != prompt_ids:
            errors.append("review %s must cover every prompt" % event.get("event_id"))
        if set(_string_ids(review.get("attempt_ids"), nonempty=True)) != attempt_ids:
            errors.append("review %s must cover every prompt attempt" % event.get("event_id"))
        if not isinstance(review.get("result"), str) or review.get("result") not in {"pass", "needs_repair"}:
            errors.append("review %s has an invalid prompt_review result" % event.get("event_id"))
        if not isinstance(review.get("gaps"), list) or any(not _nonempty_string(item) for item in review.get("gaps")):
            errors.append("review %s prompt_review gaps must be a string list" % event.get("event_id"))
        if set(_string_ids(review.get("warnings_acknowledged"), nonempty=True)) != warning_ids:
            errors.append("review %s must acknowledge every PCP warning" % event.get("event_id"))
        if not _string_ids(review.get("evidence"), nonempty=True):
            errors.append("review %s prompt_review needs evidence" % event.get("event_id"))
    return errors


def validate_prompt_catalog(trace: Mapping[str, Any]) -> List[str]:
    """Validate the versioned prompt declaration and prompt-related records."""

    errors: List[str] = []
    contract = _mapping(trace.get("trace_contract"))
    version = _schema_version(trace)
    errors.extend(validate_prompt_declaration(contract.get("prompt"), version))
    prompts = trace.get("prompts")
    attempts = trace.get("prompt_attempts")
    if not isinstance(prompts, list):
        errors.append("prompts must be a list")
        prompts = []
    if not isinstance(attempts, list):
        errors.append("prompt_attempts must be a list")
        attempts = []

    prompt_ids: set = set()
    handoff_ids: set = set()
    target_event_ids: set = set()
    target_call_ids: set = set()
    for prompt in prompts:
        errors.extend(_validate_prompt_record(prompt, trace, prompt_ids, handoff_ids, target_event_ids, target_call_ids))

    seen_prompt_ids: set = set()
    for prompt in prompts:
        if not isinstance(prompt, dict) or prompt.get("strategy") != "chained":
            if isinstance(prompt, dict) and isinstance(prompt.get("prompt_id"), str):
                seen_prompt_ids.add(prompt.get("prompt_id"))
            continue
        details = _mapping(prompt.get("strategy_details"))
        step_index = details.get("step_index")
        dependencies = details.get("depends_on_prompt_ids")
        if step_index == 1 and dependencies:
            errors.append("first chained prompt must not depend on a predecessor")
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if not isinstance(dependency, str) or dependency not in seen_prompt_ids:
                    errors.append("chained prompt dependency must resolve to an earlier prompt")
                if isinstance(dependency, str) and dependency == prompt.get("prompt_id"):
                    errors.append("chained prompt cannot depend on itself")
        if isinstance(prompt.get("prompt_id"), str):
            seen_prompt_ids.add(prompt.get("prompt_id"))

    attempt_ids: set = set()
    prior_by_id: Dict[str, Dict[str, Any]] = {}
    family_counts: Dict[str, int] = {}
    for attempt in attempts:
        errors.extend(_validate_attempt(attempt, trace, attempt_ids, prior_by_id))
        if isinstance(attempt, dict) and isinstance(attempt.get("prompt_family_id"), str):
            family_counts[attempt["prompt_family_id"]] = family_counts.get(attempt["prompt_family_id"], 0) + 1
    for family, count in family_counts.items():
        if count > 3:
            errors.append("prompt_family_id %s has more than three attempts" % family)

    events = _event_map(trace)
    calls = _call_map(trace)
    for event_id, event in events.items():
        if event.get("kind") != "handoff":
            continue
        target_event, target_call = _handoff_target(trace, event)
        if target_event is None or target_call is None:
            continue
        if event_id not in handoff_ids:
            errors.append("handoff %s has no dispatched prompt record" % event_id)
    for call_id, call in calls.items():
        if "prompt_id" not in call:
            errors.append("tool call %s must declare prompt_id, including null for direct actions" % call_id)
            continue
        prompt_id = call.get("prompt_id")
        if prompt_id is not None and (not isinstance(prompt_id, str) or prompt_id not in prompt_ids):
            errors.append("tool call %s points to an unknown prompt_id" % call_id)
        if prompt_id is None and call_id in target_call_ids:
            errors.append("prompt target call %s cannot have prompt_id null" % call_id)
    for prompt in prompts:
        if not isinstance(prompt, dict):
            continue
        for attempt_id in _list(prompt.get("supersedes_attempt_ids")):
            if not isinstance(attempt_id, str):
                errors.append("prompt %s supersedes an invalid attempt ID" % prompt.get("prompt_id"))
                continue
            attempt = prior_by_id.get(attempt_id)
            if attempt is None:
                errors.append("prompt %s supersedes an unknown attempt" % prompt.get("prompt_id"))
            elif attempt.get("prompt_family_id") != prompt.get("prompt_family_id") or attempt.get("handoff_event_id") != prompt.get("handoff_event_id"):
                errors.append("prompt %s supersedes an unrelated attempt" % prompt.get("prompt_id"))

    errors.extend(_validate_prompt_review(trace, prompt_ids, attempt_ids))
    evidence_ids = {
        item.get("evidence_id")
        for item in _list(trace.get("evidence"))
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    for record in list(prompts) + list(attempts):
        if not isinstance(record, dict):
            continue
        refs = list(_string_ids(record.get("selection_evidence"), nonempty=True))
        refs.extend(
            evidence_id
            for gate in _mapping(record.get("quality_gates")).values()
            for evidence_id in _string_ids(_mapping(gate).get("evidence"), nonempty=True)
        )
        complexity = _mapping(record.get("complexity"))
        exception = complexity.get("exception")
        if isinstance(exception, dict):
            refs.extend(_string_ids(exception.get("evidence"), nonempty=True))
        refs.extend(_string_ids(record.get("evidence"), nonempty=True))
        if any(ref not in evidence_ids for ref in refs):
            errors.append("prompt metadata references unknown evidence")
    for event in _list(trace.get("events")):
        if not isinstance(event, dict):
            continue
        review = _mapping(_mapping(event.get("payload")).get("prompt_review"))
        if review:
            if any(ref not in evidence_ids for ref in _string_ids(review.get("evidence"), nonempty=True)):
                errors.append("prompt_review references unknown evidence")
    return errors


def validate_module_root(trace: Mapping[str, Any], root: Path) -> List[str]:
    """Optionally compare declared module hashes with an explicit repository root."""

    errors: List[str] = []
    records = list(_list(trace.get("prompts"))) + list(_list(trace.get("prompt_attempts")))
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        for module in _list(record.get("modules")):
            if not isinstance(module, dict):
                continue
            path = module.get("path")
            if not isinstance(path, str):
                continue
            if path in seen:
                continue
            seen.add(path)
            candidate = root / Path(path)
            try:
                digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            except OSError as exc:
                errors.append("cannot read module %s: %s" % (path, exc))
                continue
            if digest != module.get("sha256"):
                errors.append("module hash mismatch for %s" % path)
    return errors


def _load_trace(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("trace root must be an object")
    return value


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate saturation prompt contract records.")
    parser.add_argument("--trace", type=Path, required=True, help="versioned trace JSON file")
    parser.add_argument("--root", type=Path, help="optional repository root for module hash checks")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON errors")
    args = parser.parse_args(argv)
    try:
        trace = _load_trace(args.trace)
        errors = []
        if trace.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
            errors.append("schema_version must be 3, 4, or 5")
        errors.extend(validate_prompt_catalog(trace))
        if args.root is not None:
            errors.extend(validate_module_root(trace, args.root))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    payload = {"ok": not errors, "trace": str(args.trace), "errors": errors}
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("PROMPT CONTRACT: %s" % ("PASS" if payload["ok"] else "FAIL"))
        for error in errors:
            print("  " + error)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
