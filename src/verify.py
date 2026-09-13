"""Verify SXS checkpoint identity and recorded file hashes without writing files."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.config_check import DEFAULT_CONFIGS, load_workflow_config
from src.provenance import file_hash, fingerprint, runtime_identity
from src.workspace_status import CHECKPOINTS, inspect_workspace


def verify_workspace(
    workspace: str | Path = ".", workflows: Sequence[str] | None = None
) -> dict[str, Any]:
    """Verify selected checkpoint identities and their recorded in-workspace files."""

    root = Path(workspace).resolve()
    selected = list(dict.fromkeys(workflows or CHECKPOINTS))
    status = inspect_workspace(root)
    config_valid = all(
        item["valid"]
        for item in status["configs"]
        if item["workflow"] in selected
    )
    runtime = runtime_identity()
    results = [_verify_checkpoint(root, workflow, runtime) for workflow in selected]
    issues = []
    if status["kind"] == "unrecognized":
        issues.append("directory is not a recognized SXS workspace or source checkout")
    if not config_valid:
        issues.append("one or more workflow configurations are invalid")
    for result in results:
        if not result["exists"]:
            issues.append(f"{result['workflow']} checkpoint is absent")
        elif not result["valid"]:
            issues.append(f"{result['workflow']} checkpoint integrity failed")
    valid = status["kind"] != "unrecognized" and config_valid and not issues
    return {
        "schema_version": 1,
        "workspace": root.as_posix(),
        "valid": valid,
        "issues": issues,
        "checkpoints": results,
        "scope": (
            "Selected checkpoint identity and recorded in-workspace files only; "
            "unrecorded files, external services, and scientific validity were not checked."
        ),
    }


def _verify_checkpoint(root: Path, workflow: str, runtime: dict[str, Any]) -> dict[str, Any]:
    path = root / ".sxs-state" / f"{workflow}.json"
    result: dict[str, Any] = {
        "workflow": workflow,
        "exists": path.is_file(),
        "readable": False,
        "valid": False,
        "identity_matches": False,
        "recorded_files": 0,
        "verified_files": 0,
        "missing": [],
        "changed": [],
        "outside_workspace": 0,
        "malformed": 0,
    }
    if not path.is_file():
        return result
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(checkpoint, dict):
            raise ValueError("checkpoint root is not an object")
        files = checkpoint.get("files")
        completed = checkpoint.get("completed")
        identity = checkpoint.get("identity")
        if not isinstance(files, dict) or not isinstance(completed, list) or not isinstance(identity, str):
            raise ValueError("checkpoint schema is invalid")
    except (OSError, UnicodeError, ValueError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    result["readable"] = True
    result["completed"] = completed
    config_path = root / "configs" / DEFAULT_CONFIGS[workflow].name
    try:
        config = load_workflow_config(config_path, workflow)
        result["identity_matches"] = identity == fingerprint(
            {"config": config, "runtime": runtime}
        )
    except (OSError, UnicodeError, ValueError) as exc:
        result["identity_error"] = f"{type(exc).__name__}: {exc}"

    result["recorded_files"] = len(files)
    for recorded, expected in files.items():
        if not isinstance(recorded, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            result["malformed"] += 1
            continue
        candidate = Path(recorded)
        candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if not candidate.is_relative_to(root):
            result["outside_workspace"] += 1
            continue
        relative = candidate.relative_to(root).as_posix()
        if not candidate.is_file():
            result["missing"].append(relative)
        elif file_hash(candidate) != expected:
            result["changed"].append(relative)
        else:
            result["verified_files"] += 1
    result["valid"] = bool(
        result["identity_matches"]
        and not result["missing"]
        and not result["changed"]
        and result["outside_workspace"] == 0
        and result["malformed"] == 0
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?", type=Path, default=Path("."))
    parser.add_argument(
        "--workflow",
        action="append",
        choices=list(CHECKPOINTS),
        help="Checkpoint to verify; repeat for multiple workflows (default: all)",
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable integrity report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = verify_workspace(args.workspace, args.workflow)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"SXS checkpoint verification: {report['workspace']}")
        for item in report["checkpoints"]:
            if not item["exists"]:
                detail = "absent"
            elif not item["readable"]:
                detail = f"unreadable ({item.get('error', 'invalid')})"
            else:
                detail = (
                    f"{'valid' if item['valid'] else 'failed'}; "
                    f"{item['verified_files']}/{item['recorded_files']} file hashes matched; "
                    f"identity {'matched' if item['identity_matches'] else 'mismatched'}"
                )
            print(f"{item['workflow']}: {detail}")
        for issue in report["issues"]:
            print(f"Issue: {issue}")
        print(report["scope"])
    return 0 if report["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
