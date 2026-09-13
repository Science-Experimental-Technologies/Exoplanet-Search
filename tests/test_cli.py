from __future__ import annotations

from src.cli import main
from src import __version__


def test_unified_cli_help(capsys) -> None:
    assert main(["--help"]) == 0
    output = capsys.readouterr().out
    assert "SXS | SCIX Exoplanet Search" in output
    assert "baseline" in output
    assert "scaleup" in output
    assert "search" in output
    assert "validate" in output
    assert "doctor" in output
    assert "config-check" in output
    assert "init" in output
    assert "status" in output
    assert "support-bundle" in output
    assert "verify" in output


def test_unified_cli_version(capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"SXS {__version__}"
