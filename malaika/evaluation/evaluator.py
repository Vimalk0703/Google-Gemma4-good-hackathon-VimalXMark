"""Evaluator — run golden scenarios and produce accuracy reports.

Runs scenarios at different levels:
- "protocol": Tests imci_protocol.py directly (fast, no GPU)
- "perception": Tests perception parsing with mock inference (moderate)
- "e2e": Tests full pipeline with real model (slow, needs GPU)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from malaika.evaluation.golden_scenarios import GoldenScenario


@dataclass
class ScenarioResult:
    """Result of running one golden scenario."""

    scenario_name: str
    passed: bool
    expected_classifications: list[str]
    actual_classifications: list[str]
    expected_severity: str
    actual_severity: str
    notes: str = ""


@dataclass
class EvaluationReport:
    """Complete evaluation report across all scenarios."""

    level: str  # "protocol", "perception", "e2e"
    results: list[ScenarioResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def summary(self) -> dict[str, Any]:
        """Summary dict for logging/reporting."""
        return {
            "level": self.level,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy": round(self.accuracy, 3),
            "timestamp": self.timestamp.isoformat(),
            "failures": [
                {"name": r.scenario_name, "expected": r.expected_classifications,
                 "actual": r.actual_classifications, "notes": r.notes}
                for r in self.results if not r.passed
            ],
        }

    def export_json(self, output_path: Path) -> None:
        """Export report to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            **self.summary(),
            "results": [
                {
                    "scenario": r.scenario_name,
                    "passed": r.passed,
                    "expected_classifications": r.expected_classifications,
                    "actual_classifications": r.actual_classifications,
                    "expected_severity": r.expected_severity,
                    "actual_severity": r.actual_severity,
                    "notes": r.notes,
                }
                for r in self.results
            ],
        }
        output_path.write_text(json.dumps(data, indent=2))


class Evaluator:
    """Runs golden scenarios and produces evaluation reports.

    Currently supports protocol-level evaluation (no GPU needed).
    Perception and e2e levels will be added when those modules are built.
    """

    def run_protocol_scenarios(
        self,
        scenarios: list[GoldenScenario],
    ) -> EvaluationReport:
        """Run protocol-level scenarios against imci_protocol.py.

        These test deterministic classification logic only — no model inference.

        Args:
            scenarios: List of golden scenarios to evaluate.

        Returns:
            EvaluationReport with per-scenario results.
        """
        report = EvaluationReport(level="protocol")

        for scenario in scenarios:
            if scenario.level != "protocol":
                continue

            result = self._evaluate_protocol_scenario(scenario)
            report.results.append(result)

        return report

    def _evaluate_protocol_scenario(self, scenario: GoldenScenario) -> ScenarioResult:
        """Evaluate a single protocol-level scenario.

        This will call imci_protocol.py classification functions once they exist.
        For now, returns a placeholder result.
        """
        # TODO: Wire to imci_protocol.py when it's implemented
        # For now, mark as not-yet-implemented
        return ScenarioResult(
            scenario_name=scenario.name,
            passed=False,
            expected_classifications=[c.value for c in scenario.expected_classifications],
            actual_classifications=[],
            expected_severity=scenario.expected_severity.value,
            actual_severity="not_implemented",
            notes="imci_protocol.py not yet implemented — placeholder result",
        )
