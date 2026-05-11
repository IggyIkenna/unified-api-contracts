"""Per-strategy-family risk-rule registry — Phase 2.H of risk plan.

§ 7 SSOT reconciliation
=======================

Per ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § Phase 2.H
(family-aggregate rules + cross-family correlation surveillance). The registry
seeds rules at the **PER_STRATEGY_FAMILY** scope axis. Family identifiers are
the closed-set ``StrategyFamilyId`` enum from
``unified_api_contracts.canonical.crosscutting.strategy_family`` (the
risk-aggregation axis, distinct from ``StrategyFamily`` mechanism axis in
``architecture_v2.enums``).

The 6 required rule categories per cutover family (LST_LEVERAGE_FAMILY +
FUNDING_ARB_FAMILY get full 6-rule seeds; the other 5 families get a single
placeholder rule each so the registry has at-least-one coverage across all
7 ``StrategyFamilyId`` members):

* ``FAMILY_GROSS_EXPOSURE_CAP`` — sum-of-gross-positions cap per family.
* ``FAMILY_NET_EXPOSURE_CAP`` — sum-of-net-positions cap per family.
* ``FAMILY_DRAWDOWN_CAP`` — max-drawdown cap per family (worst-case across
  member archetypes).
* ``FAMILY_CAPITAL_AT_RISK_CEILING`` — sum-of-VaR ceiling per family.
* ``FAMILY_CONCENTRATION_PER_VENUE`` — single-venue concentration cap
  (modelled via ``MaxConcentrationTrigger``; the family vs venue axis is
  enforced by the rule evaluator's per-rule grouping logic).
* ``FAMILY_CORRELATION_WITH_OTHER_FAMILY`` — cross-family rolling-returns
  correlation cap (e.g. LST_LEVERAGE_FAMILY + FUNDING_ARB_FAMILY both
  share Pyth-Solana oracle-risk exposure).

Cross-references
----------------

* Plan: ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` §
  Phase 2.H + Phase 2.I.
* Family enum: ``canonical/crosscutting/strategy_family.py``
  (``StrategyFamilyId`` + ``STRATEGY_FAMILY_REGISTRY``).
* Rule contract: ``canonical/crosscutting/risk_rule.py`` (``RiskRule`` +
  ``RiskRuleId`` + ``RiskRuleScope``).
* Aggregator: UTL ``risk/family_aggregator.py`` (Phase 2.I — rolls
  per-archetype state into per-family state for evaluation).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from unified_api_contracts.canonical.crosscutting.alerting.codes import (
    AlertSeverity,
)
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    CapitalAtRiskCeilingTrigger,
    MaxConcentrationTrigger,
    MaxCorrelationTrigger,
    MaxDrawdownTrigger,
    MaxGrossExposureTrigger,
    MaxNetExposureTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)
from unified_api_contracts.canonical.crosscutting.strategy_family import (
    StrategyFamilyId,
)

# ---------------------------------------------------------------------------
# Cutover families — full 6-rule seeds.
# ---------------------------------------------------------------------------

_LST_LEVERAGE_FAMILY_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.FAMILY_GROSS_EXPOSURE_CAP,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.LST_LEVERAGE_FAMILY.value,
        trigger=MaxGrossExposureTrigger(cap_usd=Decimal("2000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "LST_LEVERAGE_FAMILY gross-exposure cap — aggregate USD-notional "
            "across all member archetypes (CARRY_STAKED_BASIS + "
            "CARRY_RECURSIVE_STAKED). BLOCK any new instruction that would "
            "push family gross above $2M (cutover scope)."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_NET_EXPOSURE_CAP,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.LST_LEVERAGE_FAMILY.value,
        trigger=MaxNetExposureTrigger(cap_usd=Decimal("1500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "LST_LEVERAGE_FAMILY net-exposure cap — aggregate signed "
            "USD-notional across LST carry archetypes. BLOCK at $1.5M net "
            "to keep family directional risk bounded."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_DRAWDOWN_CAP,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.LST_LEVERAGE_FAMILY.value,
        trigger=MaxDrawdownTrigger(cap_bps=500),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "LST_LEVERAGE_FAMILY drawdown cap — max-drawdown across family "
            "member archetypes ≤ 500bps from peak family-NAV. BLOCK new "
            "instructions if breached (rolling 24h window)."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_CAPITAL_AT_RISK_CEILING,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.LST_LEVERAGE_FAMILY.value,
        trigger=CapitalAtRiskCeilingTrigger(ceiling_usd=Decimal("250000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "LST_LEVERAGE_FAMILY capital-at-risk ceiling — sum of 95% VaR "
            "across member archetypes ≤ $250k. SCALE_DOWN (proportional "
            "resize) when approached."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_CONCENTRATION_PER_VENUE,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.LST_LEVERAGE_FAMILY.value,
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.40")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "LST_LEVERAGE_FAMILY per-venue concentration cap — no single "
            "venue may hold > 40% of family gross exposure. SCALE_DOWN "
            "instructions that would breach the cap on the hot venue."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_CORRELATION_WITH_OTHER_FAMILY,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.LST_LEVERAGE_FAMILY.value,
        trigger=MaxCorrelationTrigger(
            cap_rho=Decimal("0.80"), window_days=30
        ),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "LST_LEVERAGE_FAMILY cross-family correlation cap — rolling 30d "
            "Pearson rho with FUNDING_ARB_FAMILY (shared Pyth-Solana oracle "
            "exposure). MONITOR-mode rule; advisory only — operator "
            "decides whether to hedge or wait for decorrelation."
        ),
        triggers_kill_switch=False,
    ),
)


_FUNDING_ARB_FAMILY_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.FAMILY_GROSS_EXPOSURE_CAP,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.FUNDING_ARB_FAMILY.value,
        trigger=MaxGrossExposureTrigger(cap_usd=Decimal("5000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "FUNDING_ARB_FAMILY gross-exposure cap — aggregate USD-notional "
            "across ARBITRAGE_PRICE_DISPERSION + CARRY_BASIS_PERP. BLOCK "
            "above $5M (higher than LST because funding-arb is delta-hedged "
            "across legs)."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_NET_EXPOSURE_CAP,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.FUNDING_ARB_FAMILY.value,
        trigger=MaxNetExposureTrigger(cap_usd=Decimal("500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "FUNDING_ARB_FAMILY net-exposure cap — funding arb is supposed "
            "to be near delta-neutral; net exposure > $500k indicates leg "
            "drift. BLOCK + page (CRITICAL — surfaces hedge breakage)."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_DRAWDOWN_CAP,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.FUNDING_ARB_FAMILY.value,
        trigger=MaxDrawdownTrigger(cap_bps=300),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "FUNDING_ARB_FAMILY drawdown cap — tighter than LST (300bps) "
            "because funding-regime blowouts unwind faster than LST yield "
            "compression. BLOCK at the threshold."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_CAPITAL_AT_RISK_CEILING,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.FUNDING_ARB_FAMILY.value,
        trigger=CapitalAtRiskCeilingTrigger(ceiling_usd=Decimal("400000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "FUNDING_ARB_FAMILY capital-at-risk ceiling — sum of 95% VaR "
            "across member archetypes ≤ $400k. SCALE_DOWN approaching."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_CONCENTRATION_PER_VENUE,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.FUNDING_ARB_FAMILY.value,
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.35")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "FUNDING_ARB_FAMILY per-venue concentration cap — no single "
            "perp venue (Bybit / Deribit / Binance / OKX / Hyperliquid / "
            "Aster) > 35% of family gross. SCALE_DOWN on the hot venue."
        ),
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.FAMILY_CORRELATION_WITH_OTHER_FAMILY,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=StrategyFamilyId.FUNDING_ARB_FAMILY.value,
        trigger=MaxCorrelationTrigger(
            cap_rho=Decimal("0.80"), window_days=30
        ),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "FUNDING_ARB_FAMILY cross-family correlation cap — rolling 30d "
            "Pearson rho with LST_LEVERAGE_FAMILY (shared Pyth-Solana "
            "oracle exposure). MONITOR-mode; mirrors the LST-family rule."
        ),
        triggers_kill_switch=False,
    ),
)


# ---------------------------------------------------------------------------
# Forward-compat families — single placeholder rule each.
# ---------------------------------------------------------------------------


def _placeholder_gross_cap(
    family_id: StrategyFamilyId,
    cap_usd: Decimal,
    description: str,
) -> RiskRule:
    """Build a single-rule placeholder for a non-cutover family.

    The 5 non-cutover families (BASIS_CARRY / OPTIONS_VOL / SPORTS_MM /
    PREDICTION_MM / STAT_ARB) get ≥1 rule each so the registry has full
    coverage across all 7 ``StrategyFamilyId`` members. Full 6-rule seeds
    land when those families' archetypes graduate to live trading.
    """
    return RiskRule(
        rule_id=RiskRuleId.FAMILY_GROSS_EXPOSURE_CAP,
        scope=RiskRuleScope.PER_STRATEGY_FAMILY,
        applies_to=family_id.value,
        trigger=MaxGrossExposureTrigger(cap_usd=cap_usd),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=description,
        triggers_kill_switch=False,
    )


_BASIS_CARRY_FAMILY_RULES: tuple[RiskRule, ...] = (
    _placeholder_gross_cap(
        StrategyFamilyId.BASIS_CARRY_FAMILY,
        Decimal("3000000"),
        "BASIS_CARRY_FAMILY placeholder gross-exposure cap — full 6-rule "
        "seed pending dated-futures cutover. BLOCK at $3M gross.",
    ),
)


_OPTIONS_VOL_FAMILY_RULES: tuple[RiskRule, ...] = (
    _placeholder_gross_cap(
        StrategyFamilyId.OPTIONS_VOL_FAMILY,
        Decimal("2000000"),
        "OPTIONS_VOL_FAMILY placeholder gross-exposure cap — full 6-rule "
        "seed pending vol-archetype cutover. BLOCK at $2M gross.",
    ),
)


_SPORTS_MM_FAMILY_RULES: tuple[RiskRule, ...] = (
    _placeholder_gross_cap(
        StrategyFamilyId.SPORTS_MM_FAMILY,
        Decimal("500000"),
        "SPORTS_MM_FAMILY placeholder gross-exposure cap — full 6-rule seed "
        "pending sports MM cutover. BLOCK at $500k gross.",
    ),
)


_PREDICTION_MM_FAMILY_RULES: tuple[RiskRule, ...] = (
    _placeholder_gross_cap(
        StrategyFamilyId.PREDICTION_MM_FAMILY,
        Decimal("250000"),
        "PREDICTION_MM_FAMILY placeholder gross-exposure cap — full 6-rule "
        "seed pending Polymarket / Kalshi MM cutover. BLOCK at $250k.",
    ),
)


_STAT_ARB_FAMILY_RULES: tuple[RiskRule, ...] = (
    _placeholder_gross_cap(
        StrategyFamilyId.STAT_ARB_FAMILY,
        Decimal("1500000"),
        "STAT_ARB_FAMILY placeholder gross-exposure cap — full 6-rule seed "
        "pending stat-arb pairs cutover. BLOCK at $1.5M gross.",
    ),
)


# ---------------------------------------------------------------------------
# Aggregate registry — exported tuple consumed by Phase 3.B rule evaluator.
# ---------------------------------------------------------------------------


STRATEGY_FAMILY_RULES: Final[tuple[RiskRule, ...]] = (
    *_LST_LEVERAGE_FAMILY_RULES,
    *_FUNDING_ARB_FAMILY_RULES,
    *_BASIS_CARRY_FAMILY_RULES,
    *_OPTIONS_VOL_FAMILY_RULES,
    *_SPORTS_MM_FAMILY_RULES,
    *_PREDICTION_MM_FAMILY_RULES,
    *_STAT_ARB_FAMILY_RULES,
)
"""All per-strategy-family rules — Phase 2.H closed set.

§ 7 SSOT reconciliation
-----------------------

Aggregates the per-family rule tuples in a single ordered SSOT. Consumers
(``risk-and-exposure-service`` Phase 4.A; UTL ``risk/preflight.py`` Phase
3.B) iterate this tuple filtered by ``rule.applies_to`` matching the
family-id of the proposed instruction's owning archetype.

Coverage invariant: every member of ``StrategyFamilyId`` enum has at least
one rule. Cutover families (LST_LEVERAGE_FAMILY + FUNDING_ARB_FAMILY) carry
the full 6-rule seed; forward-compat families carry a single placeholder
rule each until their archetypes graduate to live trading.
"""


RULES_BY_FAMILY: Final[dict[StrategyFamilyId, tuple[RiskRule, ...]]] = {
    StrategyFamilyId.LST_LEVERAGE_FAMILY: _LST_LEVERAGE_FAMILY_RULES,
    StrategyFamilyId.FUNDING_ARB_FAMILY: _FUNDING_ARB_FAMILY_RULES,
    StrategyFamilyId.BASIS_CARRY_FAMILY: _BASIS_CARRY_FAMILY_RULES,
    StrategyFamilyId.OPTIONS_VOL_FAMILY: _OPTIONS_VOL_FAMILY_RULES,
    StrategyFamilyId.SPORTS_MM_FAMILY: _SPORTS_MM_FAMILY_RULES,
    StrategyFamilyId.PREDICTION_MM_FAMILY: _PREDICTION_MM_FAMILY_RULES,
    StrategyFamilyId.STAT_ARB_FAMILY: _STAT_ARB_FAMILY_RULES,
}
"""Per-family rule lookup table — keyed by ``StrategyFamilyId``.

§ 7 SSOT reconciliation
-----------------------

Mirror of ``STRATEGY_FAMILY_RULES`` keyed for O(1) family-id lookup. The
rule evaluator at Layer 2 of risk-gates (UTL ``risk/preflight.py``) uses
this dict to filter the rule set to "rules applicable to family F" without
scanning the full tuple. Closed-set invariant: ``set(RULES_BY_FAMILY) ==
set(StrategyFamilyId)`` — every family has an entry. Tests assert this.
"""


def get_rules_for_family(
    family_id: StrategyFamilyId,
) -> tuple[RiskRule, ...]:
    """Return all rules applicable to ``family_id``.

    § 7 SSOT reconciliation
    -----------------------

    Thin lookup helper — closed-set inputs (``StrategyFamilyId``) guarantee
    a non-empty result per the registry coverage invariant. Callers do NOT
    handle missing-family-id; the StrEnum makes that case
    type-check-impossible.
    """
    return RULES_BY_FAMILY[family_id]


__all__ = [
    "RULES_BY_FAMILY",
    "STRATEGY_FAMILY_RULES",
    "get_rules_for_family",
]
