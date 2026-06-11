"""Tests for the archetype leg-spec registry (F22 — structural multi-leg model).

Covers:
  - Registry completeness for the seeded set (the 11 multi-leg + representative
    single-leg archetypes named in the Phase 2.6 leg-spec todo).
  - The staked-basis conditional: the requires_collateral_acceptance constraint
    with its straight_basis fallback_variant round-trips.
  - Every LegConstraintKind round-trips through a constraint instance.
  - The honest-gap set (archetypes WITHOUT leg structures) is explicit + disjoint.
  - Every leg cites a source_of_truth (no silently-invented venues).
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
)
from unified_api_contracts.internal.architecture_v2.enums import (
    AtomicExecutionMode,
    StrategyArchetype,
)

# The seeded set required by the Phase 2.6 leg-spec todo.
_SEEDED: frozenset[StrategyArchetype] = frozenset(
    {
        StrategyArchetype.CARRY_STAKED_BASIS,
        StrategyArchetype.CARRY_STAKED_BASIS_DATED,
        StrategyArchetype.CARRY_BASIS_PERP,
        StrategyArchetype.CARRY_BASIS_PERP_INV,
        StrategyArchetype.CARRY_BASIS_DATED,
        StrategyArchetype.CARRY_BASIS_DATED_INV,
        StrategyArchetype.CARRY_RECURSIVE_STAKED,
        StrategyArchetype.CARRY_RECURSIVE_BORROW_LENDING_ONLY,
        StrategyArchetype.YIELD_STAKING_SIMPLE,
        StrategyArchetype.YIELD_ROTATION_LENDING,
        StrategyArchetype.ARBITRAGE_PRICE_DISPERSION,
    }
)


def test_registry_completeness_for_seeded_set() -> None:
    """Every archetype in the seeded set has a leg structure, and only those."""

    assert set(ARCHETYPE_LEG_STRUCTURES) == set(_SEEDED)
    for archetype in _SEEDED:
        struct = leg_structure_for(archetype)
        assert struct is not None, f"{archetype} missing leg structure"
        assert struct.archetype_id == archetype
        assert len(struct.legs) >= 1


def test_staked_basis_is_multi_leg_not_single_staking_cell() -> None:
    """The F22 fix: CARRY_STAKED_BASIS is 4 legs, not one 'staking' cell."""

    struct = leg_structure_for(StrategyArchetype.CARRY_STAKED_BASIS)
    assert struct is not None
    roles = struct.leg_roles
    assert ArchetypeLegRole.SPOT_LONG in roles
    assert ArchetypeLegRole.STAKE in roles
    assert ArchetypeLegRole.LEND in roles
    assert ArchetypeLegRole.HEDGE_SHORT in roles
    # The hedge leg spans CeFi + DeFi venues (cross-category) — the wizard
    # single-category assumption breaker.
    hedge = struct.leg("hedge")
    assert hedge is not None
    assert "hyperliquid" in hedge.eligible_venue_ids
    assert "binance" in hedge.eligible_venue_ids  # CeFi hedge venue
    assert "deribit" in hedge.eligible_venue_ids


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
    # The stake leg is droppable (non-required) — that IS the straight-basis fallback.
    stake = struct.leg("stake")
    assert stake is not None
    assert stake.required is False


def test_every_constraint_kind_round_trips() -> None:
    """Each LegConstraintKind can be constructed + serialised + reloaded."""

    for kind in LegConstraintKind:
        c = LegConstraint(
            kind=kind,
            params={"k": "v"},
            fallback_variant="straight_basis" if kind == LegConstraintKind.REQUIRES_COLLATERAL_ACCEPTANCE else None,
            description="round-trip",
        )
        dumped = c.model_dump()
        reloaded = LegConstraint.model_validate(dumped)
        assert reloaded == c
        assert reloaded.kind == kind

    # And every kind is actually exercised by the seeded registry.
    seen: set[LegConstraintKind] = set()
    for struct in ARCHETYPE_LEG_STRUCTURES.values():
        for leg in struct.legs:
            for c in leg.constraints:
                seen.add(c.kind)
    assert seen == set(LegConstraintKind)


def test_honest_gap_set_is_explicit_and_disjoint() -> None:
    """Archetypes WITHOUT leg structures are enumerable + disjoint from seeded."""

    gaps = archetypes_without_leg_structures()
    gap_set = set(gaps)
    assert gap_set.isdisjoint(_SEEDED)
    # Together they partition the whole archetype enum (exhaustive honesty).
    assert gap_set | set(_SEEDED) == set(StrategyArchetype)
    # Deterministically ordered.
    assert list(gaps) == sorted(gaps, key=lambda a: a.value)


def test_every_leg_cites_a_source_of_truth() -> None:
    """No silently-invented venues: every leg names where its truth comes from."""

    for struct in ARCHETYPE_LEG_STRUCTURES.values():
        for leg in struct.legs:
            assert leg.source_of_truth.strip(), f"{struct.archetype_id}/{leg.leg_id} has no source"
            assert len(leg.eligible_venue_ids) >= 1


def test_all_leg_structures_deterministic_order() -> None:
    """all_leg_structures() is sorted by archetype value (stable across runs)."""

    structs = all_leg_structures()
    assert len(structs) == len(_SEEDED)
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
