"""RecoveryAuditSignoff — LLM-produced sign-off on a recovery sequence."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class SignoffVerdict(StrEnum):
    """Closed 4-set verdict from the LLM recovery-audit-signoff agent."""

    APPROVED = "APPROVED"
    APPROVED_WITH_NOTES = "APPROVED_WITH_NOTES"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    DISPUTE_AUTOMATED_ACTION = "DISPUTE_AUTOMATED_ACTION"


class RecoveryAuditSignoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    parent_incident_key: str
    timestamp: datetime
    agent_id: str
    verdict: SignoffVerdict
    narrative: str
    layer0_action_event_ids: tuple[str, ...]
    evidence_links: tuple[str, ...] = ()
    recommended_next_action: str | None = None
    confidence: Decimal | None = None
    llm_model: str = ""
    llm_session_id: str = ""

    @field_validator("timestamp")
    @classmethod
    def _timestamp_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be tz-aware UTC")
        return v

    @field_validator("confidence")
    @classmethod
    def _confidence_bounds(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError(f"confidence must be in [0, 1]; got {v}")
        return v

    @field_validator("layer0_action_event_ids")
    @classmethod
    def _at_least_one_action_id(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(v) == 0:
            raise ValueError("RecoveryAuditSignoff must reference at least 1 AgentActionEvent")
        return v
