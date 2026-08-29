"""Unified product-oriented command interface for SXS workflows."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence


Command = Callable[[Sequence[str] | None], int]


def _commands() -> dict[str, Command]:
    from src.candidate_search.run_search import main as search_main
    from src.independent_validation.run_validation import main as validate_main
    from src.pipeline import main as baseline_main
    from src.scaleup.run_scaleup import main as scaleup_main

    return {
        "baseline": baseline_main,
        "scaleup": scaleup_main,
        "search": search_main,
        "validate": validate_main,
    }


def _print_help() -> None:
    print(
        "SXS | SCIX Exoplanet Search\n\n"
        "Usage: python -m src.cli <command> [options]\n\n"
        "Commands:\n"
        "  baseline  Run or inspect the baseline recovery workflow\n"
        "  scaleup   Build the scaled benchmark and qualify the production model\n"
        "  search    Screen the deterministic unknown-target sample\n"
        "  validate  Run independent statistical and astrophysical validation\n\n"
        "Pass --help after a command to see workflow-specific options."
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
    return command(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
