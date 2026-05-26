"""IncidentEnvelope — central schema ingested by the alerting-service Incident Gateway.

Mirrors the target operating model §14.1 from
``plans/active/issues/disaster_recovery.md``. Every emitter (Layer-0 scripts,
LLM agent, manual operator action, detector trigger) wraps its event in this
envelope; the gateway dedupes by ``incident_key`` and drives state transitions.

Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity
from unified_api_contracts.canonical.crosscutting.incident.state import IncidentState


class IncidentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # ── Identity ───────────────────────────────────────────────────────────
    event_id: str
    incident_key: str
    timestamp: datetime
    state: IncidentState = IncidentState.DETECTED

    # ── Context ────────────────────────────────────────────────────────────
    environment: str
    severity_hint: AlertSeverity
    domain: str
    service: str
    component: str
    problem_type: str
    problem_summary: str
    config_hash: str
    code_version: str

    # ── Optional scoping ───────────────────────────────────────────────────
    strategy_id: str | None = None
    venue: str | None = None
    account_id: str | None = None
    instrument_id: str | None = None
    runbook_id: str | None = None

    # ── Risk context ───────────────────────────────────────────────────────
    risk_state: str = "unknown"
    """Closed-set values: 'safe' / 'protected_mode' / 'unknown' / 'live_unresolved'."""
    capital_at_risk: float | None = None
    auto_action_allowed: bool = False
    recovery_confirmed: bool = False
    """Set to True only after RECOVERY_CONFIRMED state transition."""

    # ── Audit-ack / SLA ────────────────────────────────────────────────────
    human_audit_ack_required: bool = True
    human_operational_ack_required: bool = False
    audit_ack_due_at: datetime | None = None
    audit_acked_by: str | None = None
    audit_acked_at: datetime | None = None
    operational_acked_by: str | None = None
    operational_acked_at: datetime | None = None
    audit_ack_escalation_history: tuple[dict[str, str], ...] = ()

    @field_validator("timestamp")
    @classmethod
    def _timestamp_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be tz-aware UTC")
        return v

    @field_validator("environment")
    @classmethod
    def _environment_closed_set(cls, v: str) -> str:
        if v not in ("prod", "staging", "dev"):
            raise ValueError(f"environment must be prod|staging|dev; got {v!r}")
        return v

    @field_validator("risk_state")
    @classmethod
    def _risk_state_closed_set(cls, v: str) -> str:
        if v not in ("safe", "protected_mode", "unknown", "live_unresolved"):
            raise ValueError(f"risk_state must be safe|protected_mode|unknown|live_unresolved; got {v!r}")
        return v
