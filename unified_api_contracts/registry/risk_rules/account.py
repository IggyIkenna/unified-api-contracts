"""Per-account risk-rule registry — paper + live cutover accounts (Phase 2.C).

§ 7 SSOT reconciliation
=======================

This module seeds the per-account axis of the per-axis risk-rule registry
introduced by ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``
Phase 2.C. Each ``RiskRule`` here is evaluated at Layer 2 of the 4-layer
risk-gates model against per-account state (gross exposure, net exposure,
daily P&L, drawdown-from-peak).

Composes with the canonical SSOTs per the seam diagram:

* **Risk-gates Layer 2** — pre-flight evaluator picks the account's rule set
  by matching ``rule.applies_to == account_id``.
* **Kill-switch SSOT** — ``rule.kill_switch_scope()`` returns ``None`` for
  every entry here (PER_ACCOUNT is NOT directly kill-switch-applicable per the
  ``RiskRuleScope`` orthogonality table; account-level breaches feed portfolio
  aggregates instead).
* **Alerting** — ``rule.alerting_severity`` drives the per-consequence
  AlertCode dispatch.

Cutover accounts:

* ``paper_default`` — paper-trading sandbox; replays the unified pipeline with
  the matching-engine execution-fill source (per CLAUDE.md "Batch = Live"
  principle).
* ``live_cutover_2026_05_23`` — the live wallet on real venues for the
  2026-05-23 ≥7-day continuous run.

Each account carries ≥4 rules: gross exposure, net exposure, daily loss,
drawdown. Total ≥8 rules.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    MaxDailyLossTrigger,
    MaxDrawdownTrigger,
    MaxGrossExposureTrigger,
    MaxNetExposureTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)

# ---------------------------------------------------------------------------
# paper_default — sandbox account; tighter caps + MONITOR/SCALE_DOWN bias
# ---------------------------------------------------------------------------

_PAPER_DEFAULT_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_GROSS_EXPOSURE_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="paper_default",
        trigger=MaxGrossExposureTrigger(cap_usd=Decimal("5000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Paper account gross USD-notional exposure cap.",
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_NET_EXPOSURE_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="paper_default",
        trigger=MaxNetExposureTrigger(cap_usd=Decimal("2000000")),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Paper account net USD-notional directional exposure cap.",
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DAILY_LOSS_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="paper_default",
        trigger=MaxDailyLossTrigger(cap_usd=Decimal("100000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Paper account daily loss cap (USD).",
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DRAWDOWN_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="paper_default",
        trigger=MaxDrawdownTrigger(cap_bps=1500),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Paper account drawdown-from-peak ceiling (bps).",
    ),
)

# ---------------------------------------------------------------------------
# live_cutover_2026_05_23 — real wallet, tighter risk envelope
# ---------------------------------------------------------------------------

_LIVE_CUTOVER_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.MAX_GROSS_EXPOSURE_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="live_cutover_2026_05_23",
        trigger=MaxGrossExposureTrigger(cap_usd=Decimal("1000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description="Live cutover account gross USD-notional exposure ceiling.",
        triggers_kill_switch=False,
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_NET_EXPOSURE_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="live_cutover_2026_05_23",
        trigger=MaxNetExposureTrigger(cap_usd=Decimal("500000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description="Live cutover account net USD-notional directional ceiling.",
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DAILY_LOSS_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="live_cutover_2026_05_23",
        trigger=MaxDailyLossTrigger(cap_usd=Decimal("25000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description="Live cutover account daily loss cap (USD).",
    ),
    RiskRule(
        rule_id=RiskRuleId.MAX_DRAWDOWN_PER_ACCOUNT,
        scope=RiskRuleScope.PER_ACCOUNT,
        applies_to="live_cutover_2026_05_23",
        trigger=MaxDrawdownTrigger(cap_bps=500),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description="Live cutover account drawdown-from-peak ceiling (bps).",
    ),
)

# ---------------------------------------------------------------------------
# Public registry tuple — flattened across all accounts.
# ---------------------------------------------------------------------------

ACCOUNT_RULES: tuple[RiskRule, ...] = (
    *_PAPER_DEFAULT_RULES,
    *_LIVE_CUTOVER_RULES,
)
"""Per-account rules registry seed.

≥4 rules per account across 2 cutover accounts. All entries have
``scope=PER_ACCOUNT``; ``rule.kill_switch_scope()`` returns ``None`` per the
seam orthogonality declaration (PER_ACCOUNT is not directly kill-switch-
applicable; account-level breaches feed portfolio aggregates).
"""


__all__ = ["ACCOUNT_RULES"]
