"""IncidentEvidence — 14 fields linked from every material IncidentEnvelope.

Populated by ``alerting-service/alerting_service/gateway/evidence_collector.py``
at the AUDIT_REPORT_GENERATED state transition. The collector triggers
per-service evidence-capture endpoints; each service exposes
``/evidence/{incident_key}`` which writes a snapshot to GCS at
``incidents/{date}/{key}/evidence/<type>.json``.

Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md`` §
"IncidentEvidence". Implementation plan:
``plans/active/incident_runbooks_and_evidence_store_2026_05_23.md``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IncidentEvidence(BaseModel):
    """14-field evidence bundle per material incident.

    Every field is optional individually (some incidents have no order-flow
    relevance, etc) but at minimum ``config_hash`` + ``code_version`` +
    ``runbook_version`` MUST be populated for any incident reaching
    AUDIT_REPORT_GENERATED.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_venue_api_snapshot_url: str | None = None
    """GCS URL to JSONL of venue REST API responses at incident time."""

    internal_ledger_snapshot_url: str | None = None
    """GCS URL to JSONL of internal ledger rows at incident time."""

    order_fill_records_url: str | None = None
    """GCS URL to JSONL of order + fill rows for the affected (venue, strategy,
    instrument) scope."""

    position_records_url: str | None = None
    """GCS URL to JSONL of position rows."""

    balance_records_url: str | None = None
    """GCS URL to JSONL of balance + transfer + funding rows."""

    logs_url: str | None = None
    """Cloud Logging filter URL covering the incident time window."""

    metrics_url: str | None = None
    """Prometheus / Grafana dashboard URL for the incident."""

    traces_url: str | None = None
    """OpenTelemetry / Cloud Trace URL where available."""

    agent_action_logs_url: str | None = None
    """GCS URL to the directory of AgentActionEvent JSON files for the parent
    incident_key."""

    config_hash: str
    """git rev-parse HEAD of unified-trading-pm + service repo at incident time."""

    code_version: str
    """Image digest of the running container OR git sha for VM-hosted services."""

    runbook_version: str
    """git sha of ``codex/15-runbooks/incidents/<runbook_id>.md`` at incident
    time. Lets retro-investigators see exactly which runbook the operator was
    expected to follow."""

    human_acknowledgement_trail_url: str | None = None
    """GCS URL to JSONL of ack events (operational_ack + audit_ack +
    escalation_history rows)."""

    additional_evidence: dict[str, str] = Field(default_factory=dict)
    """Free-form key→URL map for incident-specific evidence not covered above."""
