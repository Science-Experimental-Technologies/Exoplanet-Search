"""Unified product-oriented command interface for SXS workflows."""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable, Sequence


Command = Callable[[Sequence[str] | None], int]


def _commands() -> dict[str, Command]:
    from src.candidate_search.run_search import main as search_main
    from src.independent_validation.run_validation import main as validate_main
    from src.pipeline import main as baseline_main
    from src.scaleup.run_scaleup import main as scaleup_main
    from src.workbench import demo_main, analyze_main
    from src.analysis_report import main as report_main
    from src.injection import main as injection_main
    from src.independent_evaluation import main as evaluation_main

    return {
        "baseline": baseline_main,
        "scaleup": scaleup_main,
        "search": search_main,
        "validate": validate_main,
        "demo": demo_main,
        "analyze": analyze_main,
        "report": report_main,
        "inject": injection_main,
        "evaluate": evaluation_main,
    }


def _print_help() -> None:
    print(
        "SXS | SCIX Exoplanet Search\n\n"
        "Usage: python -m src.cli <command> [options]\n\n"
        "Commands:\n"
        "  baseline  Run or inspect the baseline recovery workflow\n"
        "  scaleup   Build the scaled benchmark and qualify the production model\n"
        "  search    Screen the deterministic unknown-target sample\n"
        "  validate  Run independent statistical and astrophysical validation\n"
        "  demo      Run an offline synthetic transit example\n"
        "  analyze   Analyze a CSV/FITS light curve or a Kepler KIC\n"
        "  report    Rebuild a self-contained analysis HTML report\n"
        "  inject    Measure conditional transit injection recovery\n"
        "  evaluate  Run nested target-grouped RF evaluation\n\n"
        "Pass --help after a command to see workflow-specific options."
        "\nLegacy workflows accept --workspace DIR for isolated configs and outputs."
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        _print_help()
        return 0

    command_name = arguments.pop(0)
    command = _commands().get(command_name)
    if command is None:
        print(f"Unknown command: {command_name}", file=sys.stderr)
        _print_help()
        return 2
    if "--workspace" in arguments:
        if command_name not in {"baseline", "scaleup", "search", "validate"}:
            raise ValueError("Use --output for workbench commands, --workspace for legacy workflows")
        index = arguments.index("--workspace")
        if index + 1 >= len(arguments):
            raise ValueError("--workspace requires a directory")
        destination = Path(arguments[index + 1])
        del arguments[index:index + 2]
        from src.provenance import isolated_workspace
        with isolated_workspace(destination, Path(__file__).resolve().parent.parent / "configs"):
            return command(arguments)
    return command(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
