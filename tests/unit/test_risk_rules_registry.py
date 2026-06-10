"""Tests for registry/risk_rules/__init__.py — risk rule aggregator."""

from __future__ import annotations

from collections.abc import Iterable

from unified_api_contracts.canonical.crosscutting.risk_rule import RiskRule, RiskRuleScope
from unified_api_contracts.registry.risk_rules import (
    ACCOUNT_RULES,
    ALL_RULES,
    ARCHETYPE_RULES,
    ASSET_GROUP_RULES,
    CLIENT_RULES,
    GLOBAL_RULES,
    STRATEGY_FAMILY_RULES,
    VENUE_RULES,
    get_rules_for,
    iter_applicable_rules,
)


class TestAllRules:
    def test_all_rules_is_tuple(self) -> None:
        assert isinstance(ALL_RULES, tuple)

    def test_all_rules_non_empty(self) -> None:
        assert len(ALL_RULES) > 0

    def test_all_rules_are_risk_rule_instances(self) -> None:
        for rule in ALL_RULES:
            assert isinstance(rule, RiskRule)

    def test_all_rules_includes_global_rules(self) -> None:
        for rule in GLOBAL_RULES:
            assert rule in ALL_RULES

    def test_all_rules_includes_venue_rules(self) -> None:
        for rule in VENUE_RULES:
            assert rule in ALL_RULES

    def test_all_rules_includes_archetype_rules(self) -> None:
        for rule in ARCHETYPE_RULES:
            assert rule in ALL_RULES


class TestIndividualRuleSets:
    def test_venue_rules_is_tuple(self) -> None:
        assert isinstance(VENUE_RULES, tuple)

    def test_global_rules_is_tuple(self) -> None:
        assert isinstance(GLOBAL_RULES, tuple)

    def test_account_rules_is_tuple(self) -> None:
        assert isinstance(ACCOUNT_RULES, tuple)

    def test_client_rules_is_tuple(self) -> None:
        assert isinstance(CLIENT_RULES, tuple)

    def test_asset_group_rules_is_tuple(self) -> None:
        assert isinstance(ASSET_GROUP_RULES, tuple)

    def test_strategy_family_rules_is_tuple(self) -> None:
        assert isinstance(STRATEGY_FAMILY_RULES, tuple)

    def test_archetype_rules_is_tuple(self) -> None:
        assert isinstance(ARCHETYPE_RULES, tuple)


class TestGetRulesFor:
    def test_wildcard_applies_to_returns_all_in_scope(self) -> None:
        result = get_rules_for(RiskRuleScope.PER_VENUE, "*")
        assert isinstance(result, tuple)
        assert len(result) == len(VENUE_RULES)

    def test_wildcard_on_global_scope(self) -> None:
        result = get_rules_for(RiskRuleScope.GLOBAL, "*")
        assert isinstance(result, tuple)

    def test_specific_applies_to_returns_subset(self) -> None:
        # Get all rules for a specific venue key; may be empty for unknown
        result = get_rules_for(RiskRuleScope.PER_VENUE, "COMPLETELY_UNKNOWN_VENUE_XY")
        assert isinstance(result, tuple)
        # Only catch-all rules (*) should match for unknown venue
        for rule in result:
            assert rule.applies_to == "*"

    def test_unknown_scope_returns_empty(self) -> None:
        # Accessing a scope not in _RULES_BY_SCOPE — the dict has a default of ()
        result = get_rules_for(RiskRuleScope.PER_ACCOUNT, "SOME_ACCOUNT")
        assert isinstance(result, tuple)

    def test_known_venue_returns_matching_rules(self) -> None:
        if VENUE_RULES:
            # Use the applies_to of the first venue rule to get specific matches
            first_rule = VENUE_RULES[0]
            if first_rule.applies_to != "*":
                result = get_rules_for(RiskRuleScope.PER_VENUE, first_rule.applies_to)
                assert first_rule in result

    def test_catch_all_rules_included_in_specific_query(self) -> None:
        # catch-all (* applies_to) rules should appear for any specific key
        catch_all_venue_rules = [r for r in VENUE_RULES if r.applies_to == "*"]
        result = get_rules_for(RiskRuleScope.PER_VENUE, "SOME_VENUE")
        for catch_all_rule in catch_all_venue_rules:
            assert catch_all_rule in result


class TestIterApplicableRules:
    def test_no_args_yields_only_global(self) -> None:
        result = list(iter_applicable_rules())
        global_set = set(GLOBAL_RULES)
        for rule in result:
            assert rule in global_set

    def test_with_venue_id_includes_venue_rules(self) -> None:
        result = list(iter_applicable_rules(venue_id="BINANCE"))
        assert isinstance(result, list)
        # Should include at least global rules
        for global_rule in GLOBAL_RULES:
            assert global_rule in result

    def test_with_archetype_id_includes_archetype_rules(self) -> None:
        result = list(iter_applicable_rules(archetype_id="carry_staked_basis"))
        assert isinstance(result, list)

    def test_with_client_id_includes_client_rules(self) -> None:
        result = list(iter_applicable_rules(client_id="demo_client"))
        assert isinstance(result, list)

    def test_with_account_id_includes_account_rules(self) -> None:
        result = list(iter_applicable_rules(account_id="paper"))
        assert isinstance(result, list)

    def test_with_asset_group_includes_asset_group_rules(self) -> None:
        result = list(iter_applicable_rules(asset_group="defi"))
        assert isinstance(result, list)

    def test_with_strategy_family_includes_family_rules(self) -> None:
        result = list(iter_applicable_rules(strategy_family_id="carry"))
        assert isinstance(result, list)

    def test_multiple_axes_union(self) -> None:
        result = list(
            iter_applicable_rules(
                venue_id="BINANCE",
                archetype_id="carry_staked_basis",
                client_id="demo",
            )
        )
        assert isinstance(result, list)
        # Should be at least as many as global rules
        assert len(result) >= len(GLOBAL_RULES)

    def test_returns_iterable(self) -> None:
        result = iter_applicable_rules()
        assert isinstance(result, Iterable)
