"""Alerting contracts for unified trading system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from unified_api_contracts import AlertCode
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


__all__ = [
    "AlertEvent",
    "DefiAlert",
]
