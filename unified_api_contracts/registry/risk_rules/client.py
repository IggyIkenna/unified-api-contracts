"""Per-client risk-rule registry — cutover demo client (Phase 2.D).

§ 7 SSOT reconciliation
=======================

This module seeds the per-client axis of the per-axis risk-rule registry
introduced by ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``
Phase 2.D. Each ``RiskRule`` here is evaluated at Layer 2 against per-client
subscription state (per-archetype subscription size + total subscribed
exposure + drawdown).

Composes with the canonical SSOTs per the seam diagram:

* **Risk-gates Layer 2** — pre-flight evaluator picks the client's rule set
  by matching ``rule.applies_to == client_id``.
* **Kill-switch SSOT** — ``rule.kill_switch_scope()`` returns
  ``KillSwitchScope.CLIENT`` for every entry here (per the orthogonality
  declaration in ``RiskRuleScope`` docstring).
* **Alerting** — per-consequence AlertCode dispatch via
  ``CONSEQUENCE_ALERT_CODES``.

Cutover scope (Phase 2.D — "cutover demo client only"):

* ``cutover_demo_client_2026_05_23`` — single demo client subscribed to the
  two cutover archetypes (``carry_staked_basis`` + ``ARBITRAGE_PRICE_DISPERSION``)
  for the 2026-05-23 ≥7-day continuous run.

Each client carries ≥4 rules: per-archetype subscription size + drawdown +
capital-at-risk ceiling.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    CapitalAtRiskCeilingTrigger,
    MaxDrawdownTrigger,
    MaxGrossExposureTrigger,
    MaxPositionSizeTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)

# ---------------------------------------------------------------------------
# cutover_demo_client_2026_05_23 — demo client for the 2026-05-23 live run.
# ---------------------------------------------------------------------------

_CUTOVER_DEMO_CLIENT_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_CLIENT,
        applies_to="cutover_demo_client_2026_05_23",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("250000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description=(
            "Cutover demo client per-archetype subscription size cap "
            "(applies to carry_staked_basis + ARBITRAGE_PRICE_DISPERSION)."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_GROSS_EXPOSURE_PER_ACCOUNT,
        scope=RiskRuleScope.PER_CLIENT,
        applies_to="cutover_demo_client_2026_05_23",
        trigger=MaxGrossExposureTrigger(cap_usd=Decimal("500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Cutover demo client total cross-archetype subscription cap (USD-notional).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DRAWDOWN_PER_CLIENT,
        scope=RiskRuleScope.PER_CLIENT,
        applies_to="cutover_demo_client_2026_05_23",
        trigger=MaxDrawdownTrigger(cap_bps=1000),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description="Cutover demo client drawdown-from-peak ceiling (bps).",
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.CAPITAL_AT_RISK_CEILING_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_CLIENT,
        applies_to="cutover_demo_client_2026_05_23",
        trigger=CapitalAtRiskCeilingTrigger(ceiling_usd=Decimal("150000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Cutover demo client 95% VaR ceiling — total subscribed CaR (USD).",
    ),
)

# ---------------------------------------------------------------------------
# Public registry tuple — flattened across all clients.
# ---------------------------------------------------------------------------

CLIENT_RULES: tuple[RiskRule, ...] = _CUTOVER_DEMO_CLIENT_RULES
"""Per-client rules registry seed.

≥4 rules for the single cutover demo client. All entries have
``scope=PER_CLIENT``; ``rule.kill_switch_scope()`` returns
``KillSwitchScope.CLIENT`` per the seam orthogonality declaration.
"""


__all__ = ["CLIENT_RULES"]
