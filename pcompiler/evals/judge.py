"""
LLM-as-a-judge implementation for automated prompt evaluation.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from pcompiler.evals.models import MetricScore
from pcompiler.dsl.schema import MetricType


JUDGE_SYSTEM_PROMPT = """
You are an impartial judge evaluating the quality of an LLM response based on a specific input and an optional expected answer.
Assign a score between 0.0 and 1.0 (where 1.0 is perfect) and provide a brief justification.
Respond in JSON format: {"score": float, "reason": str}
"""

JUDGE_USER_PROMPT_TEMPLATE = """
Input Variable(s): {input_vars}
Expected Answer: {expected}
Actual LLM Output: {output}

Evaluate the LLM Output based on how well it satisfies the input and matches the intent of the expected answer.
"""

class LLMJudge:
    """Uses an LLM to evaluate prompt outputs."""

    def __init__(self, executor: Callable[[str, str], str], model: str = "gpt-4o") -> None:
        """
        Args:
            executor: A function that takes (system_prompt, user_prompt) and returns the LLM response.
            model: The model identifier to use as a judge.
        """
        self.executor = executor
        self.model = model

    def evaluate(self, output: str, expected: str | None, input_vars: dict[str, Any]) -> MetricScore:
        """Evaluate the output using the LLM judge."""
        user_prompt = JUDGE_USER_PROMPT_TEMPLATE.format(
            input_vars=json.dumps(input_vars),
            expected=expected or "N/A",
            output=output
        )

        try:
            response_text = self.executor(JUDGE_SYSTEM_PROMPT, user_prompt)
            # Try to parse JSON from response
            import re
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                score = float(data.get("score", 0.0))
                reason = data.get("reason", "No reason provided")
                return MetricScore(MetricType.LLM_JUDGE, score, reason=reason)
            
            return MetricScore(MetricType.LLM_JUDGE, 0.0, reason="Failed to parse judge JSON response")
        except Exception as e:
            return MetricScore(MetricType.LLM_JUDGE, 0.0, reason=f"Judge error: {e}")
