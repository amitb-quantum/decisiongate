from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from decisiongate.cli import app


ROOT = Path(__file__).parents[1]
runner = CliRunner()


def test_cli_case_writes_both_reports(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "evaluate",
            "--case",
            str(ROOT / "cases" / "quantumeagle_scope" / "case.json"),
            "--output",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "HUMAN_VERIFY" in result.output
    assert (tmp_path / "decisiongate-report.json").exists()
    assert (tmp_path / "decisiongate-report.md").exists()


def test_cli_rejects_unknown_provider(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "evaluate",
            "--evidence",
            str(ROOT / "examples" / "clear_go.md"),
            "--decision",
            "Proceed",
            "--provider",
            "unknown",
            "--output",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0
    assert "deterministic" in result.output

