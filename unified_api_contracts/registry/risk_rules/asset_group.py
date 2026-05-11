"""Per-asset_group risk-rule registry — DeFi + CeFi cutover-relevant (Phase 2.E).

§ 7 SSOT reconciliation
=======================

This module seeds the per-asset_group axis of the per-axis risk-rule registry
introduced by ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``
Phase 2.E. Each ``RiskRule`` here is evaluated at Layer 2 against per-asset-
group aggregates (asset-group-wide gross exposure, concentration, on-chain
gas budget for DeFi only).

Composes with the canonical SSOTs per the seam diagram:

* **Risk-gates Layer 2** — pre-flight evaluator picks the asset_group's rule
  set by matching ``rule.applies_to`` against the canonical asset_group
  vocabulary (``cefi`` / ``defi`` / ``tradfi`` / ``sports`` / ``prediction``;
  lowercase per CLAUDE.md "Asset-group vocabulary" rule).
* **Kill-switch SSOT** — ``rule.kill_switch_scope()`` returns ``None`` for
  every entry here (PER_ASSET_GROUP is NOT directly kill-switch-applicable
  per the ``RiskRuleScope`` orthogonality table; asset-group-wide breaches
  feed portfolio aggregates).
* **Alerting** — per-consequence AlertCode dispatch.

Cutover-relevant asset_groups (per 2026-05-23 live-DeFi master plan):

* ``defi`` — primary cutover surface (carry_staked_basis Solana LST yields
  + ARBITRAGE_PRICE_DISPERSION on Solana perps). Adds DeFi-only gas-budget
  rule.
* ``cefi`` — hedge legs across 6 perp venues (Bybit / Deribit / Binance / OKX
  / Hyperliquid / Aster).

Each asset_group carries ≥3 rules. Total ≥6 rules.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    FundingCostCeilingTrigger,
    GasBudgetTrigger,
    MaxConcentrationTrigger,
    MaxGrossExposureTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)

# ---------------------------------------------------------------------------
# defi — primary cutover surface; adds gas-budget rule
# ---------------------------------------------------------------------------

_DEFI_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_ASSET_GROUP,
        scope=RiskRuleScope.PER_ASSET_GROUP,
        applies_to="defi",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.60")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="DeFi asset-group concentration cap as % of total portfolio NAV.",
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_GROSS_EXPOSURE_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ASSET_GROUP,
        applies_to="defi",
        trigger=MaxGrossExposureTrigger(cap_usd=Decimal("3000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="DeFi asset-group total gross USD-notional exposure cap.",
    ),
    RiskRule(
        rule_id=RiskRuleId.GAS_BUDGET_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ASSET_GROUP,
        applies_to="defi",
        trigger=GasBudgetTrigger(budget_usd=Decimal("500")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="DeFi asset-group per-instruction gas budget ceiling (USD-equivalent).",
    ),
)

# ---------------------------------------------------------------------------
# cefi — hedge-leg surface; no gas budget (centralised venues)
# ---------------------------------------------------------------------------

_CEFI_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_ASSET_GROUP,
        scope=RiskRuleScope.PER_ASSET_GROUP,
        applies_to="cefi",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.50")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="CeFi asset-group concentration cap as % of total portfolio NAV.",
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_GROSS_EXPOSURE_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ASSET_GROUP,
        applies_to="cefi",
        trigger=MaxGrossExposureTrigger(cap_usd=Decimal("5000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="CeFi asset-group total gross USD-notional exposure cap.",
    ),
    RiskRule(
        rule_id=RiskRuleId.FUNDING_COST_CEILING_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ASSET_GROUP,
        applies_to="cefi",
        trigger=FundingCostCeilingTrigger(ceiling_bps_apr=2500),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="CeFi asset-group annualised funding-cost ceiling (bps APR).",
    ),
)

# ---------------------------------------------------------------------------
# Public registry tuple — flattened across all asset_groups.
# ---------------------------------------------------------------------------

ASSET_GROUP_RULES: tuple[RiskRule, ...] = (
    *_DEFI_RULES,
    *_CEFI_RULES,
)
"""Per-asset_group rules registry seed.

≥3 rules per asset_group across 2 cutover-relevant asset_groups (defi + cefi).
All entries have ``scope=PER_ASSET_GROUP``; ``rule.kill_switch_scope()``
returns ``None`` per the seam orthogonality declaration.
"""


__all__ = ["ASSET_GROUP_RULES"]
