"""Global risk-rule registry — workspace-wide kill-condition rules (Phase 2.F).

§ 7 SSOT reconciliation
=======================

This module seeds the global axis of the per-axis risk-rule registry
introduced by ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``
Phase 2.F. Each ``RiskRule`` here is evaluated at Layer 2 against
workspace-wide aggregates (total portfolio drawdown, market-data staleness,
total-portfolio capital-at-risk).

Composes with the canonical SSOTs per the seam diagram:

* **Risk-gates Layer 2** — pre-flight evaluator always evaluates global rules
  for every order regardless of venue/account/client. ``applies_to`` is the
  sentinel ``"*"`` per the ``RiskRule.applies_to`` docstring rule.
* **Kill-switch SSOT** — ``rule.kill_switch_scope()`` returns
  ``KillSwitchScope.GLOBAL`` for every entry here (per the orthogonality
  declaration in ``RiskRuleScope`` docstring). Triggering any GLOBAL BLOCK
  rule with ``triggers_kill_switch=True`` halts the entire platform (human
  operator only restart).
* **Alerting** — per-consequence AlertCode dispatch via
  ``CONSEQUENCE_ALERT_CODES``; global rules typically fire at CRITICAL.

Module is named ``global_rules.py`` (not ``global.py``) to avoid the Python
keyword collision with ``global`` per Phase 2.F spawn instructions.

Note on rule_id coverage: the existing closed-set ``RiskRuleId`` enum has 2
``GLOBAL_``-prefixed members (``GLOBAL_PORTFOLIO_DRAWDOWN_HALT``,
``GLOBAL_DATA_STALENESS_HALT``). The third workspace-wide rule reuses
``CAPITAL_AT_RISK_CEILING_PER_ARCHETYPE`` with ``scope=GLOBAL`` for the
total-portfolio CaR ceiling — the rule-id name describes the rule semantic
while ``scope`` describes the applicability axis (they're orthogonal per the
``RiskRule`` class docstring). A workspace discovery is captured in
``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` follow-ups
for adding GLOBAL-named rule-ids (oracle outage, cross-cloud egress detected,
custody endpoint unreachable) once Phase 2.F+ scope opens.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    BinaryEventTrigger,
    CapitalAtRiskCeilingTrigger,
    MaxDrawdownTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)

# ---------------------------------------------------------------------------
# Global workspace-wide kill-condition rules — sentinel applies_to="*"
# ---------------------------------------------------------------------------

_GLOBAL_RULES: tuple[RiskRule, ...] = (
    RiskRule(
        rule_id=RiskRuleId.GLOBAL_PORTFOLIO_DRAWDOWN_HALT,
        scope=RiskRuleScope.GLOBAL,
        applies_to="*",
        trigger=MaxDrawdownTrigger(cap_bps=2000),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Workspace-wide total portfolio drawdown-from-peak halt (bps). "
            "Triggers GLOBAL kill-switch — human operator restart required."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.GLOBAL_DATA_STALENESS_HALT,
        scope=RiskRuleScope.GLOBAL,
        applies_to="*",
        trigger=BinaryEventTrigger(event_source="data_staleness"),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Workspace-wide market-data staleness halt — fires when MTDS / "
            "MDPS / features-* outputs lag freshness contract by > threshold. "
            "Triggers GLOBAL kill-switch — human operator restart required."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.CAPITAL_AT_RISK_CEILING_PER_ARCHETYPE,
        scope=RiskRuleScope.GLOBAL,
        applies_to="*",
        trigger=CapitalAtRiskCeilingTrigger(ceiling_usd=Decimal("2000000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Workspace-wide total 95% VaR ceiling (USD-notional). Fires when "
            "aggregated portfolio CaR exceeds the workspace cap. Triggers "
            "GLOBAL kill-switch — human operator restart required."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.ORACLE_OUTAGE_HALT,
        scope=RiskRuleScope.GLOBAL,
        applies_to="*",
        trigger=BinaryEventTrigger(event_source="price_oracle"),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Halt when the primary price oracle (Chainlink / Pyth) is unreachable "
            "or returning stale data beyond the freshness contract. No order is "
            "permitted without a live oracle price. Triggers GLOBAL kill-switch — "
            "human operator restart required."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.CROSS_CLOUD_EGRESS_HALT,
        scope=RiskRuleScope.GLOBAL,
        applies_to="*",
        trigger=BinaryEventTrigger(event_source="cross_cloud_egress"),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Halt when unexpected cross-cloud egress is detected — data leaving "
            "GCP to a non-approved destination. Prevents exfiltration under "
            "compromise. Corresponds to AlertCode.CROSS_CLOUD_EGRESS_DETECTED. "
            "Triggers GLOBAL kill-switch — human operator restart required."
        ),
        triggers_kill_switch=True,
    ),
    RiskRule(
        rule_id=RiskRuleId.CUSTODY_ENDPOINT_HALT,
        scope=RiskRuleScope.GLOBAL,
        applies_to="*",
        trigger=BinaryEventTrigger(event_source="custody_endpoint"),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description=(
            "Halt when the custody provider endpoint (Copper / CEFFU / "
            "CLOUD_KMS_ENCRYPTED) is unreachable — no withdrawal or settlement "
            "can be safely committed without custody confirmation. Triggers "
            "GLOBAL kill-switch — human operator restart required."
        ),
        triggers_kill_switch=True,
    ),
)

# ---------------------------------------------------------------------------
# Public registry tuple.
# ---------------------------------------------------------------------------

GLOBAL_RULES: tuple[RiskRule, ...] = _GLOBAL_RULES
"""Global workspace-wide rules registry seed.

≥3 workspace-wide kill-condition rules. All entries have ``scope=GLOBAL`` +
``applies_to="*"``; ``rule.kill_switch_scope()`` returns
``KillSwitchScope.GLOBAL`` per the seam orthogonality declaration. All entries
fire at ``AlertSeverity.CRITICAL`` with ``triggers_kill_switch=True``.
"""


__all__ = ["GLOBAL_RULES"]
