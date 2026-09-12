"""Validate SXS workflow configurations without running scientific stages."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from src.provenance import default_config_source


DEFAULT_CONFIGS = {
    "baseline": Path("configs/base.yaml"),
    "scaleup": Path("configs/scaleup.yaml"),
    "search": Path("configs/candidate_search.yaml"),
    "validate": Path("configs/independent_validation.yaml"),
}

REQUIRED_SECTIONS = {
    "baseline": {
        "project", "paths", "ingest", "catalog", "dataset", "preprocess",
        "bls", "machine_learning", "targets",
    },
    "scaleup": {
        "project", "paths", "ingest", "catalog", "dataset", "preprocess",
        "bls", "machine_learning", "scaleup", "targets",
    },
    "search": {"project", "paths", "ingest", "preprocess", "bls", "candidate_search"},
    "validate": {"project", "inputs", "bls", "fap", "vetting", "artifacts"},
}


class ConfigurationError(ValueError):
    """Raised when a YAML file violates an SXS configuration contract."""


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConfigurationError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def load_workflow_config(path: str | Path, workflow: str | None = None) -> dict[str, Any]:
    """Load and validate one workflow configuration, returning its mapping."""

    payload = _read_yaml_config(Path(path))
    selected = workflow or infer_workflow(payload)
    errors = validate_workflow_config(payload, selected)
    if errors:
        raise ConfigurationError("; ".join(errors))
    return payload


def infer_workflow(config: Mapping[str, Any]) -> str:
    """Infer a workflow from its unique top-level section."""

    if "candidate_search" in config:
        return "search"
    if "fap" in config or "vetting" in config or "inputs" in config:
        return "validate"
    if "scaleup" in config:
        return "scaleup"
    if "machine_learning" in config and "targets" in config:
        return "baseline"
    raise ConfigurationError("cannot infer workflow; pass --workflow explicitly")


def validate_workflow_config(config: Mapping[str, Any], workflow: str) -> list[str]:
    """Return all detectable structural and semantic errors for a workflow."""

    if workflow not in REQUIRED_SECTIONS:
        return [f"unknown workflow: {workflow}"]
    errors: list[str] = []
    missing = sorted(REQUIRED_SECTIONS[workflow] - set(config))
    if missing:
        errors.append(f"missing sections: {', '.join(missing)}")
    for section in REQUIRED_SECTIONS[workflow] & set(config):
        if section == "targets":
            if not isinstance(config[section], list):
                errors.append("targets must be a list")
        elif not isinstance(config[section], Mapping):
            errors.append(f"{section} must be a mapping")
    if errors:
        return errors

    project = config["project"]
    _require_keys(project, "project", {"name", "version", "random_seed"}, errors)
    if "random_seed" in project and (
        not isinstance(project["random_seed"], int)
        or isinstance(project["random_seed"], bool)
    ):
        errors.append("project.random_seed must be an integer")

    bls = config["bls"]
    _require_keys(
        bls,
        "bls",
        {"minimum_period_days", "maximum_period_days", "durations_hours", "objective", "method"},
        errors,
    )
    minimum = _positive_number(bls, "minimum_period_days", "bls", errors)
    maximum = _positive_number(bls, "maximum_period_days", "bls", errors)
    if minimum is not None and maximum is not None and minimum >= maximum:
        errors.append("bls.minimum_period_days must be less than bls.maximum_period_days")
    durations = bls.get("durations_hours")
    if not isinstance(durations, list) or not durations:
        errors.append("bls.durations_hours must be a non-empty list")
    elif any(not _is_positive_number(value) for value in durations):
        errors.append("bls.durations_hours values must be positive numbers")

    if workflow in {"baseline", "scaleup", "search"}:
        _require_keys(config["paths"], "paths", {"raw", "processed", "catalog", "reports"}, errors)
        _require_keys(config["ingest"], "ingest", {"mission", "cadence", "author"}, errors)
        _require_keys(
            config["preprocess"],
            "preprocess",
            {"quality_bitmask", "flatten_window_length"},
            errors,
        )
        _positive_integer(config["preprocess"], "flatten_window_length", "preprocess", errors)
        if (
            isinstance(config["preprocess"].get("flatten_window_length"), int)
            and config["preprocess"]["flatten_window_length"] % 2 == 0
        ):
            errors.append("preprocess.flatten_window_length must be odd")
        if "top_k" in bls:
            _positive_integer(bls, "top_k", "bls", errors)
    if workflow == "baseline":
        if not config["targets"]:
            errors.append("targets must contain at least one validation target")
        _validate_targets(config["targets"], errors)
        _require_keys(config["catalog"], "catalog", {"table", "output"}, errors)
        _require_keys(config["dataset"], "dataset", {"manifest"}, errors)
        _validate_machine_learning(config["machine_learning"], errors)
    elif workflow == "scaleup":
        _validate_machine_learning(config["machine_learning"], errors)
        _require_keys(
            config["scaleup"],
            "scaleup",
            {"workers", "target_file", "selection", "artifacts"},
            errors,
        )
        _positive_integer(config["scaleup"], "workers", "scaleup", errors)
        _require_mapping(config["scaleup"], "selection", "scaleup", errors)
        _require_mapping(config["scaleup"], "artifacts", "scaleup", errors)
    elif workflow == "search":
        search = config["candidate_search"]
        _require_keys(
            search,
            "candidate_search",
            {"sample_size", "model_path", "model_selection", "shortlist_size", "required_label", "artifacts"},
            errors,
        )
        sample_size = _positive_integer(search, "sample_size", "candidate_search", errors)
        shortlist_size = _positive_integer(search, "shortlist_size", "candidate_search", errors)
        if sample_size is not None and shortlist_size is not None and shortlist_size > sample_size:
            errors.append("candidate_search.shortlist_size cannot exceed sample_size")
        _require_mapping(search, "artifacts", "candidate_search", errors)
    else:
        _require_keys(
            config["inputs"], "inputs", {"shortlist", "target_pool", "processed_light_curves"}, errors
        )
        _require_keys(
            config["artifacts"],
            "artifacts",
            {"directory", "fap_results", "vetting_results", "crossmatch_results", "final_ranking", "report", "run_record"},
            errors,
        )
        _require_keys(
            config["fap"], "fap", {"permutations_per_target", "workers", "shuffle_method"}, errors
        )
        _positive_integer(config["fap"], "permutations_per_target", "fap", errors)
        _positive_integer(config["fap"], "workers", "fap", errors)
        _require_keys(
            config["vetting"],
            "vetting",
            {"odd_even_p_threshold", "secondary_sigma_threshold", "maximum_companion_radius_earth"},
            errors,
        )

    return errors


def check_config(path: str | Path, workflow: str | None = None) -> dict[str, Any]:
    """Return a machine-readable validation result without raising."""

    config_path = Path(path)
    result: dict[str, Any] = {
        "path": config_path.as_posix(),
        "workflow": workflow or "auto",
        "valid": False,
        "errors": [],
    }
    try:
        config = _read_yaml_config(config_path)
        selected = workflow or infer_workflow(config)
        result["workflow"] = selected
        errors = validate_workflow_config(config, selected)
        result["errors"] = errors
        result["valid"] = not errors
    except (ConfigurationError, FileNotFoundError, UnicodeError) as exc:
        result["errors"] = [str(exc)]
    return result


def _read_yaml_config(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration does not exist: {config_path}")
    try:
        payload = yaml.load(config_path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("configuration root must be a YAML mapping")
    return payload


def _require_keys(section: Mapping[str, Any], name: str, keys: set[str], errors: list[str]) -> None:
    missing = sorted(keys - set(section))
    if missing:
        errors.append(f"{name} missing keys: {', '.join(missing)}")


def _require_mapping(
    section: Mapping[str, Any], key: str, name: str, errors: list[str]
) -> Mapping[str, Any] | None:
    value = section.get(key)
    if not isinstance(value, Mapping):
        errors.append(f"{name}.{key} must be a mapping")
        return None
    return value


def _validate_machine_learning(ml: Mapping[str, Any], errors: list[str]) -> None:
    _require_keys(
        ml,
        "machine_learning",
        {"folds", "folded_bins", "negative_sample", "random_forest", "cnn"},
        errors,
    )
    _positive_integer(ml, "folds", "machine_learning", errors)
    _positive_integer(ml, "folded_bins", "machine_learning", errors)
    _require_mapping(ml, "negative_sample", "machine_learning", errors)
    _require_mapping(ml, "random_forest", "machine_learning", errors)
    _require_mapping(ml, "cnn", "machine_learning", errors)


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _positive_number(section: Mapping[str, Any], key: str, name: str, errors: list[str]) -> float | None:
    if key not in section:
        return None
    value = section[key]
    if not _is_positive_number(value):
        errors.append(f"{name}.{key} must be a positive number")
        return None
    return float(value)


def _positive_integer(section: Mapping[str, Any], key: str, name: str, errors: list[str]) -> int | None:
    if key not in section:
        return None
    value = section[key]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        errors.append(f"{name}.{key} must be a positive integer")
        return None
    return value


def _validate_targets(targets: list[Any], errors: list[str]) -> None:
    identifiers: set[str] = set()
    for index, target in enumerate(targets):
        if not isinstance(target, Mapping):
            errors.append(f"targets[{index}] must be a mapping")
            continue
        missing = sorted({"id", "id_type", "name"} - set(target))
        if missing:
            errors.append(f"targets[{index}] missing keys: {', '.join(missing)}")
        identifier = str(target.get("id", "")).strip()
        if identifier in identifiers:
            errors.append(f"duplicate target id: {identifier}")
        elif identifier:
            identifiers.add(identifier)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "configs",
        nargs="*",
        type=Path,
        help="YAML files; defaults to all four packaged workflow configs",
    )
    parser.add_argument(
        "--workflow",
        choices=["auto", *DEFAULT_CONFIGS],
        default="auto",
        help="Expected workflow for explicitly listed files",
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable validation report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.configs:
        expected = None if args.workflow == "auto" else args.workflow
        jobs = [(path, expected) for path in args.configs]
    elif args.workflow == "auto":
        source = default_config_source()
        jobs = [
            (source.joinpath(path.name), workflow)
            for workflow, path in DEFAULT_CONFIGS.items()
        ]
    else:
        jobs = [(default_config_source().joinpath(DEFAULT_CONFIGS[args.workflow].name), args.workflow)]
    checks = [check_config(path, workflow) for path, workflow in jobs]
    report = {"schema_version": 1, "valid": all(item["valid"] for item in checks), "checks": checks}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in checks:
            status = "PASS" if item["valid"] else "FAIL"
            print(f"[{status}] {item['path']} ({item['workflow']})")
            for error in item["errors"]:
                print(f"  - {error}")
        print(f"Configuration check: {'passed' if report['valid'] else 'failed'} ({len(checks)} file(s))")
    return 0 if report["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
