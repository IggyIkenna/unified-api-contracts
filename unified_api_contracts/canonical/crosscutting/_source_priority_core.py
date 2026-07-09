"""Core ``SOURCE_PRIORITY`` lookup primitives — the foundation every other
source-priority helper builds on.

Split out of ``source_priority.py`` (900-line file-size QG, 2026-07-09) —
pure file-organization move, no behavior change. ``source_priority.py``
re-exports everything here so the public import path
(``unified_api_contracts.canonical.crosscutting.source_priority``) is
unchanged.

Kept deliberately dependency-free (only :data:`SOURCE_PRIORITY` itself) so
every other ``_source_priority_*`` submodule — and the facade — can import
from here without risk of a circular import.
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting._source_priority_data import (
    SOURCE_PRIORITY,
)


def get_source_priority(asset_group: str, data_type: str) -> list[str]:
    """Return the ordered source list for a ``(asset_group, data_type)`` pair.

    Returns a copy so callers cannot mutate the registry.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi`` / ``prediction``
            / ``sports`` / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Ordered list of source keys. Top entry is primary (the
        live-time-winning source).

    Raises:
        KeyError: If the pair is not registered. Failing loud is intentional
            — silent fallback would mask schema-drift bugs.
    """
    key = (asset_group, data_type)
    if key not in SOURCE_PRIORITY:
        msg = (
            f"No source priority registered for "
            f"asset_group={asset_group!r}, data_type={data_type!r}. "
            "Register the pair in SOURCE_PRIORITY before use."
        )
        raise KeyError(msg)
    return list(SOURCE_PRIORITY[key])


def get_primary_source(asset_group: str, data_type: str) -> str:
    """Return the primary (top-of-list) source key for a pair.

    Convenience for callers that don't need the full list — most stamping
    helpers just need the live-time source name to compute available_at.
    """
    return get_source_priority(asset_group, data_type)[0]


def has_source_priority(asset_group: str, data_type: str) -> bool:
    """Check whether the pair is registered (non-raising membership test)."""
    return (asset_group, data_type) in SOURCE_PRIORITY
