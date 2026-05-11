"""Strategy-family taxonomy SSOT — RISK-aggregation family closed-set.

This module ships ``StrategyFamilyId`` — a NEW closed-enum at a NEW axis
distinct from the existing taxonomy in
``unified_api_contracts.internal.architecture_v2.enums.StrategyFamily`` (which
classifies archetypes by *mechanism* — ML_DIRECTIONAL / RULES_DIRECTIONAL /
CARRY_AND_YIELD / etc.).

§ 7 SSOT reconciliation — two orthogonal family axes
====================================================

``StrategyFamily`` (architecture_v2.enums) — **mechanism axis** (9 values).
    Used by the strategy-engine routing layer to dispatch on signal-generation
    semantics. Stable since 2026-04-21. SSOT for archetype → mechanism mapping.

``StrategyFamilyId`` (this module) — **risk-aggregation axis** (closed-set).
    Used by ``registry/risk_rules/strategy_family.py`` (Phase 2.H of
    ``risk_simulations_limits_alerting_2026_05_10``) to aggregate per-archetype
    risk into per-family caps where archetypes share an underlying risk
    cluster. Example: ``LST_LEVERAGE_FAMILY`` aggregates archetypes that
    share Solana-oracle-depeg risk (``CARRY_STAKED_BASIS`` +
    ``CARRY_RECURSIVE_STAKED``); ``FUNDING_ARB_FAMILY`` aggregates archetypes
    that share funding-rate-regime risk
    (``ARBITRAGE_PRICE_DISPERSION`` + ``CARRY_BASIS_PERP``).

The two axes don't overlap. An archetype belongs to exactly one
``StrategyFamily`` (architecture_v2) AND exactly one ``StrategyFamilyId``
(this module). Consumers of risk-aggregation use this module; consumers of
signal-generation routing use the architecture_v2 enum.

Reviewers reject any attempt to fold this module's classifications into the
architecture_v2 enum — they're orthogonal axes; merging them would conflate
mechanism with risk-cluster and break both.

Cross-references
----------------

* Plan: ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` §
  Phase 2.G + Phase 2.H + Phase 2.I.
* SSOT for archetypes: ``unified_api_contracts.internal.architecture_v2.enums``
  (``StrategyArchetype`` + ``ARCHETYPE_TO_FAMILY``).
* Companion: ``registry/risk_rules/strategy_family.py`` (Phase 2.H — per-family
  rules: gross-exposure cap, drawdown cap, capital-at-risk ceiling, etc.).
* Aggregator: UTL ``risk/family_aggregator.py`` (Phase 2.I — rolls up
  per-archetype state into per-family state).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype


class StrategyFamilyId(StrEnum):
    """Closed-set risk-aggregation family identifiers.

    § 7 SSOT reconciliation
    -----------------------

    Distinct from ``StrategyFamily`` (mechanism axis) — see module docstring.
    Members below seed the Phase 2.H registry; new families are added by
    appending here + seeding members in ``STRATEGY_FAMILY_REGISTRY`` +
    adding rules in ``registry/risk_rules/strategy_family.py``.

    Member rationale per cutover-archetype risk clustering:

    * ``LST_LEVERAGE_FAMILY`` — LST-margined leveraged carry. Shared risk:
      Solana on-chain oracle depeg (Pyth Hermes), LST tracking-error vs SOL,
      validator-set centralization. Cutover archetype: ``CARRY_STAKED_BASIS``.
    * ``FUNDING_ARB_FAMILY`` — Perpetual funding-rate arbitrage. Shared risk:
      cross-venue funding-regime correlation, perp-mark-vs-index basis
      blowout. Cutover archetype: ``ARBITRAGE_PRICE_DISPERSION``.
    * ``BASIS_CARRY_FAMILY`` — Dated-futures basis carry. Shared risk:
      roll-forward slippage, term-structure inversion.
    * ``OPTIONS_VOL_FAMILY`` — Implied-vol trading. Shared risk: vega
      blowout, vol-surface arbitrage decay.
    * ``SPORTS_MM_FAMILY`` — Sports market-making. Shared risk: late
      line-move adverse selection, sport-specific regime shifts.
    * ``PREDICTION_MM_FAMILY`` — Prediction market-making. Shared risk:
      resolution-source ambiguity, market-creator parameter changes.
    * ``STAT_ARB_FAMILY`` — Statistical-pairs arbitrage. Shared risk:
      cointegration breakdown, cross-asset volatility shock.
    """

    LST_LEVERAGE_FAMILY = "LST_LEVERAGE_FAMILY"
    FUNDING_ARB_FAMILY = "FUNDING_ARB_FAMILY"
    BASIS_CARRY_FAMILY = "BASIS_CARRY_FAMILY"
    OPTIONS_VOL_FAMILY = "OPTIONS_VOL_FAMILY"
    SPORTS_MM_FAMILY = "SPORTS_MM_FAMILY"
    PREDICTION_MM_FAMILY = "PREDICTION_MM_FAMILY"
    STAT_ARB_FAMILY = "STAT_ARB_FAMILY"


STRATEGY_FAMILY_IDS: Final[frozenset[str]] = frozenset(m.value for m in StrategyFamilyId)
"""String-membership view of :class:`StrategyFamilyId` for fast O(1) validation."""


class StrategyFamily(BaseModel):
    """Per-family contract — closed-set of archetypes the family aggregates.

    § 7 SSOT reconciliation
    -----------------------

    Named ``StrategyFamily`` to match operator-facing language in the
    deployment-UI Risk tab (Phase 6) but lives at the risk-aggregation axis
    via :class:`StrategyFamilyId`. NOT to be confused with the
    ``unified_api_contracts.internal.architecture_v2.enums.StrategyFamily``
    enum — that's the mechanism axis (9 values, taxonomic).

    Each registry entry is keyed by ``family_id``; ``members`` is a frozen
    set of ``StrategyArchetype`` enum members (the archetype enum lives at
    ``unified_api_contracts.internal.architecture_v2.enums.StrategyArchetype``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    family_id: StrategyFamilyId
    """Closed-set family identifier."""

    members: frozenset[StrategyArchetype] = Field(default_factory=frozenset)
    """Archetypes aggregated under this family. Per the cutover scope,
    minimum seed for ``LST_LEVERAGE_FAMILY`` includes ``CARRY_STAKED_BASIS``;
    ``FUNDING_ARB_FAMILY`` includes ``ARBITRAGE_PRICE_DISPERSION``. Phase 2.G
    extension may add additional members as the per-family registry seeds in
    Phase 2.H/I."""

    description: str = ""
    """Operator-facing family description rendered in the Risk tab Phase 6."""


# ---------------------------------------------------------------------------
# Seed registry — minimum cutover scope per the risk plan Phase 2.G.
# ---------------------------------------------------------------------------


STRATEGY_FAMILY_REGISTRY: Final[dict[StrategyFamilyId, StrategyFamily]] = {
    StrategyFamilyId.LST_LEVERAGE_FAMILY: StrategyFamily(
        family_id=StrategyFamilyId.LST_LEVERAGE_FAMILY,
        members=frozenset(
            {
                StrategyArchetype.CARRY_STAKED_BASIS,
                StrategyArchetype.CARRY_RECURSIVE_STAKED,
            }
        ),
        description=(
            "LST-margined leveraged carry. Shared risk cluster: Solana on-chain "
            "oracle depeg (Pyth Hermes), LST tracking-error vs SOL, "
            "validator-set centralization. Cutover archetype: CARRY_STAKED_BASIS."
        ),
    ),
    StrategyFamilyId.FUNDING_ARB_FAMILY: StrategyFamily(
        family_id=StrategyFamilyId.FUNDING_ARB_FAMILY,
        members=frozenset(
            {
                StrategyArchetype.ARBITRAGE_PRICE_DISPERSION,
                StrategyArchetype.CARRY_BASIS_PERP,
            }
        ),
        description=(
            "Perpetual funding-rate arbitrage. Shared risk cluster: cross-venue "
            "funding-regime correlation, perp-mark-vs-index basis blowout. "
            "Cutover archetype: ARBITRAGE_PRICE_DISPERSION."
        ),
    ),
    StrategyFamilyId.BASIS_CARRY_FAMILY: StrategyFamily(
        family_id=StrategyFamilyId.BASIS_CARRY_FAMILY,
        members=frozenset({StrategyArchetype.CARRY_BASIS_DATED}),
        description=(
            "Dated-futures basis carry. Shared risk cluster: roll-forward slippage, term-structure inversion."
        ),
    ),
    StrategyFamilyId.OPTIONS_VOL_FAMILY: StrategyFamily(
        family_id=StrategyFamilyId.OPTIONS_VOL_FAMILY,
        members=frozenset(
            {
                StrategyArchetype.VOL_TRADING_OPTIONS,
                StrategyArchetype.VOL_ARB_RV_IV,
                StrategyArchetype.VOL_SPREAD_STRUCTURES,
                StrategyArchetype.VOL_STRADDLE,
                StrategyArchetype.VOL_DISPERSION,
                StrategyArchetype.VOL_VARIANCE_SWAP,
            }
        ),
        description=(
            "Implied-vol trading. Shared risk cluster: vega blowout, vol-surface "
            "arbitrage decay. Seed members are the cutover-relevant vol "
            "archetypes; Phase 2.G may extend."
        ),
    ),
    StrategyFamilyId.SPORTS_MM_FAMILY: StrategyFamily(
        family_id=StrategyFamilyId.SPORTS_MM_FAMILY,
        members=frozenset({StrategyArchetype.MARKET_MAKING_EVENT_SETTLED}),
        description=(
            "Sports market-making. Shared risk cluster: late line-move adverse selection, sport-specific regime shifts."
        ),
    ),
    StrategyFamilyId.PREDICTION_MM_FAMILY: StrategyFamily(
        family_id=StrategyFamilyId.PREDICTION_MM_FAMILY,
        members=frozenset({StrategyArchetype.MARKET_MAKING_PREDICTION}),
        description=(
            "Prediction market-making. Shared risk cluster: resolution-source "
            "ambiguity, market-creator parameter changes."
        ),
    ),
    StrategyFamilyId.STAT_ARB_FAMILY: StrategyFamily(
        family_id=StrategyFamilyId.STAT_ARB_FAMILY,
        members=frozenset(
            {
                StrategyArchetype.STAT_ARB_PAIRS_FIXED,
                StrategyArchetype.STAT_ARB_CROSS_SECTIONAL,
            }
        ),
        description=(
            "Statistical-pairs arbitrage. Shared risk cluster: cointegration breakdown, cross-asset volatility shock."
        ),
    ),
}
"""Seed registry — minimum cutover scope.

§ 7 SSOT reconciliation
-----------------------

Closed-set keyed by ``StrategyFamilyId``. Phase 2.H consumers iterate over
``STRATEGY_FAMILY_REGISTRY[family_id].members`` to aggregate per-archetype
state into per-family state. The cutover-archetype membership is asserted
by ``tests/internal/unit/test_strategy_family.py``:

* ``LST_LEVERAGE_FAMILY`` contains ``CARRY_STAKED_BASIS`` (cutover lead).
* ``FUNDING_ARB_FAMILY`` contains ``ARBITRAGE_PRICE_DISPERSION``.

Additional families seeded for forward-compat with predictions / sports /
options / stat-arb workstreams that ship post-cutover but whose risk
aggregation hooks must already exist for parity with the master plan
readiness checklist Group F item 20.
"""


def family_for_archetype(archetype: StrategyArchetype) -> StrategyFamilyId | None:
    """Return the risk-aggregation family for an archetype, or ``None``.

    § 7 SSOT reconciliation
    -----------------------

    Reverse-lookup helper. Returns ``None`` if the archetype isn't yet a
    member of any registered family — by design (Phase 2.G seeds cutover
    scope; downstream may extend). Callers MUST handle the ``None`` case
    explicitly; do not assume every archetype maps to a family.
    """
    for family in STRATEGY_FAMILY_REGISTRY.values():
        if archetype in family.members:
            return family.family_id
    return None


__all__ = [
    "STRATEGY_FAMILY_IDS",
    "STRATEGY_FAMILY_REGISTRY",
    "StrategyFamily",
    "StrategyFamilyId",
    "family_for_archetype",
]
