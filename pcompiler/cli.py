"""
CLI entry point for the prompt compiler.

Commands::

    pcompile compile prompt.yaml --target gpt-4o --output result.json
    pcompile validate prompt.yaml
    pcompile models
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pcompiler import __version__
from pcompiler.compiler import PromptCompiler
from pcompiler.dsl.parser import ParseError, parse_file
from pcompiler.dsl.generator import DslGenerator
from pcompiler.evals.runner import EvalRunner

console = Console()
err_console = Console(stderr=True)


def _create_compiler() -> PromptCompiler:
    return PromptCompiler()


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(__version__, prog_name="pcompile")
def main() -> None:
    """pCompiler — compile declarative prompt specs into optimised LLM prompts."""


# ---------------------------------------------------------------------------
# compile
# ---------------------------------------------------------------------------

@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--target", "-t",
    default=None,
    help="Target model (overrides the spec's model_target). e.g. gpt-4o, claude-3.5-sonnet",
)
@click.option(
    "--output", "-o",
    default=None,
    type=click.Path(),
    help="Write JSON output to a file instead of stdout.",
)
@click.option(
    "--show-trace/--no-trace",
    default=False,
    help="Include the compilation trace in the output.",
)
def compile(file: str, target: str | None, output: str | None, show_trace: bool) -> None:
    """Compile a DSL file into an optimised, model-specific prompt."""
    compiler = _create_compiler()

    try:
        result = compiler.compile_file(file, target=target)
    except ParseError as exc:
        err_console.print(f"[bold red]Parse Error:[/] {exc}")
        sys.exit(1)
    except KeyError as exc:
        err_console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    # Build output dict
    out: dict = {
        "model_target": result.model_target,
        "plugin": result.plugin_used,
        "parameters": result.parameters,
        "payload": result.payload,
        "prompt_text": result.prompt_text,
    }
    if result.warnings:
        out["warnings"] = result.warnings
    if show_trace:
        out["trace"] = result.trace

    json_str = json.dumps(out, indent=2, ensure_ascii=False)

    if output:
        Path(output).write_text(json_str, encoding="utf-8")
        console.print(f"[green]✓[/] Compiled prompt written to [bold]{output}[/]")
    else:
        console.print(Panel(json_str, title="Compiled Prompt", border_style="green"))

    # Show warnings
    if result.warnings:
        console.print()
        console.print("[yellow]⚠ Warnings:[/]")
        for w in result.warnings:
            console.print(f"  • {w}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
def validate(file: str) -> None:
    """Validate a DSL file (static analysis only, no compilation)."""
    compiler = _create_compiler()

    try:
        analysis = compiler.validate_file(file)
    except ParseError as exc:
        err_console.print(f"[bold red]Parse Error:[/] {exc}")
        sys.exit(1)
    except KeyError as exc:
        err_console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    warnings = analysis.all_warnings
    has_errors = analysis.has_errors

    if not warnings and not has_errors:
        console.print("[green]✓ Validation passed — no issues found.[/]")
        return

    if has_errors:
        console.print("[bold red]✗ Validation failed with errors:[/]")
    else:
        console.print("[yellow]⚠ Validation passed with warnings:[/]")

    for w in warnings:
        colour = "red" if "error" in w.lower() else "yellow"
        console.print(f"  [{colour}]•[/] {w}")

    # Summary
    console.print()
    console.print(
        f"  Clarity score: [bold]{analysis.ambiguity.clarity_score}[/]  |  "
        f"Injection risk: [bold]{analysis.injection.overall_risk.value}[/]"
    )

    if has_errors:
        sys.exit(1)


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------

@main.command()
def models() -> None:
    """List all available target models and plugins."""
    compiler = _create_compiler()

    table = Table(title="Available Models & Plugins", show_lines=True)
    table.add_column("Model", style="bold cyan")
    table.add_column("Provider")
    table.add_column("Context", justify="right")
    table.add_column("Max Output", justify="right")
    table.add_column("JSON Mode")
    table.add_column("Function Calling")

    for name in compiler.registry.list_models():
        profile = compiler.registry.get(name)
        table.add_row(
            name,
            profile.provider,
            f"{profile.max_context_tokens:,}",
            f"{profile.max_output_tokens:,}",
            "✓" if profile.supports_json_mode else "✗",
            "✓" if profile.supports_function_calling else "✗",
        )

    console.print(table)

    console.print()
    plugins = compiler.plugins.list_plugins()
    if plugins:
        console.print(f"[bold]Loaded plugins:[/] {', '.join(plugins)}")
    else:
        console.print("[yellow]No plugins loaded.[/]")


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------

@main.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--mock", is_flag=True, help="Run with mock execution (no API calls).")
def eval(file: str, mock: bool) -> None:
    """Run evaluations for a prompt spec."""
    compiler = _create_compiler()

    try:
        spec = parse_file(file)
    except Exception as exc:
        err_console.print(f"[bold red]Error parsing file:[/] {exc}")
        sys.exit(1)

    if not spec.evals.cases:
        err_console.print("[yellow]No test cases found in spec. Add 'evals' to run evaluations.[/]")
        return

    # Mock execution functions
    def mock_executor(payload: Any) -> str:
        return "This is a mock response for evaluation testing."

    def mock_judge_executor(system: str, user: str) -> str:
        return '{"score": 0.9, "reason": "Looks good in mock mode."}'

    # In a real scenario, we would use the plugins to actually call the LLM
    # For now, we use mocks to demonstrate the CLI.
    if not mock:
        console.print("[dim]Note: Real execution not yet fully integrated in CLI. Using mocks...[/]")

    runner = EvalRunner(compiler, mock_executor, mock_judge_executor)
    
    with console.status("[bold green]Running evaluations..."):
        report = runner.run_eval(spec)

    # Display results
    console.print(f"\n[bold]Eval Report for {file}[/]")
    console.print(f"Success Rate: [bold]{report.success_rate:.0%}[/] ({report.passed_cases}/{report.total_cases} passed)")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Test Case")
    table.add_column("Output", width=30)
    table.add_column("Score", justify="center")
    table.add_column("Pass/Fail", justify="center")

    for result in report.results:
        status = "[green]PASS[/]" if result.passed else "[red]FAIL[/]"
        table.add_row(
            result.case_name,
            result.output[:100] + ("..." if len(result.output) > 100 else ""),
            f"{result.average_score:.2f}",
            status
        )

    console.print(table)

    if report.success_rate < 1.0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

@main.command()
@click.argument("prompt", required=False)
@click.option(
    "--file", "-f",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a text file containing the prompt.",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Path to save the generated YAML.",
)
@click.option(
    "--mock", is_flag=True, default=True,
    help="Use mock generator (currently the default).",
)
def create(prompt: str | None, file: str | None, output: str | None, mock: bool) -> None:
    """Create a DSL YAML specification from a natural language prompt."""
    if not prompt and not file:
        err_console.print("[bold red]Error:[/] You must provide either a prompt string or a --file.")
        sys.exit(1)

    if file:
        try:
            prompt_content = Path(file).read_text(encoding="utf-8")
        except Exception as exc:
            err_console.print(f"[bold red]Error reading file:[/] {exc}")
            sys.exit(1)
    else:
        prompt_content = prompt  # type: ignore

    generator = DslGenerator()
    
    with console.status("[bold green]Generating DSL specification..."):
        try:
            yaml_content = generator.generate_yaml(prompt_content)
        except Exception as exc:
            err_console.print(f"[bold red]Generation Error:[/] {exc}")
            sys.exit(1)

    if output:
        try:
            Path(output).write_text(yaml_content, encoding="utf-8")
            console.print(f"[green]✓[/] Generated DSL written to [bold]{output}[/]")
        except Exception as exc:
            err_console.print(f"[bold red]Error writing file:[/] {exc}")
            sys.exit(1)
    else:
        console.print(Panel(yaml_content, title="Generated DSL YAML", border_style="cyan"))


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
