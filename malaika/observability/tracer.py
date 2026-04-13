"""Tracer — per-IMCI-step trace recording.

Records what happened at each assessment step: input, prompt used,
model output, parsed result, confidence, and latency.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from malaika.types import AssessmentTrace, IMCIState, StepTrace


class Tracer:
    """Records per-step traces for an IMCI assessment session.

    Usage:
        tracer = Tracer(max_raw_output_length=500)
        tracer.start_session()
        tracer.record_step(...)
        trace = tracer.finish_session()
    """

    def __init__(self, max_raw_output_length: int = 500) -> None:
        self._max_raw_output_length = max_raw_output_length
        self._current_trace: AssessmentTrace | None = None

    @property
    def session_id(self) -> str | None:
        """Current session ID, or None if no session is active."""
        return self._current_trace.session_id if self._current_trace else None

    def start_session(self) -> str:
        """Start a new tracing session. Returns session ID.

        Returns:
            Unique session ID string.
        """
        session_id = uuid.uuid4().hex[:12]
        self._current_trace = AssessmentTrace(session_id=session_id)
        return session_id

    def record_step(
        self,
        *,
        imci_state: IMCIState,
        prompt_name: str,
        prompt_version: str,
        input_data: bytes | str | None = None,
        raw_output: str,
        parsed_result: str,
        confidence: float,
        latency_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        retries: int = 0,
        cache_hit: bool = False,
    ) -> StepTrace:
        """Record a single IMCI step trace.

        Args:
            imci_state: Which IMCI state this step belongs to.
            prompt_name: Name of the PromptTemplate used.
            prompt_version: Version of the prompt.
            input_data: Raw input bytes/str for hashing (NOT stored).
            raw_output: Model's raw text output (will be truncated).
            parsed_result: String representation of parsed result.
            confidence: Confidence score from the model.
            latency_ms: Inference time in milliseconds.
            tokens_in: Input token count.
            tokens_out: Output token count.
            retries: Number of self-correction retries used.
            cache_hit: Whether the response was served from cache.

        Returns:
            The recorded StepTrace.

        Raises:
            RuntimeError: If no session is active.
        """
        if self._current_trace is None:
            raise RuntimeError("No tracing session active. Call start_session() first.")

        # Hash input data — NEVER store raw media
        input_hash = ""
        if input_data is not None:
            data = input_data if isinstance(input_data, bytes) else input_data.encode()
            input_hash = f"sha256:{hashlib.sha256(data).hexdigest()[:16]}"

        # Truncate raw output for privacy/size
        truncated_output = raw_output[: self._max_raw_output_length]
        if len(raw_output) > self._max_raw_output_length:
            truncated_output += f"... [truncated, {len(raw_output)} chars total]"

        step = StepTrace(
            imci_state=imci_state,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            input_hash=input_hash,
            raw_output=truncated_output,
            parsed_result=parsed_result,
            confidence=confidence,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            retries=retries,
            cache_hit=cache_hit,
        )

        self._current_trace.steps.append(step)
        self._current_trace.total_tokens += tokens_in + tokens_out
        self._current_trace.total_latency_ms += latency_ms

        return step

    def finish_session(self) -> AssessmentTrace:
        """Finish the current tracing session and return the trace.

        Returns:
            Complete AssessmentTrace for the session.

        Raises:
            RuntimeError: If no session is active.
        """
        if self._current_trace is None:
            raise RuntimeError("No tracing session active.")

        self._current_trace.completed_at = datetime.now(tz=timezone.utc)
        trace = self._current_trace
        self._current_trace = None
        return trace

    @staticmethod
    def export_json(trace: AssessmentTrace, output_path: Path) -> None:
        """Export an assessment trace to a JSON file.

        Args:
            trace: The trace to export.
            output_path: Path to write the JSON file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "session_id": trace.session_id,
            "started_at": trace.started_at.isoformat(),
            "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
            "total_tokens": trace.total_tokens,
            "total_latency_ms": trace.total_latency_ms,
            "step_count": len(trace.steps),
            "steps": [
                {
                    "imci_state": step.imci_state.name,
                    "prompt_name": step.prompt_name,
                    "prompt_version": step.prompt_version,
                    "input_hash": step.input_hash,
                    "raw_output": step.raw_output,
                    "parsed_result": step.parsed_result,
                    "confidence": step.confidence,
                    "latency_ms": step.latency_ms,
                    "tokens_in": step.tokens_in,
                    "tokens_out": step.tokens_out,
                    "retries": step.retries,
                    "cache_hit": step.cache_hit,
                    "timestamp": step.timestamp.isoformat(),
                }
                for step in trace.steps
            ],
        }

        output_path.write_text(json.dumps(data, indent=2))
