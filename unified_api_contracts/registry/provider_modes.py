"""Provider modes from provider_api_versions.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_YAML_PATH = Path(__file__).resolve().parent / "provider_api_versions.yaml"


def get_provider_modes(provider: str) -> frozenset[str]:
    """Return the modes list for a provider as a frozenset, or frozenset() if absent/not found."""
    raw: dict[str, Any] = yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8")) or {}
    providers: dict[str, Any] = raw.get("providers") or {}
    entry: dict[str, Any] | None = providers.get(provider)
    if entry is None:
        return frozenset()
    modes: list[str] | None = entry.get("modes")
    if modes is None:
        return frozenset()
    return frozenset(str(m) for m in modes)
