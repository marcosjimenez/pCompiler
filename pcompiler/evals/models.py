"""
Data models for evaluation results and reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pcompiler.dsl.schema import MetricType


@dataclass
class MetricScore:
    """Score for a specific metric in a test case."""
    metric: MetricType
    score: float  # 0.0 to 1.0
    reason: str | None = None


@dataclass
class TestCaseResult:
    """Results for a single test case execution."""
    case_name: str
    input_vars: dict[str, Any]
    output: str
    scores: list[MetricScore] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores) / len(self.scores)

    @property
    def passed(self) -> bool:
        # Default pass threshold could be 1.0 or configurable
        return all(s.score >= 0.8 for s in self.scores)


@dataclass
class EvalReport:
    """Full report of an evaluation run."""
    results: list[TestCaseResult] = field(default_factory=list)
    threshold: float = 0.8

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def passed_cases(self) -> int:
        return sum(1 for r in self.results if r.average_score >= self.threshold)

    @property
    def success_rate(self) -> float:
        if not self.total_cases:
            return 0.0
        return self.passed_cases / self.total_cases
