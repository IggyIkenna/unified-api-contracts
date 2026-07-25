"""May-23 cutover coverage audit for the archetype capability registry.

Verifies that every archetype on the 2026-05-23 live-DeFi cutover critical
path has the cell coverage + venue declarations + representative slot labels
needed for downstream consumers (strategy-service derivation, DART
manual-trade lane, deployment-UI catalogue filter).

Plan: ``plans/active/cross_cutting_may_23_deliverables_2026_05_08.md``
deliverable #1 (Strategy catalogue) — Tab 6.A3 audit + completeness work.
Issue doc: ``plans/active/issues/cross_cutting_strategy_catalogue_already_shipped_2026_05_08.md``
Operator decision: Option A (extend existing v2 SSOTs).

Master plan reference: ``plans/active/master_to_live_defi_2026_05_23.md`` §1
"Live DeFi rollout" — `carry_staked_basis` lead + `leveraged_funding_arb`
hedge legs across 6 perp venues (Bybit, Deribit, Binance, OKX, Hyperliquid,
Aster).
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    CoverageStatus,
    capability_for,
)
from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype
from unified_api_contracts.internal.domain.strategy_service.registry import (
    STRATEGY_REGISTRY,
)

# ---------------------------------------------------------------------------
# May-23 archetype scope
# ---------------------------------------------------------------------------
#
# Per ``master_to_live_defi_2026_05_23.md`` §1 + Risk Register row "6 perp
# venues live by May 23". Aster is upcoming (not yet onboarded as a workspace
# venue per CLAUDE.md "Master Plan" + DEX perp onboarding 2026-05-07 plan)
# so the test asserts the 5 venues currently shipped: Bybit / Deribit /
# Binance / OKX / Hyperliquid.
#
# Stretch archetypes (paper-trade smoke covers them, in-scope post-May-23)
# are also asserted for cell coverage but NOT for hedge-perp-venue
# completeness — those archetypes don't carry CeFi perp hedge legs.

MAY_23_LIVE_ARCHETYPES: tuple[StrategyArchetype, ...] = (
    StrategyArchetype.CARRY_STAKED_BASIS,
    StrategyArchetype.CARRY_BASIS_PERP,
    StrategyArchetype.CARRY_BASIS_DATED,
    StrategyArchetype.CARRY_RECURSIVE_STAKED,
    StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
)

MAY_23_STRETCH_ARCHETYPES: tuple[StrategyArchetype, ...] = (
    StrategyArchetype.YIELD_STAKING_SIMPLE,
    StrategyArchetype.YIELD_ROTATION_LENDING,
    StrategyArchetype.LIQUIDATION_CAPTURE,
    StrategyArchetype.ARBITRAGE_PRICE_DISPERSION,
)

# Hedge-perp universe per master plan §1 + Risk Register. Aster excluded —
# pending venue onboarding (see notes on CARRY_STAKED_BASIS cell).
MAY_23_HEDGE_PERP_VENUES: frozenset[str] = frozenset({"bybit", "deribit", "binance", "okx", "hyperliquid"})


# ---------------------------------------------------------------------------
# Cell coverage — every May-23 archetype has at least one non-BLOCKED cell
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("archetype", MAY_23_LIVE_ARCHETYPES + MAY_23_STRETCH_ARCHETYPES)
def test_archetype_is_in_capability_registry(archetype: StrategyArchetype) -> None:
    """Every May-23 archetype has a row in ARCHETYPE_CAPABILITY_REGISTRY."""
    capability = capability_for(archetype)
    assert capability is not None, (
        f"{archetype.value} has no row in ARCHETYPE_CAPABILITY_REGISTRY — "
        "cross_cutting deliverable #1 requires every May-23 archetype to be visible."
    )


@pytest.mark.parametrize("archetype", MAY_23_LIVE_ARCHETYPES + MAY_23_STRETCH_ARCHETYPES)
def test_archetype_has_at_least_one_non_blocked_cell(archetype: StrategyArchetype) -> None:
    """Every May-23 archetype has at least one SUPPORTED or PARTIAL cell.

    A row with all cells BLOCKED would mean the archetype has no live
    routing target and can't be paper-traded — banned for May-23 scope.
    """
    capability = capability_for(archetype)
    assert capability is not None
    non_blocked = [c for c in capability.cells if c.status != CoverageStatus.BLOCKED]
    assert len(non_blocked) >= 1, (
        f"{archetype.value} has zero non-BLOCKED cells — every May-23 archetype must have at least one routable cell."
    )


@pytest.mark.parametrize("archetype", MAY_23_LIVE_ARCHETYPES)
def test_live_archetype_has_at_least_one_supported_cell(
    archetype: StrategyArchetype,
) -> None:
    """May-23 LIVE archetypes (not stretch) have at least one SUPPORTED cell.

    PARTIAL is acceptable for stretch archetypes, but the lead carry +
    ML archetypes need at least one fully SUPPORTED cell to clear the
    cutover bar.
    """
    capability = capability_for(archetype)
    assert capability is not None
    supported = [c for c in capability.cells if c.status == CoverageStatus.SUPPORTED]
    assert len(supported) >= 1, (
        f"{archetype.value} has zero SUPPORTED cells — lead May-23 archetypes need at least one SUPPORTED cell."
    )


# ---------------------------------------------------------------------------
# Slot label coverage — STRATEGY_REGISTRY rows derive from
# representative_slot_labels via _build_entries_from_capabilities. Every
# archetype that has a non-BLOCKED cell should produce at least one row.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("archetype", MAY_23_LIVE_ARCHETYPES + MAY_23_STRETCH_ARCHETYPES)
def test_strategy_registry_has_row_for_archetype(archetype: StrategyArchetype) -> None:
    """STRATEGY_REGISTRY.get_by_archetype returns at least one row.

    A cell with status != BLOCKED but empty representative_slot_labels
    produces zero rows — that's an SSOT consistency hole the registry build
    silently swallows. This test catches it.
    """
    rows = STRATEGY_REGISTRY.get_by_archetype(archetype)
    assert len(rows) >= 1, (
        f"{archetype.value} has zero rows in STRATEGY_REGISTRY despite "
        "non-BLOCKED cells — check representative_slot_labels in the manifest."
    )


# ---------------------------------------------------------------------------
# Hedge-perp venue completeness — CARRY_STAKED_BASIS specifically declares
# the 5-venue hedge universe (Bybit / Deribit / Binance / OKX / Hyperliquid)
# per master plan §1.
# ---------------------------------------------------------------------------


def test_carry_staked_basis_declares_full_hedge_perp_universe() -> None:
    """CARRY_STAKED_BASIS cell venue_ids includes the 5 hedge perp venues.

    Aster is intentionally excluded — pending venue onboarding per CLAUDE.md
    "Master Plan" + the DEX perp onboarding 2026-05-07 follow-up plan. When
    Aster lands, extend the cell + this test.
    """
    capability = capability_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert capability is not None
    declared_venues: set[str] = set()
    for cell in capability.cells:
        if cell.status == CoverageStatus.BLOCKED:
            continue
        declared_venues.update(cell.venue_ids)
    missing = MAY_23_HEDGE_PERP_VENUES - declared_venues
    assert not missing, (
        f"CARRY_STAKED_BASIS missing hedge perp venues: {sorted(missing)}. "
        "Master plan §1 requires the 5-venue hedge universe to be declared."
    )


def test_carry_staked_basis_has_cefi_hedge_slot_labels() -> None:
    """CARRY_STAKED_BASIS has representative slot labels for CeFi-perp hedge legs.

    The strategy is 3-leg atomic (stake + lending + perp). The hyperliquid
    DeFi-perp variant is present from the original manifest seed (the
    Solana-native "drift" variant was removed 2026-07-16 and the "gmx_v2"
    variant was removed 2026-07-25 — operator rulings: all Solana perp DEXes
    dropped except Jupiter, not integrated; GMX has unreliable historical
    funding data, see
    unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md);
    this test asserts the CeFi-perp hedge variants (binance / bybit / okx /
    deribit) added 2026-05-08 are also present.
    """
    capability = capability_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert capability is not None
    all_slot_labels: list[str] = []
    for cell in capability.cells:
        if cell.status == CoverageStatus.BLOCKED:
            continue
        all_slot_labels.extend(cell.representative_slot_labels)
    # Lower-case substring search across all labels — cells encode hedge
    # venue inside the slot id (e.g., ``lido-aave-binance-eth-usdt-prod``).
    joined = "|".join(all_slot_labels).lower()
    cefi_hedge_venues = {"binance", "bybit", "deribit", "okx"}
    missing_in_labels = {v for v in cefi_hedge_venues if v not in joined}
    assert not missing_in_labels, (
        f"CARRY_STAKED_BASIS slot labels do not represent CeFi hedge venues: "
        f"{sorted(missing_in_labels)}. Slot labels: {all_slot_labels}"
    )


# ---------------------------------------------------------------------------
# Cross-venue funding rate dispersion (leveraged_funding_arb / multi-venue
# perp basis) — the second May-23 lead. ARBITRAGE_PRICE_DISPERSION CEFI/perp
# cell is the canonical home for cross-venue funding-rate dispersion per
# the codex strategy catalogue.
# ---------------------------------------------------------------------------


def test_leveraged_funding_arb_declares_cefi_perp_universe() -> None:
    """ARBITRAGE_PRICE_DISPERSION CeFi/perp cell covers the cross-venue perp universe.

    Master plan §1 (item 2 — ``leveraged_funding_arb``) needs at least 3
    venues for cross-venue spread trades; the test enforces the full 5-venue
    universe so the registry covers every pairwise spread combination.
    """
    capability = capability_for(StrategyArchetype.ARBITRAGE_PRICE_DISPERSION)
    assert capability is not None
    cefi_perp_cells = [
        c
        for c in capability.cells
        if c.asset_group.value == "CEFI" and c.instrument_type.value == "perp" and c.status != CoverageStatus.BLOCKED
    ]
    assert cefi_perp_cells, (
        "ARBITRAGE_PRICE_DISPERSION has no CEFI/perp cell — "
        "cross-venue funding-rate dispersion (leveraged_funding_arb) blocked."
    )
    declared_venues: set[str] = set()
    for cell in cefi_perp_cells:
        declared_venues.update(cell.venue_ids)
    missing = MAY_23_HEDGE_PERP_VENUES - declared_venues
    assert not missing, (
        f"ARBITRAGE_PRICE_DISPERSION CEFI/perp missing venues: {sorted(missing)}. "
        "Cross-venue funding dispersion needs the full 5-venue universe."
    )


# ---------------------------------------------------------------------------
# CARRY_BASIS_PERP — leveraged_funding_arb hedge leg variant (single-perp
# carry, distinct from cross-venue dispersion above).
# ---------------------------------------------------------------------------


def test_carry_basis_perp_declares_full_cefi_hedge_universe() -> None:
    """CARRY_BASIS_PERP CeFi/perp cell covers the 5 hedge perp venues."""
    capability = capability_for(StrategyArchetype.CARRY_BASIS_PERP)
    assert capability is not None
    cefi_perp_cells = [
        c
        for c in capability.cells
        if c.asset_group.value == "CEFI" and c.instrument_type.value == "perp" and c.status != CoverageStatus.BLOCKED
    ]
    assert cefi_perp_cells, "CARRY_BASIS_PERP has no CEFI/perp cell."
    declared_venues: set[str] = set()
    for cell in cefi_perp_cells:
        declared_venues.update(cell.venue_ids)
    missing = MAY_23_HEDGE_PERP_VENUES - declared_venues
    assert not missing, f"CARRY_BASIS_PERP CEFI/perp missing venues: {sorted(missing)}."


# ---------------------------------------------------------------------------
# ML_DIRECTIONAL_CONTINUOUS — CeFi ML on BTC / ETH spot + perp per master
# plan Group F + cefi_master.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("instrument", ["spot", "perp"])
def test_ml_directional_continuous_declares_cefi_ml_venues(instrument: str) -> None:
    """ML_DIRECTIONAL_CONTINUOUS CeFi/{spot,perp} cells cover Binance / OKX / Bybit.

    Per ``master_to_live_defi_2026_05_23.md`` Group F item 17 + cefi_master
    — CeFi ML training + inference targets these 3 venues.
    """
    capability = capability_for(StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS)
    assert capability is not None
    cells = [
        c
        for c in capability.cells
        if c.asset_group.value == "CEFI"
        and c.instrument_type.value == instrument
        and c.status != CoverageStatus.BLOCKED
    ]
    assert cells, f"ML_DIRECTIONAL_CONTINUOUS has no CEFI/{instrument} cell."
    declared_venues: set[str] = set()
    for cell in cells:
        declared_venues.update(cell.venue_ids)
    required = {"binance", "okx", "bybit"}
    missing = required - declared_venues
    assert not missing, f"ML_DIRECTIONAL_CONTINUOUS CEFI/{instrument} missing venues: {sorted(missing)}."


# ---------------------------------------------------------------------------
# CARRY_STAKED_BASIS LST coverage — Solana (jito/marinade) + Ethereum
# (lido/rocketpool) + Aave V3 lending leg.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "required_venue",
    ["lido", "rocketpool", "jito", "marinade", "aave_v3", "kamino"],
)
def test_carry_staked_basis_declares_lst_and_lending_legs(required_venue: str) -> None:
    """CARRY_STAKED_BASIS declares each LST + lending leg venue.

    Solana side: jito (jitoSOL), marinade (mSOL).
    Ethereum side: lido (stETH), rocketpool (rETH).
    Lending: aave_v3 (Ethereum / Arbitrum / Base), kamino (Solana).
    """
    capability = capability_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert capability is not None
    declared_venues: set[str] = set()
    for cell in capability.cells:
        if cell.status == CoverageStatus.BLOCKED:
            continue
        declared_venues.update(cell.venue_ids)
    assert required_venue in declared_venues, (
        f"CARRY_STAKED_BASIS missing required leg venue: {required_venue}. Declared: {sorted(declared_venues)}"
    )


# ---------------------------------------------------------------------------
# Manifest schema integrity — assert the registry loaded cleanly
# (catches manifest JSON syntax errors + Pydantic validation failures
# at module import time).
# ---------------------------------------------------------------------------


def test_capability_registry_loaded_with_22_archetypes() -> None:
    """Manifest declares 53 archetypes — adding to MAY_23 must not regress.

    Updated 2026-06-22: 22 → 23 with TSMOM_BTC_CTA (RULES_DIRECTIONAL CeFi BTC trend CTA).
    Updated 2026-07-21: 23 → 53 — Phase-9 capability-manifest regeneration adds the 18 new
    VOL_TRADING archetypes, 8 new MARKET_MAKING archetypes, and the 4-archetype PORTFOLIO
    family (enum-level since 2026-04, never had manifest cells until now).
    """
    assert len(ARCHETYPE_CAPABILITY_REGISTRY) == 53


def test_strategy_registry_non_empty() -> None:
    """STRATEGY_REGISTRY derived from capability matrix is non-empty."""
    assert len(STRATEGY_REGISTRY) > 0
