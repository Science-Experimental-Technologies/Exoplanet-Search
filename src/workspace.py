"""Initialize an isolated SXS workspace without running a workflow."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from src.config_check import DEFAULT_CONFIGS, check_config
from src.provenance import initialize_workspace


def initialize(destination: str | Path) -> dict:
    """Create or inspect a marked workspace and validate its copied configs."""

    summary = initialize_workspace(Path(destination))
    root = Path(summary["workspace"])
    checks = [
        check_config(root / "configs" / path.name, workflow)
        for workflow, path in DEFAULT_CONFIGS.items()
    ]
    return {
        "schema_version": 1,
        "status": "initialized" if summary["created"] else "existing",
        "workspace": summary["workspace"],
        "configs": summary["configs"],
        "valid": all(check["valid"] for check in checks),
        "checks": checks,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="New workspace directory, or an existing marked SXS workspace")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable initialization report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = initialize(args.workspace)
    from src.execution import ACTIVE_OPERATION

    operation = ACTIVE_OPERATION.get()
    if operation:
        operation.register(Path(report["workspace"]), legacy=True)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        verb = "Created" if report["status"] == "initialized" else "Reused"
        print(f"{verb} SXS workspace: {report['workspace']}")
        print(
            f"Configurations: {len(report['configs'])} available, "
            f"{'valid' if report['valid'] else 'invalid'}"
        )
        print(f"Next: sxs baseline --workspace \"{report['workspace']}\" --dry-run")
    return 0 if report["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
