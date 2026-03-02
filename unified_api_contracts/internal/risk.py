"""Internal risk schemas — metrics, alerts, exposure, pre-trade checks, account state."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskStatus(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertType(StrEnum):
    PRE_TRADE_REJECTION = "PRE_TRADE_REJECTION"
    RISK_WARNING = "RISK_WARNING"
    RISK_CRITICAL = "RISK_CRITICAL"
    EXPOSURE_BREACH = "EXPOSURE_BREACH"
    MARGIN_WARNING = "MARGIN_WARNING"
    LIQUIDATION_RISK = "LIQUIDATION_RISK"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class RiskPosition(BaseModel):
    """Position as tracked by risk-and-exposure-service."""

    client_id: str
    strategy_id: str | None = None
    venue: str
    instrument: str
    quantity: Decimal
    avg_price: Decimal
    position_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    last_updated: datetime


class RiskMetrics(BaseModel):
    """Computed risk metrics per client (output of risk engine)."""

    client_id: str
    timestamp: datetime
    leverage: float
    margin_usage: float
    concentration: float
    drawdown: float
    account_equity: Decimal
    total_position_value: Decimal
    cash_balance: Decimal
    leverage_status: RiskStatus
    concentration_status: RiskStatus
    drawdown_status: RiskStatus
    var_1d: float | None = None
    var_5d: float | None = None
    expected_shortfall: float | None = None
    beta: float | None = None


class AlertContextData(BaseModel):
    client_id: str
    strategy_id: str | None = None
    metric_type: str | None = None
    venue: str | None = None
    instrument: str | None = None
    position_size: Decimal | None = None
    trade_id: str | None = None
    order_id: str | None = None
    extra: dict[str, str | float | int | bool | None] = Field(default_factory=dict)


class AlertMessage(BaseModel):
    """Risk alert published to risk consumers (Pub/Sub or GCS)."""

    alert_type: AlertType
    client_id: str
    metric: str
    current_value: float
    threshold: float
    timestamp: datetime
    recommended_action: str | None = None
    context: AlertContextData | None = None
    severity: str = "WARNING"


class PreTradeCheckRequest(BaseModel):
    client_id: str
    strategy_id: str | None = None
    venue: str
    instrument: str
    side: str
    quantity: Decimal
    estimated_price: Decimal
    order_type: str | None = None


class PreTradeCheckResponse(BaseModel):
    approved: bool
    client_id: str
    instrument: str
    reason: str | None = None
    alerts: list[AlertMessage] = Field(default_factory=list)
    timestamp: datetime | None = None


class ExposureSummary(BaseModel):
    client_id: str
    timestamp: datetime
    gross_exposure: Decimal
    net_exposure: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    by_venue: dict[str, Decimal] = Field(default_factory=dict)
    by_instrument: dict[str, Decimal] = Field(default_factory=dict)
    total_positions: int = 0


class Balance(BaseModel):
    currency: str
    free: Decimal
    locked: Decimal
    total: Decimal


class MarginState(BaseModel):
    account_id: str
    venue: str
    timestamp: datetime
    margin_level: float
    total_collateral: Decimal
    total_debt: Decimal
    available_margin: Decimal
    liquidation_price: Decimal | None = None
    margin_ratio: float | None = None
    is_margin_call: bool = False


class InternalPosition(BaseModel):
    """Position tracked by unified-trade-execution-interface / position-balance-monitor."""

    instrument_id: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    leverage: float | None = None
    liquidation_price: Decimal | None = None
    realized_pnl: Decimal | None = None


class AccountState(BaseModel):
    """Snapshot of a venue account — published after each fill or periodic sync."""

    timestamp: datetime
    venue: str
    account_id: str
    positions: list[InternalPosition] = Field(default_factory=list)
    balances: dict[str, Balance] = Field(default_factory=dict)
    margin: MarginState | None = None
