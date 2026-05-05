"""Observability — per-step tracing, cost tracking, and feedback for IMCI assessments.

Usage:
    from malaika.observability import Tracer, CostTracker

    tracer = Tracer()
    tracer.start_session()
    tracer.record_step(imci_state=..., prompt_name=..., ...)
    trace = tracer.finish_session()
"""

from malaika.observability.cost_tracker import CostTracker
from malaika.observability.feedback import FeedbackCollector
from malaika.observability.tracer import Tracer

__all__ = ["CostTracker", "FeedbackCollector", "Tracer"]
