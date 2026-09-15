"""Deterministic routing for a bounded, non-private reasoning scaffold."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


POLICY_VERSION = "reasoning-scaffold-v1"
DECISION_DIRECT = "direct"
DECISION_ACTIVATE = "activate"
DECISION_ESCALATE = "escalate"
ACTIVATION_TRIGGER_CODES = (
    "interdependent_acceptance",
    "cross_module_dependency",
    "material_repair",
)
ESCALATION_TRIGGER_CODE = "user_decision_required"
USER_DECISION_SIGNAL = "requires_user_decision"
SIGNAL_FIELDS = ACTIVATION_TRIGGER_CODES + (USER_DECISION_SIGNAL,)
SCAFFOLD_FIELDS = (
    "intended_behavior",
    "assumptions",
    "invariants_and_risks",
    "planned_checks",
    "evidence_refs",
)


def _validate_inputs(
    signals: Mapping[str, bool], evidence_ids: Sequence[str]
) -> None:
    """Validate the exact, evidence-backed classifier inputs."""

    if not isinstance(signals, Mapping) or set(signals) != set(SIGNAL_FIELDS):
        raise ValueError("signals must contain the four canonical signal names")
    if any(type(signals[name]) is not bool for name in SIGNAL_FIELDS):
        raise ValueError("all scaffold signals must be booleans")
    if isinstance(evidence_ids, (str, bytes)) or not isinstance(
        evidence_ids, Sequence
    ):
        raise ValueError("evidence_ids must be a sequence of evidence IDs")
    values = list(evidence_ids)
    if not values or any(
        not isinstance(value, str)
        or not value.startswith("EV-")
        or not value[3:].strip()
        for value in values
    ):
        raise ValueError(
            "evidence_ids must contain non-empty EV- identifiers"
        )
    if len(set(values)) != len(values):
        raise ValueError("evidence_ids must not contain duplicates")


def classify_activation(
    signals: Mapping[str, bool], evidence_ids: Sequence[str]
) -> Dict[str, Any]:
    """Select direct, scaffold, or escalation routing from fixed signals.

    Args:
        signals: The four canonical boolean preflight signals.
        evidence_ids: Registered evidence supporting the preflight decision.

    Returns:
        A deterministic routing record with scaffold fields when activated.

    Raises:
        ValueError: If the signal or evidence contract is malformed.
    """

    _validate_inputs(signals, evidence_ids)
    evidence = list(evidence_ids)
    if signals[USER_DECISION_SIGNAL]:
        return {
            "policy_version": POLICY_VERSION,
            "decision": DECISION_ESCALATE,
            "trigger_codes": [ESCALATION_TRIGGER_CODE],
            "reason": (
                "A user decision is required before implementation routing."
            ),
            "selection_evidence": evidence,
            "scaffold_fields": [],
        }

    active_triggers = [
        code for code in ACTIVATION_TRIGGER_CODES if signals[code]
    ]
    if active_triggers:
        return {
            "policy_version": POLICY_VERSION,
            "decision": DECISION_ACTIVATE,
            "trigger_codes": active_triggers,
            "reason": "An approved task signal requires a bounded scaffold.",
            "selection_evidence": evidence,
            "scaffold_fields": list(SCAFFOLD_FIELDS),
        }

    return {
        "policy_version": POLICY_VERSION,
        "decision": DECISION_DIRECT,
        "trigger_codes": [],
        "reason": "No approved scaffold activation signal is present.",
        "selection_evidence": evidence,
        "scaffold_fields": [],
    }


def scaffold_instructions() -> str:
    """Return the bounded prompt text for an activated scaffold.

    Returns:
        English instructions for a concise, evidence-oriented summary.
    """

    return (
        "Return only a concise structured summary with these fields: "
        "intended_behavior, assumptions, invariants_and_risks, "
        "planned_checks, and evidence_refs. State checks and decisions at a "
        "high level. Do not provide hidden chain-of-thought or a private "
        "scratchpad, and do not include secrets or unnecessary PII."
    )
