"""Inter-service domain event schemas — wire format for Pub/Sub + GCS replay.

Distinct from :mod:`unified_api_contracts.internal.events` which holds **lifecycle**
events (STARTED / FAILED / etc.). This module owns the **domain** events that
services emit to each other to coordinate state: position changes, fills, margin
breaches, risk events, kill-switches, P&L points.

Per audit P1.1 + P1.0b (workspace audit 2026-05-01): the gap was that risk-event,
fill-event, liquidation-alert, position-snapshot, margin-event wire formats lived
as service-local assumptions instead of in UAC. This module fixes that.

Every domain event inherits from :class:`EventEnvelope` so the receiver always
sees ``event_id``, ``run_id``, ``correlation_id``, ``causation_id``, and
``schema_version`` regardless of payload type. That gives reconciliation +
overnight cascade debugging a stable lineage chain.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from unified_api_contracts.internal.modes import LogLevel
from unified_api_contracts.internal.risk import (
    AlertContextData,
    AlertType,
    Balance,
    InternalPosition,
    MarginHealthSnapshot,
    PnLAttributionRecord,
)

# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


class EventEnvelope(BaseModel):
    """Base envelope every inter-service domain event inherits.

    Lineage chain: ``run_id`` groups everything for one orchestration run;
    ``scenario_id`` groups events fired by an overnight test scenario;
    ``correlation_id`` chains a single business action across services;
    ``causation_id`` points back to the parent event in the chain.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique per emission.")
    event_type: str = Field(description="Discriminator. Subclasses set ``Literal``.")
    schema_version: str = Field(default="1", description="Bump on breaking change.")
    run_id: str = Field(description="Orchestration run id (batch run, live shard, scenario).")
    scenario_id: str | None = Field(
        default=None,
        description="Overnight test scenario id, if any.",
    )
    strategy_id: str | None = None
    client_id: str | None = Field(default=None, json_schema_extra={"pii": True})
    instrument_id: str | None = None
    venue_id: str | None = None
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Same id across the full request chain.",
    )
    causation_id: str | None = Field(
        default=None,
        description="event_id of the event that caused this one (parent in chain).",
    )
    created_at: datetime
    severity: LogLevel = LogLevel.INFO


# ---------------------------------------------------------------------------
# Margin / liquidation
# ---------------------------------------------------------------------------


class MarginEventSeverity(StrEnum):
    """Severity ladder for ``MarginEvent``. Maps to alerting routing."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    LIQUIDATION = "liquidation"


class MarginEvent(EventEnvelope):
    """Emitted by position-balance-monitor whenever margin/HF crosses a threshold.

    Single canonical producer: strategy-service/position. Consumers:
    alerting-service (route by severity), strategy-service (kill-switch guard),
    execution-service (deleverage executor on critical/liquidation),
    strategy-service/risk (time-series logging),
    strategy-service/pnl (liquidation attribution).
    """

    event_type: Literal["MarginEvent"] = Field(default="MarginEvent", description="Event discriminator")
    margin_severity: MarginEventSeverity
    snapshot: MarginHealthSnapshot
    threshold_breached: str = Field(
        description="Threshold that fired (e.g. 'health_factor<warning')",
    )
    distance_to_liquidation_pct: Decimal | None = None
    recommended_action: str | None = Field(
        default=None,
        description="One-line operator hint (e.g. 'top up collateral', 'reduce position 25%').",
    )


class LiquidationAlert(EventEnvelope):
    """Emitted when an actual liquidation event occurred (post-fact).

    Distinct from ``MarginEvent`` (forward-looking warning). Consumed by
    strategy-service/pnl for liquidation P&L attribution and by
    alerting-service for incident routing.
    """

    event_type: Literal["LiquidationAlert"] = Field(default="LiquidationAlert", description="Event discriminator")
    venue_id: str | None = None
    protocol: str
    instrument_liquidated: str
    quantity_liquidated: Decimal
    liquidation_price: Decimal
    realized_loss_usd: Decimal
    liquidator_address: str | None = None
    tx_hash: str | None = None


# ---------------------------------------------------------------------------
# Position / balance / fill
# ---------------------------------------------------------------------------


class PositionSnapshotEvent(EventEnvelope):
    """Per-account position snapshot. Emitted by PBM after each material change."""

    event_type: Literal["PositionSnapshotEvent"] = Field(
        default="PositionSnapshotEvent", description="Event discriminator"
    )
    account_id: str = Field(json_schema_extra={"pii": True})
    venue_id: str | None = None
    positions: list[InternalPosition] = Field(default_factory=list)


class BalanceSnapshot(EventEnvelope):
    """Per-account balance snapshot. Emitted by PBM."""

    event_type: Literal["BalanceSnapshot"] = Field(default="BalanceSnapshot", description="Event discriminator")
    account_id: str = Field(json_schema_extra={"pii": True})
    venue_id: str | None = None
    balances: dict[str, Balance] = Field(default_factory=dict)


class FillEvent(EventEnvelope):
    """Trade fill emitted by execution-service after each venue confirmation.

    In batch mode the fill comes from the matching engine simulator; in live
    mode it comes from the venue. Consumers cannot tell the difference — that's
    the batch=live invariant. The ``fill_source`` discriminator records which
    path produced this fill for reconciliation purposes only.
    """

    event_type: Literal["FillEvent"] = Field(default="FillEvent", description="Event discriminator")
    instrument_id: str | None = None
    venue_id: str | None = None
    side: str
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")
    fill_source: Literal["matching_engine", "live_venue"] = "live_venue"
    venue_response_id: str | None = None
    client_order_id: str | None = None


class OrderSubmitted(EventEnvelope):
    """Order submission acknowledged by the venue (or matching engine in batch)."""

    event_type: Literal["OrderSubmitted"] = Field(default="OrderSubmitted", description="Event discriminator")
    client_order_id: str
    venue_order_id: str | None = None
    instrument_id: str | None = None
    venue_id: str | None = None
    side: str
    quantity: Decimal
    submitted_price: Decimal | None = None


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


class PriceSnapshot(EventEnvelope):
    """Mark-price snapshot. Emitted by market-tick-data-service feeders."""

    event_type: Literal["PriceSnapshot"] = Field(default="PriceSnapshot", description="Event discriminator")
    instrument_id: str
    mark_price: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    venue_id: str | None = None


# ---------------------------------------------------------------------------
# Risk / kill-switch
# ---------------------------------------------------------------------------


class RiskEvent(EventEnvelope):
    """Risk threshold breach. Emitted by strategy-service/risk."""

    event_type: Literal["RiskEvent"] = Field(default="RiskEvent", description="Event discriminator")
    alert_type: AlertType
    metric: str
    current_value: Decimal
    threshold: Decimal
    context: AlertContextData | None = None


class KillSwitchTrigger(EventEnvelope):
    """Kill switch fired. Consumed by execution (drain), strategy (pause),
    alerting (route to incident channels)."""

    event_type: Literal["KillSwitchTrigger"] = Field(default="KillSwitchTrigger", description="Event discriminator")
    reason: str
    triggered_by: str = Field(description="company | client | account | strategy id")
    scope: dict[str, str] = Field(
        default_factory=dict,
        description="entity_type/entity_id/strategy_type/venue/instrument scoping.",
    )
    auto_deactivate_at: datetime | None = None


class DeleverageActionSubmitted(EventEnvelope):
    """Deleverage executor submitted a margin-restore action.

    Emitted by execution-service in response to ``MarginEvent`` of severity
    ``critical`` or ``liquidation``. Same code path batch=live; in batch, the
    matching engine simulates the action's fill.
    """

    event_type: Literal["DeleverageActionSubmitted"] = Field(
        default="DeleverageActionSubmitted", description="Event discriminator"
    )
    margin_event_id: str = Field(description="Caused-by event_id (causation chain).")
    action_kind: Literal[
        "topup_collateral",
        "repay_debt",
        "close_most_risky_leg",
        "unwind_to_maintenance_margin",
        "cap_new_exposure",
    ]
    target_instrument_id: str
    target_quantity: Decimal | None = None


# ---------------------------------------------------------------------------
# P&L
# ---------------------------------------------------------------------------


class PnLPoint(EventEnvelope):
    """Single point on the strategy/account P&L time-series.

    Emitted by PBM (the ledger owner). Consumed by pnl-attribution for alpha
    decomposition and by alerting for drawdown rules.
    """

    event_type: Literal["PnLPoint"] = Field(default="PnLPoint", description="Event discriminator")
    account_id: str = Field(json_schema_extra={"pii": True})
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    drawdown_pct: Decimal | None = None


class PnLAttributionPublished(EventEnvelope):
    """Daily attribution decomposition. Emitted by strategy-service/pnl."""

    event_type: Literal["PnLAttributionPublished"] = Field(
        default="PnLAttributionPublished", description="Event discriminator"
    )
    record: PnLAttributionRecord
