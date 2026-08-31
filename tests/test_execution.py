import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.cli import main
from src.execution import WorkspaceLock, WorkspaceBusy
from src.workbench import new_run


def test_cli_error_codes_and_interruption_status(tmp_path, monkeypatch, capsys):
    def broken(argv):
        new_run(tmp_path / "failure", "test")
        raise RuntimeError("controlled failure")
    monkeypatch.setattr("src.cli._commands", lambda: {"fake": broken})
    assert main(["fake"]) == 1
    assert "controlled failure" in capsys.readouterr().err
    assert json.loads((tmp_path / "failure/operation.json").read_text())["status"] == "failed"
    def interrupted(argv):
        new_run(tmp_path / "interrupt", "test")
        raise KeyboardInterrupt
    monkeypatch.setattr("src.cli._commands", lambda: {"fake": interrupted})
    assert main(["fake"]) == 130
    assert json.loads((tmp_path / "interrupt/operation.json").read_text())["status"] == "interrupted"
    with WorkspaceLock(tmp_path / "interrupt"):
        pass  # Interrupt releases the lock.
    assert main(["missing"]) == 2


def test_lock_excludes_another_process_and_recovers_after_exit(tmp_path):
    source = Path(__file__).resolve().parents[1]
    code = ("import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
            "from src.execution import WorkspaceLock; "
            "lock=WorkspaceLock(Path(sys.argv[2])); lock.__enter__(); print('locked',flush=True); input()")
    child = subprocess.Popen([sys.executable, "-c", code, str(source), str(tmp_path / "workspace")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(WorkspaceBusy):
            with WorkspaceLock(tmp_path / "workspace"):
                pass
        child.communicate("\n", timeout=10)
        with WorkspaceLock(tmp_path / "workspace"):
            pass
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()


def test_runtime_records_all_scientific_dependencies():
    from src.provenance import runtime_identity
    packages = runtime_identity()["packages"]
    assert {"lightkurve", "batman-package", "tensorflow", "mlflow", "joblib", "PyYAML"} <= packages.keys()
