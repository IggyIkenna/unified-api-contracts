"""Closed-set sanity tests for the UAC circuit-breaker taxonomy.

Phase 1.F of ``disaster_recovery_circuit_breakers_2026_05_10.md``
(``unified-trading-pm/plans/active/``).

Verifies:

1. Every enum (:class:`CircuitBreakerId` / :class:`BreakerScope` /
   :class:`BreakerAction` / :class:`BreakerRecoveryMode`) is a closed set
   with no value duplicates.
2. :data:`BREAKER_RECOVERY_DEFAULTS` covers every :class:`BreakerAction`
   member + the per-action rationale matches Q8 ratification 2026-05-10.
3. :class:`BreakerConfig` validators reject inconsistent
   ``recovery_mode``/``cooldown_seconds`` combinations.
4. :class:`BreakerConfig` auto-fills ``recovery_mode`` from
   :data:`BREAKER_RECOVERY_DEFAULTS` when omitted.
5. Per-archetype registry seeds carry >= 10 :class:`BreakerConfig` plus
   matching :class:`BreakerRecoveryRule` entries for both cutover
   archetypes.
6. Every Pydantic class docstring includes the seam citation per the
   risk-plan § 7 SSOT reconciliation mandate.
7. :class:`BreakerRecoveryRule` semantics: ``auto_disarm_after_seconds=None``
   for ``MANUAL_UNKILL``-style rules in the registry.
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts import (
    BREAKER_RECOVERY_DEFAULTS,
    AlertSeverity,
    BreakerAction,
    BreakerConfig,
    BreakerRecoveryMode,
    BreakerRecoveryRule,
    BreakerScope,
    BreakerTrigger,
    CircuitBreakerId,
    ThresholdUnit,
)
from unified_api_contracts.registry.circuit_breakers import (
    PER_ARCHETYPE_BREAKERS,
    PER_ARCHETYPE_RECOVERY_RULES,
)

# ---------------------------------------------------------------------------
# Closed-set sanity — enums
# ---------------------------------------------------------------------------


def test_circuit_breaker_id_no_duplicate_values() -> None:
    values = [m.value for m in CircuitBreakerId]
    assert len(values) == len(set(values))


def test_breaker_scope_closed_set() -> None:
    assert {m.value for m in BreakerScope} == {
        "PER_VENUE",
        "PER_ARCHETYPE",
        "PER_ACCOUNT",
        "PER_ASSET_GROUP",
        "GLOBAL",
    }


def test_breaker_action_closed_set() -> None:
    assert {m.value for m in BreakerAction} == {
        "BLOCK_NEW",
        "CANCEL_OPEN",
        "SCALE_DOWN",
        "KILL_ALL",
    }


def test_breaker_recovery_mode_closed_set() -> None:
    assert {m.value for m in BreakerRecoveryMode} == {
        "manual_unkill",
        "auto_cooldown",
    }


def test_circuit_breaker_id_has_carry_staked_basis_breakers() -> None:
    """The 10 breakers cited in DR plan Phase 1.B for ``carry_staked_basis``."""
    expected_carry = {
        "ORACLE_DEVIATION_BPS",
        "RPC_OUTAGE_SECONDS",
        "GAS_PRICE_SURGE_GWEI",
        "POSITION_LIMIT_EXCEEDED",
        "DRAWDOWN_DAILY_BPS",
        "LIQUIDATION_CASCADE_RISK",
        "VENUE_OUTAGE_SECONDS",
        "CUSTODY_DISCONNECT_SECONDS",
        "MANIFEST_PHANTOM_RATE_BPS",
        "BATCH_LIVE_DIVERGENCE_BPS",
    }
    enum_values = {m.value for m in CircuitBreakerId}
    assert expected_carry.issubset(enum_values)


def test_circuit_breaker_id_has_arbitrage_price_dispersion_breakers() -> None:
    """The 10 ARBITRAGE_PRICE_DISPERSION breakers cited in DR plan."""
    expected_arb = {
        "FUNDING_RATE_FLIP_BPS",
        "BASIS_INVERSION_BPS",
        "SPREAD_BLOWOUT_BPS",
        "CROSS_VENUE_DIVERGENCE_BPS",
        "INVENTORY_IMBALANCE_RATIO",
        "FILL_LATENCY_BREACH_MS",
        "REJECT_RATE_BPS",
        "PNL_VARIANCE_SIGMA",
        "HEDGE_GAP_NOTIONAL_USD",
        "CLOCK_SKEW_MS",
    }
    enum_values = {m.value for m in CircuitBreakerId}
    assert expected_arb.issubset(enum_values)


# ---------------------------------------------------------------------------
# BREAKER_RECOVERY_DEFAULTS SSOT
# ---------------------------------------------------------------------------


def test_breaker_recovery_defaults_covers_every_action() -> None:
    """Per Q8 ratification 2026-05-10: every BreakerAction has a default mode."""
    for action in BreakerAction:
        assert action in BREAKER_RECOVERY_DEFAULTS


def test_breaker_recovery_defaults_q8_ratification_semantics() -> None:
    """Per-action defaults match the Q8 ratification 2026-05-10 doc.

    - BLOCK_NEW -> auto_cooldown (least-restrictive; auto-resume safe).
    - CANCEL_OPEN -> manual_unkill (cancelled orders are gone).
    - SCALE_DOWN -> auto_cooldown (partial unwind has natural inverse).
    - KILL_ALL -> manual_unkill (full unwind needs operator sign-off).
    """
    assert BREAKER_RECOVERY_DEFAULTS[BreakerAction.BLOCK_NEW] == BreakerRecoveryMode.AUTO_COOLDOWN
    assert BREAKER_RECOVERY_DEFAULTS[BreakerAction.CANCEL_OPEN] == BreakerRecoveryMode.MANUAL_UNKILL
    assert BREAKER_RECOVERY_DEFAULTS[BreakerAction.SCALE_DOWN] == BreakerRecoveryMode.AUTO_COOLDOWN
    assert BREAKER_RECOVERY_DEFAULTS[BreakerAction.KILL_ALL] == BreakerRecoveryMode.MANUAL_UNKILL


def test_breaker_recovery_defaults_is_dict_mapping_action_to_mode() -> None:
    for action, mode in BREAKER_RECOVERY_DEFAULTS.items():
        assert isinstance(action, BreakerAction)
        assert isinstance(mode, BreakerRecoveryMode)


# ---------------------------------------------------------------------------
# BreakerConfig validator semantics
# ---------------------------------------------------------------------------


def _trigger(bid: CircuitBreakerId = CircuitBreakerId.ORACLE_DEVIATION_BPS) -> BreakerTrigger:
    return BreakerTrigger(
        trigger_type=bid,
        threshold_value=Decimal("100"),
        threshold_unit=ThresholdUnit.BPS_OF_ONE,
    )


def test_breaker_config_auto_cooldown_requires_cooldown_seconds() -> None:
    with pytest.raises(ValidationError, match="cooldown_seconds REQUIRED"):
        BreakerConfig(
            breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
            scope=BreakerScope.GLOBAL,
            applies_to="*",
            trigger=_trigger(),
            action=BreakerAction.BLOCK_NEW,
            recovery_mode=BreakerRecoveryMode.AUTO_COOLDOWN,
            cooldown_seconds=None,
            alerting_severity=AlertSeverity.WARN,
        )


def test_breaker_config_manual_unkill_rejects_cooldown_seconds() -> None:
    with pytest.raises(ValidationError, match="cooldown_seconds MUST be None"):
        BreakerConfig(
            breaker_id=CircuitBreakerId.LIQUIDATION_CASCADE_RISK,
            scope=BreakerScope.GLOBAL,
            applies_to="*",
            trigger=_trigger(CircuitBreakerId.LIQUIDATION_CASCADE_RISK),
            action=BreakerAction.KILL_ALL,
            recovery_mode=BreakerRecoveryMode.MANUAL_UNKILL,
            cooldown_seconds=300,
            alerting_severity=AlertSeverity.CRITICAL,
        )


def test_breaker_config_auto_cooldown_rejects_zero_cooldown() -> None:
    with pytest.raises(ValidationError, match="cooldown_seconds REQUIRED"):
        BreakerConfig(
            breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
            scope=BreakerScope.GLOBAL,
            applies_to="*",
            trigger=_trigger(),
            action=BreakerAction.BLOCK_NEW,
            recovery_mode=BreakerRecoveryMode.AUTO_COOLDOWN,
            cooldown_seconds=0,
            alerting_severity=AlertSeverity.WARN,
        )


def test_breaker_config_fills_default_recovery_mode_when_omitted() -> None:
    """When recovery_mode is None, it should auto-fill from
    :data:`BREAKER_RECOVERY_DEFAULTS`."""
    cfg = BreakerConfig(
        breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
        scope=BreakerScope.GLOBAL,
        applies_to="*",
        trigger=_trigger(),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=120,
        alerting_severity=AlertSeverity.WARN,
    )
    assert cfg.recovery_mode == BreakerRecoveryMode.AUTO_COOLDOWN


def test_breaker_config_fills_manual_unkill_default_when_omitted() -> None:
    cfg = BreakerConfig(
        breaker_id=CircuitBreakerId.LIQUIDATION_CASCADE_RISK,
        scope=BreakerScope.GLOBAL,
        applies_to="*",
        trigger=_trigger(CircuitBreakerId.LIQUIDATION_CASCADE_RISK),
        action=BreakerAction.KILL_ALL,
        alerting_severity=AlertSeverity.CRITICAL,
    )
    assert cfg.recovery_mode == BreakerRecoveryMode.MANUAL_UNKILL
    assert cfg.cooldown_seconds is None


def test_breaker_config_explicit_override_allowed() -> None:
    """Per-breaker override away from default IS allowed; the rationale lives
    in the registry seed description."""
    cfg = BreakerConfig(
        breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
        scope=BreakerScope.GLOBAL,
        applies_to="*",
        trigger=_trigger(),
        action=BreakerAction.BLOCK_NEW,
        recovery_mode=BreakerRecoveryMode.MANUAL_UNKILL,
        cooldown_seconds=None,
        alerting_severity=AlertSeverity.WARN,
    )
    assert cfg.recovery_mode == BreakerRecoveryMode.MANUAL_UNKILL


def test_breaker_config_is_frozen() -> None:
    cfg = BreakerConfig(
        breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
        scope=BreakerScope.GLOBAL,
        applies_to="*",
        trigger=_trigger(),
        action=BreakerAction.BLOCK_NEW,
        cooldown_seconds=120,
        alerting_severity=AlertSeverity.WARN,
    )
    with pytest.raises(ValidationError):
        cfg.action = BreakerAction.KILL_ALL  # type: ignore[misc]


def test_breaker_trigger_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        BreakerTrigger.model_validate(
            {
                "trigger_type": CircuitBreakerId.ORACLE_DEVIATION_BPS.value,
                "threshold_value": "100",
                "threshold_unit": ThresholdUnit.BPS_OF_ONE.value,
                "unknown_field": "x",
            }
        )


# ---------------------------------------------------------------------------
# Per-archetype registry coverage
# ---------------------------------------------------------------------------


def test_registry_has_two_cutover_archetypes() -> None:
    assert set(PER_ARCHETYPE_BREAKERS.keys()) == {
        "CARRY_STAKED_BASIS",
        "ARBITRAGE_PRICE_DISPERSION",
    }


@pytest.mark.parametrize("archetype", ["CARRY_STAKED_BASIS", "ARBITRAGE_PRICE_DISPERSION"])
def test_registry_per_archetype_has_at_least_10_breakers(archetype: str) -> None:
    assert len(PER_ARCHETYPE_BREAKERS[archetype]) >= 10


@pytest.mark.parametrize("archetype", ["CARRY_STAKED_BASIS", "ARBITRAGE_PRICE_DISPERSION"])
def test_registry_per_archetype_has_matching_recovery_rules(archetype: str) -> None:
    """Every BreakerConfig has a matching BreakerRecoveryRule keyed by breaker_id."""
    configs = PER_ARCHETYPE_BREAKERS[archetype]
    rules = PER_ARCHETYPE_RECOVERY_RULES[archetype]
    config_ids = {c.breaker_id for c in configs}
    rule_ids = {r.breaker_id for r in rules}
    assert config_ids == rule_ids, f"Archetype {archetype} drift: configs={config_ids} rules={rule_ids}"


@pytest.mark.parametrize("archetype", ["CARRY_STAKED_BASIS", "ARBITRAGE_PRICE_DISPERSION"])
def test_registry_breakers_use_valid_enum_ids(archetype: str) -> None:
    for cfg in PER_ARCHETYPE_BREAKERS[archetype]:
        assert isinstance(cfg.breaker_id, CircuitBreakerId)
        assert isinstance(cfg.scope, BreakerScope)
        assert isinstance(cfg.action, BreakerAction)
        assert isinstance(cfg.recovery_mode, BreakerRecoveryMode)


@pytest.mark.parametrize("archetype", ["CARRY_STAKED_BASIS", "ARBITRAGE_PRICE_DISPERSION"])
def test_registry_recovery_rules_use_valid_enum_ids(archetype: str) -> None:
    for rule in PER_ARCHETYPE_RECOVERY_RULES[archetype]:
        assert isinstance(rule.breaker_id, CircuitBreakerId)
        assert isinstance(rule.guard_description, str) and rule.guard_description
        assert rule.retry_policy in {"exponential", "linear", "none"}


def test_registry_no_duplicate_breaker_ids_per_archetype() -> None:
    for archetype, configs in PER_ARCHETYPE_BREAKERS.items():
        ids = [c.breaker_id for c in configs]
        assert len(ids) == len(set(ids)), f"{archetype} has duplicate breaker IDs"


def test_registry_combined_breaker_count() -> None:
    """Total breakers across both archetypes: 10 + 10 = 20 minimum."""
    total = sum(len(v) for v in PER_ARCHETYPE_BREAKERS.values())
    assert total >= 20


def test_registry_recovery_rules_kill_all_breakers_have_no_auto_disarm() -> None:
    """KILL_ALL action defaults to MANUAL_UNKILL -> matching rule should have
    ``auto_disarm_after_seconds=None``."""
    for archetype, configs in PER_ARCHETYPE_BREAKERS.items():
        rules_by_id = {r.breaker_id: r for r in PER_ARCHETYPE_RECOVERY_RULES[archetype]}
        for cfg in configs:
            if cfg.action == BreakerAction.KILL_ALL:
                rule = rules_by_id[cfg.breaker_id]
                assert rule.auto_disarm_after_seconds is None, (
                    f"{cfg.breaker_id.value} KILL_ALL should have auto_disarm_after_seconds=None"
                )


# ---------------------------------------------------------------------------
# § 7 SSOT reconciliation seam citation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "klass",
    [
        BreakerTrigger,
        BreakerConfig,
        BreakerRecoveryRule,
    ],
)
def test_pydantic_class_docstring_cites_section_7_seam(klass: type) -> None:
    """Every Pydantic class in circuit_breaker.py MUST cite the
    § 7 SSOT reconciliation seam per the risk-plan mandate
    (risk_simulations_limits_alerting_2026_05_10.md:44-87)."""
    doc = inspect.getdoc(klass) or ""
    assert "§ 7 SSOT reconciliation" in doc, f"{klass.__name__} docstring missing '§ 7 SSOT reconciliation' subsection"


@pytest.mark.parametrize(
    "klass",
    [
        CircuitBreakerId,
        BreakerScope,
        BreakerAction,
        BreakerRecoveryMode,
    ],
)
def test_enum_class_docstring_cites_section_7_seam(klass: type) -> None:
    """Every closed-set enum in circuit_breaker.py MUST cite the seam too."""
    doc = inspect.getdoc(klass) or ""
    assert "§ 7 SSOT reconciliation" in doc, f"{klass.__name__} docstring missing '§ 7 SSOT reconciliation' subsection"


# ---------------------------------------------------------------------------
# BreakerRecoveryRule semantics
# ---------------------------------------------------------------------------


def test_breaker_recovery_rule_retry_policy_closed_set() -> None:
    """Closed string-set for retry_policy: exponential | linear | none."""
    rule = BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
        guard_description="x",
        retry_policy="exponential",
    )
    assert rule.retry_policy == "exponential"


def test_breaker_recovery_rule_frozen() -> None:
    rule = BreakerRecoveryRule(
        breaker_id=CircuitBreakerId.ORACLE_DEVIATION_BPS,
        guard_description="x",
    )
    with pytest.raises(ValidationError):
        rule.guard_description = "y"  # type: ignore[misc]


def test_breaker_recovery_rule_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        BreakerRecoveryRule.model_validate(
            {
                "breaker_id": CircuitBreakerId.ORACLE_DEVIATION_BPS.value,
                "guard_description": "x",
                "extra_field": "y",
            }
        )


# ---------------------------------------------------------------------------
# Facade re-export
# ---------------------------------------------------------------------------


def test_facade_exports_breaker_taxonomy() -> None:
    """Verify the workspace-public surface exposes the breaker taxonomy
    per UAC import-surface enforcement."""
    import unified_api_contracts as uac

    assert uac.CircuitBreakerId is CircuitBreakerId
    assert uac.BreakerScope is BreakerScope
    assert uac.BreakerAction is BreakerAction
    assert uac.BreakerRecoveryMode is BreakerRecoveryMode
    assert uac.BreakerTrigger is BreakerTrigger
    assert uac.BreakerConfig is BreakerConfig
    assert uac.BreakerRecoveryRule is BreakerRecoveryRule
    assert uac.BREAKER_RECOVERY_DEFAULTS is BREAKER_RECOVERY_DEFAULTS
