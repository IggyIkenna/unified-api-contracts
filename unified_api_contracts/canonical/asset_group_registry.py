"""Cross-asset-group canonical inventory registry — Phase 5C.

Provides a single entry-point that returns the full canonical surface for any
asset_group: venues, data_types, and source coverage-start windows.

Resolves the § A1 problem from the 2026-05-08 catalogue audit: there was no
central "give me everything for asset_group X" surface — the data was spread
across VENUES_BY_ASSET_GROUP, DATA_TYPES_BY_ASSET_GROUP, and 5 per-asset-group
``*_SOURCE_COVERAGE_START`` dicts in ``coverage_starts.py``.

Usage::

    from unified_api_contracts.canonical.asset_group_registry import (
        get_canonical_inventory,
    )
    inv = get_canonical_inventory("cefi")
    print(inv.venues)           # ("BINANCE-SPOT", "BINANCE-FUTURES", ...)
    print(inv.data_types)       # ("book_snapshot_5", "futures_chain", ...)
    print(inv.source_coverage_start)  # {"BINANCE-SPOT": date(2017, 8, 17), ...}

SSOT: cross_asset_group_catalogue_audit_2026_05_10.md Phase 5C.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from unified_api_contracts.canonical.coverage_starts import (
    CEFI_SOURCE_COVERAGE_START,
    DEFI_SOURCE_COVERAGE_START,
    PREDICTION_SOURCE_COVERAGE_START,
    SPORTS_SOURCE_COVERAGE_START,
    TRADFI_SOURCE_COVERAGE_START,
)
from unified_api_contracts.registry.market_data_categories import (
    DATA_TYPES_BY_ASSET_GROUP,
    VENUES_BY_ASSET_GROUP,
)

_COVERAGE_BY_ASSET_GROUP: dict[str, dict[str, date]] = {
    "cefi": CEFI_SOURCE_COVERAGE_START,
    "defi": DEFI_SOURCE_COVERAGE_START,
    "tradfi": TRADFI_SOURCE_COVERAGE_START,
    "sports": SPORTS_SOURCE_COVERAGE_START,
    "prediction": PREDICTION_SOURCE_COVERAGE_START,
}

KNOWN_ASSET_GROUPS: frozenset[str] = frozenset(_COVERAGE_BY_ASSET_GROUP)


@dataclass(frozen=True)
class AssetGroupInventory:
    """Canonical surface for a single asset_group.

    Attributes:
        asset_group: Lowercase asset-group key (cefi/defi/tradfi/sports/prediction).
        venues: Ordered tuple of canonical venue IDs for this asset_group.
        data_types: Ordered tuple of canonical data_type strings.
        source_coverage_start: Venue/source-name → earliest available date.
            Key format varies by asset_group (venue IDs for cefi/defi; source
            names like "DATABENTO" for tradfi; league keys for sports).
    """

    asset_group: str
    venues: tuple[str, ...]
    data_types: tuple[str, ...]
    source_coverage_start: dict[str, date]


def get_canonical_inventory(asset_group: str) -> AssetGroupInventory:
    """Return the canonical inventory for ``asset_group``.

    Args:
        asset_group: Lowercase asset-group key — one of
            ``cefi`` / ``defi`` / ``tradfi`` / ``sports`` / ``prediction``.

    Returns:
        :class:`AssetGroupInventory` with venues, data_types, and
        source_coverage_start populated from UAC SSOTs.

    Raises:
        KeyError: If ``asset_group`` is not a known asset_group key.
    """
    ag = asset_group.lower()
    if ag not in KNOWN_ASSET_GROUPS:
        raise KeyError(
            f"Unknown asset_group {asset_group!r}. "
            f"Known: {sorted(KNOWN_ASSET_GROUPS)}"
        )
    return AssetGroupInventory(
        asset_group=ag,
        venues=tuple(VENUES_BY_ASSET_GROUP.get(ag, [])),
        data_types=tuple(DATA_TYPES_BY_ASSET_GROUP.get(ag, [])),
        source_coverage_start=dict(_COVERAGE_BY_ASSET_GROUP[ag]),
    )


__all__ = [
    "KNOWN_ASSET_GROUPS",
    "AssetGroupInventory",
    "get_canonical_inventory",
]
