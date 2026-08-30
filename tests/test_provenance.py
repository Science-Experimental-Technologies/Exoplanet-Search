import numpy as np
import pandas as pd
import pytest

from src.provenance import ResumeGuard, atomic_json, file_hash, isolated_workspace
from src.independent_validation.fap import _valid_cache, run_fap


def test_resume_requires_identical_inputs_config_and_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    source = tmp_path / "data/input.csv"
    source.write_text("original")
    with pytest.raises(RuntimeError, match="checkpoint"):
        ResumeGuard("test", {"seed": 1}, True)
    guard = ResumeGuard("test", {"seed": 1}, False)
    guard.mark("stage")
    guard.save()
    assert ResumeGuard("test", {"seed": 1}, True).allows("stage")
    guard.completed = {"a", "b", "c"}
    guard.invalidate_from("b", ["a", "b", "c"])
    assert guard.completed == {"a"}
    with pytest.raises(RuntimeError, match="changed"):
        ResumeGuard("test", {"seed": 2}, True)
    source.write_text("modified")
    with pytest.raises(RuntimeError, match="changed"):
        ResumeGuard("test", {"seed": 1}, True)


def test_null_cache_requires_fingerprint_checksum_and_finite_draws(tmp_path):
    path = tmp_path / "cache.parquet"
    pd.DataFrame({"iteration": [0, 1], "null_max_power": [1., 2.]}).to_parquet(path)
    assert not _valid_cache(path, 2, "a")
    atomic_json(path.with_suffix(".json"), {"fingerprint": "a", "sha256": file_hash(path)})
    assert _valid_cache(path, 2, "a")
    assert not _valid_cache(path, 2, "b")
    pd.DataFrame({"iteration": [0, 1], "null_max_power": [1., np.nan]}).to_parquet(path)
    assert not _valid_cache(path, 2, "a")


def test_unsupported_null_method_fails_before_writing(tmp_path):
    with pytest.raises(ValueError, match="Unsupported"):
        run_fap(pd.DataFrame(), {"fap": {"shuffle_method": "not-implemented"}})


def test_workspace_keeps_outputs_separate_and_restores_cwd(tmp_path):
    from pathlib import Path
    original = Path.cwd()
    configs = tmp_path / "source"
    configs.mkdir()
    (configs / "sample.yaml").write_text("seed: 42")
    destination = tmp_path / "run"
    with isolated_workspace(destination, configs):
        assert Path.cwd() == destination
        assert Path("configs/sample.yaml").is_file()
    assert Path.cwd() == original
    with pytest.raises(ValueError, match="not an SXS workspace"):
        with isolated_workspace(configs, configs):
            pass


def test_fap_cache_reuse_and_seed_invalidation(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import src.independent_validation.fap as module
    from src.workbench import prepare, synthetic_curve
    monkeypatch.setattr(module, "ProcessPoolExecutor", ThreadPoolExecutor)
    frame, _ = synthetic_curve()
    processed, _ = prepare(frame)
    processed.to_parquet(tmp_path / "1_clean.parquet", index=False)
    config = {"project": {"random_seed": 3}, "inputs": {"processed_light_curves": str(tmp_path)},
              "artifacts": {"fap_results": str(tmp_path / "fap.parquet")},
              "fap": {"shuffle_method": "independent_segment_circular_shift", "minimum_roll_fraction": .1,
                      "permutations_per_target": 2, "workers": 1},
              "bls": {"minimum_period_days": .5, "maximum_period_days": 8, "durations_hours": [2., 4.],
                      "frequency_oversampling": 2, "duration_oversampling": 10, "objective": "snr", "method": "fast"}}
    shortlist = pd.DataFrame({"target_id": ["1"], "candidate_id": ["1-r1"], "power": [20.]})
    first = run_fap(shortlist, config)
    cache = next((tmp_path / "null_cache").glob("*.parquet"))
    checksum = file_hash(cache)
    run_fap(shortlist, config)
    assert len(list((tmp_path / "null_cache").glob("*.parquet"))) == 1
    config["project"]["random_seed"] = 4
    run_fap(shortlist, config)
    assert len(list((tmp_path / "null_cache").glob("*.parquet"))) == 2
    assert file_hash(cache) == checksum and len(first) == 2
