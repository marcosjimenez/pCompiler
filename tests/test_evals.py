import pytest
from pcompiler.evals.metrics import calculate_metric
from pcompiler.dsl.schema import MetricType, PromptSpec, EvalConfig, EvalTestCase
from pcompiler.evals.models import MetricScore, EvalReport
from pcompiler.evals.runner import EvalRunner
from pcompiler.compiler import PromptCompiler

def test_heuristic_metrics():
    # Exact Match
    res = calculate_metric(MetricType.EXACT_MATCH, "Hello World", "Hello World")
    assert res.score == 1.0
    
    res = calculate_metric(MetricType.EXACT_MATCH, "Hello", "World")
    assert res.score == 0.0

    # Includes
    res = calculate_metric(MetricType.INCLUDES, "The quick brown fox", "brown")
    assert res.score == 1.0

    res = calculate_metric(MetricType.INCLUDES, "The quick brown fox", "blue")
    assert res.score == 0.0

    # Regex
    res = calculate_metric(MetricType.REGEX, "Order #12345", r"Order #\d+")
    assert res.score == 1.0

    res = calculate_metric(MetricType.REGEX, "Order #ABC", r"Order #\d+")
    assert res.score == 0.0

def test_eval_runner_mock():
    compiler = PromptCompiler()
    
    spec = PromptSpec(
        task="test",
        evals=EvalConfig(
            cases=[
                EvalTestCase(
                    name="Test 1",
                    input={"input": "query 1"},
                    expected="response 1",
                    metrics=[MetricType.INCLUDES]
                )
            ]
        )
    )

    def mock_executor(payload):
        return "This is response 1 from the mock."

    runner = EvalRunner(compiler, mock_executor)
    report = runner.run_eval(spec)

    assert report.total_cases == 1
    assert report.passed_cases == 1
    assert report.results[0].scores[0].metric == MetricType.INCLUDES
    assert report.results[0].scores[0].score == 1.0

def test_llm_judge_mock():
    compiler = PromptCompiler()
    
    spec = PromptSpec(
        task="test",
        evals=EvalConfig(
            cases=[
                EvalTestCase(
                    name="Judge Test",
                    input={"input": "Why is sky blue?"},
                    expected="Rayleigh scattering",
                    metrics=[MetricType.LLM_JUDGE]
                )
            ]
        )
    )

    def mock_executor(payload):
        return "The sky appears blue due to Rayleigh scattering."

    def mock_judge_executor(system, user):
        return '{"score": 0.95, "reason": "Accurate explanation."}'

    runner = EvalRunner(compiler, mock_executor, mock_judge_executor)
    report = runner.run_eval(spec)

    assert report.results[0].scores[0].metric == MetricType.LLM_JUDGE
    assert report.results[0].scores[0].score == 0.95
    assert "Accurate explanation" in report.results[0].scores[0].reason

def test_eval_threshold():
    compiler = PromptCompiler()
    
    spec = PromptSpec(
        task="test",
        evals=EvalConfig(
            threshold=1.0, # Strict
            cases=[
                EvalTestCase(
                    name="Fail Test",
                    input={"input": "x"},
                    expected="y",
                    metrics=[MetricType.EXACT_MATCH]
                )
            ]
        )
    )

    def mock_executor(payload):
        return "z"

    runner = EvalRunner(compiler, mock_executor)
    report = runner.run_eval(spec)

    assert report.passed_cases == 0
    assert report.success_rate == 0.0
