"""IncidentEnvelope — central schema ingested by the alerting-service Incident Gateway.

Mirrors the target operating model §14.1 from
``plans/active/issues/disaster_recovery.md``. Every emitter (Layer-0 scripts,
LLM agent, manual operator action, detector trigger) wraps its event in this
envelope; the gateway dedupes by ``incident_key`` and drives state transitions.

Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from unified_api_contracts.canonical.crosscutting.alerting import AlertSeverity
from unified_api_contracts.canonical.crosscutting.incident.evidence import (
    IncidentEvidence,
)
from unified_api_contracts.canonical.crosscutting.incident.state import IncidentState


class IncidentEnvelope(BaseModel):
    """Central incident schema.

    Snapshotted at each state transition (envelope is FROZEN; transitions
    create a new envelope with updated ``state`` + relevant fields). The
    Incident Gateway persists the full sequence of envelope snapshots to
    GCS at ``incidents/{YYYY-MM-DD}/{incident_key}/snapshots/{event_id}.json``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ── Identity + lifecycle
    event_id: str
    """UUID unique per snapshot — every state transition writes a new event_id."""

    incident_key: str
    """Stable dedup hash over (service, component, problem_type, strategy_id,
    venue, instrument_id). Same root cause across N retries = 1 incident."""

    timestamp: datetime
    """tz-aware UTC of this snapshot."""

    state: IncidentState
    """Current lifecycle state. See state.py ALLOWED_TRANSITIONS."""

    # ── Environment + provenance
    environment: str
    """e.g. 'prod' / 'staging' / 'dev'."""

    severity_hint: AlertSeverity
    """Initial guess from the emitter. Gateway may override via
    ImmediateSev0Override evaluation OR via LLM DISPUTE_AUTOMATED_ACTION."""

    domain: str
    """e.g. 'live_trading' / 'batch' / 'reference_data' / 'observability'."""

    service: str
    """Source service — e.g. 'execution-service', 'mtds', 'strategy-service'."""

    component: str
    """Source component path within the service."""

    # ── Scope (any subset of these may be set)
    strategy_id: str | None = None
    strategy_family: str | None = None
    venue: str | None = None
    account_id: str | None = None
    instrument_id: str | None = None

    # ── Problem description
    problem_type: str
    """Closed-set fnmatch pattern used by routing rules. e.g.
    'OOM_DETECTED', 'POSITION_DRIFT_CRITICAL', 'LIQUIDATION_EVENT_DETECTED'."""

    problem_summary: str
    """One-line human-readable description."""

    # ── Risk state (populated by Incident Gateway evaluation)
    risk_state: str = "unknown"
    """Closed-set values: 'safe' / 'protected_mode' / 'unknown' /
    'live_unresolved'."""

    capital_at_risk: bool = False
    """True if there is exposure that could lose value in current state."""

    # ── Action authorization
    auto_action_allowed: bool = True
    """False blocks all Layer-0 + Layer-1.5 attempts; only operator manual
    actions allowed."""

    auto_action_taken: str | None = None
    """ActionType value if any Layer-0 action has fired; None otherwise."""

    recovery_confirmed: bool = False
    """Set to True only after RECOVERY_CONFIRMED state transition. Forbidden
    to set True before then — would bypass the 5-tuple verification gate."""

    # ── Human ack tracking
    human_operational_ack_required: bool = True
    """If True, operator must indicate ownership via OperationalAckButton
    before incident can reach AUDIT_REPORT_GENERATED."""

    human_audit_ack_required: bool = True
    """If True, audit-ack queue holds the incident until operator clicks
    AuditAckButton. Default True for all material incidents."""

    operational_acked_by: str | None = None
    operational_acked_at: datetime | None = None
    audit_acked_by: str | None = None
    audit_acked_at: datetime | None = None
    """Distinct ack timestamps. Operational ack does NOT transition state;
    audit ack transitions to HUMAN_AUDIT_ACKED. See
    ``codex/15-runbooks/alerting/audit-acknowledgement-flow.md``."""

    audit_ack_due_at: datetime | None = None
    """SLA deadline. Populated at AUDIT_REPORT_GENERATED transition based on
    AuditAckSLAPolicy lookup by severity."""

    # ── Operator support
    runbook_id: str | None = None
    """e.g. 'RB-INFRA-001'. Surfaces in DART for operator."""

    dashboard_url: str | None = None
    logs_url: str | None = None
    kill_switch_url: str | None = None

    # ── Reproducibility (MANDATORY at AUDIT_REPORT_GENERATED)
    config_hash: str
    code_version: str

    # ── Evidence (populated at AUDIT_REPORT_GENERATED)
    evidence: IncidentEvidence | None = None

    # ── Audit-ack escalation history (append-only)
    audit_ack_escalation_history: tuple[dict[str, str], ...] = Field(default=())
    """Each entry: {'timestamp', 'escalation_step', 'target', 'channel',
    'delivery_status'}."""

    @field_validator("timestamp", "audit_ack_due_at", "operational_acked_at", "audit_acked_at")
    @classmethod
    def _datetimes_tz_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("datetime fields must be tz-aware UTC")
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
