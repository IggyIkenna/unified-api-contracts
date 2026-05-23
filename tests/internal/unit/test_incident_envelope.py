"""Closed-set sanity tests for the UAC incident schemas.

Phase 1 of ``plans/active/incident_gateway_and_state_machine_2026_05_23.md``
+ Phase 1 of ``plans/active/ai_recovery_audit_signoff_agent_2026_05_23.md``
+ Phase 1 of ``plans/active/audit_acknowledgement_sla_and_state_2026_05_23.md``.

Enforces:

1. IncidentState has exactly 13 closed-set members.
2. ALLOWED_TRANSITIONS rejects ``AUTO_ACTION_SUCCEEDED → RESOLVED`` (central invariant).
3. ImmediateSev0Override is exactly 7 members.
4. ActionType is exactly 10 members.
5. SignoffVerdict is exactly 4 members.
6. RecoveryVerificationResult.all_passed() requires all 5 True.
7. AuditAckSLAPolicy is monotonic + lookup_sla(severity) closed-set.
8. IncidentEnvelope datetime fields reject naive datetime.
9. ``recovery_confirmed`` defaults to False on a fresh envelope.
10. ``audit_ack_due_at`` is None until set explicitly.
11. AlertChannel taxonomy includes the 3 new channels (TWILIO_VOICE/SMS, PHYSICAL_PAGER).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.alerting import AlertChannel, AlertSeverity
from unified_api_contracts.incident import (
    ALLOWED_TRANSITIONS,
    LIVE_AUDIT_ACK_POLICIES,
    ActionProvenance,
    ActionStatus,
    ActionType,
    AgentActionEvent,
    AuditAckSLAPolicy,
    IllegalIncidentTransitionError,
    ImmediateSev0Override,
    IncidentEnvelope,
    IncidentEvidence,
    IncidentState,
    RecoveryAuditSignoff,
    RecoveryVerificationResult,
    SignoffVerdict,
    assert_allowed_transition,
    lookup_sla,
)


# ---------------------------------------------------------------------------
# Closed-set sanity
# ---------------------------------------------------------------------------


def test_incident_state_has_14_members() -> None:
    """14 states per target model `disaster_recovery.md` §6.3.

    DETECTED / AUTO_ACTION_STARTED / AUTO_ACTION_SUCCEEDED / AUTO_ACTION_FAILED /
    RECOVERY_VERIFICATION_STARTED / RECOVERY_CONFIRMED / RECOVERY_UNCERTAIN /
    SAFE_MODE_ACTIVE / HUMAN_OPERATIONAL_ACKED / AUDIT_REPORT_GENERATED /
    HUMAN_AUDIT_ACKED / ESCALATED / RESOLVED / CLOSED.

    (Earlier prose called this "13-state" — that was a typo in the audit doc.
    The state machine has always had 14 named states.)
    """
    assert len(list(IncidentState)) == 14


def test_immediate_sev0_override_has_7_members() -> None:
    assert len(list(ImmediateSev0Override)) == 7


def test_action_type_has_10_members() -> None:
    """10 Layer-0 deterministic recovery actions per
    `plans/active/agent_recovery_controller_layer0_deterministic_2026_05_23.md`."""
    assert len(list(ActionType)) == 10


def test_signoff_verdict_has_4_members() -> None:
    verdicts = {v for v in SignoffVerdict}
    assert verdicts == {
        SignoffVerdict.APPROVED,
        SignoffVerdict.APPROVED_WITH_NOTES,
        SignoffVerdict.ESCALATE_TO_HUMAN,
        SignoffVerdict.DISPUTE_AUTOMATED_ACTION,
    }


def test_action_status_includes_blocked_by_loop_detector() -> None:
    """Layer-0 scripts MUST surface RepeatedRepairLoopDetector verdict."""
    assert ActionStatus.BLOCKED_BY_LOOP_DETECTOR in ActionStatus
    assert ActionStatus.DRY_RUN in ActionStatus


def test_action_provenance_5_set() -> None:
    """5-set: AUTOMATIC / MANUAL_OPERATOR / LLM_LAYER15 / GATEWAY_DISPUTE / BREAKER_AUTO."""
    provs = {p for p in ActionProvenance}
    assert provs == {
        ActionProvenance.AUTOMATIC,
        ActionProvenance.MANUAL_OPERATOR,
        ActionProvenance.LLM_LAYER15,
        ActionProvenance.GATEWAY_DISPUTE,
        ActionProvenance.BREAKER_AUTO,
    }


# ---------------------------------------------------------------------------
# Central invariant: AUTO_ACTION_SUCCEEDED ≠ RESOLVED
# ---------------------------------------------------------------------------


def test_auto_action_succeeded_cannot_transition_directly_to_resolved() -> None:
    """The central invariant from the operator's target operating model.

    Recovery must be verified before the incident closes.
    """
    assert IncidentState.RESOLVED not in ALLOWED_TRANSITIONS[IncidentState.AUTO_ACTION_SUCCEEDED]


def test_auto_action_succeeded_transitions_only_to_recovery_verification_started() -> None:
    assert ALLOWED_TRANSITIONS[IncidentState.AUTO_ACTION_SUCCEEDED] == frozenset(
        {IncidentState.RECOVERY_VERIFICATION_STARTED}
    )


def test_assert_allowed_transition_raises_on_forbidden_jump() -> None:
    with pytest.raises(IllegalIncidentTransitionError):
        assert_allowed_transition(
            IncidentState.AUTO_ACTION_SUCCEEDED, IncidentState.RESOLVED
        )


def test_assert_allowed_transition_passes_on_valid() -> None:
    assert_allowed_transition(
        IncidentState.AUTO_ACTION_SUCCEEDED,
        IncidentState.RECOVERY_VERIFICATION_STARTED,
    )


def test_closed_is_terminal() -> None:
    assert ALLOWED_TRANSITIONS[IncidentState.CLOSED] == frozenset()


def test_every_state_has_a_transition_entry() -> None:
    """Every state name appears as a key in ALLOWED_TRANSITIONS (even if terminal)."""
    for state in IncidentState:
        assert state in ALLOWED_TRANSITIONS


# ---------------------------------------------------------------------------
# RecoveryVerificationResult
# ---------------------------------------------------------------------------


def test_recovery_verification_all_passed_requires_all_5_true() -> None:
    rv = RecoveryVerificationResult(
        health_checks_passed=True,
        positions_reconciled=True,
        orders_reconciled=True,
        market_data_fresh=True,
        strategy_state_restored=True,
    )
    assert rv.all_passed() is True


def test_recovery_verification_any_false_fails_all_passed() -> None:
    rv = RecoveryVerificationResult(
        health_checks_passed=True,
        positions_reconciled=False,
        orders_reconciled=True,
        market_data_fresh=True,
        strategy_state_restored=True,
    )
    assert rv.all_passed() is False


# ---------------------------------------------------------------------------
# AuditAckSLAPolicy + lookup_sla
# ---------------------------------------------------------------------------


def test_lookup_sla_covers_all_4_severities() -> None:
    for sev in (
        AlertSeverity.CRITICAL,
        AlertSeverity.HIGH,
        AlertSeverity.WARN,
        AlertSeverity.INFO,
    ):
        lookup_sla(sev)


def test_sla_critical_has_5min_default() -> None:
    p = lookup_sla(AlertSeverity.CRITICAL)
    assert p.default_seconds == 300


def test_sla_info_has_no_enforcement() -> None:
    p = lookup_sla(AlertSeverity.INFO)
    assert p.default_seconds is None
    assert p.secondary_human_after_seconds is None
    assert p.founder_after_seconds is None


def test_sla_warn_no_physical_pager() -> None:
    p = lookup_sla(AlertSeverity.WARN)
    assert p.physical_pager_after_seconds is None


def test_sla_monotonic_ladder_enforced() -> None:
    """Non-monotonic policy rejected at construct time."""
    with pytest.raises(ValidationError):
        AuditAckSLAPolicy(
            severity=AlertSeverity.HIGH,
            default_seconds=7200,
            secondary_human_after_seconds=3600,  # < default — violation
            founder_after_seconds=21600,
        )


def test_live_audit_ack_policies_is_4_tuple() -> None:
    assert len(LIVE_AUDIT_ACK_POLICIES) == 4


# ---------------------------------------------------------------------------
# IncidentEnvelope construct-time validators
# ---------------------------------------------------------------------------


def _minimal_envelope(**overrides: object) -> IncidentEnvelope:
    defaults: dict[str, object] = {
        "event_id": "evt-1",
        "incident_key": "key-1",
        "timestamp": datetime.now(UTC),
        "state": IncidentState.DETECTED,
        "environment": "prod",
        "severity_hint": AlertSeverity.HIGH,
        "domain": "live_trading",
        "service": "execution-service",
        "component": "order-router",
        "problem_type": "OOM_DETECTED",
        "problem_summary": "Service OOM",
        "config_hash": "sha256:abc",
        "code_version": "v1.0.0",
    }
    defaults.update(overrides)
    return IncidentEnvelope(**defaults)  # type: ignore[arg-type]


def test_envelope_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        _minimal_envelope(timestamp=datetime.now())  # naive


def test_envelope_rejects_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        _minimal_envelope(environment="qa")  # not in {prod, staging, dev}


def test_envelope_rejects_unknown_risk_state() -> None:
    with pytest.raises(ValidationError):
        _minimal_envelope(risk_state="risky")  # not in closed set


def test_envelope_defaults_recovery_confirmed_to_false() -> None:
    env = _minimal_envelope()
    assert env.recovery_confirmed is False
    assert env.audit_ack_due_at is None


def test_envelope_defaults_human_audit_ack_required_to_true() -> None:
    env = _minimal_envelope()
    assert env.human_audit_ack_required is True


# ---------------------------------------------------------------------------
# AgentActionEvent
# ---------------------------------------------------------------------------


def test_action_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        AgentActionEvent(
            event_id="a-1",
            parent_incident_key="i-1",
            timestamp=datetime.now(),  # naive
            agent_id="agent-recovery-controller",
            action_type=ActionType.RESTART_SERVICE,
            action_status=ActionStatus.STARTED,
            provenance=ActionProvenance.AUTOMATIC,
            runbook_id="RB-INFRA-001",
            config_hash="sha:abc",
            code_version="v1",
        )


def test_action_event_rejects_bad_runbook_id() -> None:
    with pytest.raises(ValidationError):
        AgentActionEvent(
            event_id="a-1",
            parent_incident_key="i-1",
            timestamp=datetime.now(UTC),
            agent_id="agent-recovery-controller",
            action_type=ActionType.RESTART_SERVICE,
            action_status=ActionStatus.STARTED,
            provenance=ActionProvenance.AUTOMATIC,
            runbook_id="RUNBOOK-001",  # missing RB- prefix
            config_hash="sha:abc",
            code_version="v1",
        )


# ---------------------------------------------------------------------------
# RecoveryAuditSignoff
# ---------------------------------------------------------------------------


def _signoff(**overrides: object) -> RecoveryAuditSignoff:
    defaults: dict[str, object] = {
        "event_id": "s-1",
        "parent_incident_key": "i-1",
        "timestamp": datetime.now(UTC),
        "agent_id": "recovery-audit-signoff",
        "verdict": SignoffVerdict.APPROVED,
        "narrative": "Layer-0 restart succeeded; positions reconciled.",
        "layer0_action_event_ids": ("a-1",),
        "llm_model": "claude-sonnet-4-6",
        "llm_session_id": "sess-1",
    }
    defaults.update(overrides)
    return RecoveryAuditSignoff(**defaults)  # type: ignore[arg-type]


def test_signoff_requires_at_least_one_action_id() -> None:
    with pytest.raises(ValidationError):
        _signoff(layer0_action_event_ids=())


def test_signoff_confidence_bounds() -> None:
    _signoff(confidence=Decimal("0.95"))  # OK
    _signoff(confidence=Decimal("0"))  # OK
    _signoff(confidence=Decimal("1"))  # OK
    _signoff(confidence=None)  # OK
    with pytest.raises(ValidationError):
        _signoff(confidence=Decimal("1.5"))


def test_signoff_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        _signoff(timestamp=datetime.now())


# ---------------------------------------------------------------------------
# AlertChannel — 3 new channels (TWILIO_VOICE / TWILIO_SMS / PHYSICAL_PAGER)
# ---------------------------------------------------------------------------


def test_alert_channel_has_new_layer3_layer4_channels() -> None:
    """3 new channels added 2026-05-23 for Layer-3 + Layer-4 escalation."""
    assert AlertChannel.TWILIO_VOICE in AlertChannel
    assert AlertChannel.TWILIO_SMS in AlertChannel
    assert AlertChannel.PHYSICAL_PAGER in AlertChannel
    assert AlertChannel.TWILIO_VOICE.value == "twilio_voice"
    assert AlertChannel.TWILIO_SMS.value == "twilio_sms"
    assert AlertChannel.PHYSICAL_PAGER.value == "physical_pager"


def test_alert_channel_has_minimum_8_members() -> None:
    """5 original + 3 new = 8."""
    assert len(list(AlertChannel)) >= 8


# ---------------------------------------------------------------------------
# IncidentEvidence
# ---------------------------------------------------------------------------


def test_incident_evidence_requires_only_3_reproducibility_fields() -> None:
    """All URL fields optional; only config_hash + code_version + runbook_version required."""
    e = IncidentEvidence(
        config_hash="sha256:abc",
        code_version="v1.0.0",
        runbook_version="codex-sha-def",
    )
    assert e.config_hash == "sha256:abc"
    assert e.additional_evidence == {}


def test_incident_evidence_missing_runbook_version_raises() -> None:
    with pytest.raises(ValidationError):
        IncidentEvidence(
            config_hash="sha256:abc",
            code_version="v1.0.0",
            # runbook_version missing
        )
