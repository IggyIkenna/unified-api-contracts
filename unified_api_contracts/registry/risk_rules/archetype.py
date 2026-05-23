"""Per-archetype risk-rule registry seed — Phase 2.A of risk plan.

This module is the canonical SSOT for **per-archetype risk rules** evaluated at
Layer 2 of the 4-layer risk-gates model
(``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``). It seeds
the closed-set ``RiskRule`` registry for the 2026-05-23 cutover archetypes:

* ``CARRY_STAKED_BASIS`` — LST-yield carry archetype (Solana-side staked basis
  via jitoSOL / mSOL / bSOL; on-chain Pyth-fed pricing).
* ``ARBITRAGE_PRICE_DISPERSION`` — funding-rate dispersion arbitrage across
  the 6 perp venues (Bybit, Deribit, Binance, OKX, Hyperliquid, Aster).

§ 7 SSOT reconciliation
=======================

Per ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7 SSOT
reconciliation seam (Framing 1)" — picked by operator 2026-05-10. Each
``RiskRule`` here is evaluated at Layer 2 of the risk-gates model and composes
with the 5 canonical SSOTs:

* **Risk-gates 4 layers** — Layer 2 (risk-and-exposure-service pre-flight). UTL
  ``risk/rule_evaluator.py`` (Phase 3.A) dispatches on
  ``trigger.trigger_type``.
* **8-event lifecycle SSOT** — every fire emits ``RiskRuleFiredEvent`` (per
  the consequence-to-events mapping in
  ``CONSEQUENCE_EVENTS_EMITTED`` declared on the canonical SSOT
  ``unified_api_contracts.canonical.crosscutting.risk_rule``).
* **Kill-switch trigger set** — ``RiskRule.kill_switch_scope()`` returns
  ``KillSwitchScope.ARCHETYPE`` for every rule in this module (the rules are
  ``scope=PER_ARCHETYPE``); downstream kill-switch fires when consequence is
  ``BLOCK`` + ``triggers_kill_switch=True``.
* **Circuit-breaker action set** — aggregated BLOCK rate >= threshold across
  archetype instructions may transition the venue circuit-breaker per the
  ``RISK_TO_BREAKER_ESCALATION_MAP`` (declared separately in
  ``circuit_breaker.py``).
* **Strategy kill-switch behaviour 4-set** — Layer 3 strategy engine consumes
  the BLOCK + kill-switch-engaged combination + dispatches one of
  ``STOP_NEW_ONLY`` / ``FAST_UNWIND`` / ``SLOW_UNWIND`` / ``DELTA_HEDGE``
  per per-archetype config.

Consequence → severity mapping (per the seam diagram):

* ``BLOCK`` → ``AlertSeverity.HIGH`` or ``CRITICAL`` (paging tier).
* ``SCALE_DOWN`` → ``AlertSeverity.WARN`` (Telegram-only).
* ``MONITOR`` → ``AlertSeverity.INFO`` (dashboard only) or ``WARN`` (Telegram
  for elevated MONITOR rules).
* ``TEST_ONLY`` → ``AlertSeverity.INFO`` (log-only).

Coverage discipline (per Phase 2.A done-definition + plan Scope item 2):

* Each cutover archetype gets >=10 rules across the axes — position size,
  drawdown, leverage, concentration, correlation, slippage budget, funding
  cost ceiling (ARBITRAGE_PRICE_DISPERSION-specific), gas budget
  (CARRY_STAKED_BASIS-specific since it's on-chain), capital-at-risk
  ceiling, daily-loss cap, plus archetype-specific risk surfaces (oracle
  deviation, LST depeg, basis-inversion, cross-venue spread watch).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from ...canonical.crosscutting.alerting.codes import AlertSeverity
from ...canonical.crosscutting.risk_rule import (
    CapitalAtRiskCeilingTrigger,
    FundingCostCeilingTrigger,
    GasBudgetTrigger,
    MaxConcentrationTrigger,
    MaxCorrelationTrigger,
    MaxDailyLossTrigger,
    MaxDrawdownTrigger,
    MaxLeverageTrigger,
    MaxPositionSizeTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
    SlippageBudgetTrigger,
)

# ---------------------------------------------------------------------------
# CARRY_STAKED_BASIS — LST-yield carry archetype (Solana on-chain).
# ---------------------------------------------------------------------------

_CARRY_STAKED_BASIS_RULES: Final[tuple[RiskRule, ...]] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("2500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Hard cap on aggregate LST-basis position notional. Blocks new entry "
            "above 2.5M USD to bound oracle / depeg blast radius."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DRAWDOWN_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxDrawdownTrigger(cap_bps=800),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Archetype-level drawdown ceiling of 8% from peak NAV. BLOCK + kill-switch arms FAST_UNWIND on the LST leg."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_LEVERAGE_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxLeverageTrigger(cap_ratio=Decimal("3.5")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Effective leverage (gross-notional / equity) ceiling 3.5x. "
            "SCALE_DOWN sizes instructions down toward the cap rather than "
            "rejecting outright."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("40.0")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "No single LST instrument (jitoSOL / mSOL / bSOL) may exceed 40% of "
            "total archetype portfolio NAV. Bounds single-validator + "
            "single-LST-protocol exposure."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CORRELATION_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxCorrelationTrigger(
            cap_rho=Decimal("0.90"),
            window_days=30,
        ),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Cross-LST 30-day rolling-return correlation ceiling rho=0.90. "
            "When all three LSTs co-move tightly (depeg cascade), MONITOR "
            "raises a WARN alert for operator review."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.SLIPPAGE_BUDGET_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=SlippageBudgetTrigger(budget_bps=35),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Per-instruction slippage budget 35 bps over benchmark-arrival mid. "
            "If projected slippage exceeds, SCALE_DOWN reduces clip size to "
            "fit the budget."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.GAS_BUDGET_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=GasBudgetTrigger(budget_usd=Decimal("50")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Per-instruction Solana priority-fee + LST-protocol fee budget USD 50. "
            "BLOCK above ceiling — congestion-spike protection critical for "
            "on-chain archetype profitability."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.CAPITAL_AT_RISK_CEILING_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=CapitalAtRiskCeilingTrigger(ceiling_usd=Decimal("750000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "95%-VaR capital-at-risk ceiling 750k USD. Captures tail-risk "
            "blast radius from validator-slashing + LST-depeg + Solana-halt "
            "combined scenarios."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DAILY_LOSS_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxDailyLossTrigger(cap_usd=Decimal("100000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Per-day archetype loss cap 100k USD. BLOCK arms STOP_NEW_ONLY "
            "kill-switch until next UTC-day rollover or operator unkill."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("1000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Per-LST-instrument hard size cap 1M USD. SCALE_DOWN trims new "
            "entries above the cap; bounds per-LST-protocol concentration."
        ),
    ),
    # Archetype-specific risk surfaces — oracle deviation, LST depeg watch.
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_ASSET_GROUP,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("70.0")),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.INFO,
        description=(
            "DeFi asset-group concentration ceiling 70% of archetype NAV. "
            "MONITOR alert when LST-basis exposure swamps non-LST hedge legs."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CORRELATION_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxCorrelationTrigger(
            cap_rho=Decimal("0.95"),
            window_days=7,
        ),
        consequence=RiskRuleConsequence.TEST_ONLY,
        alerting_severity=AlertSeverity.INFO,
        description=(
            "7-day cross-LST correlation > 0.95 routes new entries to "
            "matching-engine TEST_ONLY mode — flags potential depeg-cascade "
            "regime before committing real capital."
        ),
    ),
)


# ---------------------------------------------------------------------------
# ARBITRAGE_PRICE_DISPERSION — funding-rate dispersion across perp venues.
# ---------------------------------------------------------------------------

_ARBITRAGE_PRICE_DISPERSION_RULES: Final[tuple[RiskRule, ...]] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("5000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Aggregate cross-venue arb-leg notional cap 5M USD. Bounds "
            "blast radius if any one of the 6 perp venues halts mid-trade."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DRAWDOWN_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxDrawdownTrigger(cap_bps=500),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Archetype drawdown ceiling 5% from peak NAV — tighter than carry "
            "because funding-arb relies on mean-reversion + extended drawdown "
            "signals regime break. BLOCK arms FAST_UNWIND."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_LEVERAGE_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxLeverageTrigger(cap_ratio=Decimal("5.0")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Effective leverage ceiling 5x — higher than carry-basis since "
            "delta-neutral funding-arb supports tighter margin. SCALE_DOWN "
            "instructions toward the cap."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("25.0")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Per-perp-instrument NAV concentration ceiling 25%. Bounds "
            "single-venue + single-symbol exposure across the 6 perp venues."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CORRELATION_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxCorrelationTrigger(
            cap_rho=Decimal("0.85"),
            window_days=14,
        ),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Cross-venue funding-rate 14-day correlation ceiling rho=0.85. "
            "Above ceiling = funding signals collapsing toward a common factor "
            "(less dispersion to harvest); MONITOR raises WARN."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.SLIPPAGE_BUDGET_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=SlippageBudgetTrigger(budget_bps=15),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Per-leg slippage budget 15 bps — tighter than carry since "
            "funding-arb edge is measured in basis-points. SCALE_DOWN clip "
            "size if projected slippage exceeds."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.FUNDING_COST_CEILING_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=FundingCostCeilingTrigger(ceiling_bps_apr=2500),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Aggregate funding-cost annualised ceiling 25% APR — short-leg + "
            "long-leg net carry must stay within this. BLOCK new entries when "
            "funding spikes invert the arb thesis."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.CAPITAL_AT_RISK_CEILING_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=CapitalAtRiskCeilingTrigger(ceiling_usd=Decimal("1500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "95%-VaR capital-at-risk ceiling 1.5M USD. Captures tail risk from "
            "simultaneous venue halt + funding-regime break + basis-inversion."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DAILY_LOSS_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxDailyLossTrigger(cap_usd=Decimal("150000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Per-day archetype loss cap 150k USD. Arms STOP_NEW_ONLY "
            "kill-switch until next UTC-day rollover or operator unkill."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_VENUE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("1500000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description=(
            "Per-venue notional cap 1.5M USD — caps single-venue blast radius "
            "across the 6 perp venues (Bybit / Deribit / Binance / OKX / "
            "Hyperliquid / Aster). SCALE_DOWN trims new entries above the cap."
        ),
    ),
    # Archetype-specific risk surfaces — cross-venue spread watch + basis inversion.
    RiskRule(
        rule_id=RiskRuleId.MAX_CORRELATION_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxCorrelationTrigger(
            cap_rho=Decimal("0.70"),
            window_days=3,
        ),
        consequence=RiskRuleConsequence.TEST_ONLY,
        alerting_severity=AlertSeverity.INFO,
        description=(
            "Short-window (3-day) cross-venue funding-rate correlation > 0.70 "
            "routes new entries to TEST_ONLY mode — flags rapid regime "
            "convergence before committing real capital."
        ),
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_ASSET_GROUP,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="ARBITRAGE_PRICE_DISPERSION",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("80.0")),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.INFO,
        description=(
            "CeFi asset-group concentration ceiling 80% — MONITOR fires when "
            "the 6 perp venues swamp other asset-group exposures, signaling "
            "single-asset-class regime."
        ),
    ),
)


ARCHETYPE_RULES: Final[tuple[RiskRule, ...]] = _CARRY_STAKED_BASIS_RULES + _ARBITRAGE_PRICE_DISPERSION_RULES
"""Per-archetype risk-rule registry — flat tuple of all rules across the 2
cutover archetypes.

Phase 2.A registry seed per
``plans/active/risk_simulations_limits_alerting_2026_05_10.md``. Aggregator at
``registry/risk_rules/__init__.py`` (Sub coordinator's scope) merges this with
the per-venue / per-account / per-client / per-asset_group / global / strategy-
family registries into the workspace ``RISK_RULE_REGISTRY``.

Each rule's ``scope`` is ``PER_ARCHETYPE`` and ``applies_to`` is one of:

* ``"CARRY_STAKED_BASIS"`` — 12 rules covering position size + drawdown +
  leverage + concentration + correlation + slippage + gas budget +
  capital-at-risk + daily loss + per-instrument size + asset-group
  concentration + short-window correlation regime watch.
* ``"ARBITRAGE_PRICE_DISPERSION"`` — 12 rules covering position size +
  drawdown + leverage + concentration + correlation + slippage + funding cost
  ceiling + capital-at-risk + daily loss + per-venue size + short-window
  correlation regime watch + asset-group concentration.
"""


# Per-archetype concentration multiplier (added 2026-05-12 per defi_recursive_borrow
# Phase 8 design). Higher multipliers penalise concentration in (chain x asset x
# protocol). Risk-and-exposure-service computes
# ``max_position_usd_per_archetype = base_cap_usd / multiplier`` — recursive variants
# get HALF the headroom of simple variants on the same (chain x asset x protocol)
# tuple. Wires into existing ``_HYPERLIQUID_RULES`` proposal-time veto.
ARCHETYPE_CONCENTRATION_MULTIPLIER: Final[dict[str, Decimal]] = {
    "CARRY_STAKED_BASIS": Decimal("1.0"),
    "CARRY_STAKED_BASIS_DATED": Decimal("1.0"),
    "CARRY_BASIS_PERP": Decimal("1.0"),
    "CARRY_BASIS_DATED": Decimal("1.0"),
    "CARRY_BASIS_DATED_INV": Decimal("1.0"),
    "ARBITRAGE_PRICE_DISPERSION": Decimal("1.0"),
    "ML_DIRECTIONAL_CONTINUOUS": Decimal("1.0"),
    # Recursive-borrow archetypes (Family 0/1/2) — 1.5x penalises concentration
    # because liquidation-cascade risk in same (chain x asset x protocol) compounds.
    "CARRY_RECURSIVE_STAKED": Decimal("1.5"),
    "CARRY_RECURSIVE_BORROW_LENDING_ONLY": Decimal("1.5"),
    "CARRY_BASIS_PERP_INV": Decimal("1.5"),
}


def get_archetype_concentration_multiplier(archetype: str) -> Decimal:
    """Return concentration-cap multiplier for archetype (default 1.0 if unknown)."""
    return ARCHETYPE_CONCENTRATION_MULTIPLIER.get(archetype, Decimal("1.0"))


__all__ = [
    "ARCHETYPE_CONCENTRATION_MULTIPLIER",
    "ARCHETYPE_RULES",
    "get_archetype_concentration_multiplier",
]
