"""DeFi alert model — canonical shape for DeFi-specific alerts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.alerting.codes import AlertCode
from unified_api_contracts.canonical.crosscutting.errors.defi import DefiAlertType


class DefiAlert(BaseModel):
    """A DeFi-specific alert emitted by alerting-service DeFi rules."""

    alert_type: DefiAlertType
    severity: str = "warning"
    protocol: str | None = None
    asset: str | None = None
    message: str
    details: dict[str, str | int | float | bool] = Field(default_factory=dict)
    code: AlertCode | None = Field(
        default=None,
        description=(
            "Closed-set alert code (UAC top-level facade `AlertCode`). Optional during the producer-migration "
            "window started 2026-05-08 (Phase 3 of alerting_service_live_rules_2026_05_07.md, operator decision "
            "Option A). Producers SHOULD stamp this on every emit; legacy `alert_type` (DefiAlertType) coexists "
            "for backwards compat and will be deprecated post-cutover."
        ),
    )
