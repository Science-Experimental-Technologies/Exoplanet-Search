from __future__ import annotations

from src.cli import main


def test_unified_cli_help(capsys) -> None:
    assert main(["--help"]) == 0
    output = capsys.readouterr().out
    assert "SXS | SCIX Exoplanet Search" in output
    assert "baseline" in output
    assert "scaleup" in output
    assert "search" in output
    assert "validate" in output
