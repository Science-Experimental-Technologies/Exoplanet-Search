from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config_check import ConfigurationError, check_config, load_workflow_config, main


def test_packaged_workflow_configs_pass(capsys) -> None:
    assert main(["--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["valid"] is True
    assert {item["workflow"] for item in report["checks"]} == {
        "baseline",
        "scaleup",
        "search",
        "validate",
    }


def test_auto_detection_and_semantic_failure(tmp_path: Path) -> None:
    source = Path("configs/candidate_search.yaml").read_text(encoding="utf-8")
    invalid = tmp_path / "search.yaml"
    invalid.write_text(source.replace("sample_size: 250", "sample_size: 10"), encoding="utf-8")
    result = check_config(invalid)
    assert result["workflow"] == "search"
    assert result["valid"] is False
    assert "shortlist_size cannot exceed sample_size" in result["errors"][0]


def test_duplicate_yaml_keys_are_rejected(tmp_path: Path) -> None:
    invalid = tmp_path / "duplicate.yaml"
    invalid.write_text("project: {}\nproject: {}\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="duplicate YAML key: project"):
        load_workflow_config(invalid, "baseline")


def test_explicit_workflow_mismatch_fails(capsys) -> None:
    assert main(["configs/base.yaml", "--workflow", "search"]) == 3
    assert "candidate_search" in capsys.readouterr().out


def test_nested_mapping_type_is_rejected_without_crashing(tmp_path: Path) -> None:
    source = Path("configs/candidate_search.yaml").read_text(encoding="utf-8")
    invalid = tmp_path / "search.yaml"
    invalid.write_text(source.replace("  artifacts:\n", "  artifacts: invalid\n  ignored:\n"), encoding="utf-8")
    result = check_config(invalid, "search")
    assert result["valid"] is False
    assert "candidate_search.artifacts must be a mapping" in result["errors"]
