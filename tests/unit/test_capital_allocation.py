"""Unit tests for the capital allocation SSOT.

Covers cross_cutting deliverable #3 — :class:`CapitalAllocation`,
:data:`CAPITAL_ALLOCATION_SEED`, the lookup helpers, and the fail-loud
validators.

Migrated 2026-05-08 from ``tests/unit/test_client_model.py`` per the Option A
recipe in
``unified-trading-pm/plans/active/issues/cross_cutting_strategy_catalogue_already_shipped_2026_05_08.md``.
The ``Client`` + ``VenueAccount`` test cases were deleted because the
parallel-SSOT classes they covered were reverted (the canonical client SSOTs
are :class:`ClientDefinition` + :class:`TradingAccount`).

Plan-of-record:
``unified-trading-pm/plans/active/cross_cutting_may_23_deliverables_2026_05_08.md``
deliverable #3.
"""

from __future__ import annotations

import dataclasses

import pytest

from unified_api_contracts.internal.architecture_v2.capital_allocation import (
    CAPITAL_ALLOCATION_SEED,
    AllocationViolationError,
    CapitalAllocation,
    get_capital_allocation,
    is_allocation_declared,
    is_within_allocation,
    validate_allocation_respect,
)
from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype

# ---------------------------------------------------------------------------
# CapitalAllocation — __post_init__ bounds validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_capital", [0.0, -0.01, -1_000_000.0])
def test_capital_allocation_rejects_non_positive_capital(bad_capital: float) -> None:
    with pytest.raises(ValueError, match="initial_capital_usd"):
        CapitalAllocation(
            client_id="x",
            archetype=StrategyArchetype.CARRY_STAKED_BASIS,
            venue="aave_v3_arbitrum",
            initial_capital_usd=bad_capital,
        )


@pytest.mark.parametrize("bad_pct", [0.0, -0.1, 1.01, 2.0])
def test_capital_allocation_rejects_out_of_bounds_position_pct(bad_pct: float) -> None:
    with pytest.raises(ValueError, match="max_position_pct"):
        CapitalAllocation(
            client_id="x",
            archetype=StrategyArchetype.CARRY_STAKED_BASIS,
            venue="aave_v3_arbitrum",
            initial_capital_usd=10_000.0,
            max_position_pct=bad_pct,
        )


@pytest.mark.parametrize("bad_pct", [0.0, -0.1, 1.01, 2.0])
def test_capital_allocation_rejects_out_of_bounds_drawdown_pct(bad_pct: float) -> None:
    with pytest.raises(ValueError, match="max_drawdown_pct"):
        CapitalAllocation(
            client_id="x",
            archetype=StrategyArchetype.CARRY_STAKED_BASIS,
            venue="aave_v3_arbitrum",
            initial_capital_usd=10_000.0,
            max_drawdown_pct=bad_pct,
        )


def test_capital_allocation_accepts_boundary_values() -> None:
    """Exactly 1.0 is allowed for both percentage caps; tiny positive epsilon
    is allowed for capital."""
    allocation = CapitalAllocation(
        client_id="x",
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        venue="aave_v3_arbitrum",
        initial_capital_usd=0.01,
        max_position_pct=1.0,
        max_drawdown_pct=1.0,
    )
    assert allocation.max_position_pct == 1.0
    assert allocation.max_drawdown_pct == 1.0


def test_capital_allocation_is_frozen_and_hashable() -> None:
    allocation = CapitalAllocation(
        client_id="x",
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        venue="aave_v3_arbitrum",
        initial_capital_usd=10_000.0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        allocation.initial_capital_usd = 0.0  # type: ignore[misc]
    # Hashable smoke test
    _ = {allocation}


def test_capital_allocation_archetype_is_strategy_archetype_enum() -> None:
    """archetype field must be a StrategyArchetype enum member, not a raw string.

    Tightening the placeholder ``ArchetypeRef = str`` to the canonical UAC
    enum was the central goal of the Option A migration. Verify it sticks.
    """
    allocation = CapitalAllocation(
        client_id="x",
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        venue="aave_v3_arbitrum",
        initial_capital_usd=10_000.0,
    )
    assert isinstance(allocation.archetype, StrategyArchetype)
    assert allocation.archetype == StrategyArchetype.CARRY_STAKED_BASIS


# ---------------------------------------------------------------------------
# get_capital_allocation + is_allocation_declared lookup behaviour
# ---------------------------------------------------------------------------


def test_get_capital_allocation_returns_seed_entry() -> None:
    allocation = get_capital_allocation("ikenna", StrategyArchetype.CARRY_STAKED_BASIS, "aave_v3_arbitrum")
    assert allocation.client_id == "ikenna"
    assert allocation.archetype == StrategyArchetype.CARRY_STAKED_BASIS
    assert allocation.venue == "aave_v3_arbitrum"
    assert allocation.initial_capital_usd > 0


def test_get_capital_allocation_raises_for_unknown_triple() -> None:
    with pytest.raises(KeyError, match="No CapitalAllocation declared"):
        get_capital_allocation("nonexistent", StrategyArchetype.CARRY_STAKED_BASIS, "aave_v3_arbitrum")


def test_is_allocation_declared_membership() -> None:
    assert is_allocation_declared("ikenna", StrategyArchetype.CARRY_STAKED_BASIS, "aave_v3_arbitrum") is True
    assert is_allocation_declared("nonexistent", StrategyArchetype.CARRY_STAKED_BASIS, "aave_v3_arbitrum") is False


# ---------------------------------------------------------------------------
# is_within_allocation + validate_allocation_respect
# ---------------------------------------------------------------------------


def _sample_allocation() -> CapitalAllocation:
    return CapitalAllocation(
        client_id="x",
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        venue="aave_v3_arbitrum",
        initial_capital_usd=100_000.0,
        max_position_pct=0.5,
        max_drawdown_pct=0.10,
    )


def test_is_within_allocation_happy_path() -> None:
    allocation = _sample_allocation()
    # Position 40k USD < 50k cap; drawdown 5% < 10% cap.
    assert is_within_allocation(allocation, position_value_usd=40_000.0, drawdown_pct=0.05) is True


def test_is_within_allocation_returns_false_when_position_exceeds_cap() -> None:
    allocation = _sample_allocation()
    # Position 50_001 > cap 50_000.
    assert is_within_allocation(allocation, position_value_usd=50_001.0, drawdown_pct=0.0) is False


def test_is_within_allocation_returns_false_when_drawdown_exceeds_cap() -> None:
    allocation = _sample_allocation()
    # Position fine but drawdown 10.1% > 10% cap.
    assert is_within_allocation(allocation, position_value_usd=0.0, drawdown_pct=0.101) is False


@pytest.mark.parametrize(
    ("position", "drawdown", "match_dim"),
    [
        (50_001.0, 0.0, "Position"),
        (0.0, 0.101, "Drawdown"),
    ],
)
def test_validate_allocation_respect_raises_on_violation(position: float, drawdown: float, match_dim: str) -> None:
    allocation = _sample_allocation()
    with pytest.raises(AllocationViolationError, match=match_dim):
        validate_allocation_respect(allocation, position, drawdown)


def test_validate_allocation_respect_silent_on_within_envelope() -> None:
    allocation = _sample_allocation()
    # Should not raise.
    validate_allocation_respect(allocation, proposed_position_value_usd=10_000.0, current_drawdown_pct=0.05)


# ---------------------------------------------------------------------------
# Seed-dictionary invariants — coverage guarantee for May-23 cutover
# ---------------------------------------------------------------------------


def test_capital_allocation_seed_non_empty() -> None:
    assert len(CAPITAL_ALLOCATION_SEED) > 0


def test_capital_allocation_seed_covers_carry_archetype_family() -> None:
    """At least one carry archetype must be seeded — this is the May-23 lead."""
    archetypes = {key[1] for key in CAPITAL_ALLOCATION_SEED}
    assert any("CARRY" in archetype.value for archetype in archetypes), f"No carry archetype in seed: {archetypes}"


def test_capital_allocation_seed_covers_ml_directional_archetype_family() -> None:
    """At least one ml_directional archetype seeded — CeFi-ML is in May-23 scope."""
    archetypes = {key[1] for key in CAPITAL_ALLOCATION_SEED}
    assert any("ML_DIRECTIONAL" in archetype.value for archetype in archetypes), (
        f"No ml_directional archetype in seed: {archetypes}"
    )


def test_capital_allocation_seed_keys_match_internal_fields() -> None:
    """Every seed key (client_id, archetype, venue) must match the
    CapitalAllocation's stored client_id / archetype / venue. Catches typos
    that would otherwise hide silent lookup mismatches."""
    for (key_client, key_archetype, key_venue), allocation in CAPITAL_ALLOCATION_SEED.items():
        assert allocation.client_id == key_client
        assert allocation.archetype == key_archetype
        assert allocation.venue == key_venue


def test_capital_allocation_seed_keys_use_strategy_archetype_enum() -> None:
    """Tightening of the seed-key archetype axis from raw strings to the
    canonical :class:`StrategyArchetype` enum is part of Option A. Verify."""
    for key in CAPITAL_ALLOCATION_SEED:
        _, key_archetype, _ = key
        assert isinstance(key_archetype, StrategyArchetype)
