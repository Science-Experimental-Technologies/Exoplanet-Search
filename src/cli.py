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


def _dispatch(arguments, operation) -> int:
    from src.execution import WorkspaceLock
    command_name = arguments.pop(0)
    command = _commands().get(command_name)
    if command is None:
        raise ValueError(f"Unknown command: {command_name}")
    if "--help" in arguments or "-h" in arguments:
        return command(arguments)
    if "--workspace" in arguments:
        if command_name not in {"baseline", "scaleup", "search", "validate"}:
            raise ValueError("Use --output for workbench commands, --workspace for legacy workflows")
        index = arguments.index("--workspace")
        if index + 1 >= len(arguments):
            raise ValueError("--workspace requires a directory")
        destination = Path(arguments[index + 1])
        del arguments[index:index + 2]
        from src.provenance import isolated_workspace
        operation.contexts.enter_context(isolated_workspace(destination))
        operation.register(Path.cwd(), legacy=True)
        return command(arguments)
    if command_name in {"baseline", "scaleup", "search", "validate"}:
        if "--dry-run" in arguments:
            return command(arguments)
        operation.contexts.enter_context(WorkspaceLock(Path.cwd()))
        operation.register(Path.cwd(), legacy=True)
        return command(arguments)
    if command_name == "report":
        from argparse import ArgumentParser
        parser = ArgumentParser(add_help=False)
        parser.add_argument("--run-dir", type=Path, required=True)
        options, _ = parser.parse_known_args(arguments)
        if not options.run_dir.is_dir():
            raise FileNotFoundError(f"Run directory does not exist: {options.run_dir}")
        operation.contexts.enter_context(WorkspaceLock(options.run_dir))
        operation.register(options.run_dir, legacy=True)
        return command(arguments)
    return command(arguments)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        _print_help()
        return 0

    from src.execution import ACTIVE_OPERATION, Operation, WorkspaceBusy
    operation = Operation(arguments[0])
    token = ACTIVE_OPERATION.set(operation)
    try:
        code = _dispatch(arguments, operation)
        operation.finish("completed" if code == 0 else "acceptance_failed" if code == 3 else "failed", code)
        return code
    except SystemExit as exc:
        code = int(exc.code or 0)
        operation.finish("completed" if code == 0 else "failed", code)
        return code
    except KeyboardInterrupt:
        operation.finish("interrupted", 130, "Interrupted by user")
        print("SXS interrupted. Completed checkpoints and partial outputs are retained.", file=sys.stderr)
        return 130
    except Exception as exc:
        code = 4 if isinstance(exc, WorkspaceBusy) else 2 if isinstance(exc, (ValueError, FileNotFoundError, KeyError)) else 1
        operation.finish("failed", code, str(exc))
        print(f"SXS error [{code}]: {exc}", file=sys.stderr)
        return code
    finally:
        operation.close()
        ACTIVE_OPERATION.reset(token)


if __name__ == "__main__":
    raise SystemExit(main())
