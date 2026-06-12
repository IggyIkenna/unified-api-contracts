"""Tests for the COLLATERAL_REGISTRY MVP-universe backfill (2026-06-12).

Validates that every backfilled entry is well-formed, that every populated
numeric carries a non-empty ``source_of_truth`` / ``source_note`` citation, the
per-venue entry counts for the seeded set, and an HONEST enumeration of the
venues still missing a policy (staking venues + any not yet covered).

Plan: ``plans/active/capability_wizard_and_manifest_2026_06_11.md`` Phase 2
"Registry backfills".
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.internal.architecture_v2.collateral_registry import (
    BROKER_REGISTRY,
    COLLATERAL_REGISTRY,
    STAKING_VENUES_NO_COLLATERAL_POLICY,
    CollateralPolicy,
    VenueCollateralKind,
)

# MVP venue universe from archetype_leg_spec.py eligible venues.
_PERP_VENUES = {"hyperliquid", "gmx_v2", "drift", "binance", "bybit", "deribit", "okx"}
_LENDING_VENUES = {"aave_v3", "kamino"}
_STAKING_VENUES = {"lido", "rocketpool", "jito", "marinade"}


def _by_id(venue_id: str) -> CollateralPolicy:
    return next(p for p in COLLATERAL_REGISTRY if p.venue_id == venue_id)


# ---------------------------------------------------------------------------
# Coverage — per-venue entry-count assertions for the seeded set
# ---------------------------------------------------------------------------


def test_all_perp_and_lending_venues_registered() -> None:
    """Every MVP perp + lending venue has exactly one CollateralPolicy."""
    registered = {p.venue_id for p in COLLATERAL_REGISTRY}
    assert registered >= _PERP_VENUES, f"missing perp venues: {_PERP_VENUES - registered}"
    assert registered >= _LENDING_VENUES, f"missing lending venues: {_LENDING_VENUES - registered}"
    # No duplicate venue_id rows.
    venue_ids = [p.venue_id for p in COLLATERAL_REGISTRY]
    assert len(venue_ids) == len(set(venue_ids))


def test_staking_venues_have_no_collateral_policy() -> None:
    """Staking venues deliberately carry NO CollateralPolicy (documented why)."""
    registered = {p.venue_id for p in COLLATERAL_REGISTRY}
    assert _STAKING_VENUES.isdisjoint(registered)
    assert set(STAKING_VENUES_NO_COLLATERAL_POLICY) == _STAKING_VENUES


def test_perp_venues_classified_perp_kind() -> None:
    for vid in _PERP_VENUES:
        kind = _by_id(vid).venue_kind
        assert kind in {VenueCollateralKind.PERP_CEX, VenueCollateralKind.PERP_DEX}, vid


def test_lending_venues_classified_lending_kind() -> None:
    for vid in _LENDING_VENUES:
        assert _by_id(vid).venue_kind is VenueCollateralKind.LENDING, vid


def test_honest_enumeration_of_missing_venues() -> None:
    """The ONLY MVP venues without a policy are the 4 staking venues (by design)."""
    registered = {p.venue_id for p in COLLATERAL_REGISTRY}
    mvp = _PERP_VENUES | _LENDING_VENUES | _STAKING_VENUES
    missing = mvp - registered
    assert missing == _STAKING_VENUES, f"unexpected missing MVP venues: {missing - _STAKING_VENUES}"


# ---------------------------------------------------------------------------
# Provenance — every populated numeric carries a citation
# ---------------------------------------------------------------------------


def test_every_policy_has_source_of_truth() -> None:
    for p in COLLATERAL_REGISTRY:
        assert p.source_of_truth.strip(), f"{p.venue_id}: empty source_of_truth"


def test_every_asset_haircut_has_source_note() -> None:
    """Every AssetHaircut (accepted OR rejected) cites where it came from."""
    for p in COLLATERAL_REGISTRY:
        for ah in p.accepted_collateral:
            assert ah.source_note.strip(), f"{p.venue_id}/{ah.asset}: empty source_note"


def test_populated_numerics_are_in_range() -> None:
    for p in COLLATERAL_REGISTRY:
        if p.max_ltv is not None:
            assert Decimal("0") <= p.max_ltv <= Decimal("1"), p.venue_id
        if p.liquidation_ltv is not None:
            assert Decimal("0") <= p.liquidation_ltv <= Decimal("1"), p.venue_id
        if p.maintenance_margin is not None:
            assert Decimal("0") <= p.maintenance_margin <= Decimal("1"), p.venue_id
        for ah in p.accepted_collateral:
            assert Decimal("0") <= ah.haircut_pct <= Decimal("100"), f"{p.venue_id}/{ah.asset}"
            if ah.max_ltv is not None:
                assert Decimal("0") <= ah.max_ltv <= Decimal("1")
            if ah.liquidation_threshold is not None:
                assert Decimal("0") <= ah.liquidation_threshold <= Decimal("1")


def test_rejected_rows_carry_zero_haircut() -> None:
    """Documented negatives (accepted=False) carry haircut_pct=0 by convention."""
    for p in COLLATERAL_REGISTRY:
        for ah in p.accepted_collateral:
            if not ah.accepted:
                assert ah.haircut_pct == Decimal("0"), f"{p.venue_id}/{ah.asset}"


# ---------------------------------------------------------------------------
# Sourced-value spot checks (the load-bearing numbers)
# ---------------------------------------------------------------------------


def test_hyperliquid_is_usdc_only() -> None:
    """Hyperliquid accepts USDC only; rejects every LST (USDC-only by design)."""
    hl = _by_id("hyperliquid")
    accepted = set(hl.accepted_assets())
    assert accepted == {"USDC"}
    rejected = {ah.asset for ah in hl.accepted_collateral if not ah.accepted}
    assert {"stETH", "wstETH"} <= rejected


def test_deribit_steth_haircut_7_5() -> None:
    deribit = _by_id("deribit")
    steth = next(ah for ah in deribit.accepted_collateral if ah.asset == "stETH")
    assert steth.accepted
    assert steth.haircut_pct == Decimal("7.5")


def test_drift_accepts_solana_lsts() -> None:
    drift = _by_id("drift")
    accepted = set(drift.accepted_assets())
    assert {"mSOL", "JitoSOL"} <= accepted
    msol = next(ah for ah in drift.accepted_collateral if ah.asset == "mSOL")
    assert msol.haircut_pct == Decimal("10")


def test_aave_per_asset_ltv() -> None:
    """Aave wstETH/WETH carry per-asset LTV on the AssetHaircut (additive field)."""
    aave = _by_id("aave_v3")
    wsteth = next(ah for ah in aave.accepted_collateral if ah.asset == "wstETH")
    assert wsteth.max_ltv == Decimal("0.795")
    assert wsteth.liquidation_threshold == Decimal("0.83")
    weth = next(ah for ah in aave.accepted_collateral if ah.asset == "WETH")
    assert weth.max_ltv == Decimal("0.825")
    assert weth.liquidation_threshold == Decimal("0.86")


def test_kamino_partial_ltv_none_but_haircut_sourced() -> None:
    """Kamino is PARTIAL: LST haircut sourced, per-asset LTV honestly None."""
    kamino = _by_id("kamino")
    assert kamino.max_ltv is None
    assert kamino.liquidation_ltv is None
    msol = next(ah for ah in kamino.accepted_collateral if ah.asset == "mSOL")
    assert msol.haircut_pct == Decimal("15")
    assert msol.source_note.strip()


def test_brokers_remain_honest_gap() -> None:
    assert BROKER_REGISTRY == []
