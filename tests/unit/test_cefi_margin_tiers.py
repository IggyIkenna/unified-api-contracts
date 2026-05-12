"""Tests for ``unified_api_contracts.registry.cefi_margin_tiers``.

Covers the Phase 1E extension that added Deribit + Hyperliquid + Aster perp
margin tier schedules (defi_catalogue_chain_primitives_2026_05_10 Phase 1E).
Per FLAG 1 RESOLVED 2026-05-10, on-chain perp venues (Hyperliquid + Aster)
are classified under ``VENUES_BY_ASSET_GROUP['cefi']``; ``cefi_margin_tiers``
is the canonical perp margin SSOT for both CEX and on-chain perp venues.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.registry.cefi_margin_tiers import (
    CEFI_MARGIN_TIERS,
    VenueMarginSchedule,
    get_margin_schedule,
    get_margin_tier,
    maintenance_margin_for,
)

# Venues added in Phase 1E (Deribit + on-chain perp DEXes Hyperliquid + Aster).
NEW_PERP_VENUES: tuple[str, ...] = ("deribit", "hyperliquid", "aster")

# All venues now present in the registry (CEX + on-chain perp).
ALL_PERP_VENUES: tuple[str, ...] = (
    "binance",
    "bybit",
    "okx",
    "deribit",
    "hyperliquid",
    "aster",
)


@pytest.mark.parametrize("venue", NEW_PERP_VENUES)
@pytest.mark.parametrize("asset", ["BTC", "ETH"])
def test_new_venue_has_btc_and_eth_schedules(venue: str, asset: str) -> None:
    """Every Phase 1E venue MUST have BTC + ETH schedules registered."""
    schedule = get_margin_schedule(venue, asset)
    assert schedule is not None, f"missing schedule for ({venue}, {asset})"
    assert isinstance(schedule, VenueMarginSchedule)
    assert schedule.venue == venue
    assert schedule.asset == asset


@pytest.mark.parametrize("venue", ALL_PERP_VENUES)
@pytest.mark.parametrize("asset", ["BTC", "ETH"])
def test_every_venue_asset_has_at_least_three_tiers(venue: str, asset: str) -> None:
    """Every registered (venue, asset) MUST expose >= 3 tiers."""
    schedule = get_margin_schedule(venue, asset)
    assert schedule is not None
    assert len(schedule.tiers) >= 3, f"({venue}, {asset}) has only {len(schedule.tiers)} tiers; expected >= 3"


def test_deribit_btc_schedule_lookup_non_none() -> None:
    """``get_margin_schedule('DERIBIT', 'BTC')`` returns a populated schedule.

    Case-insensitive lookup is exercised by the uppercase venue arg — the
    helper normalises with ``venue.lower()``.
    """
    schedule = get_margin_schedule("DERIBIT", "BTC")
    assert schedule is not None
    assert schedule.venue == "deribit"
    assert schedule.asset == "BTC"
    assert len(schedule.tiers) >= 3


def test_hyperliquid_eth_tier_resolution_at_1_5m_notional() -> None:
    """A 1.5M USD position on Hyperliquid ETH-PERP MUST resolve to tier 2.

    Tier 1 cap is 1_000_000; tier 2 cap is 5_000_000. So 1_500_000 falls into
    tier 2 (first tier whose max_notional_usd accommodates the position).
    """
    tier = get_margin_tier("HYPERLIQUID", "ETH", Decimal("1500000"))
    assert tier is not None
    assert tier.tier == 2
    assert tier.max_notional_usd == Decimal("5000000")
    assert tier.initial_margin_rate == Decimal("0.05")
    assert tier.maintenance_margin_rate == Decimal("0.025")


def test_aster_btc_tier_resolution_small_notional() -> None:
    """50k USD on Aster BTC-PERP MUST resolve to tier 1 (cap 100_000)."""
    tier = get_margin_tier("aster", "BTC", Decimal("50000"))
    assert tier is not None
    assert tier.tier == 1
    assert tier.max_notional_usd == Decimal("100000")


def test_maintenance_margin_for_hyperliquid_eth_1_5m() -> None:
    """Convenience MMR lookup matches the tier 2 value (0.025)."""
    mmr = maintenance_margin_for("hyperliquid", "ETH", Decimal("1500000"))
    assert mmr == Decimal("0.025")


def test_registry_contains_all_twelve_entries() -> None:
    """CEFI_MARGIN_TIERS keys MUST cover all 6 venues x BTC/ETH."""
    expected_keys: set[tuple[str, str]] = {(venue, asset) for venue in ALL_PERP_VENUES for asset in ("BTC", "ETH")}
    assert set(CEFI_MARGIN_TIERS.keys()) == expected_keys


@pytest.mark.parametrize("venue", NEW_PERP_VENUES)
@pytest.mark.parametrize("asset", ["BTC", "ETH"])
def test_new_venue_tiers_monotonic_in_notional_and_margin(venue: str, asset: str) -> None:
    """Tiers MUST be monotonically increasing in max_notional + margin rates,
    and monotonically decreasing in max_leverage (sanity check on the schedule
    shape)."""
    schedule = get_margin_schedule(venue, asset)
    assert schedule is not None
    prev_notional = Decimal("0")
    prev_imr = Decimal("0")
    prev_mmr = Decimal("0")
    prev_lev = 1_000_000
    for tier in schedule.tiers:
        assert tier.max_notional_usd > prev_notional, (
            f"{venue}/{asset} tier {tier.tier} notional not strictly increasing"
        )
        assert tier.initial_margin_rate >= prev_imr
        assert tier.maintenance_margin_rate >= prev_mmr
        assert tier.max_leverage <= prev_lev
        prev_notional = tier.max_notional_usd
        prev_imr = tier.initial_margin_rate
        prev_mmr = tier.maintenance_margin_rate
        prev_lev = tier.max_leverage
