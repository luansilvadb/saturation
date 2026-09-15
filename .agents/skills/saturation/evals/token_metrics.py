"""Deterministic, descriptive token metrics for saturation prompt traces.

The fixture estimator is intentionally a stable proxy rather than a claim
about any provider tokenizer.  Provider measurements are optional telemetry
and never participate in the workflow grade.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import prompt_contract


TOKEN_USAGE_VERSION = 1
TOKEN_USAGE_KEY = "token_usage"
TOKEN_USAGE_FIELDS = ("version", "records")
TOKEN_USAGE_RECORD_FIELDS = (
    "prompt_id",
    "input_tokens",
    "measurement_scope",
    "provider",
    "model",
    "encoding",
)
ESTIMATOR_ID = "utf8_bytes_div4_v1"
ESTIMATOR_SCOPE = "normalized_rendered_prompt"
OBSERVED_SCOPE = "api_request"


def estimate_input_tokens(text: str) -> int:
    """Estimate input tokens from canonical prompt bytes.

    The estimator is deliberately versioned and model-independent.  Four
    UTF-8 bytes are treated as one estimated token, rounded up, with a minimum
    of one token for non-empty prompts.
    """

    normalized = prompt_contract.normalize_prompt(text)
    byte_count = len(normalized.encode("utf-8"))
    return max(1, (byte_count + 3) // 4)


def _stable_number(value: float) -> Optional[float]:
    if not math.isfinite(value):
        return None
    return int(value) if value.is_integer() else round(value, 3)


def _percentile(values: Sequence[int], fraction: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return _stable_number(float(ordered[rank]))


def summarize_rows(
    rows: Iterable[Mapping[str, Any]], *, include_records: bool = True
) -> Dict[str, Any]:
    """Summarize rows carrying ``phase`` and integer ``input_tokens``."""

    materialized = [dict(row) for row in rows]
    values = [
        int(row["input_tokens"])
        for row in materialized
        if isinstance(row.get("input_tokens"), int)
        and not isinstance(row.get("input_tokens"), bool)
        and row.get("input_tokens") >= 0
    ]

    def stats(numbers: Sequence[int]) -> Dict[str, Any]:
        return {
            "count": len(numbers),
            "total": sum(numbers),
            "average": _stable_number(sum(numbers) / len(numbers)) if numbers else None,
            "max": max(numbers) if numbers else None,
            "p50": _percentile(numbers, 0.50),
            "p95": _percentile(numbers, 0.95),
        }

    by_phase: Dict[str, List[int]] = defaultdict(list)
    for row in materialized:
        value = row.get("input_tokens")
        phase = row.get("phase", "unknown")
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
        ):
            by_phase[str(phase)].append(value)

    result = stats(values)
    result["by_phase"] = {
        phase: stats(numbers)
        for phase, numbers in sorted(by_phase.items())
    }
    if include_records:
        result["records"] = materialized
    return result


def _event_phase_map(trace: Mapping[str, Any]) -> Dict[str, str]:
    phases: Dict[str, str] = {}
    events = trace.get("events", [])
    if not isinstance(events, list):
        return phases
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = event.get("event_id")
        payload = event.get("payload")
        if not isinstance(event_id, str) or not isinstance(payload, dict):
            continue
        state = payload.get("state")
        if isinstance(state, dict) and isinstance(state.get("phase"), str):
            phases[event_id] = state["phase"]
    return phases


def _record_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _estimated_rows(
    prompts: Sequence[Mapping[str, Any]],
    *,
    id_key: str,
    phase_for_row: Optional[Mapping[str, str]] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, record in enumerate(prompts):
        text = record.get("rendered_prompt")
        if not isinstance(text, str):
            continue
        identifier = record.get(id_key)
        if not isinstance(identifier, str) or not identifier:
            identifier = "%s-%d" % (id_key, index)
        phase = record.get("phase")
        if not isinstance(phase, str) and phase_for_row is not None:
            handoff_id = record.get("handoff_event_id")
            phase = phase_for_row.get(handoff_id)
        rows.append(
            {
                "id": identifier,
                "phase": phase if isinstance(phase, str) and phase else "unknown",
                "input_tokens": estimate_input_tokens(text),
            }
        )
    return rows


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def observed_usage(trace: Mapping[str, Any]) -> Dict[str, Any]:
    """Parse optional ``evaluation.token_usage`` without affecting grading."""

    empty: Dict[str, Any] = {
        "status": "not_available",
        "measurement_scope": None,
        "provider": None,
        "model": None,
        "encoding": None,
        "record_count": 0,
        "missing_prompt_ids": [],
        "unknown_prompt_ids": [],
        "errors": [],
        "records": [],
    }
    evaluation = trace.get("evaluation")
    if not isinstance(evaluation, dict) or TOKEN_USAGE_KEY not in evaluation:
        return empty

    block = evaluation.get(TOKEN_USAGE_KEY)
    errors: List[str] = []
    if not isinstance(block, dict):
        return {**empty, "status": "invalid", "errors": ["token_usage must be an object"]}
    if set(block) != set(TOKEN_USAGE_FIELDS):
        errors.append("token_usage must contain exactly version and records")
    if (
        not isinstance(block.get("version"), int)
        or isinstance(block.get("version"), bool)
        or block.get("version") != TOKEN_USAGE_VERSION
    ):
        errors.append("token_usage.version must be 1")
    records = block.get("records")
    if not isinstance(records, list):
        errors.append("token_usage.records must be a list")
        records = []

    prompts = _record_list(trace.get("prompts", []))
    prompt_ids = {
        prompt.get("prompt_id")
        for prompt in prompts
        if isinstance(prompt, dict) and isinstance(prompt.get("prompt_id"), str)
    }
    seen: set[str] = set()
    normalized_records: List[Dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append("token_usage record %d must be an object" % index)
            continue
        if set(record) != set(TOKEN_USAGE_RECORD_FIELDS):
            errors.append("token_usage record %d has the wrong fields" % index)
            continue
        prompt_id = record.get("prompt_id")
        if not _nonempty_string(prompt_id):
            errors.append("token_usage record %d prompt_id must be non-empty" % index)
        elif prompt_id in seen:
            errors.append("token_usage prompt IDs must be unique")
        else:
            seen.add(prompt_id)
        if not _valid_nonnegative_int(record.get("input_tokens")):
            errors.append("token_usage input_tokens must be a non-negative integer")
        if record.get("measurement_scope") != OBSERVED_SCOPE:
            errors.append("token_usage measurement_scope must be api_request")
        for field in ("provider", "model", "encoding"):
            if not _nonempty_string(record.get(field)):
                errors.append("token_usage %s must be non-empty" % field)
        if (
            _nonempty_string(prompt_id)
            and prompt_id not in prompt_ids
        ):
            empty["unknown_prompt_ids"].append(prompt_id)
        if _nonempty_string(prompt_id) and _valid_nonnegative_int(record.get("input_tokens")):
            normalized_records.append(dict(record))

    missing = sorted(prompt_ids - seen)
    unknown = sorted(set(empty["unknown_prompt_ids"]))
    if missing:
        errors.append("token_usage is missing prompt IDs: " + ",".join(missing))
    if unknown:
        errors.append("token_usage contains unknown prompt IDs: " + ",".join(unknown))

    if errors:
        return {
            **empty,
            "status": "invalid",
            "record_count": len(records),
            "missing_prompt_ids": missing,
            "unknown_prompt_ids": unknown,
            "errors": errors,
        }

    profiles = {
        (
            record["measurement_scope"],
            record["provider"],
            record["model"],
            record["encoding"],
        )
        for record in normalized_records
    }
    if len(profiles) == 1:
        scope, provider, model, encoding = next(iter(profiles))
    else:
        scope = OBSERVED_SCOPE
        provider = model = encoding = None
    return {
        "status": "available",
        "measurement_scope": scope,
        "provider": provider,
        "model": model,
        "encoding": encoding,
        "record_count": len(normalized_records),
        "missing_prompt_ids": [],
        "unknown_prompt_ids": [],
        "errors": [],
        "records": normalized_records,
    }


def build_metrics(trace: Mapping[str, Any]) -> Dict[str, Any]:
    """Build estimated and optional observed prompt-input token metrics."""

    prompts = _record_list(trace.get("prompts", []))
    attempts = _record_list(trace.get("prompt_attempts", []))
    phase_map = _event_phase_map(trace)
    estimated_prompts = _estimated_rows(
        prompts,
        id_key="prompt_id",
    )
    estimated_attempts = _estimated_rows(
        attempts,
        id_key="attempt_id",
        phase_for_row=phase_map,
    )
    observed = observed_usage(trace)
    prompt_phase = {
        row["prompt_id"]: row.get("phase", "unknown")
        for row in prompts
        if isinstance(row.get("prompt_id"), str)
    }
    observed_rows = [
        {
            "id": record["prompt_id"],
            "phase": prompt_phase.get(record["prompt_id"], "unknown"),
            "input_tokens": record["input_tokens"],
        }
        for record in observed["records"]
    ]

    return {
        "estimated": {
            "estimator": ESTIMATOR_ID,
            "measurement_scope": ESTIMATOR_SCOPE,
            "dispatched": summarize_rows(estimated_prompts),
            "attempts": summarize_rows(estimated_attempts),
        },
        "observed": {
            "status": observed["status"],
            "measurement_scope": observed["measurement_scope"],
            "provider": observed["provider"],
            "model": observed["model"],
            "encoding": observed["encoding"],
            "record_count": observed["record_count"],
            "missing_prompt_ids": observed["missing_prompt_ids"],
            "unknown_prompt_ids": observed["unknown_prompt_ids"],
            "errors": observed["errors"],
            "dispatched": summarize_rows(observed_rows),
        },
    }
