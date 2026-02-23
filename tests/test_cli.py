"""Tests for CLI commands."""

from click.testing import CliRunner

from pcompiler.cli import main


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_models_command():
    runner = CliRunner()
    result = runner.invoke(main, ["models"])
    assert result.exit_code == 0
    assert "gpt-4o" in result.output
    assert "claude" in result.output.lower()
    assert "gemini" in result.output.lower()


def test_compile_example(tmp_path):
    spec = tmp_path / "test.yaml"
    spec.write_text("task: summarize\nmodel_target: gpt-4o\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["compile", str(spec)])
    assert result.exit_code == 0
    assert "Compiled Prompt" in result.output


def test_compile_to_file(tmp_path):
    spec = tmp_path / "test.yaml"
    spec.write_text("task: summarize\nmodel_target: gpt-4o\n", encoding="utf-8")
    out = tmp_path / "out.json"

    runner = CliRunner()
    result = runner.invoke(main, ["compile", str(spec), "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert data["model_target"] == "gpt-4o"


def test_compile_with_target_override(tmp_path):
    spec = tmp_path / "test.yaml"
    spec.write_text("task: summarize\nmodel_target: gpt-4o\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["compile", str(spec), "--target", "claude-3.5-sonnet"])
    assert result.exit_code == 0
    assert "claude" in result.output.lower()


def test_compile_invalid_file(tmp_path):
    spec = tmp_path / "invalid.yaml"
    spec.write_text(":::bad:::", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["compile", str(spec)])
    assert result.exit_code != 0


def test_validate_clean(tmp_path):
    spec = tmp_path / "test.yaml"
    spec.write_text("task: summarize\nmodel_target: gpt-4o\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(spec)])
    assert result.exit_code == 0


def test_validate_with_warnings(tmp_path):
    spec = tmp_path / "test.yaml"
    spec.write_text(
        "task: t\nconstraints:\n  temperature: 0.01\n  tone: creative\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(spec)])
    assert result.exit_code == 0  # warnings are not errors
