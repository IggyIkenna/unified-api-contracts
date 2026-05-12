"""Per-archetype risk-rule registry conformance tests.

Phase 2.A of ``risk_simulations_limits_alerting_2026_05_10``. Enforces:

1. ``ARCHETYPE_RULES`` non-empty + ≥10 rules per cutover archetype.
2. Every rule's ``scope == PER_ARCHETYPE`` + ``applies_to`` is one of the 2
   cutover archetypes (``CARRY_STAKED_BASIS`` /
   ``ARBITRAGE_PRICE_DISPERSION``).
3. Every rule's ``trigger.trigger_type`` is a known closed-union member.
4. Consequence → ``alerting_severity`` matches the seam-diagram severity map:
   BLOCK → HIGH or CRITICAL; SCALE_DOWN → WARN; MONITOR → INFO or WARN;
   TEST_ONLY → INFO.
5. ``RiskRule.kill_switch_scope() == KillSwitchScope.ARCHETYPE`` for every
   rule (per the orthogonality declaration; PER_ARCHETYPE maps 1:1 to
   KillSwitchScope.ARCHETYPE).
6. No duplicate ``(rule_id, applies_to)`` pairs.
7. Spot-checks on archetype-specific axis coverage (each archetype has the
   required axes from § Scope item 2).
"""

from __future__ import annotations

from typing import Final

import pytest

from unified_api_contracts.canonical.crosscutting.alerting.codes import (
    AlertSeverity,
    KillSwitchScope,
)
from unified_api_contracts.canonical.crosscutting.risk_rule import (
    CapitalAtRiskCeilingTrigger,
    FundingCostCeilingTrigger,
    GasBudgetTrigger,
    MaxConcentrationTrigger,
    MaxCorrelationTrigger,
    MaxDailyLossTrigger,
    MaxDrawdownTrigger,
    MaxLeverageTrigger,
    MaxPositionSizeTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleScope,
    SlippageBudgetTrigger,
)
from unified_api_contracts.registry.risk_rules.archetype import ARCHETYPE_RULES

_CUTOVER_ARCHETYPES: Final[frozenset[str]] = frozenset({"CARRY_STAKED_BASIS", "ARBITRAGE_PRICE_DISPERSION"})


_KNOWN_TRIGGER_TYPES: Final[frozenset[str]] = frozenset(
    {
        "max_position_size",
        "max_drawdown",
        "max_leverage",
        "max_concentration",
        "max_correlation",
        "slippage_budget_exceeded",
        "funding_cost_ceiling",
        "gas_budget_exceeded",
        "capital_at_risk_ceiling",
        "max_oi",
        "max_gross_exposure",
        "max_net_exposure",
        "max_daily_loss",
    }
)


# ---------------------------------------------------------------------------
# Basic shape + coverage.
# ---------------------------------------------------------------------------


def test_archetype_rules_non_empty() -> None:
    """Phase 2.A done-definition: registry seed has rules."""
    assert len(ARCHETYPE_RULES) > 0, "ARCHETYPE_RULES must seed at least one rule."


@pytest.mark.parametrize("archetype", sorted(_CUTOVER_ARCHETYPES))
def test_archetype_rules_min_count(archetype: str) -> None:
    """Each cutover archetype gets ≥10 rules per § Scope item 2."""
    matching = [r for r in ARCHETYPE_RULES if r.applies_to == archetype]
    assert len(matching) >= 10, (
        f"Archetype {archetype!r} has only {len(matching)} rules; "
        "≥10 required per Phase 2.A done-definition + plan Scope item 2."
    )


def test_archetype_rules_total_minimum() -> None:
    """Sanity: ≥20 total rules across both cutover archetypes."""
    assert len(ARCHETYPE_RULES) >= 20, (
        f"ARCHETYPE_RULES has {len(ARCHETYPE_RULES)} rules; ≥20 required (≥10 per archetype × 2 archetypes)."
    )


# ---------------------------------------------------------------------------
# Scope + applies_to invariants.
# ---------------------------------------------------------------------------


def test_every_rule_scope_is_per_archetype() -> None:
    """All rules in this registry are scoped per-archetype."""
    for rule in ARCHETYPE_RULES:
        assert rule.scope is RiskRuleScope.PER_ARCHETYPE, (
            f"Rule {rule.rule_id} has scope={rule.scope}; expected PER_ARCHETYPE for archetype.py registry."
        )


def test_every_applies_to_is_cutover_archetype() -> None:
    """Every applies_to is a cutover-archetype key."""
    for rule in ARCHETYPE_RULES:
        assert rule.applies_to in _CUTOVER_ARCHETYPES, (
            f"Rule {rule.rule_id} applies_to={rule.applies_to!r}; expected one of {sorted(_CUTOVER_ARCHETYPES)!r}."
        )


# ---------------------------------------------------------------------------
# Trigger-type closed-union conformance.
# ---------------------------------------------------------------------------


def test_every_trigger_type_is_known_closed_union_member() -> None:
    """Trigger types must be members of the closed-union discriminator."""
    for rule in ARCHETYPE_RULES:
        trigger_type = rule.trigger.trigger_type
        assert trigger_type in _KNOWN_TRIGGER_TYPES, (
            f"Rule {rule.rule_id} has trigger_type={trigger_type!r}; "
            f"not in known closed-union set {sorted(_KNOWN_TRIGGER_TYPES)!r}."
        )


def test_every_trigger_is_correct_pydantic_subclass() -> None:
    """Pydantic discriminated-union dispatch resolves to typed subclass."""
    type_to_class: dict[str, type] = {
        "max_position_size": MaxPositionSizeTrigger,
        "max_drawdown": MaxDrawdownTrigger,
        "max_leverage": MaxLeverageTrigger,
        "max_concentration": MaxConcentrationTrigger,
        "max_correlation": MaxCorrelationTrigger,
        "slippage_budget_exceeded": SlippageBudgetTrigger,
        "funding_cost_ceiling": FundingCostCeilingTrigger,
        "gas_budget_exceeded": GasBudgetTrigger,
        "capital_at_risk_ceiling": CapitalAtRiskCeilingTrigger,
        "max_daily_loss": MaxDailyLossTrigger,
    }
    for rule in ARCHETYPE_RULES:
        expected_cls = type_to_class.get(rule.trigger.trigger_type)
        if expected_cls is None:
            continue  # Trigger types not exercised in this registry are fine.
        assert isinstance(rule.trigger, expected_cls), (
            f"Rule {rule.rule_id}: trigger discriminator says "
            f"{rule.trigger.trigger_type!r} but Pydantic resolved to "
            f"{type(rule.trigger).__name__} (expected "
            f"{expected_cls.__name__})."
        )


# ---------------------------------------------------------------------------
# Consequence → severity seam-diagram conformance.
# ---------------------------------------------------------------------------


def test_consequence_severity_mapping_matches_seam_diagram() -> None:
    """Severity per consequence per the seam diagram cross-product table.

    * BLOCK → HIGH or CRITICAL.
    * SCALE_DOWN → WARN.
    * MONITOR → INFO or WARN.
    * TEST_ONLY → INFO.
    """
    allowed: dict[RiskRuleConsequence, frozenset[AlertSeverity]] = {
        RiskRuleConsequence.BLOCK: frozenset({AlertSeverity.HIGH, AlertSeverity.CRITICAL}),
        RiskRuleConsequence.SCALE_DOWN: frozenset({AlertSeverity.WARN}),
        RiskRuleConsequence.MONITOR: frozenset({AlertSeverity.INFO, AlertSeverity.WARN}),
        RiskRuleConsequence.TEST_ONLY: frozenset({AlertSeverity.INFO}),
    }
    for rule in ARCHETYPE_RULES:
        permitted = allowed[rule.consequence]
        assert rule.alerting_severity in permitted, (
            f"Rule {rule.rule_id} (applies_to={rule.applies_to!r}): "
            f"consequence={rule.consequence.value} paired with severity="
            f"{rule.alerting_severity.value}; seam-diagram requires "
            f"severity ∈ {sorted(s.value for s in permitted)!r}."
        )


# ---------------------------------------------------------------------------
# Kill-switch scope orthogonality.
# ---------------------------------------------------------------------------


def test_every_rule_kill_switch_scope_is_archetype() -> None:
    """PER_ARCHETYPE rules map to KillSwitchScope.ARCHETYPE per seam diagram.

    Orthogonality declaration: ``RiskRule.kill_switch_scope()`` maps
    ``RiskRuleScope.PER_ARCHETYPE`` → ``KillSwitchScope.ARCHETYPE``. Every
    rule in this registry is PER_ARCHETYPE-scoped so all map identically.
    """
    for rule in ARCHETYPE_RULES:
        assert rule.kill_switch_scope() is KillSwitchScope.ARCHETYPE, (
            f"Rule {rule.rule_id} (applies_to={rule.applies_to!r}): "
            f"kill_switch_scope() returned {rule.kill_switch_scope()!r}; "
            "expected KillSwitchScope.ARCHETYPE for PER_ARCHETYPE rules."
        )


def test_triggers_kill_switch_only_on_block_rules() -> None:
    """Per seam-diagram orthogonality: only BLOCK consequence is meaningful
    for ``triggers_kill_switch``. SCALE_DOWN / MONITOR / TEST_ONLY ignore the
    field. We assert no non-BLOCK rule sets ``triggers_kill_switch=True`` to
    avoid operator-confusion when reading the registry."""
    for rule in ARCHETYPE_RULES:
        if rule.consequence is not RiskRuleConsequence.BLOCK:
            assert not rule.triggers_kill_switch, (
                f"Rule {rule.rule_id} (consequence="
                f"{rule.consequence.value}) sets triggers_kill_switch=True; "
                "this field is only meaningful for BLOCK consequence."
            )


# ---------------------------------------------------------------------------
# Deduplication.
# ---------------------------------------------------------------------------


def test_no_duplicate_rules_with_same_trigger_payload() -> None:
    """Rules may share ``(rule_id, applies_to)`` if the trigger payload
    differs (e.g. same ``MAX_CORRELATION_PER_ARCHETYPE`` rule_id evaluated at
    different rolling windows for regime-watch vs hard cap). What MUST be
    unique is the full ``(rule_id, applies_to, trigger.model_dump())`` tuple
    — otherwise registry lookup is ambiguous + the evaluator double-counts.
    """
    seen: set[tuple[str, str, str]] = set()
    duplicates: list[tuple[str, str, str]] = []
    for rule in ARCHETYPE_RULES:
        # ``model_dump_json`` gives a deterministic Pydantic serialisation
        # we can use as a set key.
        trigger_repr = rule.trigger.model_dump_json()
        key = (rule.rule_id.value, rule.applies_to, trigger_repr)
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    assert not duplicates, f"Duplicate (rule_id, applies_to, trigger) entries in ARCHETYPE_RULES: {duplicates!r}."


# ---------------------------------------------------------------------------
# Axis coverage spot-checks per § Scope item 2.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("archetype", "required_trigger_type"),
    [
        ("CARRY_STAKED_BASIS", "max_position_size"),
        ("CARRY_STAKED_BASIS", "max_drawdown"),
        ("CARRY_STAKED_BASIS", "max_leverage"),
        ("CARRY_STAKED_BASIS", "max_concentration"),
        ("CARRY_STAKED_BASIS", "max_correlation"),
        ("CARRY_STAKED_BASIS", "slippage_budget_exceeded"),
        # Archetype-specific: gas budget for on-chain Solana archetype.
        ("CARRY_STAKED_BASIS", "gas_budget_exceeded"),
        ("CARRY_STAKED_BASIS", "capital_at_risk_ceiling"),
        ("CARRY_STAKED_BASIS", "max_daily_loss"),
        ("ARBITRAGE_PRICE_DISPERSION", "max_position_size"),
        ("ARBITRAGE_PRICE_DISPERSION", "max_drawdown"),
        ("ARBITRAGE_PRICE_DISPERSION", "max_leverage"),
        ("ARBITRAGE_PRICE_DISPERSION", "max_concentration"),
        ("ARBITRAGE_PRICE_DISPERSION", "max_correlation"),
        ("ARBITRAGE_PRICE_DISPERSION", "slippage_budget_exceeded"),
        # Archetype-specific: funding-cost ceiling for funding-arb archetype.
        ("ARBITRAGE_PRICE_DISPERSION", "funding_cost_ceiling"),
        ("ARBITRAGE_PRICE_DISPERSION", "capital_at_risk_ceiling"),
        ("ARBITRAGE_PRICE_DISPERSION", "max_daily_loss"),
    ],
)
def test_axis_coverage_per_archetype(archetype: str, required_trigger_type: str) -> None:
    """Every required axis from § Scope item 2 has at least one rule per
    archetype."""
    matching = [
        r for r in ARCHETYPE_RULES if r.applies_to == archetype and r.trigger.trigger_type == required_trigger_type
    ]
    assert len(matching) >= 1, (
        f"Archetype {archetype!r} has 0 rules with trigger_type="
        f"{required_trigger_type!r}; § Scope item 2 requires coverage of "
        "this axis."
    )


def test_every_rule_is_pydantic_frozen() -> None:
    """RiskRule is declared with ``frozen=True``; mutation must error."""
    for rule in ARCHETYPE_RULES:
        with pytest.raises((TypeError, ValueError, Exception)):
            # Pydantic frozen models raise on attribute mutation.
            rule.description = "mutated"  # type: ignore[misc]


def test_every_rule_has_non_empty_description() -> None:
    """Operator-facing description is required + must be non-trivial."""
    for rule in ARCHETYPE_RULES:
        assert len(rule.description.strip()) >= 20, (
            f"Rule {rule.rule_id} description is too short or empty: "
            f"{rule.description!r}; operator-facing rules need a real "
            "description."
        )


def test_every_rule_is_riskrule_instance() -> None:
    """Sanity: tuple members are all ``RiskRule`` instances (Pydantic
    discriminated-union sometimes resolves surprisingly)."""
    for rule in ARCHETYPE_RULES:
        assert isinstance(rule, RiskRule), f"ARCHETYPE_RULES member is not a RiskRule: {type(rule).__name__}."
