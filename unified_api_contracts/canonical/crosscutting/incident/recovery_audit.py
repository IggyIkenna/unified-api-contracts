"""RecoveryAuditSignoff — LLM Layer-1 audit verdict for every recovery action.

Written by the ``agent-orchestrator`` ``recovery-audit-signoff`` custom-role
agent (Layer-1) for every AgentActionEvent it observes. The verdict is
INFORMATIONAL — even APPROVED still requires human audit-ack within SLA per
operator HARD RULE 2026-05-23.

Codex SSOT: ``codex/04-architecture/recovery-defence-in-depth-layers.md``
§ "Layer 1".
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class SignoffVerdict(StrEnum):
    """Closed 4-set verdict from the LLM recovery-audit-signoff agent."""

    APPROVED = "APPROVED"
    """Automation was right; no operator action required beyond audit-ack."""

    APPROVED_WITH_NOTES = "APPROVED_WITH_NOTES"
    """Automation was right; notes surface in DART as info banner."""

    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    """Automation may have been right but is ambiguous; audit_ack_due_at is
    shortened to 1h regardless of severity."""

    DISPUTE_AUTOMATED_ACTION = "DISPUTE_AUTOMATED_ACTION"
    """Automation was WRONG. Gateway forces SAFE_MODE_ACTIVE + SEV0 escalation
    + invokes ``pause_strategy`` for the affected strategy with
    provenance=GATEWAY_DISPUTE."""


class RecoveryAuditSignoff(BaseModel):
    """Single signoff doc written by the LLM agent per AgentActionEvent (or
    per IncidentEnvelope for cluster-of-actions summaries).

    Persisted to GCS at
    ``gs://<kill-switch-audit>/incidents/{date}/{key}/signoffs/{event_id}.json``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    """UUID for this signoff event."""

    parent_incident_key: str
    """Stable dedup key linking to the parent IncidentEnvelope."""

    timestamp: datetime
    """tz-aware UTC."""

    agent_id: str
    """``recovery-audit-signoff`` agent identifier from agent-orchestrator."""

    verdict: SignoffVerdict

    narrative: str
    """Free-text reasoning. Operator reads this in the DART LLM Audit Verdicts
    panel to inform their audit-ack decision."""

    layer0_action_event_ids: tuple[str, ...]
    """Cross-references to the AgentActionEvent rows this signoff audited.
    Usually a single ID; may be multiple if the signoff covers a sequence."""

    evidence_links: tuple[str, ...] = ()
    """GCS URLs to evidence the LLM consulted — runbook, recent metric query,
    similar past incidents, etc."""

    recommended_next_action: str | None = None
    """Free-form operator suggestion when verdict is ESCALATE_TO_HUMAN /
    DISPUTE_AUTOMATED_ACTION."""

    confidence: Decimal | None = None
    """0..1 confidence the LLM assigns to its verdict. None when not declared."""

    llm_model: str
    """e.g. 'claude-sonnet-4-6' / 'claude-opus-4-7'."""

    llm_session_id: str
    """Opaque session identifier for re-tracing the LLM context."""

    @field_validator("timestamp")
    @classmethod
    def _timestamp_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be tz-aware UTC")
        return v

    @field_validator("confidence")
    @classmethod
    def _confidence_bounds(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError(f"confidence must be in [0, 1]; got {v}")
        return v

    @field_validator("layer0_action_event_ids")
    @classmethod
    def _at_least_one_action_id(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(v) == 0:
            raise ValueError("RecoveryAuditSignoff must reference at least 1 AgentActionEvent")
        return v
