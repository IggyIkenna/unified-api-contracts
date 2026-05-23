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
    RiskRule,
    RiskRuleConsequence,
    RiskRuleFiredEvent,
    RiskRuleId,
    RiskRuleScope,
    RiskRuleTrigger,
    SlippageBudgetTrigger,
    risk_rule_fired_event,
)
from .canonical.crosscutting.strategy_family import (
    STRATEGY_FAMILY_IDS,
    STRATEGY_FAMILY_REGISTRY,
    StrategyFamily,
    StrategyFamilyId,
    family_for_archetype,
)

__all__ = [
    # Phase 2 — per-axis registry aggregator (shipped Round 2 sub-agents D/E/F)
    "ACCOUNT_RULES",
    "ALL_RULES",
    "ARCHETYPE_RULES",
    "ASSET_GROUP_RULES",
    "CLIENT_RULES",
    "CONSEQUENCE_ALERT_CODES",
    "CONSEQUENCE_EVENTS_EMITTED",
    "GLOBAL_RULES",
    "RISK_RULE_IDS",
    "STRATEGY_FAMILY_IDS",
    "STRATEGY_FAMILY_REGISTRY",
    "STRATEGY_FAMILY_RULES",
    "VENUE_RULES",
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
    "StrategyFamily",
    "StrategyFamilyId",
    "family_for_archetype",
    "get_max_position_size_usd_for_venue",
    "get_rules_for",
    "iter_applicable_rules",
    "risk_rule_fired_event",
]

# Re-export the per-axis registry aggregator at the risk facade.
from .registry.risk_rules import (
    ACCOUNT_RULES,
    ALL_RULES,
    ARCHETYPE_RULES,
    ASSET_GROUP_RULES,
    CLIENT_RULES,
    GLOBAL_RULES,
    STRATEGY_FAMILY_RULES,
    VENUE_RULES,
    get_max_position_size_usd_for_venue,
    get_rules_for,
    iter_applicable_rules,
)

# Per-strategy drawdown + response-policy schemas (added 2026-05-23).
# Implementation plan:
# ``plans/active/drawdown_liquidation_policy_and_strategy_risk_config_2026_05_23.md``.
from .canonical.crosscutting.risk import (
    DrawdownThresholdKind,
    ExpectedDrawdownModel,
    ExpectedDrawdownModelBasis,
    ResponsePolicy,
    RiskThresholds,
)
