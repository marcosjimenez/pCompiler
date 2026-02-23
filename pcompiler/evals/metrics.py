"""
Implementation of automated metrics for prompt evaluation.
"""

from __future__ import annotations

import re
from typing import Any

from pcompiler.evals.models import MetricScore
from pcompiler.dsl.schema import MetricType


def exact_match(output: str, expected: str) -> MetricScore:
    """Check if output matches expected exactly."""
    score = 1.0 if output.strip() == expected.strip() else 0.0
    return MetricScore(MetricType.EXACT_MATCH, score)


def includes(output: str, expected: str) -> MetricScore:
    """Check if output contains the expected substring."""
    score = 1.0 if expected.strip() in output else 0.0
    return MetricScore(MetricType.INCLUDES, score)


def regex_match(output: str, pattern: str) -> MetricScore:
    """Check if output matches a regex pattern."""
    try:
        score = 1.0 if re.search(pattern, output) else 0.0
    except re.error as e:
        return MetricScore(MetricType.REGEX, 0.0, reason=f"Invalid regex: {e}")
    return MetricScore(MetricType.REGEX, score)


def calculate_metric(metric_type: MetricType, output: str, expected: str | None) -> MetricScore:
    """Dispatch to the correct metric implementation."""
    if expected is None and metric_type != MetricType.LLM_JUDGE:
        return MetricScore(metric_type, 0.0, reason="Missing expected value")

    if metric_type == MetricType.EXACT_MATCH:
        return exact_match(output, expected)
    if metric_type == MetricType.INCLUDES:
        return includes(output, expected)
    if metric_type == MetricType.REGEX:
        return regex_match(output, expected)
    
    # Placeholder for semantic similarity
    if metric_type == MetricType.SEMANTIC_SIMILARITY:
        return MetricScore(MetricType.SEMANTIC_SIMILARITY, 0.5, reason="Semantic metric not implemented")

    return MetricScore(metric_type, 0.0, reason=f"Metric {metric_type} not handled here")
