"""Risk-rule taxonomy SSOT — closed-set rule-id, scope, consequence, trigger conditions.

This module is the workspace SSOT for **pre-flight risk-rule decisions** evaluated
at Layer 2 of the 4-layer risk-gates model (see
``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``). It introduces
``RiskRuleConsequence`` as a NEW pre-flight rule-decision abstraction — distinct
from + composing with the 5 canonical workspace risk SSOTs (risk-gates layers,
8-event lifecycle, kill-switch trigger set, circuit-breaker action set, strategy
kill-switch behaviour set).

§ 7 SSOT reconciliation
=======================

Per ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § "§ 7 SSOT
reconciliation seam (Framing 1)" — picked by operator 2026-05-10. The seam
diagram + cross-product table in that plan body is the canonical reconciliation
between ``RiskRuleConsequence`` and the 5 canonical SSOTs:

* **Risk-gates 4 layers** — ``codex/09-strategy/architecture-v2/cross-cutting/risk-gates.md``.
  ``RiskRuleConsequence`` evaluates at Layer 2 (strategy-service/risk pre-flight);
  ``ErrorAction`` taxonomy classifies Layer 4 (venue-side) errors.
  They don't overlap.
* **8-event lifecycle SSOT** — every fire emits ``RiskRuleFiredEvent`` plus
  the corresponding instruction-lifecycle event (BLOCK → ``INSTRUCTION_REJECTED_RISK``;
  others → ``INSTRUCTION_ACCEPTED_PREFLIGHT`` with annotations).
* **Kill-switch trigger set** — ``codex/04-architecture/kill-switch-circuit-breaker.md``.
  ``RiskRule.kill_switch_scope()`` maps ``RiskRuleScope`` →
  ``KillSwitchScope`` for the orthogonal axis (rule applicability vs kill-switch
  blast radius).
* **Circuit-breaker action set** — ``plans/active/alerting_service_live_rules_2026_05_07.md``.
  Aggregated BLOCK rate ≥ threshold triggers circuit-breaker state transitions
  (CLOSED → DEGRADED → OPEN); SCALE_DOWN / MONITOR / TEST_ONLY do not.
* **Strategy kill-switch behaviour 4-set** — ``STOP_NEW_ONLY`` / ``FAST_UNWIND``
  / ``SLOW_UNWIND`` / ``DELTA_HEDGE`` — engaged downstream when a BLOCK rule's
  ``triggers_kill_switch`` evaluates true.

Reviewers reject Phase 1+ contributors that bypass this seam (e.g. inlining
risk-rule logic in execution-service instead of routing through Layer 2).
"""

from ._base import RISK_RULE_IDS, RiskRule
from ._enums import RiskRuleConsequence, RiskRuleId, RiskRuleScope
from ._events import (
    CONSEQUENCE_ALERT_CODES,
    CONSEQUENCE_EVENTS_EMITTED,
    RiskRuleFiredEvent,
    risk_rule_fired_event,
)
from ._triggers import (
    BinaryEventTrigger,
    CapitalAtRiskCeilingTrigger,
    CounterpartyRatioCapTrigger,
    FundingCostCeilingTrigger,
    GasBudgetTrigger,
    MaxConcentrationTrigger,
    MaxCorrelationTrigger,
    MaxDailyLossTrigger,
    MaxDrawdownTrigger,
    MaxGrossExposureTrigger,
    MaxLeverageTrigger,
    MaxNetExposureTrigger,
    MaxOITrigger,
    MaxPositionSizeTrigger,
    RiskRuleTrigger,
    SlippageBudgetTrigger,
)

__all__ = [
    "CONSEQUENCE_ALERT_CODES",
    "CONSEQUENCE_EVENTS_EMITTED",
    "RISK_RULE_IDS",
    "BinaryEventTrigger",
    "CapitalAtRiskCeilingTrigger",
    "CounterpartyRatioCapTrigger",
    "FundingCostCeilingTrigger",
    "GasBudgetTrigger",
    "MaxConcentrationTrigger",
    "MaxCorrelationTrigger",
    "MaxDailyLossTrigger",
    "MaxDrawdownTrigger",
    "MaxGrossExposureTrigger",
    "MaxLeverageTrigger",
    "MaxNetExposureTrigger",
    "MaxOITrigger",
    "MaxPositionSizeTrigger",
    "RiskRule",
    "RiskRuleConsequence",
    "RiskRuleFiredEvent",
    "RiskRuleId",
    "RiskRuleScope",
    "RiskRuleTrigger",
    "SlippageBudgetTrigger",
    "risk_rule_fired_event",
]
