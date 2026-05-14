"""Alerting contracts for unified trading system."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Import AlertCode from its definition module rather than the top-level
# UAC facade — when this module loads as part of UAC __init__'s transitive
# chain (canonical_mappings → canonical/__init__.py → crosscutting/...
# → instruments_preflight_dag → internal/events → internal/alerting/...),
# the top-level facade hasn't yet bound AlertCode (line 26 in __init__.py
# imports alerting AFTER this chain triggers). Direct module import is
# circular-safe.
from unified_api_contracts.canonical.crosscutting.alerting.codes import AlertCode
from unified_api_contracts.internal.alerting.alerts import DefiAlert


class AlertEvent(BaseModel):
    """A fired alert event emitted by the alerting service."""

    alert_id: str = Field(description="Unique identifier for this alert event")
    rule_id: str = Field(description="ID of the alert rule that fired")
    triggered_at: datetime = Field(description="UTC timestamp when alert was triggered")
    severity: Literal["DEBUG", "INFO", "WARNING", "CRITICAL", "FATAL"] = Field(
        description="Severity level of the alert"
    )
    message: str = Field(description="Human-readable alert message")
    metric_value: float = Field(description="Current value of the monitored metric")
    threshold: float = Field(description="Threshold value that was breached")
    strategy_id: str | None = Field(default=None, description="Strategy that triggered the alert, if applicable")
    venue: str | None = Field(default=None, description="Trading venue, if applicable")
    code: AlertCode | None = Field(
        default=None,
        description=(
            "Closed-set alert code (UAC top-level facade `AlertCode`). Optional during the producer-migration "
            "window started 2026-05-08 (Phase 3 of alerting_service_live_rules_2026_05_07.md, operator decision "
            "Option A). Producers SHOULD stamp this on every emit; alerting-service rule-matching prefers `code` "
            "when present and falls back to `rule_id` regex when absent. Will become required post-cutover."
        ),
    )


class GovernanceForumProposal(BaseModel):
    """A governance forum proposal detected by the forum watcher (D.7).

    Produced by alerting-service ``governance_forum_watcher`` when a proposal
    on Snapshot.org or Tally matches depeg-risk keywords.  Distinct from
    ``unified_api_contracts.internal.domain.defi.GovernanceProposal`` which
    captures on-chain governance contract events for simulation.

    SSOT: ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` Phase D.7.
    """

    model_config = ConfigDict(frozen=True)

    forum: str = Field(description="Forum source: 'Snapshot' or 'Tally'")
    proposal_id: str = Field(description="Unique proposal identifier from the forum")
    title: str = Field(description="Proposal title")
    tags: list[str] = Field(description="Matched risk keywords")
    posted_at: datetime = Field(description="UTC timestamp when proposal was posted")
    url: str = Field(description="Canonical URL of the proposal")
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Correlation ID for tracing alert emissions",
    )

    def to_alert_payload(self) -> dict[str, object]:
        """Serialize to alert event payload dict."""
        return {
            "event_name": AlertCode.GOVERNANCE_INCIDENT_DETECTED.value,
            "forum": self.forum,
            "proposal_id": self.proposal_id,
            "title": self.title,
            "tags": self.tags,
            "posted_at": self.posted_at.isoformat(),
            "url": self.url,
            "correlation_id": self.correlation_id,
        }


class IssuePauseEvent(BaseModel):
    """A detected stablecoin issuer-pause event, ready to emit as an alert (D.5).

    Produced by alerting-service ``stablecoin_issuer_pause_subscriber`` when
    Circle, Tether, or MakerDAO signals a redemption halt or PSM cage event.

    SSOT: ``plans/active/risk_simulations_limits_alerting_2026_05_10.md`` Phase D.5.
    """

    model_config = ConfigDict(frozen=True)

    stable: str = Field(description="Stablecoin ticker: 'USDC', 'USDT', or 'DAI'")
    issuer: str = Field(description="Issuer name: 'Circle', 'Tether', or 'MakerDAO'")
    paused_at: datetime = Field(description="UTC timestamp of detected pause")
    source_url: str = Field(description="URL of the source that indicated the pause")
    reason: str = Field(description="Human-readable description of the halt signal")
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Correlation ID for tracing alert emissions",
    )

    def to_alert_payload(self) -> dict[str, object]:
        """Serialize to alert event payload dict."""
        return {
            "event_name": AlertCode.STABLECOIN_ISSUER_PAUSED.value,
            "stable": self.stable,
            "issuer": self.issuer,
            "paused_at": self.paused_at.isoformat(),
            "source_url": self.source_url,
            "reason": self.reason,
            "correlation_id": self.correlation_id,
        }


__all__ = [
    "AlertEvent",
    "DefiAlert",
    "GovernanceForumProposal",
    "IssuePauseEvent",
]
