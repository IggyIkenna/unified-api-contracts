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
from unified_api_contracts.canonical.crosscutting.incident.evidence import IncidentEvidence
from unified_api_contracts.canonical.crosscutting.incident.state import IncidentState


class IncidentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_key: str
    detected_at: datetime
    severity: AlertSeverity
    state: IncidentState = IncidentState.DETECTED
    service: str
    description: str = ""
    evidence: IncidentEvidence = Field(default_factory=IncidentEvidence)
    tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("detected_at")
    @classmethod
    def _detected_at_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("detected_at must be tz-aware UTC")
        return v
