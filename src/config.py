"""Shared configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_targets(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Load inline v1 targets or an external Phase 7 target list."""

    inline = config.get("targets") or []
    if inline:
        return list(inline)
    target_file = config.get("scaleup", {}).get("target_file")
    if not target_file:
        return []
    path = Path(target_file)
    if not path.is_file():
        raise FileNotFoundError(f"Scale-up target file does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    targets = payload.get("targets") or []
    if not targets:
        raise ValueError(f"Scale-up target file contains no targets: {path}")
    return list(targets)


def artifact_path(config: dict[str, Any], key: str, default: str | Path) -> Path:
    """Resolve an optional Phase 7 artifact override without changing v1 paths."""

    return Path(config.get("scaleup", {}).get("artifacts", {}).get(key, default))
