"""Tests for the archetype leg-spec registry (F22 + Phase 6A — full 57 coverage).

Covers:
  - EXHAUSTIVE registry completeness: all 57 ``StrategyArchetype`` values have a
    structure (real or not_registered) — no absent keys (Phase 6A).
  - The not_registered set is explicit (legs=() + cited reason) + the partition
    real ∪ not_registered == all 57.
  - The staked-basis conditional: requires_collateral_acceptance with its
    straight_basis fallback_variant round-trips.
  - Every LegConstraintKind round-trips through a constraint instance.
  - Every real leg cites a source_of_truth (no silently-invented venues).
  - Per-family role sanity (carry / arbitrage / stat-arb / vol / market-making).
  - Determinism of all_leg_structures() ordering.
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.archetype_leg_spec import (
    ARCHETYPE_LEG_STRUCTURES,
    ArchetypeLegRole,
    ArchetypeLegStructure,
    LegConstraint,
    LegConstraintKind,
    all_leg_structures,
    archetypes_without_leg_structures,
    leg_structure_for,
    registered_leg_structures,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    AtomicExecutionMode,
    StrategyArchetype,
)

# The archetypes that are GENUINELY underivable (no engine + thin/overlay doc) —
# explicit not_registered structures (Phase 6A).
_EXPECTED_NOT_REGISTERED: frozenset[StrategyArchetype] = frozenset(
    {
        StrategyArchetype.ARBITRAGE_MEV_SANDWICH,
        StrategyArchetype.PORTFOLIO_FACTOR_ALLOCATION,
        StrategyArchetype.PORTFOLIO_MULTI_STRATEGY,
        StrategyArchetype.PORTFOLIO_RISK_PARITY,
        StrategyArchetype.PORTFOLIO_TACTICAL_OVERLAY,
        StrategyArchetype.VOL_0DTE_PIN_RISK,
    }
)


def test_registry_enumerates_all_57_archetypes() -> None:
    """Phase 6A: every StrategyArchetype has a structure — no absent keys."""

    assert set(ARCHETYPE_LEG_STRUCTURES) == set(StrategyArchetype)
    assert len(ARCHETYPE_LEG_STRUCTURES) == len(StrategyArchetype)
    for archetype in StrategyArchetype:
        struct = leg_structure_for(archetype)
        assert struct is not None, f"{archetype} missing leg structure (registry must be exhaustive)"
        assert struct.archetype_id == archetype


def test_not_registered_set_is_explicit_and_cited() -> None:
    """The not_registered set is exactly the expected gaps, each with legs=() + reason."""

    gaps = set(archetypes_without_leg_structures())
    assert gaps == set(_EXPECTED_NOT_REGISTERED)
    for archetype in gaps:
        struct = ARCHETYPE_LEG_STRUCTURES[archetype]
        assert struct.not_registered is True
        assert struct.legs == ()
        assert struct.not_registered_reason.strip(), f"{archetype} not_registered without a reason"


def test_real_and_not_registered_partition_the_enum() -> None:
    """real ∪ not_registered == all 58, disjoint."""

    real = {s.archetype_id for s in registered_leg_structures()}
    gaps = set(archetypes_without_leg_structures())
    assert real.isdisjoint(gaps)
    assert real | gaps == set(StrategyArchetype)
    # 52 real, 6 not_registered (CARRY_FUNDING_DISPERSION added 2026-06-19).
    assert len(real) == 52
    assert len(gaps) == 6


def test_staked_basis_is_multi_leg_not_single_staking_cell() -> None:
    """The F22 fix: CARRY_STAKED_BASIS is 4 legs, not one 'staking' cell."""

    struct = leg_structure_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert struct is not None
    roles = struct.leg_roles
    assert ArchetypeLegRole.SPOT_LONG in roles
    assert ArchetypeLegRole.STAKE in roles
    assert ArchetypeLegRole.LEND in roles
    assert ArchetypeLegRole.HEDGE_SHORT in roles
    hedge = struct.leg("hedge")
    assert hedge is not None
    assert "hyperliquid" in hedge.eligible_venue_ids
    assert "binance" in hedge.eligible_venue_ids  # CeFi hedge venue
    assert "deribit" in hedge.eligible_venue_ids


def test_staked_basis_spot_leg_is_selectable_venue_axis() -> None:
    """Plan ``defi_collateral_sizing_and_wizard_full_parameterization_2026_06_17``
    Phase D: the spot leg (USDC→native SWAP) is a SELECTABLE venue axis (Binance
    vs DEX, liquidity-driven), no longer just {uniswap_v3, jupiter}.

    The SWAP trades USDC↔native (ETH/SOL), so the eligible set is the realistic
    liquid USDC↔native spot venues across both families: a CEX (binance) + the
    family DEXes (uniswap_v3/curve for ETH; jupiter/orca/raydium for SOL).
    """

    struct = leg_structure_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert struct is not None
    spot = struct.leg("spot")
    assert spot is not None
    venues = set(spot.eligible_venue_ids)
    # >2 venues now (was {uniswap_v3, jupiter})
    assert len(venues) > 2
    # Binance-spot is now selectable (the operator's headline ask).
    assert "binance" in venues
    # The original DEX venues survive.
    assert "uniswap_v3" in venues
    assert "jupiter" in venues
    # The added family DEXes.
    assert {"curve", "orca", "raydium"}.issubset(venues)


def test_staked_basis_collateral_conditional_with_fallback() -> None:
    """The requires_collateral_acceptance constraint + straight_basis fallback."""

    struct = leg_structure_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert struct is not None
    hedge = struct.leg("hedge")
    assert hedge is not None
    coll = [c for c in hedge.constraints if c.kind == LegConstraintKind.REQUIRES_COLLATERAL_ACCEPTANCE]
    assert len(coll) == 1
    assert coll[0].fallback_variant == "straight_basis"
    assert coll[0].params.get("venue_role") == "hedge_short"
    stake = struct.leg("stake")
    assert stake is not None
    assert stake.required is False


def test_every_constraint_kind_round_trips() -> None:
    """Each LegConstraintKind can be constructed + serialised + reloaded + is used."""

    for kind in LegConstraintKind:
        c = LegConstraint(
            kind=kind,
            params={"k": "v"},
            fallback_variant="straight_basis" if kind == LegConstraintKind.REQUIRES_COLLATERAL_ACCEPTANCE else None,
            description="round-trip",
        )
        reloaded = LegConstraint.model_validate(c.model_dump())
        assert reloaded == c
        assert reloaded.kind == kind

    seen: set[LegConstraintKind] = set()
    for struct in ARCHETYPE_LEG_STRUCTURES.values():
        for leg in struct.legs:
            for c in leg.constraints:
                seen.add(c.kind)
    assert seen == set(LegConstraintKind)


def test_every_real_leg_cites_a_source_of_truth() -> None:
    """No silently-invented venues: every real leg names its source + has ≥1 venue."""

    for struct in registered_leg_structures():
        assert struct.legs, f"{struct.archetype_id} registered but legless"
        for leg in struct.legs:
            assert leg.source_of_truth.strip(), f"{struct.archetype_id}/{leg.leg_id} has no source"
            assert len(leg.eligible_venue_ids) >= 1


def test_all_leg_structures_deterministic_order() -> None:
    """all_leg_structures() is sorted by archetype value (stable across runs)."""

    structs = all_leg_structures()
    assert len(structs) == len(StrategyArchetype)
    ids = [s.archetype_id.value for s in structs]
    assert ids == sorted(ids)


def test_execution_coupling_reuses_atomic_execution_mode() -> None:
    """Leg structures use the existing AtomicExecutionMode vocabulary."""

    recursive = leg_structure_for(StrategyArchetype.CARRY_RECURSIVE_STAKED)
    assert recursive is not None
    assert recursive.execution_coupling == AtomicExecutionMode.ATOMIC_ON_CHAIN
    staked = leg_structure_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert staked is not None
    assert staked.execution_coupling == AtomicExecutionMode.LEADER_HEDGE
    arb = leg_structure_for(StrategyArchetype.ARBITRAGE_PRICE_DISPERSION)
    assert arb is not None
    assert arb.execution_coupling == AtomicExecutionMode.ATOMIC


def test_required_legs_property() -> None:
    """required_legs excludes the droppable stake leg in the staked basis."""

    struct: ArchetypeLegStructure | None = leg_structure_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert struct is not None
    required_ids = {leg.leg_id for leg in struct.required_legs}
    assert "spot" in required_ids
    assert "hedge" in required_ids
    assert "stake" not in required_ids  # droppable → straight basis


def test_per_family_role_sanity() -> None:
    """Per-family role sanity: arbitrage pairs long+short, stat-arb pairs long+short,
    vol options carry option legs, market-making carries a quote leg, DeFi-LP carries lp."""

    # Stat-arb pairs: a long + a short leg.
    pairs = leg_structure_for(StrategyArchetype.STAT_ARB_PAIRS_FIXED)
    assert pairs is not None
    pair_roles = set(pairs.leg_roles)
    assert ArchetypeLegRole.SPOT_LONG in pair_roles
    assert ArchetypeLegRole.SPOT_SHORT in pair_roles

    # Cross-sectional: long basket + short basket.
    xs = leg_structure_for(StrategyArchetype.STAT_ARB_CROSS_SECTIONAL)
    assert xs is not None
    assert {ArchetypeLegRole.SPOT_LONG, ArchetypeLegRole.SPOT_SHORT}.issubset(set(xs.leg_roles))

    # MEV liquidation bundle: a flash-borrow (borrow) leg, atomic.
    bundle = leg_structure_for(StrategyArchetype.ARBITRAGE_MEV_LIQUIDATION_BUNDLE)
    assert bundle is not None
    assert ArchetypeLegRole.BORROW in bundle.leg_roles
    assert bundle.execution_coupling == AtomicExecutionMode.ATOMIC

    # DeFi LP: an lp_provide leg.
    lp = leg_structure_for(StrategyArchetype.DEFI_LP_CONCENTRATED)
    assert lp is not None
    assert ArchetypeLegRole.LP_PROVIDE in lp.leg_roles

    # Vol straddle: at least two option legs (call + put).
    straddle = leg_structure_for(StrategyArchetype.VOL_STRADDLE)
    assert straddle is not None
    from unified_api_contracts.internal.architecture_v2.archetype_capability import (
        ArchetypeInstrumentType,
    )

    option_legs = [leg for leg in straddle.legs if ArchetypeInstrumentType.OPTION in leg.instrument_types]
    assert len(option_legs) >= 2

    # Market-making continuous: a quote leg present.
    mm = leg_structure_for(StrategyArchetype.MARKET_MAKING_CONTINUOUS)
    assert mm is not None
    assert mm.leg("quote") is not None


def test_not_registered_invariant_rejects_legs() -> None:
    """A not_registered structure with legs raises (the validator)."""

    import pytest

    from unified_api_contracts.internal.architecture_v2.archetype_capability import (
        ArchetypeInstrumentType,
    )
    from unified_api_contracts.internal.architecture_v2.archetype_leg_spec import ArchetypeLegSpec
    from unified_api_contracts.internal.architecture_v2.enums import VenueCategoryV2

    with pytest.raises(ValueError, match="not_registered"):
        ArchetypeLegStructure(
            archetype_id=StrategyArchetype.VOL_STRADDLE,
            legs=(
                ArchetypeLegSpec(
                    leg_id="x",
                    role=ArchetypeLegRole.SPOT_LONG,
                    required=True,
                    instrument_types=(ArchetypeInstrumentType.OPTION,),
                    asset_groups=(VenueCategoryV2.CEFI,),
                    eligible_venue_ids=("deribit",),
                    source_of_truth="test",
                ),
            ),
            execution_coupling=AtomicExecutionMode.ATOMIC,
            not_registered=True,
            not_registered_reason="should-fail",
        )

    with pytest.raises(ValueError, match="≥1 leg"):
        ArchetypeLegStructure(
            archetype_id=StrategyArchetype.VOL_STRADDLE,
            legs=(),
            execution_coupling=AtomicExecutionMode.ATOMIC,
        )
