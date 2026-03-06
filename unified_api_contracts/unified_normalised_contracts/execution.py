"""Canonical execution schemas — self-contained (no internal imports).

Identifier convention
---------------------
``instrument_id``   — venue-opaque execution identifier used in CanonicalOrder,
                      CanonicalFill, and ExecutionInstruction. May be a numeric or
                      string ID assigned by the venue (e.g. Binance symbol "BTCUSDT",
                      Deribit contract name "BTC-PERPETUAL"). Execution adapters are
                      responsible for mapping this to the canonical ``instrument_key``
                      when bridging to market-data layer.

``instrument_key``  — canonical cross-venue market-data identifier in
                      ``VENUE:TYPE:SYMBOL`` format. Lives in domain.py schemas only;
                      NOT used in execution schemas. Execution-to-market-data joins
                      must go through the instruments-service lookup.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    TWAP = "twap"
    VWAP = "vwap"


class OrderStatus(StrEnum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(StrEnum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    GTD = "GTD"
    POST_ONLY = "POST_ONLY"


class OperationType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    SWAP = "SWAP"
    LEND = "LEND"
    BORROW = "BORROW"
    REPAY = "REPAY"
    WITHDRAW = "WITHDRAW"
    DEPOSIT = "DEPOSIT"
    REBALANCE = "REBALANCE"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class BenchmarkType(StrEnum):
    ARRIVAL = "arrival"
    VWAP = "vwap"
    TWAP = "twap"
    CLOSE = "close"
    MID = "mid"


# ---------------------------------------------------------------------------
# Order / Fill — canonical cross-venue
# ---------------------------------------------------------------------------


class CanonicalOrder(BaseModel):
    order_id: str
    client_order_id: str | None = None
    timestamp: datetime
    venue: str
    instrument_id: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal | None = None
    average_fill_price: Decimal | None = None
    strategy_id: str | None = None
    client_id: str | None = Field(default=None, json_schema_extra={"pii": True})


class CanonicalFill(BaseModel):
    """Fill record — also used as Pub/Sub fill-events-{venue} message body."""

    fill_id: str
    order_id: str
    timestamp: datetime
    venue: str
    instrument_id: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    fee: Decimal | None = None
    fee_currency: str | None = None
    is_maker: bool | None = None
    strategy_id: str | None = None
    client_id: str | None = Field(default=None, json_schema_extra={"pii": True})


# ---------------------------------------------------------------------------
# Execution instructions (strategy → execution routing)
# ---------------------------------------------------------------------------


class ExecutionInstruction(BaseModel):
    """Single atomic execution directive (from execution-services)."""

    instruction_id: str
    operation: OperationType
    timestamp: datetime
    from_venue: str | None = None
    to_venue: str | None = None
    instrument_id: str | None = None
    token_in: str | None = None
    amount: Decimal | None = None
    token_out: str | None = None
    direction: str | None = None
    target_position: Decimal | None = None
    max_slippage_bps: int | None = None
    limit_price: Decimal | None = None
    order_type: OrderType | None = None
    benchmark_price: Decimal | None = None
    benchmark_type: BenchmarkType | None = None
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    gas_limit: int | None = None
    priority_fee_gwei: float | None = None
    deadline_timestamp: datetime | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Result of a single ExecutionInstruction."""

    instruction_id: str
    operation: OperationType
    status: ExecutionStatus
    timestamp_submitted: datetime
    timestamp_completed: datetime | None = None
    actual_execution_price: Decimal | None = None
    benchmark_price: Decimal | None = None
    amount_executed: Decimal | None = None
    amount_received: Decimal | None = None
    slippage_bps: float | None = None
    gas_used: int | None = None
    gas_price_gwei: float | None = None
    transaction_hash: str | None = None
    error_message: str | None = None


__all__ = [
    "CanonicalFill",
    "CanonicalOrder",
    "ExecutionInstruction",
    "ExecutionResult",
    "OrderSide",
    "OrderStatus",
    "OrderType",
]
