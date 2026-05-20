"""Domain facade -- re-exports from canonical/domain/execution/ + venue helpers."""

from __future__ import annotations

from unified_api_contracts.canonical.domain.execution import *
from unified_api_contracts.registry.capability_declarations import (
    CEFI_CAPABILITIES,
    DEFI_CAPABILITIES,
    SPORTS_CAPABILITIES,
    TRADFI_CAPABILITIES,
)

# Prediction market slugs within SPORTS_CAPABILITIES — binary YES/NO sides, not HOME/AWAY/DRAW.
_PREDICTION_SOURCES: frozenset[str] = frozenset({"kalshi", "polymarket"})


def _build_venue_asset_group_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for cap in CEFI_CAPABILITIES:
        lookup[cap.source] = "cefi"
    for cap in DEFI_CAPABILITIES:
        lookup[cap.source] = "defi"
    for cap in SPORTS_CAPABILITIES:
        lookup[cap.source] = "prediction" if cap.source in _PREDICTION_SOURCES else "sports"
    for cap in TRADFI_CAPABILITIES:
        lookup[cap.source] = "tradfi"
    return lookup


_VENUE_ASSET_GROUP: dict[str, str] = _build_venue_asset_group_lookup()


def get_venue_asset_group(venue: str) -> str:
    """Return asset_group for a venue slug from CAPABILITY_DECLARATIONS.

    Returns "cefi", "defi", "sports", "prediction", or "tradfi".
    Unknown venues fall back to "cefi".
    """
    return _VENUE_ASSET_GROUP.get(venue.lower(), "cefi")
