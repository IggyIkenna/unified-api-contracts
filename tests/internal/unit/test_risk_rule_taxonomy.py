"""Closed-set sanity tests for the UAC risk-rule taxonomy.

Phase 1.D of ``risk_simulations_limits_alerting_2026_05_10``. Enforces:

1. ``RiskRuleId`` / ``RiskRuleScope`` / ``RiskRuleConsequence`` closed sets
   are stable + non-duplicating.
2. Every enum docstring carries the "§ 7 SSOT reconciliation" subsection
   (seam-citation discipline per Phase 1.A).
3. ``RiskRule`` Pydantic dataclass validates correctly + rejects unknown
   scopes / consequences / trigger types.
4. Seam-diagram conformance — one test per ``RiskRuleConsequence`` value
   verifying the documented events_emitted + AlertCode mapping matches the
   cross-product table in the plan body.
5. ``RiskRule.kill_switch_scope()`` orthogonality mapping per the seam
   diagram declaration.
6. AlertCode closed-set extension landed cleanly (39 → 45) and the 6 new
   codes resolve.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.alerting import ALERT_CODES, AlertCode, AlertSeverity, KillSwitchScope
from unified_api_contracts.risk import (
    CONSEQUENCE_ALERT_CODES,
    CONSEQUENCE_EVENTS_EMITTED,
    RISK_RULE_IDS,
    MaxConcentrationTrigger,
    MaxDrawdownTrigger,
    MaxLeverageTrigger,
    MaxPositionSizeTrigger,
    RiskRule,
    RiskRuleConsequence,
    RiskRuleId,
    RiskRuleScope,
)

# ---------------------------------------------------------------------------
# Closed-set sanity — RiskRuleId
# ---------------------------------------------------------------------------


def test_risk_rule_ids_frozenset_matches_enum() -> None:
    assert frozenset(m.value for m in RiskRuleId) == RISK_RULE_IDS


def test_risk_rule_ids_no_duplicates() -> None:
    values = [m.value for m in RiskRuleId]
    assert len(values) == len(set(values))


def test_risk_rule_ids_all_uppercase_snake() -> None:
    for rid in RiskRuleId:
        assert rid.value.isupper(), f"{rid.value} must be UPPER_SNAKE_CASE"
        assert " " not in rid.value
        assert rid.value.replace("_", "").isalnum()


# ---------------------------------------------------------------------------
# Closed-set sanity — RiskRuleScope + RiskRuleConsequence
# ---------------------------------------------------------------------------


def test_risk_rule_scope_closed_set() -> None:
    expected = {
        "PER_ARCHETYPE",
        "PER_VENUE",
        "PER_ACCOUNT",
        "PER_ASSET_GROUP",
        "PER_CLIENT",
        "PER_STRATEGY_FAMILY",
        "GLOBAL",
    }
    assert {m.value for m in RiskRuleScope} == expected


def test_risk_rule_consequence_closed_set() -> None:
    expected = {"BLOCK", "SCALE_DOWN", "MONITOR", "TEST_ONLY"}
    assert {m.value for m in RiskRuleConsequence} == expected


def test_risk_rule_consequence_no_duplicates() -> None:
    values = [m.value for m in RiskRuleConsequence]
    assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# § 7 seam-citation discipline (Phase 1.A reviewer requirement)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "enum_cls",
    [RiskRuleId, RiskRuleScope, RiskRuleConsequence],
)
def test_enum_docstring_cites_seam_reconciliation(enum_cls: type) -> None:
    """Every enum docstring MUST include the § 7 SSOT reconciliation subsection.

    Phase 1.A reviewer requirement per
    ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``. Catches
    drift where a contributor adds a new enum / new member without updating
    the seam citation.
    """
    doc = enum_cls.__doc__ or ""
    assert "§ 7 SSOT reconciliation" in doc, (
        f"{enum_cls.__name__} docstring missing '§ 7 SSOT reconciliation' subsection"
    )


def test_risk_rule_class_docstring_cites_seam() -> None:
    doc = RiskRule.__doc__ or ""
    assert "§ 7 SSOT reconciliation" in doc


def test_kill_switch_scope_method_docstring_cites_seam() -> None:
    doc = RiskRule.kill_switch_scope.__doc__ or ""
    assert "§ 7 SSOT reconciliation" in doc


# ---------------------------------------------------------------------------
# RiskRule Pydantic validation
# ---------------------------------------------------------------------------


def _sample_rule() -> RiskRule:
    return RiskRule(
        rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxPositionSizeTrigger(cap_usd=Decimal("100000")),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.HIGH,
        description="Per-archetype gross USD-notional cap.",
        triggers_kill_switch=True,
    )


def test_risk_rule_constructs_with_typed_fields() -> None:
    rule = _sample_rule()
    assert rule.rule_id is RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE
    assert rule.scope is RiskRuleScope.PER_ARCHETYPE
    assert rule.consequence is RiskRuleConsequence.BLOCK
    assert rule.alerting_severity is AlertSeverity.HIGH
    assert rule.triggers_kill_switch is True


def test_risk_rule_rejects_unknown_scope() -> None:
    with pytest.raises(ValidationError):
        RiskRule(
            rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE,
            scope="PER_GALAXY",  # type: ignore[arg-type]
            applies_to="CARRY_STAKED_BASIS",
            trigger=MaxPositionSizeTrigger(cap_usd=Decimal("100000")),
            consequence=RiskRuleConsequence.BLOCK,
            alerting_severity=AlertSeverity.HIGH,
            description="bogus",
        )


def test_risk_rule_rejects_unknown_consequence() -> None:
    with pytest.raises(ValidationError):
        RiskRule(
            rule_id=RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE,
            scope=RiskRuleScope.PER_ARCHETYPE,
            applies_to="CARRY_STAKED_BASIS",
            trigger=MaxPositionSizeTrigger(cap_usd=Decimal("100000")),
            consequence="SET_ON_FIRE",  # type: ignore[arg-type]
            alerting_severity=AlertSeverity.HIGH,
            description="bogus",
        )


def test_risk_rule_rejects_unknown_rule_id() -> None:
    with pytest.raises(ValidationError):
        RiskRule(
            rule_id="MAX_NONSENSE_LIMIT",  # type: ignore[arg-type]
            scope=RiskRuleScope.PER_ARCHETYPE,
            applies_to="CARRY_STAKED_BASIS",
            trigger=MaxPositionSizeTrigger(cap_usd=Decimal("100000")),
            consequence=RiskRuleConsequence.BLOCK,
            alerting_severity=AlertSeverity.HIGH,
            description="bogus",
        )


def test_risk_rule_rejects_extra_fields() -> None:
    """Pydantic ``extra='forbid'`` — schema is closed."""
    with pytest.raises(ValidationError):
        RiskRule.model_validate(
            {
                "rule_id": RiskRuleId.MAX_POSITION_SIZE_PER_ARCHETYPE.value,
                "scope": RiskRuleScope.PER_ARCHETYPE.value,
                "applies_to": "CARRY_STAKED_BASIS",
                "trigger": {
                    "trigger_type": "max_position_size",
                    "cap_usd": "100000",
                },
                "consequence": RiskRuleConsequence.BLOCK.value,
                "alerting_severity": AlertSeverity.HIGH.value,
                "description": "bogus",
                "extra_field": "rejected",
            }
        )


def test_risk_rule_frozen() -> None:
    """Pydantic ``frozen=True`` — immutable after construction."""
    rule = _sample_rule()
    with pytest.raises(ValidationError):
        rule.applies_to = "OTHER"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Trigger discriminated-union dispatch
# ---------------------------------------------------------------------------


def test_trigger_dispatches_on_discriminator() -> None:
    rule = RiskRule(
        rule_id=RiskRuleId.MAX_DRAWDOWN_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxDrawdownTrigger(cap_bps=500),
        consequence=RiskRuleConsequence.BLOCK,
        alerting_severity=AlertSeverity.CRITICAL,
        description="Per-archetype drawdown cap.",
    )
    assert isinstance(rule.trigger, MaxDrawdownTrigger)
    assert rule.trigger.cap_bps == 500


def test_trigger_round_trips_via_json() -> None:
    rule = _sample_rule()
    blob = rule.model_dump_json()
    restored = RiskRule.model_validate_json(blob)
    assert restored == rule


def test_trigger_leverage_dispatches() -> None:
    trigger = MaxLeverageTrigger(cap_ratio=Decimal("3.0"))
    rule = RiskRule(
        rule_id=RiskRuleId.MAX_LEVERAGE_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=trigger,
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Per-archetype leverage cap.",
    )
    assert isinstance(rule.trigger, MaxLeverageTrigger)
    assert rule.trigger.cap_ratio == Decimal("3.0")


def test_trigger_concentration_dispatches() -> None:
    rule = RiskRule(
        rule_id=RiskRuleId.MAX_CONCENTRATION_PER_INSTRUMENT,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxConcentrationTrigger(cap_pct=Decimal("0.25")),
        consequence=RiskRuleConsequence.MONITOR,
        alerting_severity=AlertSeverity.WARN,
        description="Per-instrument concentration cap.",
    )
    assert isinstance(rule.trigger, MaxConcentrationTrigger)


# ---------------------------------------------------------------------------
# kill_switch_scope() — orthogonality mapping per the § 7 seam diagram
# ---------------------------------------------------------------------------


def test_kill_switch_scope_per_venue() -> None:
    rule = _sample_rule().model_copy(update={"scope": RiskRuleScope.PER_VENUE})
    assert rule.kill_switch_scope() is KillSwitchScope.VENUE


def test_kill_switch_scope_per_archetype() -> None:
    rule = _sample_rule()
    assert rule.kill_switch_scope() is KillSwitchScope.ARCHETYPE


def test_kill_switch_scope_per_client() -> None:
    rule = _sample_rule().model_copy(update={"scope": RiskRuleScope.PER_CLIENT})
    assert rule.kill_switch_scope() is KillSwitchScope.CLIENT


def test_kill_switch_scope_global() -> None:
    rule = _sample_rule().model_copy(update={"scope": RiskRuleScope.GLOBAL})
    assert rule.kill_switch_scope() is KillSwitchScope.GLOBAL


def test_kill_switch_scope_per_account_none() -> None:
    """PER_ACCOUNT not directly kill-switch-applicable per the seam diagram."""
    rule = _sample_rule().model_copy(update={"scope": RiskRuleScope.PER_ACCOUNT})
    assert rule.kill_switch_scope() is None


def test_kill_switch_scope_per_asset_group_none() -> None:
    rule = _sample_rule().model_copy(update={"scope": RiskRuleScope.PER_ASSET_GROUP})
    assert rule.kill_switch_scope() is None


# ---------------------------------------------------------------------------
# § 7 seam-diagram conformance — one per RiskRuleConsequence value
# ---------------------------------------------------------------------------


def test_seam_conformance_block_events() -> None:
    """BLOCK emits INSTRUCTION_REJECTED_RISK + RiskRuleFiredEvent per seam diagram."""
    events = CONSEQUENCE_EVENTS_EMITTED[RiskRuleConsequence.BLOCK]
    assert "INSTRUCTION_REJECTED_RISK" in events
    assert "RiskRuleFiredEvent" in events


def test_seam_conformance_scale_down_events() -> None:
    events = CONSEQUENCE_EVENTS_EMITTED[RiskRuleConsequence.SCALE_DOWN]
    assert "INSTRUCTION_ACCEPTED_PREFLIGHT" in events
    assert "RESIZED_EXECUTION" in events
    assert "RiskRuleFiredEvent" in events


def test_seam_conformance_monitor_events() -> None:
    events = CONSEQUENCE_EVENTS_EMITTED[RiskRuleConsequence.MONITOR]
    assert "INSTRUCTION_ACCEPTED_PREFLIGHT" in events
    assert "RiskRuleFiredEvent" in events
    # MONITOR is passthrough — no resize, no test-route
    assert "RESIZED_EXECUTION" not in events
    assert "ORDER_SUBMITTED" not in events


def test_seam_conformance_test_only_events() -> None:
    events = CONSEQUENCE_EVENTS_EMITTED[RiskRuleConsequence.TEST_ONLY]
    assert "INSTRUCTION_ACCEPTED_PREFLIGHT" in events
    assert "ORDER_SUBMITTED" in events
    assert "RiskRuleFiredEvent" in events


def test_seam_events_cover_full_consequence_closed_set() -> None:
    """Every RiskRuleConsequence value MUST appear in CONSEQUENCE_EVENTS_EMITTED."""
    assert set(CONSEQUENCE_EVENTS_EMITTED) == set(RiskRuleConsequence)


def test_seam_alert_codes_cover_full_consequence_closed_set() -> None:
    assert set(CONSEQUENCE_ALERT_CODES) == set(RiskRuleConsequence)


# ---------------------------------------------------------------------------
# AlertCode closed-set extension — Phase 1.E (39 → 45)
# ---------------------------------------------------------------------------


def test_new_alert_codes_resolve() -> None:
    """All 6 new codes from Phase 1.E + 1.F resolve through AlertCode."""
    assert AlertCode.RISK_RULE_BLOCKED.value == "RISK_RULE_BLOCKED"
    assert AlertCode.RISK_RULE_SCALED_DOWN.value == "RISK_RULE_SCALED_DOWN"
    assert AlertCode.RISK_RULE_MONITOR_FIRED.value == "RISK_RULE_MONITOR_FIRED"
    assert AlertCode.RISK_RULE_TEST_ONLY_ROUTED.value == "RISK_RULE_TEST_ONLY_ROUTED"
    assert AlertCode.KILL_SWITCH_AUTO_RECOVERED.value == "KILL_SWITCH_AUTO_RECOVERED"
    assert AlertCode.KILL_SWITCH_MANUAL_UNKILLED.value == "KILL_SWITCH_MANUAL_UNKILLED"


def test_consequence_alert_code_strings_resolve_to_alert_code_members() -> None:
    """CONSEQUENCE_ALERT_CODES values are valid AlertCode .value strings."""
    for consequence, code_str in CONSEQUENCE_ALERT_CODES.items():
        assert code_str in ALERT_CODES, f"{consequence}: {code_str} not in AlertCode closed-set"


def test_alert_code_set_grew_by_at_least_six() -> None:
    """Phase 1.E + 1.F together MUST add the 6 new codes — the closed-set
    grows from 39 (pre-rename baseline) to ≥45."""
    assert len(ALERT_CODES) >= 45


def test_no_pre_existing_shadowing_of_new_codes() -> None:
    """No legacy code shadows any new RISK_RULE_/KILL_SWITCH_AUTO_/_MANUAL_ name."""
    new_codes = {
        "RISK_RULE_BLOCKED",
        "RISK_RULE_SCALED_DOWN",
        "RISK_RULE_MONITOR_FIRED",
        "RISK_RULE_TEST_ONLY_ROUTED",
        "KILL_SWITCH_AUTO_RECOVERED",
        "KILL_SWITCH_MANUAL_UNKILLED",
    }
    # Each new code appears exactly once in the closed set.
    for code in new_codes:
        matching = [c for c in ALERT_CODES if c == code]
        assert len(matching) == 1, f"{code} expected exactly once, found {len(matching)}"


# ---------------------------------------------------------------------------
# Facade import — risk.py re-exports the canonical symbols
# ---------------------------------------------------------------------------


def test_facade_exports_risk_rule_symbols() -> None:
    from unified_api_contracts import risk as risk_facade

    assert hasattr(risk_facade, "RiskRule")
    assert hasattr(risk_facade, "RiskRuleId")
    assert hasattr(risk_facade, "RiskRuleScope")
    assert hasattr(risk_facade, "RiskRuleConsequence")
    assert hasattr(risk_facade, "CONSEQUENCE_EVENTS_EMITTED")
    assert hasattr(risk_facade, "CONSEQUENCE_ALERT_CODES")
    assert hasattr(risk_facade, "RiskRuleFiredEvent")
    assert hasattr(risk_facade, "risk_rule_fired_event")


# ---------------------------------------------------------------------------
# RiskRuleFiredEvent — 8-event-lifecycle entry for the risk-rule layer
# ---------------------------------------------------------------------------


def _scaled_down_rule() -> RiskRule:
    return RiskRule(
        rule_id=RiskRuleId.MAX_DRAWDOWN_PER_ARCHETYPE,
        scope=RiskRuleScope.PER_ARCHETYPE,
        applies_to="CARRY_STAKED_BASIS",
        trigger=MaxDrawdownTrigger(cap_bps=500),
        consequence=RiskRuleConsequence.SCALE_DOWN,
        alerting_severity=AlertSeverity.WARN,
        description="Per-archetype drawdown — scale down at 500 bps.",
    )


def test_risk_rule_fired_event_block_carries_kill_switch() -> None:
    from datetime import UTC, datetime

    from unified_api_contracts.risk import RiskRuleFiredEvent, risk_rule_fired_event

    rule = _sample_rule()  # BLOCK + triggers_kill_switch=True, PER_ARCHETYPE
    fired_at = datetime(2026, 5, 12, 9, 30, tzinfo=UTC)
    event = risk_rule_fired_event(rule, fired_at=fired_at, instruction_id="ord-1")

    assert isinstance(event, RiskRuleFiredEvent)
    assert event.rule_id is rule.rule_id
    assert event.scope is RiskRuleScope.PER_ARCHETYPE
    assert event.applies_to == "CARRY_STAKED_BASIS"
    assert event.consequence is RiskRuleConsequence.BLOCK
    assert event.alerting_severity is AlertSeverity.HIGH
    assert event.alert_code is AlertCode(CONSEQUENCE_ALERT_CODES[RiskRuleConsequence.BLOCK])
    assert event.fired_at == fired_at
    assert event.instruction_id == "ord-1"
    assert event.triggers_kill_switch is True
    assert event.kill_switch_scope is KillSwitchScope.ARCHETYPE


def test_risk_rule_fired_event_scale_down_no_kill_switch() -> None:
    from datetime import UTC, datetime

    from unified_api_contracts.risk import risk_rule_fired_event

    rule = _scaled_down_rule()
    event = risk_rule_fired_event(
        rule,
        fired_at=datetime(2026, 5, 12, tzinfo=UTC),
        trigger_detail={"observed": "600", "threshold": "500", "units": "bps"},
    )
    assert event.consequence is RiskRuleConsequence.SCALE_DOWN
    assert event.alert_code is AlertCode(CONSEQUENCE_ALERT_CODES[RiskRuleConsequence.SCALE_DOWN])
    assert event.triggers_kill_switch is False
    assert event.kill_switch_scope is None
    assert event.trigger_detail == {"observed": "600", "threshold": "500", "units": "bps"}


def test_risk_rule_fired_event_alert_codes_cover_all_consequences() -> None:
    from datetime import UTC, datetime

    from unified_api_contracts.risk import risk_rule_fired_event

    fired_at = datetime(2026, 5, 12, tzinfo=UTC)
    for consequence in RiskRuleConsequence:
        rule = RiskRule(
            rule_id=RiskRuleId.MAX_LEVERAGE_PER_ARCHETYPE,
            scope=RiskRuleScope.PER_ARCHETYPE,
            applies_to="CARRY_STAKED_BASIS",
            trigger=MaxLeverageTrigger(cap_ratio=Decimal("3")),
            consequence=consequence,
            alerting_severity=AlertSeverity.INFO,
            description="Per-archetype leverage cap.",
        )
        event = risk_rule_fired_event(rule, fired_at=fired_at)
        assert event.alert_code is AlertCode(CONSEQUENCE_ALERT_CODES[consequence])


def test_risk_rule_fired_event_frozen_and_extra_forbid() -> None:
    from datetime import UTC, datetime

    from unified_api_contracts.risk import RiskRuleFiredEvent, risk_rule_fired_event

    event = risk_rule_fired_event(_sample_rule(), fired_at=datetime(2026, 5, 12, tzinfo=UTC))
    with pytest.raises(ValidationError):
        event.consequence = RiskRuleConsequence.MONITOR  # type: ignore[misc]
    with pytest.raises(ValidationError):
        RiskRuleFiredEvent(  # type: ignore[call-arg]
            rule_id=RiskRuleId.MAX_LEVERAGE_PER_ARCHETYPE,
            scope=RiskRuleScope.GLOBAL,
            applies_to="*",
            consequence=RiskRuleConsequence.BLOCK,
            alerting_severity=AlertSeverity.CRITICAL,
            alert_code=AlertCode(CONSEQUENCE_ALERT_CODES[RiskRuleConsequence.BLOCK]),
            fired_at=datetime(2026, 5, 12, tzinfo=UTC),
            nonsense_field="x",
        )
