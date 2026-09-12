"""Inspect an SXS workspace without modifying files or validating large artifacts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.config_check import DEFAULT_CONFIGS, check_config


CHECKPOINTS = ("baseline", "scaleup", "search")
RUN_RECORDS = {
    "baseline": Path("reports/pipeline_run_latest.json"),
    "scaleup": Path("reports/scaleup_run_latest.json"),
    "search": Path("reports/search_run_latest.json"),
    "validate": Path("reports/validation_run_latest.json"),
}


def inspect_workspace(workspace: str | Path = ".") -> dict[str, Any]:
    """Return a bounded status summary; checkpoint hashes are not recomputed."""

    root = Path(workspace).resolve()
    issues: list[str] = []
    marker_path = root / ".sxs-workspace.json"
    if marker_path.is_file():
        kind = "workspace"
        marker = _json_record(marker_path)
        if not marker["readable"]:
            issues.append(f"unreadable workspace marker: {marker['error']}")
    elif (root / "configs").is_dir() and (root / ".git").exists():
        kind = "source_checkout"
        marker = {"path": marker_path.as_posix(), "exists": False, "readable": False, "data": None}
    else:
        kind = "unrecognized"
        marker = {"path": marker_path.as_posix(), "exists": False, "readable": False, "data": None}
        issues.append("directory is neither a marked SXS workspace nor a source checkout")

    configs = [
        check_config(root / "configs" / path.name, workflow)
        for workflow, path in DEFAULT_CONFIGS.items()
    ]
    for check in configs:
        if not check["valid"]:
            issues.append(f"invalid {check['workflow']} config: {'; '.join(check['errors'])}")

    checkpoints = []
    for name in CHECKPOINTS:
        record = _json_record(root / ".sxs-state" / f"{name}.json")
        data = record.get("data") or {}
        record["workflow"] = name
        record["completed"] = data.get("completed", []) if record["readable"] else []
        record.pop("data", None)
        checkpoints.append(record)
        if record["exists"] and not record["readable"]:
            issues.append(f"unreadable {name} checkpoint: {record['error']}")

    operation = _json_record(root / ".sxs-state/operation_latest.json")
    if operation["exists"] and not operation["readable"]:
        issues.append(f"unreadable operation record: {operation['error']}")

    runs = []
    for name, relative in RUN_RECORDS.items():
        record = _json_record(root / relative)
        data = record.get("data") or {}
        record.update(
            workflow=name,
            status=data.get("status") if record["readable"] else None,
            acceptance_passed=_acceptance_passed(data) if record["readable"] else None,
        )
        record.pop("data", None)
        runs.append(record)
        if record["exists"] and not record["readable"]:
            issues.append(f"unreadable {name} run record: {record['error']}")

    operation_data = operation.pop("data", None) or {}
    operation.update(
        command=operation_data.get("command") if operation["readable"] else None,
        status=operation_data.get("status") if operation["readable"] else None,
        updated_at_utc=operation_data.get("updated_at_utc") if operation["readable"] else None,
    )
    return {
        "schema_version": 1,
        "workspace": root.as_posix(),
        "kind": kind,
        "valid": not issues,
        "issues": issues,
        "marker": marker,
        "configs": configs,
        "operation": operation,
        "checkpoints": checkpoints,
        "runs": runs,
        "scope": "Metadata and configuration only; artifact hashes and external services were not checked.",
    }


def _json_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": path.as_posix(), "exists": False, "readable": False, "data": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON root is not an object")
        return {"path": path.as_posix(), "exists": True, "readable": True, "data": data}
    except (OSError, UnicodeError, ValueError) as exc:
        return {
            "path": path.as_posix(),
            "exists": True,
            "readable": False,
            "data": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _acceptance_passed(data: dict[str, Any]) -> bool | None:
    acceptance = data.get("acceptance")
    if isinstance(acceptance, dict) and isinstance(acceptance.get("passed"), bool):
        return acceptance["passed"]
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable status report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = inspect_workspace(args.workspace)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"SXS status: {report['workspace']}")
        print(f"Type: {report['kind']}")
        print(f"Configuration: {'valid' if all(item['valid'] for item in report['configs']) else 'invalid'}")
        operation = report["operation"]
        if operation["readable"]:
            print(f"Last operation: {operation['command']} ({operation['status']})")
        else:
            print("Last operation: none")
        recorded = [item["workflow"] for item in report["checkpoints"] if item["readable"]]
        print(f"Recorded checkpoints: {', '.join(recorded) if recorded else 'none'}")
        completed = [f"{item['workflow']}={item['status']}" for item in report["runs"] if item["readable"]]
        print(f"Run records: {', '.join(completed) if completed else 'none'}")
        for issue in report["issues"]:
            print(f"Issue: {issue}")
        print(report["scope"])
    return 0 if report["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
