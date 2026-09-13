from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.cli import main
from src.provenance import file_hash, fingerprint, runtime_identity
from src.verify import verify_workspace


def _checkpoint(workspace: Path, artifact: Path, files: dict[str, str] | None = None) -> Path:
    config = yaml.safe_load((workspace / "configs/base.yaml").read_text(encoding="utf-8"))
    payload = {
        "identity": fingerprint({"config": config, "runtime": runtime_identity()}),
        "files": files if files is not None else {str(artifact.resolve()): file_hash(artifact)},
        "completed": ["0", "1"],
    }
    path = workspace / ".sxs-state/baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_verify_matches_identity_and_recorded_file_hashes(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    capsys.readouterr()
    artifact = workspace / "data/result.txt"
    artifact.parent.mkdir()
    artifact.write_text("accepted", encoding="utf-8")
    _checkpoint(workspace, artifact)

    assert main(["verify", str(workspace), "--workflow", "baseline", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    result = report["checkpoints"][0]
    assert result["valid"] is True
    assert result["verified_files"] == result["recorded_files"] == 1

    artifact.write_text("changed", encoding="utf-8")
    report = verify_workspace(workspace, ["baseline"])
    assert report["valid"] is False
    assert report["checkpoints"][0]["changed"] == ["data/result.txt"]

    artifact.write_text("accepted", encoding="utf-8")
    config_path = workspace / "configs/base.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("random_seed: 42", "random_seed: 43"),
        encoding="utf-8",
    )
    report = verify_workspace(workspace, ["baseline"])
    assert report["checkpoints"][0]["identity_matches"] is False
    assert report["valid"] is False


def test_verify_reports_absent_checkpoint_as_not_verified(tmp_path: Path) -> None:
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    report = verify_workspace(workspace, ["baseline"])
    assert report["valid"] is False
    assert report["checkpoints"][0]["exists"] is False
    assert "baseline checkpoint is absent" in report["issues"]


def test_verify_never_hashes_recorded_paths_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "experiment"
    assert main(["init", str(workspace), "--json"]) == 0
    artifact = workspace / "inside.txt"
    artifact.write_text("inside", encoding="utf-8")
    external = tmp_path / "outside.txt"
    external.write_text("outside", encoding="utf-8")
    _checkpoint(workspace, artifact, {str(external.resolve()): file_hash(external)})
    report = verify_workspace(workspace, ["baseline"])
    result = report["checkpoints"][0]
    assert result["outside_workspace"] == 1
    assert result["verified_files"] == 0
    assert report["valid"] is False
