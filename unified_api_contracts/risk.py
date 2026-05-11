"""Risk facade — workspace-public surface for risk-rule taxonomy + strategy-family registry.

Consumers MUST import from this facade, not from the deep
``unified_api_contracts.canonical.crosscutting.risk_rule`` or
``unified_api_contracts.canonical.crosscutting.strategy_family`` paths (per UAC
import-surface rules).

Example::

    from unified_api_contracts.risk import (
        RiskRule,
        RiskRuleConsequence,
        RiskRuleId,
        RiskRuleScope,
        StrategyFamilyId,
        STRATEGY_FAMILY_REGISTRY,
    )

§ 7 SSOT reconciliation
-----------------------

The risk-rule taxonomy + strategy-family-id registry are NEW SSOTs introduced
by ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` Phase 1 +
Phase 2.G. Both compose with — but do NOT replace — the 5 canonical workspace
SSOTs (risk-gates layers, 8-event lifecycle, kill-switch trigger set,
circuit-breaker action set, strategy kill-switch behaviour set). See the
``RiskRuleConsequence`` docstring for the cross-product table reference.

Note: ``StrategyFamilyId`` (risk-aggregation axis) is distinct from
``StrategyFamily`` (mechanism axis) in
``unified_api_contracts.internal.architecture_v2.enums``. They're orthogonal
— see ``strategy_family.py`` module docstring for the seam.
"""

from __future__ import annotations

from .canonical.crosscutting.risk_rule import (
    CONSEQUENCE_ALERT_CODES,
    CONSEQUENCE_EVENTS_EMITTED,
    RISK_RULE_IDS,
    CapitalAtRiskCeilingTrigger,
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
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
    RiskRuleTrigger,
    SlippageBudgetTrigger,
)
from .canonical.crosscutting.strategy_family import (
    STRATEGY_FAMILY_IDS,
    STRATEGY_FAMILY_REGISTRY,
    StrategyFamily,
    StrategyFamilyId,
    family_for_archetype,
)

__all__ = [
    "CONSEQUENCE_ALERT_CODES",
    "CONSEQUENCE_EVENTS_EMITTED",
    "CapitalAtRiskCeilingTrigger",
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
    "RISK_RULE_IDS",
    "RiskRule",
    "RiskRuleConsequence",
    "RiskRuleId",
    "RiskRuleScope",
    "RiskRuleTrigger",
    "SlippageBudgetTrigger",
    "STRATEGY_FAMILY_IDS",
    "STRATEGY_FAMILY_REGISTRY",
    "StrategyFamily",
    "StrategyFamilyId",
    "family_for_archetype",
]
