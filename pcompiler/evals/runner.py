"""
Evaluation runner that executes test cases and collects metrics.
"""

from __future__ import annotations

from typing import Any, Callable

from pcompiler.compiler import PromptCompiler
from pcompiler.dsl.schema import PromptSpec, MetricType
from pcompiler.evals.models import EvalReport, TestCaseResult, MetricScore
from pcompiler.evals.metrics import calculate_metric
from pcompiler.evals.judge import LLMJudge


class EvalRunner:
    """Orchestrates the evaluation of a PromptSpec against its test cases."""

    def __init__(
        self,
        compiler: PromptCompiler,
        executor: Callable[[dict[str, Any]], str],
        judge_executor: Callable[[str, str], str] | None = None
    ) -> None:
        """
        Args:
            compiler: The PromptCompiler instance.
            executor: Function that takes compiled payload and returns LLM text.
            judge_executor: Function for the LLM judge calls.
        """
        self.compiler = compiler
        self.executor = executor
        self.judge = LLMJudge(judge_executor) if judge_executor else None

    def run_eval(self, spec: PromptSpec) -> EvalReport:
        """Run all evals defined in the spec."""
        report = EvalReport(threshold=spec.evals.threshold)
        
        for case in spec.evals.cases:
            # 1. Compile with input variables injected (simplified for now)
            # In a real scenario, we'd need to substitute variables in the DSL
            # For now, let's assume the executor handles input vars or we merge them
            
            # Simple simulation of variable injection:
            # (In a more robust version, this would happen in the compiler/parser)
            compiled = self.compiler.compile(spec)
            
            # 2. Execute
            output = self.executor(compiled.payload)
            
            # 3. Calculate metrics
            case_result = TestCaseResult(
                case_name=case.name,
                input_vars=case.input,
                output=output
            )
            
            for metric_type in case.metrics:
                if metric_type == MetricType.LLM_JUDGE:
                    if self.judge:
                        score = self.judge.evaluate(output, case.expected, case.input)
                    else:
                        score = MetricScore(MetricType.LLM_JUDGE, 0.0, reason="No judge executor provided")
                else:
                    score = calculate_metric(metric_type, output, case.expected)
                case_result.scores.append(score)
            
            report.results.append(case_result)
            
        return report
