"""Output Validator — Layer 3: Validate model output before clinical logic.

Checks: valid JSON (if expected), schema conformance, physiological plausibility,
confidence thresholds.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from malaika.types import ValidatedOutput

if TYPE_CHECKING:
    from malaika.config import GuardConfig
    from malaika.prompts.base import PromptTemplate


class OutputParseError(Exception):
    """Model output could not be parsed or validated.

    This triggers the self-correction retry in inference.py.
    """


# ---------------------------------------------------------------------------
# Physiological plausibility ranges
# ---------------------------------------------------------------------------

_PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "breath_count": (0, 30),  # Max for 15s video (120/min)
    "breathing_rate": (5, 120),  # Breaths per minute (pediatric)
    "estimated_rate_per_minute": (5, 120),
    "heart_rate": (60, 220),  # BPM (pediatric)
    "estimated_bpm": (60, 220),
    "confidence": (0.0, 1.0),
    "muac_mm": (50, 250),  # Mid-upper arm circumference
}


def validate_output(
    raw_output: str,
    prompt: PromptTemplate,
    config: GuardConfig,
) -> ValidatedOutput:
    """Validate model output against prompt's expected format and schema.

    Args:
        raw_output: Raw text output from Gemma 4.
        prompt: The PromptTemplate used (defines expected format/schema).
        config: Guard configuration with confidence thresholds.

    Returns:
        ValidatedOutput with parsed data and status.

    Raises:
        OutputParseError: If output is invalid and should trigger self-correction.
    """
    if prompt.expected_output_format == "text":
        # Free-form text (treatment, conversation) — minimal validation
        if not raw_output.strip():
            raise OutputParseError("Model returned empty output")
        return ValidatedOutput(
            status="valid",
            parsed={"text": raw_output.strip()},
            raw_output=raw_output,
        )

    if prompt.expected_output_format == "json":
        return _validate_json_output(raw_output, prompt, config)

    if prompt.expected_output_format == "number":
        return _validate_number_output(raw_output, prompt, config)

    raise OutputParseError(f"Unknown expected format: {prompt.expected_output_format}")


def _validate_json_output(
    raw_output: str,
    prompt: PromptTemplate,
    config: GuardConfig,
) -> ValidatedOutput:
    """Validate JSON output from model."""

    # 1. Extract JSON from model output (may have surrounding text)
    parsed = _extract_json(raw_output)
    if parsed is None:
        raise OutputParseError(
            f"Could not extract valid JSON from model output. "
            f"Raw output starts with: {raw_output[:200]!r}"
        )

    # 2. Schema validation (if schema defined)
    if prompt.output_schema is not None:
        _check_required_fields(parsed, prompt.output_schema)

    # 3. Physiological plausibility
    for field_name, value in parsed.items():
        if field_name in _PLAUSIBLE_RANGES and isinstance(value, (int, float)):
            lo, hi = _PLAUSIBLE_RANGES[field_name]
            if not (lo <= value <= hi):
                raise OutputParseError(
                    f"Implausible value for '{field_name}': {value} (expected range: {lo}-{hi})"
                )

    # 4. Confidence gating
    confidence = parsed.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < config.minimum_confidence:
        return ValidatedOutput(
            status="uncertain",
            parsed=parsed,
            raw_output=raw_output,
        )

    return ValidatedOutput(
        status="valid",
        parsed=parsed,
        raw_output=raw_output,
    )


def _validate_number_output(
    raw_output: str,
    prompt: PromptTemplate,
    config: GuardConfig,
) -> ValidatedOutput:
    """Validate numeric output from model."""
    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", raw_output)
    if not numbers:
        raise OutputParseError(
            f"Could not extract a number from model output: {raw_output[:200]!r}"
        )

    value = float(numbers[0])
    return ValidatedOutput(
        status="valid",
        parsed={"value": value},
        raw_output=raw_output,
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from model output, handling common quirks.

    Models often wrap JSON in markdown code blocks or add explanatory text.
    This function tries multiple extraction strategies.
    """
    # Strategy 1: Direct parse
    try:
        result = json.loads(text.strip())
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: Find JSON in markdown code block
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block:
        try:
            result = json.loads(code_block.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first { ... } block
    brace_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 4: Find nested { ... { ... } ... } block
    nested_match = re.search(r"\{(?:[^{}]|\{[^{}]*\})*\}", text, re.DOTALL)
    if nested_match:
        try:
            result = json.loads(nested_match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


def _check_required_fields(parsed: dict[str, Any], schema: dict[str, Any]) -> None:
    """Check that required fields from schema are present in parsed output."""
    required = schema.get("required", [])
    missing = [f for f in required if f not in parsed]
    if missing:
        raise OutputParseError(
            f"Missing required fields in model output: {missing}. Got fields: {list(parsed.keys())}"
        )


def build_correction_prompt(
    original_prompt: PromptTemplate,
    failed_output: str,
    error_message: str,
    attempt: int,
) -> str:
    """Build a correction prompt for self-correction retry.

    Args:
        original_prompt: The prompt that produced invalid output.
        failed_output: The model's invalid output.
        error_message: Why the output was rejected.
        attempt: Which retry attempt this is (1 or 2).

    Returns:
        Correction instruction to append to the conversation.
    """
    if attempt == 1:
        # First retry: explain the error, ask for correct format
        schema_hint = ""
        if original_prompt.output_schema:
            required = original_prompt.output_schema.get("required", [])
            schema_hint = f" Required fields: {required}."

        return (
            f"Your previous response could not be parsed. "
            f"Error: {error_message}\n\n"
            f"Please respond ONLY with a valid JSON object.{schema_hint}\n"
            f"Do not include any text before or after the JSON."
        )

    # Second retry: simplify — just ask for the most critical fields
    return (
        "Please respond with ONLY a JSON object on a single line. "
        "Include at minimum a 'confidence' field (0.0 to 1.0). "
        'Example format: {"confidence": 0.8, "description": "your observation"}'
    )
