"""Generic config-versioning primitives — shared by every config-as-data
surface (``MVP_SCOPE``, the sports-leagues registry, the prediction-markets
taxonomy).

The gap (audit §B3): pure **config** — which families are MVP, which leagues,
which market-groups — has no version distinct from code/semver. A config
change is *data*, not logic, so it must NOT force a repo semver bump, but it
MUST be tracked so a coverage delta in data-status attributes to a
**scope-change** (the config moved) vs a **data-change** (the data moved).

Mechanism: a monotonic ``config_version`` integer + a deterministic
``config_content_hash`` (content-addressed). PER-CONFIG, not a single global
int — ``MVP_SCOPE`` / leagues / prediction-markets change independently, so a
leagues edit must not bump the MVP_SCOPE version and falsely flag an MVP
coverage delta. Metadata only — never a GCS hive-path segment (unlike
``formula_version``).

The hash MUST be stable across processes (independent of
``PYTHONHASHSEED`` string-hash randomisation) — :func:`canonical_config_repr`
SORTS every set/frozenset/dict before serialising (the
generators-must-be-deterministic rule).

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md`` §
"Config versioning (config_version)".
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, fields, is_dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class ConfigDescriptor:
    """``(config_version, config_content_hash)`` pair surfaced in data-status
    so a coverage delta attributes to scope-change vs data-change."""

    config_version: int
    config_content_hash: str


def canonical_config_repr(obj: object) -> str:
    """Deterministic string for a config value.

    Frozensets / sets / dict keys are SORTED so the hash is stable across
    processes (independent of ``PYTHONHASHSEED``). Frozen dataclasses and
    Pydantic models serialise via their declared field order (stable).
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        parts = [f"{f.name}={canonical_config_repr(getattr(obj, f.name))}" for f in fields(obj)]
        return f"{type(obj).__name__}({','.join(parts)})"
    if isinstance(obj, BaseModel):
        parts = [f"{name}={canonical_config_repr(getattr(obj, name))}" for name in type(obj).model_fields]
        return f"{type(obj).__name__}({','.join(parts)})"
    if isinstance(obj, (frozenset, set)):
        return "{" + ",".join(sorted(canonical_config_repr(x) for x in obj)) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(canonical_config_repr(x) for x in obj) + "]"
    if isinstance(obj, dict):
        return "{" + ",".join(f"{k}:{canonical_config_repr(v)}" for k, v in sorted(obj.items())) + "}"
    return repr(obj)


def compute_config_content_hash(version: int, items: Sequence[tuple[str, object]]) -> str:
    """SHA-256 (16-hex prefix) of a config's ``version`` + its ``(key, value)``
    content pairs.

    Callers pass ``items`` already in a deterministic order (sort the keys).
    The serialisation is byte-stable, so the digest flips IFF the version or
    any value's canonical content flips.
    """
    hasher = hashlib.sha256()
    hasher.update(str(version).encode())
    hasher.update(b"\x00")
    for key, value in items:
        hasher.update(f"{key}={canonical_config_repr(value)}".encode())
        hasher.update(b"\x00")
    return hasher.hexdigest()[:16]


__all__ = [
    "ConfigDescriptor",
    "canonical_config_repr",
    "compute_config_content_hash",
]
