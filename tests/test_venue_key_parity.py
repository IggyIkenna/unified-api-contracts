"""Venue-key parity tests — Phase 1D (cross_asset_group_catalogue_audit_2026_05_10.md).

Asserts that every venue-keyed dict in UAC uses canonical uppercase keys and that
``to_canonical_venue`` resolves all known aliases.

Covers DF-4 (BLAZESTAKE→SOLBLAZE-SOLANA), DF-17 (TRADERJOEV2→TRADER_JOEV2),
CF-3 (CeFi uppercase), SP-3 (Sports uppercase).

CF-4 (BINANCE vs BINANCE-SPOT split) is NOT covered here — requires structural
refactor of CEFI_SOURCE_COVERAGE_START; deferred to a separate plan.
DF-5 (sDAI SPARK vs MAKER attribution) is NOT covered here — deferred separately.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.defi_protocol_registry import DEFI_VENUE_TO_PROTOCOL
from unified_api_contracts.registry.defi_venue_capabilities import (
    DEFI_VENUE_DATA_TYPE_CAPABILITIES,
)
from unified_api_contracts.registry.defi_venues import (
    ALL_DEFI_VENUES,
    DEFI_VENUE_PHASE,
    LEGACY_DEFI_VENUE_ALIASES,
    MTDS_DEFI_VENUES,
    to_canonical_venue,
)
from unified_api_contracts.registry.market_data_categories import VENUES_BY_ASSET_GROUP

# ---------------------------------------------------------------------------
# to_canonical_venue — unit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Simple uppercase normalization (CeFi / Sports)
        ("binance-spot", "BINANCE-SPOT"),
        ("okx", "OKX"),
        ("odds_api", "ODDS_API"),
        ("pinnacle", "PINNACLE"),
        # DeFi alias resolution
        ("aavev3", "AAVEV3-ETHEREUM"),
        ("AAVEV3", "AAVEV3-ETHEREUM"),
        ("trader_joev2", "TRADER_JOEV2-AVALANCHE"),
        ("TRADERJOEV2-AVALANCHE", "TRADER_JOEV2-AVALANCHE"),  # DF-17
        ("blazestake", "SOLBLAZE-SOLANA"),  # DF-4
        ("BLAZESTAKE-SOLANA", "SOLBLAZE-SOLANA"),  # DF-4
        ("solblaze", "SOLBLAZE-SOLANA"),
        ("lido", "LIDO-ETHEREUM"),
        ("radiant", "RADIANT-ARBITRUM"),
        # Unknown venue — returned uppercase as-is
        ("MY-CUSTOM-VENUE", "MY-CUSTOM-VENUE"),
        ("unknown_venue", "UNKNOWN_VENUE"),
    ],
)
def test_to_canonical_venue(raw: str, expected: str) -> None:
    assert to_canonical_venue(raw) == expected


# ---------------------------------------------------------------------------
# DEFI_VENUE_DATA_TYPE_CAPABILITIES — all keys must be in ALL_DEFI_VENUES
# ---------------------------------------------------------------------------


def test_defi_capability_keys_are_canonical() -> None:
    """Every DEFI_VENUE_DATA_TYPE_CAPABILITIES key must appear in ALL_DEFI_VENUES."""
    all_venues_set = set(ALL_DEFI_VENUES)
    bad = [v for v in DEFI_VENUE_DATA_TYPE_CAPABILITIES if v not in all_venues_set]
    assert not bad, f"DEFI_VENUE_DATA_TYPE_CAPABILITIES has {len(bad)} keys not in ALL_DEFI_VENUES: {sorted(bad)}"


# ---------------------------------------------------------------------------
# DEFI_VENUE_PHASE — all keys must be in ALL_DEFI_VENUES
# ---------------------------------------------------------------------------


def test_defi_venue_phase_keys_are_canonical() -> None:
    """Every DEFI_VENUE_PHASE key must appear in ALL_DEFI_VENUES."""
    all_venues_set = set(ALL_DEFI_VENUES)
    bad = [v for v in DEFI_VENUE_PHASE if v not in all_venues_set]
    assert not bad, f"DEFI_VENUE_PHASE has {len(bad)} keys not in ALL_DEFI_VENUES: {sorted(bad)}"


# ---------------------------------------------------------------------------
# DEFI_VENUE_TO_PROTOCOL — all keys must be in ALL_DEFI_VENUES
# ---------------------------------------------------------------------------


def test_defi_venue_to_protocol_keys_are_canonical() -> None:
    """Every DEFI_VENUE_TO_PROTOCOL key must appear in ALL_DEFI_VENUES (DF-17 guard)."""
    all_venues_set = set(ALL_DEFI_VENUES)
    bad = [v for v in DEFI_VENUE_TO_PROTOCOL if v not in all_venues_set]
    assert not bad, f"DEFI_VENUE_TO_PROTOCOL has {len(bad)} keys not in ALL_DEFI_VENUES: {sorted(bad)}"


# ---------------------------------------------------------------------------
# MTDS_DEFI_VENUES — all entries must be in ALL_DEFI_VENUES
# ---------------------------------------------------------------------------


def test_mtds_defi_venues_are_canonical() -> None:
    """Every MTDS_DEFI_VENUES entry must appear in ALL_DEFI_VENUES."""
    all_venues_set = set(ALL_DEFI_VENUES)
    bad = [v for v in MTDS_DEFI_VENUES if v not in all_venues_set]
    assert not bad, f"MTDS_DEFI_VENUES has {len(bad)} entries not in ALL_DEFI_VENUES: {sorted(bad)}"


# ---------------------------------------------------------------------------
# VENUES_BY_ASSET_GROUP — all venues must be uppercase (CF-3/SP-3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "asset_group",
    ["cefi", "sports", "defi", "tradfi", "prediction"],
)
def test_venues_by_asset_group_are_uppercase(asset_group: str) -> None:
    """VENUES_BY_ASSET_GROUP values must use uppercase venue IDs (CF-3/SP-3)."""
    venues = VENUES_BY_ASSET_GROUP.get(asset_group, [])
    bad = [v for v in venues if v != v.upper()]
    assert not bad, f"VENUES_BY_ASSET_GROUP['{asset_group}'] has {len(bad)} non-uppercase entries: {sorted(bad)}"


# ---------------------------------------------------------------------------
# LEGACY_DEFI_VENUE_ALIASES — alias values must be in ALL_DEFI_VENUES
# ---------------------------------------------------------------------------


def test_legacy_alias_targets_are_canonical() -> None:
    """Every LEGACY_DEFI_VENUE_ALIASES value must appear in ALL_DEFI_VENUES."""
    all_venues_set = set(ALL_DEFI_VENUES)
    bad = {k: v for k, v in LEGACY_DEFI_VENUE_ALIASES.items() if v not in all_venues_set}
    assert not bad, (
        f"LEGACY_DEFI_VENUE_ALIASES has {len(bad)} values not in ALL_DEFI_VENUES: {dict(sorted(bad.items()))}"
    )
