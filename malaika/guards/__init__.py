"""Security Guard Pipeline — three-layer validation for every perception call.

Usage:
    from malaika.guards import run_input_pipeline, run_output_pipeline

    validated = run_input_pipeline(file_path, media_type="image", config=guard_config)
    # ... inference happens ...
    result = run_output_pipeline(raw_output, prompt=prompt_template, config=guard_config)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from malaika.guards.content_filter import sanitize_text, wrap_safe_prompt
from malaika.guards.input_guard import validate_file
from malaika.guards.output_validator import validate_output

if TYPE_CHECKING:
    from pathlib import Path

    from malaika.config import GuardConfig
    from malaika.prompts.base import PromptTemplate
    from malaika.types import ValidatedInput, ValidatedOutput


def run_input_pipeline(
    file_path: Path,
    media_type: str,
    config: GuardConfig,
) -> ValidatedInput:
    """Run input guard on a file. Raises InputValidationError on failure.

    Args:
        file_path: Path to the file to validate.
        media_type: One of "image", "audio", "video".
        config: Guard configuration with size limits and allowed formats.

    Returns:
        ValidatedInput with confirmed format and size.

    Raises:
        InputValidationError: If validation fails at any step.
    """
    return validate_file(file_path, media_type, config)


def run_output_pipeline(
    raw_output: str,
    prompt: PromptTemplate,
    config: GuardConfig,
) -> ValidatedOutput:
    """Run output validator on model output.

    Args:
        raw_output: Raw text output from Gemma 4.
        prompt: The PromptTemplate that was used (for schema validation).
        config: Guard configuration with confidence thresholds.

    Returns:
        ValidatedOutput with parsed data and validation status.
    """
    return validate_output(raw_output, prompt, config)


__all__ = [
    "run_input_pipeline",
    "run_output_pipeline",
    "sanitize_text",
    "validate_file",
    "validate_output",
    "wrap_safe_prompt",
]
