"""Feedback Collector — link corrections to specific assessment traces.

When a result is corrected ("this was actually normal breathing"),
the correction is linked to the specific StepTrace so we can:
1. Identify which prompts produce wrong results
2. Generate correction pairs for prompt improvement
3. Create fine-tuning data from real-world corrections
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Correction:
    """A correction linking a wrong result to what was actually correct."""

    session_id: str
    step_index: int               # Index into AssessmentTrace.steps
    prompt_name: str              # Which prompt produced the wrong result
    prompt_version: str

    original_output: str          # What the model said (truncated)
    original_parsed: str          # How it was parsed

    corrected_value: str          # What it should have been
    correction_reason: str        # Why it was wrong

    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


class FeedbackCollector:
    """Collects and exports corrections for prompt improvement.

    Usage:
        collector = FeedbackCollector()
        collector.add_correction(
            session_id="abc123",
            step_index=2,
            prompt_name="breathing.count_rate_from_video",
            prompt_version="1.0.0",
            original_output='{"breath_count": 8}',
            original_parsed="BreathingRateResult(breath_count=8, rate=32)",
            corrected_value="breath_count should be 14 (rate=56)",
            correction_reason="Model undercounted — chest movements were subtle",
        )
    """

    def __init__(self) -> None:
        self._corrections: list[Correction] = []

    def add_correction(
        self,
        *,
        session_id: str,
        step_index: int,
        prompt_name: str,
        prompt_version: str,
        original_output: str,
        original_parsed: str,
        corrected_value: str,
        correction_reason: str,
    ) -> Correction:
        """Record a correction.

        Args:
            session_id: Which assessment session.
            step_index: Which step in the assessment trace.
            prompt_name: The prompt that produced wrong output.
            prompt_version: Version of the prompt.
            original_output: What the model said (raw, truncated).
            original_parsed: How we parsed it.
            corrected_value: What the correct answer should be.
            correction_reason: Human explanation of why it was wrong.

        Returns:
            The recorded Correction.
        """
        correction = Correction(
            session_id=session_id,
            step_index=step_index,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            original_output=original_output[:500],
            original_parsed=original_parsed,
            corrected_value=corrected_value,
            correction_reason=correction_reason,
        )
        self._corrections.append(correction)
        return correction

    @property
    def corrections(self) -> list[Correction]:
        """All recorded corrections."""
        return list(self._corrections)

    def corrections_for_prompt(self, prompt_name: str) -> list[Correction]:
        """Get all corrections for a specific prompt.

        Args:
            prompt_name: The prompt to filter by.

        Returns:
            List of corrections for this prompt.
        """
        return [c for c in self._corrections if c.prompt_name == prompt_name]

    def export_json(self, output_path: Path) -> None:
        """Export all corrections to JSON for analysis.

        Args:
            output_path: Path to write the JSON file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data: list[dict[str, Any]] = [
            {
                "session_id": c.session_id,
                "step_index": c.step_index,
                "prompt_name": c.prompt_name,
                "prompt_version": c.prompt_version,
                "original_output": c.original_output,
                "original_parsed": c.original_parsed,
                "corrected_value": c.corrected_value,
                "correction_reason": c.correction_reason,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in self._corrections
        ]

        output_path.write_text(json.dumps(data, indent=2))

    def clear(self) -> None:
        """Clear all corrections."""
        self._corrections.clear()
