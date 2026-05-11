"""Closed-set sanity tests for the per-axis risk-rule registries (venue / account / client / asset_group / global).

Phase 2.B-F of ``risk_simulations_limits_alerting_2026_05_10``. Enforces:

1. Each per-axis registry is non-empty + meets the minimum-count contract from
   the plan body (≥15 venue / ≥8 account / ≥4 client / ≥6 asset_group /
   ≥3 global).
2. Every rule's ``scope`` matches the axis it lives in.
3. Every rule's ``applies_to`` is sanity-checked (non-empty + axis-appropriate
   sentinel).
4. ``RiskRule.kill_switch_scope()`` orthogonality mapping per the § 7 seam
   diagram holds for every entry.
5. Per-consequence ``alerting_severity`` is consistent with the seam
   declarations (BLOCK → HIGH/CRITICAL, SCALE_DOWN → WARN, MONITOR →
   INFO/WARN, TEST_ONLY → INFO).

Spawn scope: ``ikenna-slot7-r2-risk-other-axes`` per
``plans/active/work_split_2026_05_11_ikenna.md`` Slot 7 Sub-E.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.alerting import (
    AlertSeverity,
    KillSwitchScope,
)
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    RiskRule,
    RiskRuleConsequence,
    RiskRuleScope,
)
from unified_api_contracts.registry.risk_rules.account import ACCOUNT_RULES
from unified_api_contracts.registry.risk_rules.asset_group import ASSET_GROUP_RULES
from unified_api_contracts.registry.risk_rules.client import CLIENT_RULES
from unified_api_contracts.registry.risk_rules.global_rules import GLOBAL_RULES
from unified_api_contracts.registry.risk_rules.venue import VENUE_RULES

# ---------------------------------------------------------------------------
# Cutover-archetype canonical applies_to vocabularies.
# ---------------------------------------------------------------------------

_CUTOVER_VENUES: frozenset[str] = frozenset(
    {
        # CeFi perp venues per master plan.
        "bybit",
        "deribit",
        "binance",
        "okx",
        "hyperliquid",
        "aster",
        # Solana DeFi protocols (carry_staked_basis LST yields).
        "marinade",
        "jito",
        "sanctum",
    }
)

_CUTOVER_ACCOUNTS: frozenset[str] = frozenset(
    {"paper_default", "live_cutover_2026_05_23"}
)

_CUTOVER_CLIENTS: frozenset[str] = frozenset({"cutover_demo_client_2026_05_23"})

_CUTOVER_ASSET_GROUPS: frozenset[str] = frozenset({"defi", "cefi"})

# ---------------------------------------------------------------------------
# Per-axis non-empty + minimum-count contract (per spawn instructions).
# ---------------------------------------------------------------------------


def test_venue_rules_non_empty_and_min_count() -> None:
    """Per spawn: ≥15 venue rules total (≥3 rules × ≥5 venues; we ship 9 venues × 3)."""
    assert len(VENUE_RULES) >= 15


def test_account_rules_non_empty_and_min_count() -> None:
    """Per spawn: ≥8 account rules total (≥4 rules × 2 accounts)."""
    assert len(ACCOUNT_RULES) >= 8


def test_client_rules_non_empty_and_min_count() -> None:
    """Per spawn: ≥4 client rules total (≥4 rules × 1 cutover demo client)."""
    assert len(CLIENT_RULES) >= 4


def test_asset_group_rules_non_empty_and_min_count() -> None:
    """Per spawn: ≥6 asset_group rules total (≥3 rules × 2 asset_groups)."""
    assert len(ASSET_GROUP_RULES) >= 6


def test_global_rules_non_empty_and_min_count() -> None:
    """Per spawn: ≥3 workspace-wide kill-condition rules."""
    assert len(GLOBAL_RULES) >= 3


# ---------------------------------------------------------------------------
# Scope discipline — every rule's scope matches the axis it lives in.
# ---------------------------------------------------------------------------


def test_every_venue_rule_has_per_venue_scope() -> None:
    for rule in VENUE_RULES:
        assert rule.scope is RiskRuleScope.PER_VENUE, (
            f"venue rule {rule.rule_id} applies_to={rule.applies_to} has wrong scope {rule.scope}"
        )


def test_every_account_rule_has_per_account_scope() -> None:
    for rule in ACCOUNT_RULES:
        assert rule.scope is RiskRuleScope.PER_ACCOUNT, (
            f"account rule {rule.rule_id} applies_to={rule.applies_to} has wrong scope {rule.scope}"
        )


def test_every_client_rule_has_per_client_scope() -> None:
    for rule in CLIENT_RULES:
        assert rule.scope is RiskRuleScope.PER_CLIENT, (
            f"client rule {rule.rule_id} applies_to={rule.applies_to} has wrong scope {rule.scope}"
        )


def test_every_asset_group_rule_has_per_asset_group_scope() -> None:
    for rule in ASSET_GROUP_RULES:
        assert rule.scope is RiskRuleScope.PER_ASSET_GROUP, (
            f"asset_group rule {rule.rule_id} applies_to={rule.applies_to} has wrong scope {rule.scope}"
        )


def test_every_global_rule_has_global_scope() -> None:
    for rule in GLOBAL_RULES:
        assert rule.scope is RiskRuleScope.GLOBAL, (
            f"global rule {rule.rule_id} applies_to={rule.applies_to} has wrong scope {rule.scope}"
        )


# ---------------------------------------------------------------------------
# applies_to sanity — axis-appropriate key shape per RiskRule docstring.
# ---------------------------------------------------------------------------


def test_venue_applies_to_in_cutover_set() -> None:
    """Every PER_VENUE rule's applies_to is a known cutover venue (lowercase)."""
    for rule in VENUE_RULES:
        assert rule.applies_to in _CUTOVER_VENUES, (
            f"venue rule applies_to={rule.applies_to!r} not in cutover venue set"
        )
        assert rule.applies_to == rule.applies_to.lower(), (
            f"venue applies_to should be lowercase, got {rule.applies_to!r}"
        )


def test_account_applies_to_in_cutover_set() -> None:
    for rule in ACCOUNT_RULES:
        assert rule.applies_to in _CUTOVER_ACCOUNTS, (
            f"account rule applies_to={rule.applies_to!r} not in cutover account set"
        )


def test_client_applies_to_in_cutover_set() -> None:
    for rule in CLIENT_RULES:
        assert rule.applies_to in _CUTOVER_CLIENTS, (
            f"client rule applies_to={rule.applies_to!r} not in cutover client set"
        )


def test_asset_group_applies_to_in_cutover_set() -> None:
    """asset_group keys stay lowercase per CLAUDE.md "Asset-group vocabulary" rule."""
    for rule in ASSET_GROUP_RULES:
        assert rule.applies_to in _CUTOVER_ASSET_GROUPS, (
            f"asset_group rule applies_to={rule.applies_to!r} not in cutover set"
        )
        assert rule.applies_to == rule.applies_to.lower()


def test_global_applies_to_is_sentinel() -> None:
    """GLOBAL rules use the '*' sentinel per RiskRule docstring."""
    for rule in GLOBAL_RULES:
        assert rule.applies_to == "*", (
            f"global rule applies_to should be '*' sentinel, got {rule.applies_to!r}"
        )


# ---------------------------------------------------------------------------
# kill_switch_scope() orthogonality mapping per the § 7 seam diagram.
# ---------------------------------------------------------------------------


def test_venue_rules_kill_switch_scope_is_venue() -> None:
    for rule in VENUE_RULES:
        assert rule.kill_switch_scope() is KillSwitchScope.VENUE


def test_account_rules_kill_switch_scope_is_none() -> None:
    """PER_ACCOUNT not directly kill-switch-applicable per seam diagram."""
    for rule in ACCOUNT_RULES:
        assert rule.kill_switch_scope() is None


def test_client_rules_kill_switch_scope_is_client() -> None:
    for rule in CLIENT_RULES:
        assert rule.kill_switch_scope() is KillSwitchScope.CLIENT


def test_asset_group_rules_kill_switch_scope_is_none() -> None:
    """PER_ASSET_GROUP not directly kill-switch-applicable per seam diagram."""
    for rule in ASSET_GROUP_RULES:
        assert rule.kill_switch_scope() is None


def test_global_rules_kill_switch_scope_is_global() -> None:
    for rule in GLOBAL_RULES:
        assert rule.kill_switch_scope() is KillSwitchScope.GLOBAL


# ---------------------------------------------------------------------------
# Consequence → alerting_severity mapping consistent per seam diagram.
# ---------------------------------------------------------------------------

# BLOCK typically pairs with HIGH or CRITICAL.
_BLOCK_VALID_SEVERITIES: frozenset[AlertSeverity] = frozenset(
    {AlertSeverity.HIGH, AlertSeverity.CRITICAL}
)
# SCALE_DOWN typically pairs with WARN; MONITOR pairs with WARN or INFO;
# TEST_ONLY pairs with INFO.
_SCALE_DOWN_VALID_SEVERITIES: frozenset[AlertSeverity] = frozenset({AlertSeverity.WARN})
_MONITOR_VALID_SEVERITIES: frozenset[AlertSeverity] = frozenset(
    {AlertSeverity.INFO, AlertSeverity.WARN}
)
_TEST_ONLY_VALID_SEVERITIES: frozenset[AlertSeverity] = frozenset({AlertSeverity.INFO})


def _check_severity_consequence_consistency(rule: RiskRule) -> None:
    if rule.consequence is RiskRuleConsequence.BLOCK:
        assert rule.alerting_severity in _BLOCK_VALID_SEVERITIES, (
            f"rule {rule.rule_id} applies_to={rule.applies_to} BLOCK paired with non-HIGH/CRITICAL "
            f"severity {rule.alerting_severity}"
        )
    elif rule.consequence is RiskRuleConsequence.SCALE_DOWN:
        assert rule.alerting_severity in _SCALE_DOWN_VALID_SEVERITIES, (
            f"rule {rule.rule_id} applies_to={rule.applies_to} SCALE_DOWN paired with non-WARN "
            f"severity {rule.alerting_severity}"
        )
    elif rule.consequence is RiskRuleConsequence.MONITOR:
        assert rule.alerting_severity in _MONITOR_VALID_SEVERITIES, (
            f"rule {rule.rule_id} applies_to={rule.applies_to} MONITOR paired with non-INFO/WARN "
            f"severity {rule.alerting_severity}"
        )
    elif rule.consequence is RiskRuleConsequence.TEST_ONLY:
        assert rule.alerting_severity in _TEST_ONLY_VALID_SEVERITIES, (
            f"rule {rule.rule_id} applies_to={rule.applies_to} TEST_ONLY paired with non-INFO "
            f"severity {rule.alerting_severity}"
        )


@pytest.mark.parametrize(
    ("axis_name", "rules"),
    [
        ("venue", VENUE_RULES),
        ("account", ACCOUNT_RULES),
        ("client", CLIENT_RULES),
        ("asset_group", ASSET_GROUP_RULES),
        ("global", GLOBAL_RULES),
    ],
)
def test_consequence_severity_consistent(
    axis_name: str, rules: tuple[RiskRule, ...]
) -> None:
    """Per-axis sweep: every rule's consequence + severity match the seam mapping."""
    assert rules, f"{axis_name} registry must be non-empty"
    for rule in rules:
        _check_severity_consequence_consistency(rule)


# ---------------------------------------------------------------------------
# Per-venue distribution sanity — every cutover venue has ≥3 rules.
# ---------------------------------------------------------------------------


def test_every_cutover_venue_has_min_3_rules() -> None:
    """Per spawn: ≥3 rules per venue (MaxOI + single-instrument size + cross-instrument size)."""
    counts: dict[str, int] = {}
    for rule in VENUE_RULES:
        counts[rule.applies_to] = counts.get(rule.applies_to, 0) + 1
    for venue in _CUTOVER_VENUES:
        assert counts.get(venue, 0) >= 3, (
            f"cutover venue {venue!r} has only {counts.get(venue, 0)} rules (expected ≥3)"
        )


def test_every_cutover_account_has_min_4_rules() -> None:
    """Per spawn: ≥4 rules per account."""
    counts: dict[str, int] = {}
    for rule in ACCOUNT_RULES:
        counts[rule.applies_to] = counts.get(rule.applies_to, 0) + 1
    for account in _CUTOVER_ACCOUNTS:
        assert counts.get(account, 0) >= 4, (
            f"cutover account {account!r} has only {counts.get(account, 0)} rules (expected ≥4)"
        )


def test_every_cutover_asset_group_has_min_3_rules() -> None:
    """Per spawn: ≥3 rules per asset_group."""
    counts: dict[str, int] = {}
    for rule in ASSET_GROUP_RULES:
        counts[rule.applies_to] = counts.get(rule.applies_to, 0) + 1
    for ag in _CUTOVER_ASSET_GROUPS:
        assert counts.get(ag, 0) >= 3, (
            f"cutover asset_group {ag!r} has only {counts.get(ag, 0)} rules (expected ≥3)"
        )


# ---------------------------------------------------------------------------
# DeFi-only gas budget rule lives in asset_group registry per Phase 2.E spec.
# ---------------------------------------------------------------------------


def test_defi_asset_group_has_gas_budget_rule() -> None:
    """Phase 2.E spec: DeFi asset_group must include a gas-budget rule (DeFi only)."""
    defi_rules = [rule for rule in ASSET_GROUP_RULES if rule.applies_to == "defi"]
    gas_rules = [
        rule
        for rule in defi_rules
        if rule.trigger.trigger_type == "gas_budget_exceeded"
    ]
    assert gas_rules, "DeFi asset_group registry must contain a gas-budget rule"


def test_cefi_asset_group_has_no_gas_budget_rule() -> None:
    """CeFi venues don't have on-chain gas; gas-budget rule is DeFi-only per Phase 2.E spec."""
    cefi_rules = [rule for rule in ASSET_GROUP_RULES if rule.applies_to == "cefi"]
    gas_rules = [
        rule
        for rule in cefi_rules
        if rule.trigger.trigger_type == "gas_budget_exceeded"
    ]
    assert not gas_rules, "CeFi asset_group must NOT contain a gas-budget rule"


# ---------------------------------------------------------------------------
# Global rules — every rule triggers kill-switch + fires CRITICAL.
# ---------------------------------------------------------------------------


def test_every_global_rule_triggers_kill_switch() -> None:
    """Workspace-wide kill-condition rules MUST set triggers_kill_switch=True."""
    for rule in GLOBAL_RULES:
        assert rule.triggers_kill_switch, (
            f"global rule {rule.rule_id} must trigger kill-switch"
        )


def test_every_global_rule_fires_critical() -> None:
    """Workspace-wide kill conditions fire at CRITICAL severity."""
    for rule in GLOBAL_RULES:
        assert rule.alerting_severity is AlertSeverity.CRITICAL


# ---------------------------------------------------------------------------
# Cross-axis aggregate count sanity.
# ---------------------------------------------------------------------------


def test_total_rule_count_across_other_axes() -> None:
    """Total of Phase 2.B-F rule count meets ≥36 aggregate seed expectation."""
    total = (
        len(VENUE_RULES)
        + len(ACCOUNT_RULES)
        + len(CLIENT_RULES)
        + len(ASSET_GROUP_RULES)
        + len(GLOBAL_RULES)
    )
    # 15 venue + 8 account + 4 client + 6 asset_group + 3 global = 36
    assert total >= 36, (
        f"aggregate Phase 2.B-F rule count = {total}, expected ≥36"
    )
