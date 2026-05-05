"""Evaluation — golden dataset testing and offline accuracy reporting.

Usage:
    from malaika.evaluation import GOLDEN_SCENARIOS, Evaluator

    evaluator = Evaluator()
    report = evaluator.run_protocol_scenarios(GOLDEN_SCENARIOS)
    print(report.summary())
"""

from malaika.evaluation.evaluator import EvaluationReport, Evaluator
from malaika.evaluation.golden_scenarios import GOLDEN_SCENARIOS, GoldenScenario

__all__ = ["GOLDEN_SCENARIOS", "EvaluationReport", "Evaluator", "GoldenScenario"]
