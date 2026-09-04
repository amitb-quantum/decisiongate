"""DecisionGate command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from decisiongate.engine import DecisionGate
from decisiongate.providers.openai import OpenAIProvider
from decisiongate.reporting import write_reports

app = typer.Typer(
    help="Falsification-first adjudication for LLM-assisted decisions.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main() -> None:
    """Run an auditable decision evaluation."""


@app.command()
def evaluate(
    evidence: Annotated[
        list[Path] | None,
        typer.Option("--evidence", "-e", help="Evidence file; repeat for multiple files."),
    ] = None,
    decision: Annotated[
        str | None,
        typer.Option("--decision", "-d", help="Proposed decision to adjudicate."),
    ] = None,
    case: Annotated[
        Path | None,
        typer.Option("--case", help="JSON case manifest containing decision and evidence paths."),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Directory for JSON and Markdown reports."),
    ] = Path("."),
    provider: Annotated[
        str,
        typer.Option(help="Analysis provider: deterministic or openai."),
    ] = "deterministic",
) -> None:
    """Evaluate one proposed decision against supplied local evidence."""
    if case:
        data = json.loads(case.read_text(encoding="utf-8"))
        decision = decision or data["decision"]
        evidence = evidence or [case.parent / item for item in data["evidence"]]
    if not decision or not evidence:
        raise typer.BadParameter("Provide --decision and --evidence, or provide --case")
    if provider == "deterministic":
        model_provider = None
    elif provider == "openai":
        model_provider = OpenAIProvider()
    else:
        raise typer.BadParameter("--provider must be 'deterministic' or 'openai'")
    try:
        report = DecisionGate(provider=model_provider).evaluate(evidence, decision)
        json_path, markdown_path = write_reports(report, output)
    except (OSError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Evaluation failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    color = {"GO": "green", "NO_GO": "red", "HUMAN_VERIFY": "yellow"}[report.disposition]
    console.print(f"Disposition: [{color}]{report.disposition}[/{color}]")
    console.print(f"JSON: {json_path.resolve()}")
    console.print(f"Markdown: {markdown_path.resolve()}")


if __name__ == "__main__":  # pragma: no cover
    app()
