"""Tests for ``registry/risk_rules/strategy_family.py`` — Phase 2.H of risk plan.

§ 7 SSOT reconciliation
=======================

Per ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` § Phase
2.H done-definition + cross-product table:

* Cutover families (LST_LEVERAGE_FAMILY + FUNDING_ARB_FAMILY) carry the full
  6-rule seed covering ``FAMILY_GROSS_EXPOSURE_CAP`` /
  ``FAMILY_NET_EXPOSURE_CAP`` / ``FAMILY_DRAWDOWN_CAP`` /
  ``FAMILY_CAPITAL_AT_RISK_CEILING`` / ``FAMILY_CONCENTRATION_PER_VENUE`` /
  ``FAMILY_CORRELATION_WITH_OTHER_FAMILY``.
* Forward-compat families (BASIS_CARRY / OPTIONS_VOL / SPORTS_MM /
  PREDICTION_MM / STAT_ARB) carry ≥1 rule each so the registry has full
  ``StrategyFamilyId`` coverage.
* ``RULES_BY_FAMILY`` keys == ``StrategyFamilyId`` members (closed-set
  coverage invariant).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.canonical.crosscutting.risk_rule import (
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)
from unified_api_contracts.canonical.crosscutting.strategy_family import (
    StrategyFamilyId,
)
from unified_api_contracts.registry.risk_rules.strategy_family import (
    RULES_BY_FAMILY,
    STRATEGY_FAMILY_RULES,
    get_rules_for_family,
)

# ---------------------------------------------------------------------------
# Coverage invariants — every StrategyFamilyId has at least one rule.
# ---------------------------------------------------------------------------


def test_rules_by_family_covers_all_strategy_family_ids() -> None:
    """Closed-set coverage — every ``StrategyFamilyId`` is a key."""
    assert set(RULES_BY_FAMILY.keys()) == set(StrategyFamilyId)


def test_every_family_has_at_least_one_rule() -> None:
    """Each family entry has ≥1 ``RiskRule``."""
    for family_id, rules in RULES_BY_FAMILY.items():
        assert len(rules) >= 1, f"{family_id.value} has zero rules"


def test_strategy_family_rules_tuple_non_empty() -> None:
    """The flat ``STRATEGY_FAMILY_RULES`` tuple is non-empty."""
    assert len(STRATEGY_FAMILY_RULES) >= 7
    # 6 LST + 6 FUNDING_ARB + 5 placeholders = 17 minimum.


def test_strategy_family_rules_aggregates_match_dict() -> None:
    """Flat tuple length == sum of per-family tuple lengths."""
    aggregate_count = sum(len(rs) for rs in RULES_BY_FAMILY.values())
    assert len(STRATEGY_FAMILY_RULES) == aggregate_count


# ---------------------------------------------------------------------------
# Cutover family — full 6-rule seed.
# ---------------------------------------------------------------------------


def test_lst_leverage_family_has_six_rules() -> None:
    """LST_LEVERAGE_FAMILY carries the full 6-rule seed per Phase 2.H."""
    rules = RULES_BY_FAMILY[StrategyFamilyId.LST_LEVERAGE_FAMILY]
    assert len(rules) == 6


def test_funding_arb_family_has_six_rules() -> None:
    """FUNDING_ARB_FAMILY carries the full 6-rule seed per Phase 2.H."""
    rules = RULES_BY_FAMILY[StrategyFamilyId.FUNDING_ARB_FAMILY]
    assert len(rules) == 6


def test_lst_leverage_family_rule_ids_match_required_six() -> None:
    """LST family covers all 6 required rule-id categories."""
    rules = RULES_BY_FAMILY[StrategyFamilyId.LST_LEVERAGE_FAMILY]
    rule_ids = {r.rule_id for r in rules}
    required = {
        RiskRuleId.FAMILY_GROSS_EXPOSURE_CAP,
        RiskRuleId.FAMILY_NET_EXPOSURE_CAP,
        RiskRuleId.FAMILY_DRAWDOWN_CAP,
        RiskRuleId.FAMILY_CAPITAL_AT_RISK_CEILING,
        RiskRuleId.FAMILY_CONCENTRATION_PER_VENUE,
        RiskRuleId.FAMILY_CORRELATION_WITH_OTHER_FAMILY,
    }
    assert rule_ids == required


def test_funding_arb_family_rule_ids_match_required_six() -> None:
    """FUNDING_ARB family covers all 6 required rule-id categories."""
    rules = RULES_BY_FAMILY[StrategyFamilyId.FUNDING_ARB_FAMILY]
    rule_ids = {r.rule_id for r in rules}
    required = {
        RiskRuleId.FAMILY_GROSS_EXPOSURE_CAP,
        RiskRuleId.FAMILY_NET_EXPOSURE_CAP,
        RiskRuleId.FAMILY_DRAWDOWN_CAP,
        RiskRuleId.FAMILY_CAPITAL_AT_RISK_CEILING,
        RiskRuleId.FAMILY_CONCENTRATION_PER_VENUE,
        RiskRuleId.FAMILY_CORRELATION_WITH_OTHER_FAMILY,
    }
    assert rule_ids == required


# ---------------------------------------------------------------------------
# Scope invariants.
# ---------------------------------------------------------------------------


def test_all_rules_are_per_strategy_family_scope() -> None:
    """Every rule in the registry has scope=PER_STRATEGY_FAMILY."""
    for rule in STRATEGY_FAMILY_RULES:
        assert rule.scope is RiskRuleScope.PER_STRATEGY_FAMILY


def test_applies_to_matches_a_strategy_family_id() -> None:
    """Every rule's ``applies_to`` resolves to a ``StrategyFamilyId`` value."""
    family_values = {m.value for m in StrategyFamilyId}
    for rule in STRATEGY_FAMILY_RULES:
        assert rule.applies_to in family_values


# ---------------------------------------------------------------------------
# Kill-switch orthogonality — family-aggregate rules do NOT directly trigger
# kill-switch (portfolio-aggregate axis, not blast-radius).
# ---------------------------------------------------------------------------


def test_no_family_rule_triggers_kill_switch() -> None:
    """Family-aggregate rules are portfolio-aggregate, not blast-radius."""
    for rule in STRATEGY_FAMILY_RULES:
        assert rule.triggers_kill_switch is False


def test_kill_switch_scope_is_none_for_per_strategy_family() -> None:
    """``RiskRule.kill_switch_scope()`` returns None for family scope.

    Family-aggregate rules escalate via the circuit-breaker BLOCK-rate path,
    not the kill-switch's per-blast-radius halt mechanism.
    """
    for rule in STRATEGY_FAMILY_RULES:
        assert rule.kill_switch_scope() is None


# ---------------------------------------------------------------------------
# Lookup helper.
# ---------------------------------------------------------------------------


def test_get_rules_for_family_returns_expected() -> None:
    """``get_rules_for_family`` returns the same tuple as ``RULES_BY_FAMILY[]``."""
    for family_id in StrategyFamilyId:
        assert get_rules_for_family(family_id) == RULES_BY_FAMILY[family_id]


def test_get_rules_for_lst_family_returns_six() -> None:
    """Concrete spot-check on LST family."""
    rules = get_rules_for_family(StrategyFamilyId.LST_LEVERAGE_FAMILY)
    assert len(rules) == 6


# ---------------------------------------------------------------------------
# Consequence + severity sanity per seam diagram.
# ---------------------------------------------------------------------------


def test_block_rules_carry_high_or_critical_severity() -> None:
    """BLOCK consequences pair with HIGH / CRITICAL severity."""
    from unified_api_contracts.canonical.crosscutting.alerting.codes import (
        AlertSeverity,
    )

    for rule in STRATEGY_FAMILY_RULES:
        if rule.consequence is RiskRuleConsequence.BLOCK:
            assert rule.alerting_severity in {
                AlertSeverity.HIGH,
                AlertSeverity.CRITICAL,
            }


def test_monitor_rules_carry_info_or_warn_severity() -> None:
    """MONITOR consequences pair with INFO / WARN severity."""
    from unified_api_contracts.canonical.crosscutting.alerting.codes import (
        AlertSeverity,
    )

    for rule in STRATEGY_FAMILY_RULES:
        if rule.consequence is RiskRuleConsequence.MONITOR:
            assert rule.alerting_severity in {
                AlertSeverity.INFO,
                AlertSeverity.WARN,
            }


def test_scale_down_rules_carry_warn_severity() -> None:
    """SCALE_DOWN consequences pair with WARN severity."""
    from unified_api_contracts.canonical.crosscutting.alerting.codes import (
        AlertSeverity,
    )

    for rule in STRATEGY_FAMILY_RULES:
        if rule.consequence is RiskRuleConsequence.SCALE_DOWN:
            assert rule.alerting_severity is AlertSeverity.WARN


# ---------------------------------------------------------------------------
# Cross-family correlation rule pairing (LST + FUNDING_ARB share Pyth Solana).
# ---------------------------------------------------------------------------


def test_lst_family_has_correlation_with_other_family_rule() -> None:
    """LST_LEVERAGE_FAMILY carries a cross-family correlation rule.

    Per the plan body: LST_LEVERAGE_FAMILY + FUNDING_ARB_FAMILY both share
    Pyth-Solana oracle-risk exposure; their cross-family correlation is
    surveilled.
    """
    rules = RULES_BY_FAMILY[StrategyFamilyId.LST_LEVERAGE_FAMILY]
    correlation_rules = [r for r in rules if r.rule_id is RiskRuleId.FAMILY_CORRELATION_WITH_OTHER_FAMILY]
    assert len(correlation_rules) == 1
    rule = correlation_rules[0]
    assert rule.consequence is RiskRuleConsequence.MONITOR


def test_funding_arb_family_has_correlation_with_other_family_rule() -> None:
    """FUNDING_ARB_FAMILY mirrors the LST correlation surveillance rule."""
    rules = RULES_BY_FAMILY[StrategyFamilyId.FUNDING_ARB_FAMILY]
    correlation_rules = [r for r in rules if r.rule_id is RiskRuleId.FAMILY_CORRELATION_WITH_OTHER_FAMILY]
    assert len(correlation_rules) == 1


# ---------------------------------------------------------------------------
# Immutability + Pydantic frozen contract.
# ---------------------------------------------------------------------------


def test_rule_models_are_frozen() -> None:
    """``RiskRule`` instances are immutable per Pydantic frozen ConfigDict."""
    rule = STRATEGY_FAMILY_RULES[0]
    with pytest.raises(Exception):
        rule.applies_to = "tampered"  # pyright: ignore[reportAttributeAccessIssue]


# ---------------------------------------------------------------------------
# Forward-compat families — placeholder rule sanity.
# ---------------------------------------------------------------------------


def test_basis_carry_family_has_at_least_one_rule() -> None:
    rules = RULES_BY_FAMILY[StrategyFamilyId.BASIS_CARRY_FAMILY]
    assert len(rules) >= 1
    assert rules[0].applies_to == StrategyFamilyId.BASIS_CARRY_FAMILY.value


def test_options_vol_family_has_at_least_one_rule() -> None:
    rules = RULES_BY_FAMILY[StrategyFamilyId.OPTIONS_VOL_FAMILY]
    assert len(rules) >= 1


def test_sports_mm_family_has_at_least_one_rule() -> None:
    rules = RULES_BY_FAMILY[StrategyFamilyId.SPORTS_MM_FAMILY]
    assert len(rules) >= 1


def test_prediction_mm_family_has_at_least_one_rule() -> None:
    rules = RULES_BY_FAMILY[StrategyFamilyId.PREDICTION_MM_FAMILY]
    assert len(rules) >= 1


def test_stat_arb_family_has_at_least_one_rule() -> None:
    rules = RULES_BY_FAMILY[StrategyFamilyId.STAT_ARB_FAMILY]
    assert len(rules) >= 1


# ---------------------------------------------------------------------------
# Cap-value sanity (no negative caps).
# ---------------------------------------------------------------------------


def test_gross_exposure_caps_are_positive() -> None:
    """All gross-exposure caps are positive Decimal values."""
    from unified_api_contracts.canonical.crosscutting.risk_rule import (
        MaxGrossExposureTrigger,
    )

    for rule in STRATEGY_FAMILY_RULES:
        if isinstance(rule.trigger, MaxGrossExposureTrigger):
            assert rule.trigger.cap_usd > Decimal("0")


def test_drawdown_caps_are_positive_bps() -> None:
    """All drawdown caps are positive bps values."""
    from unified_api_contracts.canonical.crosscutting.risk_rule import (
        MaxDrawdownTrigger,
    )

    for rule in STRATEGY_FAMILY_RULES:
        if isinstance(rule.trigger, MaxDrawdownTrigger):
            assert rule.trigger.cap_bps > 0


def test_correlation_caps_are_in_unit_interval() -> None:
    """Pearson rho caps are in (0, 1]."""
    from unified_api_contracts.canonical.crosscutting.risk_rule import (
        MaxCorrelationTrigger,
    )

    for rule in STRATEGY_FAMILY_RULES:
        if isinstance(rule.trigger, MaxCorrelationTrigger):
            assert Decimal("0") < rule.trigger.cap_rho <= Decimal("1")
            assert rule.trigger.window_days > 0


# ---------------------------------------------------------------------------
# Distinct cap values per family — sanity that we didn't copy-paste.
# ---------------------------------------------------------------------------


def test_lst_and_funding_arb_gross_caps_differ() -> None:
    """LST gross cap differs from FUNDING_ARB gross cap (different risk profiles)."""
    from unified_api_contracts.canonical.crosscutting.risk_rule import (
        MaxGrossExposureTrigger,
    )

    def _gross_cap(family_id: StrategyFamilyId) -> Decimal:
        rules = RULES_BY_FAMILY[family_id]
        gross_rules = [r for r in rules if r.rule_id is RiskRuleId.FAMILY_GROSS_EXPOSURE_CAP]
        assert len(gross_rules) == 1
        trigger = gross_rules[0].trigger
        assert isinstance(trigger, MaxGrossExposureTrigger)
        return trigger.cap_usd

    lst_cap = _gross_cap(StrategyFamilyId.LST_LEVERAGE_FAMILY)
    fa_cap = _gross_cap(StrategyFamilyId.FUNDING_ARB_FAMILY)
    assert lst_cap != fa_cap


def test_no_duplicate_rule_id_within_family() -> None:
    """Within a single family, each rule_id appears at most once."""
    for family_id, rules in RULES_BY_FAMILY.items():
        rule_ids = [r.rule_id for r in rules]
        # Forward-compat families have a single placeholder, so the
        # uniqueness check holds trivially. Cutover families have 6 distinct
        # rule_ids.
        assert len(rule_ids) == len(set(rule_ids)), f"{family_id.value} has duplicate rule_ids"
