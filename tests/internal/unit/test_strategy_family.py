"""Closed-set sanity tests for the UAC strategy-family (risk-aggregation) registry.

Phase 2.G of ``risk_simulations_limits_alerting_2026_05_10``. Enforces:

1. ``StrategyFamilyId`` closed set is stable + non-duplicating.
2. ``STRATEGY_FAMILY_REGISTRY`` keys cover the full closed set.
3. Cutover-archetype membership: ``CARRY_STAKED_BASIS`` ∈
   ``LST_LEVERAGE_FAMILY``; ``ARBITRAGE_PRICE_DISPERSION`` ∈
   ``FUNDING_ARB_FAMILY``.
4. ``StrategyFamily`` Pydantic dataclass validates + is frozen.
5. ``family_for_archetype`` reverse-lookup returns expected family for
   cutover archetypes, ``None`` for unmapped.
6. Orthogonality: ``StrategyFamilyId`` (risk-aggregation axis) is distinct
   from the mechanism-axis ``StrategyFamily`` enum in
   ``unified_api_contracts.internal.architecture_v2.enums`` — they share no
   member names (codifies the two-orthogonal-axes invariant).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.enums import (
    StrategyArchetype,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    StrategyFamily as MechanismStrategyFamily,
)
from unified_api_contracts.risk import (
    STRATEGY_FAMILY_IDS,
    STRATEGY_FAMILY_REGISTRY,
    StrategyFamily,
    StrategyFamilyId,
    family_for_archetype,
)


# ---------------------------------------------------------------------------
# Closed-set sanity
# ---------------------------------------------------------------------------


def test_strategy_family_id_frozenset_matches_enum() -> None:
    assert frozenset(m.value for m in StrategyFamilyId) == STRATEGY_FAMILY_IDS


def test_strategy_family_id_no_duplicates() -> None:
    values = [m.value for m in StrategyFamilyId]
    assert len(values) == len(set(values))


def test_strategy_family_id_all_uppercase_snake() -> None:
    for fid in StrategyFamilyId:
        assert fid.value.isupper(), f"{fid.value} must be UPPER_SNAKE_CASE"
        assert " " not in fid.value
        assert fid.value.endswith("_FAMILY"), (
            f"{fid.value} must end with _FAMILY for grep-ability"
        )


# ---------------------------------------------------------------------------
# Registry coverage
# ---------------------------------------------------------------------------


def test_registry_keys_cover_closed_set() -> None:
    """Every StrategyFamilyId member MUST have a registry entry."""
    assert set(STRATEGY_FAMILY_REGISTRY.keys()) == set(StrategyFamilyId)


def test_registry_entries_are_strategy_family_models() -> None:
    for fid, fam in STRATEGY_FAMILY_REGISTRY.items():
        assert isinstance(fam, StrategyFamily)
        assert fam.family_id is fid


def test_registry_every_family_has_at_least_one_member() -> None:
    """Empty-member families are a smell — Phase 2.G seeds cutover scope."""
    for fid, fam in STRATEGY_FAMILY_REGISTRY.items():
        assert len(fam.members) >= 1, f"{fid} has no archetype members"


def test_registry_no_overlapping_membership() -> None:
    """An archetype belongs to AT MOST one risk-aggregation family.

    Two families claiming the same archetype would double-count risk.
    """
    seen: dict[StrategyArchetype, StrategyFamilyId] = {}
    for fid, fam in STRATEGY_FAMILY_REGISTRY.items():
        for archetype in fam.members:
            assert archetype not in seen, (
                f"{archetype} appears in {seen[archetype]} AND {fid}"
            )
            seen[archetype] = fid


# ---------------------------------------------------------------------------
# Cutover archetypes — explicit assertion per Phase 2.G done-definition
# ---------------------------------------------------------------------------


def test_carry_staked_basis_in_lst_leverage_family() -> None:
    lst = STRATEGY_FAMILY_REGISTRY[StrategyFamilyId.LST_LEVERAGE_FAMILY]
    assert StrategyArchetype.CARRY_STAKED_BASIS in lst.members


def test_arbitrage_price_dispersion_in_funding_arb_family() -> None:
    funding = STRATEGY_FAMILY_REGISTRY[StrategyFamilyId.FUNDING_ARB_FAMILY]
    assert StrategyArchetype.ARBITRAGE_PRICE_DISPERSION in funding.members


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------


def test_strategy_family_frozen() -> None:
    fam = STRATEGY_FAMILY_REGISTRY[StrategyFamilyId.LST_LEVERAGE_FAMILY]
    with pytest.raises(ValidationError):
        fam.description = "rewrite"  # type: ignore[misc]


def test_strategy_family_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        StrategyFamily.model_validate(
            {
                "family_id": StrategyFamilyId.LST_LEVERAGE_FAMILY.value,
                "members": [],
                "description": "test",
                "extra_field": "rejected",
            }
        )


def test_strategy_family_rejects_unknown_family_id() -> None:
    with pytest.raises(ValidationError):
        StrategyFamily.model_validate(
            {
                "family_id": "MEME_COIN_FAMILY",
                "members": [],
                "description": "bogus",
            }
        )


# ---------------------------------------------------------------------------
# family_for_archetype reverse-lookup
# ---------------------------------------------------------------------------


def test_family_for_archetype_cutover_lead() -> None:
    assert (
        family_for_archetype(StrategyArchetype.CARRY_STAKED_BASIS)
        is StrategyFamilyId.LST_LEVERAGE_FAMILY
    )


def test_family_for_archetype_cutover_pair() -> None:
    assert (
        family_for_archetype(StrategyArchetype.ARBITRAGE_PRICE_DISPERSION)
        is StrategyFamilyId.FUNDING_ARB_FAMILY
    )


def test_family_for_archetype_unmapped_returns_none() -> None:
    """MEV archetypes are NOT yet members of any risk-aggregation family
    (Phase 2.G seeds cutover scope only; MEV is post-cutover)."""
    assert family_for_archetype(StrategyArchetype.ARBITRAGE_MEV_SANDWICH) is None


# ---------------------------------------------------------------------------
# Orthogonality vs mechanism-axis StrategyFamily enum
# ---------------------------------------------------------------------------


def test_strategy_family_id_orthogonal_to_mechanism_axis() -> None:
    """StrategyFamilyId (risk-aggregation) and architecture_v2.StrategyFamily
    (mechanism) MUST not share member names.

    They're orthogonal axes per the strategy_family.py module docstring; a
    shared name would invite consumers to conflate them. Codifies the
    invariant at test-time so future contributors can't drift.
    """
    risk_axis = {m.value for m in StrategyFamilyId}
    mechanism_axis = {m.value for m in MechanismStrategyFamily}
    assert risk_axis.isdisjoint(mechanism_axis), (
        f"Name collision: {risk_axis & mechanism_axis}"
    )


def test_facade_exports_strategy_family_symbols() -> None:
    from unified_api_contracts import risk as risk_facade

    assert hasattr(risk_facade, "StrategyFamilyId")
    assert hasattr(risk_facade, "StrategyFamily")
    assert hasattr(risk_facade, "STRATEGY_FAMILY_REGISTRY")
    assert hasattr(risk_facade, "family_for_archetype")
