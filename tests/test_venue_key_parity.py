"""Venue-key parity tests — Phase 1D (cross_asset_group_catalogue_audit_2026_05_10.md).

Asserts that every venue-keyed dict in UAC uses canonical uppercase keys and that
``to_canonical_venue`` resolves all known aliases.

Covers DF-4 (BLAZESTAKE→SOLBLAZE-SOLANA), DF-17 (TRADERJOEV2→TRADER_JOE_V2, underscore-canonical 2026-06-01),
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
    DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED,
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
        ("aavev3", "AAVE_V3-ETHEREUM"),
        ("AAVE_V3", "AAVE_V3-ETHEREUM"),
        ("trader_joev2", "TRADER_JOE_V2-AVALANCHE"),
        ("TRADERJOEV2-AVALANCHE", "TRADER_JOE_V2-AVALANCHE"),  # DF-17 (underscore-canonical 2026-06-01)
        ("TRADER_JOEV2-AVALANCHE", "TRADER_JOE_V2-AVALANCHE"),  # legacy glued -CHAIN → canonical
        ("velodromev2", "VELODROME_V2-OPTIMISM"),
        ("VELODROMEV2-OPTIMISM", "VELODROME_V2-OPTIMISM"),  # legacy glued -CHAIN → canonical
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
# DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED — 2026-07-22 honest-
# coverage correction (design doc "Correction Design: 11 DeFi Venues →
# Honest-Coverage Registry"). Pins the exact 6-venue ACCURATE-BUT-MANUAL-ONLY
# membership and guards against re-widening it to the 5 venues that do NOT
# qualify (FRAX=UNVERIFIED-CLAIM; ALCHEMY/FLASHBOTS/ACROSS/STARGATE=STILL-
# BROKEN), and against any entry claiming ongoing/scheduled capture.
# ---------------------------------------------------------------------------


def test_defi_adapter_verified_keys_are_canonical() -> None:
    """Every DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED key is in ALL_DEFI_VENUES."""
    all_venues_set = set(ALL_DEFI_VENUES)
    bad = [v for v in DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED if v not in all_venues_set]
    assert not bad, (
        f"DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED has entries not in ALL_DEFI_VENUES: {sorted(bad)}"
    )


def test_defi_adapter_verified_is_empty_post_graduation() -> None:
    """The 2026-07-22 design doc's 6-venue ACCURATE-BUT-MANUAL-ONLY set graduated
    to DEFI_VENUE_PHASE="live" 2026-07-31 (defi_venue_pipeline_to_live_ao_build_
    2026_07_30.md todo 5, once todo 2 confirmed 3 consecutive real scheduled
    production runs -- this dict's own documented promotion criterion) and were
    removed from here. Regression guard against silently re-adding FRAX
    (UNVERIFIED-CLAIM) or ALCHEMY/FLASHBOTS/ACROSS/STARGATE (STILL-BROKEN) --
    none of those 5 ever qualified as ACCURATE-BUT-MANUAL-ONLY -- via an empty
    dict; a future genuinely-new ACCURATE-BUT-MANUAL-ONLY venue is expected to
    update this test's `expected` set, not treated as drift.
    """
    expected: set[str] = set()
    actual = set(DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED)
    assert actual == expected, (
        f"DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED membership drifted from the "
        f"post-2026-07-31-graduation empty set. "
        f"Missing: {sorted(expected - actual)}; unexpected extras: {sorted(actual - expected)}"
    )
    graduated = {
        "ANKR-ETHEREUM",
        "STADER-ETHEREUM",
        "STAKEWISE-ETHEREUM",
        "SWELL-ETHEREUM",
        "MANTLE-ETHEREUM",
        "MAKER-ETHEREUM",
    }
    now_live = {v for v in graduated if DEFI_VENUE_PHASE.get(v) == "live"}
    assert now_live == graduated, (
        f"Expected all 6 graduated venues to be phase=='live'; these are not: {sorted(graduated - now_live)}"
    )


def test_defi_adapter_verified_excludes_still_broken_and_unverified_venues() -> None:
    """FRAX (UNVERIFIED-CLAIM) and ALCHEMY/FLASHBOTS/ACROSS/STARGATE (STILL-BROKEN)
    must never appear in DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED."""
    excluded = {
        "FRAX-ETHEREUM",
        "ALCHEMY-ETHEREUM",
        "FLASHBOTS-ETHEREUM",
        "ACROSS-ETHEREUM",
        "STARGATE-ETHEREUM",
    }
    present = excluded & set(DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED)
    assert not present, (
        f"DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED must not contain "
        f"UNVERIFIED-CLAIM/STILL-BROKEN venues, found: {sorted(present)}"
    )


def test_defi_adapter_verified_wording_has_no_overclaim() -> None:
    """Every note must be scoped to a single manual/ad-hoc verification, never
    imply ongoing/scheduled/"months-long" capture (the original false claim
    this registry correction was written to fix)."""
    banned_phrases = ("months-long", "verified working", "captured data")
    for venue, note in DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED.items():
        lowered = note.lower()
        for phrase in banned_phrases:
            assert phrase not in lowered, f"{venue} note overclaims via banned phrase {phrase!r}: {note!r}"
        assert "manual" in lowered or "ad-hoc" in lowered, (
            f"{venue} note must disclose manual/ad-hoc provenance: {note!r}"
        )


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
