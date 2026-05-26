"""IncidentEvidence — structured evidence URLs attached to an incident envelope."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IncidentEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_venue_api_snapshot_url: str | None = None
    internal_ledger_snapshot_url: str | None = None
    order_fill_records_url: str | None = None
    position_records_url: str | None = None
    balance_records_url: str | None = None
    logs_url: str | None = None
    metrics_url: str | None = None
    traces_url: str | None = None
    agent_action_logs_url: str | None = None
    human_acknowledgement_trail_url: str | None = None
    config_hash: str
    code_version: str
    runbook_version: str
    additional_evidence: dict[str, str] = Field(default_factory=dict)
