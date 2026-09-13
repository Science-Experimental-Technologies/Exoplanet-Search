from __future__ import annotations

import json

from src import doctor


def test_doctor_json_reports_runtime(capsys) -> None:
    code = doctor.main(["--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "ok"
    assert payload["python"]["supported"] is True
    assert all(item["ok"] for item in payload["dependencies"])
    assert all(item["available"] for item in payload["default_configs"])
    assert all(item["valid"] for item in payload["default_configs"])
    assert payload["network"] == {"requested": False, "checks": []}


def test_doctor_network_failure_is_explicit(monkeypatch, capsys) -> None:
    def fail(*_args, **_kwargs):
        raise TimeoutError("offline test")

    monkeypatch.setattr(doctor, "urlopen", fail)
    assert doctor.main(["--network", "--timeout", "0.1"]) == 3
    output = capsys.readouterr().out
    assert "Status: FAILED" in output
    assert "TimeoutError: offline test" in output


def test_doctor_rejects_invalid_timeout() -> None:
    try:
        doctor.main(["--timeout", "0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("invalid timeout should be rejected")


def test_doctor_ignores_unselected_optional_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(doctor.metadata, "version", lambda _name: doctor.__version__)
    monkeypatch.setattr(
        doctor.metadata,
        "requires",
        lambda _name: [
            "numpy==1.26.4",
            'tensorflow==2.18.1; extra == "full"',
            'pytest==9.1.1; extra == "test"',
        ],
    )
    assert doctor._declared_requirements() == [("numpy", "1.26.4")]
