"""Content fingerprints and fail-closed workflow resume checkpoints."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
from importlib.metadata import version, PackageNotFoundError
from importlib.resources import files
from contextlib import contextmanager
import os
import math


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def runtime_identity() -> dict:
    packages = {}
    for name in ("numpy", "pandas", "astropy", "scipy", "scikit-learn", "lightkurve",
                 "batman-package", "tensorflow", "tensorflow-cpu", "mlflow", "astroquery",
                 "pyarrow", "matplotlib", "joblib", "PyYAML"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "unavailable"
    root = Path(__file__).parent
    return {"python": platform.python_version(), "packages": packages,
            "platform": platform.platform(), "machine": platform.machine(),
            "source": {p.relative_to(root).as_posix(): file_hash(p) for p in sorted(root.rglob("*.py"))}}


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(json_safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def json_safe(value):
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class ResumeGuard:
    """Reject missing/stale checkpoints; never infer completion from old files alone.

    Hashing is deliberately conservative and can be expensive for mission data.
    Checkpoints are local to a working directory. Concurrent workflows sharing
    that directory are unsupported. No checkpoint is written during dry runs.
    """

    def __init__(self, name: str, config: dict, resume: bool):
        self.config = config
        self.path = Path(".sxs-state") / f"{name}.json"
        self.identity = fingerprint({"config": config, "runtime": runtime_identity()})
        self.completed: set[str] = set()
        if resume:
            try:
                previous = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise RuntimeError("Resume requires a new fingerprinted checkpoint; use a separate workspace for a fresh run") from exc
            if previous.get("identity") != self.identity or previous.get("files") != self.snapshot():
                raise RuntimeError("Resume refused: configuration, runtime, or artifacts changed; start a separate experiment")
            self.completed = set(previous["completed"])

    def snapshot(self) -> dict:
        roots = {Path("data"), Path("models"), Path("reports")}
        roots.update(Path(p) for p in self.config.get("paths", {}).values() if isinstance(p, str))
        def visit(value):
            if isinstance(value, dict):
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, str) and len(value) < 240 and "://" not in value:
                try:
                    if Path(value).is_file():
                        roots.add(Path(value))
                except OSError:
                    pass
        visit(self.config)
        files = {p.resolve() for root in roots for p in
                 ([root] if root.is_file() else root.rglob("*")) if p.is_file()}
        return {str(p): file_hash(p) for p in sorted(files)}

    def mark(self, step: object) -> None:
        self.completed.add(str(step))

    def allows(self, step: object) -> bool:
        return str(step) in self.completed

    def invalidate_from(self, step: object, order) -> None:
        ordered = [str(item) for item in order]
        self.completed.difference_update(ordered[ordered.index(str(step)):])

    def save(self) -> None:
        atomic_json(self.path, {"identity": self.identity, "files": self.snapshot(),
                               "completed": sorted(self.completed)})


def default_config_source():
    checkout = Path(__file__).resolve().parent.parent / "configs"
    return checkout if checkout.is_dir() else files("src").joinpath("default_configs")


def initialize_workspace(destination: Path, config_source=None) -> dict:
    """Create a marked workspace with independent copies of the default configs."""

    destination = destination.resolve()
    config_source = default_config_source() if config_source is None else config_source
    with _workspace_lock(destination):
        return _initialize_workspace_files(destination, config_source)


@contextmanager
def _workspace_lock(destination: Path):
    from src.execution import WorkspaceLock

    with WorkspaceLock(destination):
        yield


def _initialize_workspace_files(destination: Path, config_source) -> dict:
    marker = destination / ".sxs-workspace.json"
    if destination.exists():
        if not marker.is_file():
            raise ValueError("Existing directory is not an SXS workspace; choose a new directory")
        config_directory = destination / "configs"
        if not config_directory.is_dir():
            raise ValueError("SXS workspace is missing its configs directory")
        created = False
    else:
        if not config_source.is_dir():
            raise ValueError("Workspace creation requires packaged workflow configurations")
        destination.mkdir(parents=True)
        config_directory = destination / "configs"
        config_directory.mkdir()
        names = []
        for config in config_source.iterdir():
            if config.name.endswith(".yaml") and config.is_file():
                (config_directory / config.name).write_bytes(config.read_bytes())
                names.append(config.name)
        if not names:
            raise ValueError("Workspace creation found no packaged YAML configurations")
        atomic_json(
            marker,
            {
                "schema_version": 1,
                "source": "default-config-source",
                "purpose": "isolated workflow outputs",
                "configs": sorted(names),
            },
        )
        created = True
    names = sorted(path.name for path in config_directory.glob("*.yaml") if path.is_file())
    return {"workspace": str(destination), "created": created, "configs": names}


@contextmanager
def isolated_workspace(destination: Path, config_source=None):
    from src.execution import WorkspaceLock

    with WorkspaceLock(destination):
        with _isolated_workspace(destination, config_source) as workspace:
            yield workspace


@contextmanager
def _isolated_workspace(destination: Path, config_source=None):
    """Create an explicit legacy-workflow sandbox; reuse only marked workspaces."""
    destination = destination.resolve()
    # The caller already holds the workspace lock.
    config_source = default_config_source() if config_source is None else config_source
    _initialize_workspace_files(destination, config_source)
    previous = Path.cwd()
    try:
        os.chdir(destination)
        yield destination
    finally:
        os.chdir(previous)
