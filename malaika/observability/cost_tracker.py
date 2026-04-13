"""Cost Tracker — token counts, latency, and VRAM monitoring per inference call.

Tracks the computational cost of each Gemma 4 call and aggregates
per-assessment totals for performance budget enforcement.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class CallCost:
    """Cost of a single inference call."""

    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    cache_hit: bool = False
    vram_mb: float = 0.0


@dataclass
class SessionCost:
    """Aggregated cost for an entire assessment session."""

    calls: list[CallCost] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(c.tokens_in + c.tokens_out for c in self.calls)

    @property
    def total_latency_ms(self) -> float:
        return sum(c.latency_ms for c in self.calls)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def cache_hits(self) -> int:
        return sum(1 for c in self.calls if c.cache_hit)

    @property
    def avg_latency_ms(self) -> float:
        if not self.calls:
            return 0.0
        return self.total_latency_ms / len(self.calls)

    @property
    def total_retries(self) -> int:
        # Retries are tracked in tracer, not here
        return 0

    def summary(self) -> dict[str, float | int]:
        """Return a summary dict for logging/reporting."""
        return {
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "call_count": self.call_count,
            "cache_hits": self.cache_hits,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
        }


class CostTracker:
    """Tracks inference cost across an assessment session.

    Usage:
        tracker = CostTracker()
        with tracker.track_call() as cost:
            # ... do inference ...
            cost.tokens_in = 1024
            cost.tokens_out = 45
        print(tracker.session.summary())
    """

    def __init__(self) -> None:
        self.session = SessionCost()

    @contextmanager
    def track_call(self) -> Generator[CallCost, None, None]:
        """Context manager that times an inference call and records its cost.

        Usage:
            with tracker.track_call() as cost:
                result = model.generate(...)
                cost.tokens_in = count_tokens(input)
                cost.tokens_out = count_tokens(output)

        The latency is measured automatically by the context manager.
        """
        cost = CallCost()
        start = time.monotonic()
        try:
            yield cost
        finally:
            cost.latency_ms = (time.monotonic() - start) * 1000
            self.session.calls.append(cost)

    def get_vram_mb(self) -> float:
        """Get current VRAM usage in MB. Returns 0.0 if CUDA unavailable."""
        try:
            import torch

            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / (1024 * 1024)
        except ImportError:
            pass
        return 0.0

    def reset(self) -> None:
        """Reset session cost tracking."""
        self.session = SessionCost()
