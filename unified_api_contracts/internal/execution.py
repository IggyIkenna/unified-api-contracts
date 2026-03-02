"""Internal execution schemas — orders, fills, execution reports, manual instructions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

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
    GTC = "GTC"  # Good till cancel
    IOC = "IOC"  # Immediate or cancel
    FOK = "FOK"  # Fill or kill
    GTD = "GTD"  # Good till date
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
# Order / Fill — canonical cross-venue (from unified-trade-execution-interface)
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
    client_id: str | None = None


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
    client_id: str | None = None


class FillEventPubSubPayload(BaseModel):
    """JSON body of a Pub/Sub message on topic fill-events-{venue}."""

    fill_id: str
    order_id: str
    timestamp: str = Field(description="ISO 8601 UTC")
    venue: str
    instrument_id: str
    side: str
    quantity: str
    price: str
    fee: str | None = None
    fee_currency: str | None = None
    strategy_id: str | None = None
    client_id: str | None = None


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


# ---------------------------------------------------------------------------
# Backtest actor messages
# ---------------------------------------------------------------------------


class OrderSubmittedMessage(BaseModel):
    message_type: Literal["OrderSubmitted"] = "OrderSubmitted"
    order_id: str
    side: OrderSide
    quantity: Decimal
    benchmark_price: Decimal | None = None
    exec_algorithm: str | None = None
    timestamp: datetime
    context: dict[str, str | float | int | bool | None] = Field(default_factory=dict)


class TPHitMessage(BaseModel):
    message_type: Literal["TPHit"] = "TPHit"
    price: Decimal
    timestamp: datetime
    direction: str
    target_price: Decimal


class SLHitMessage(BaseModel):
    message_type: Literal["SLHit"] = "SLHit"
    price: Decimal
    timestamp: datetime
    direction: str
    target_price: Decimal


class CandleCloseWarningMessage(BaseModel):
    message_type: Literal["CandleCloseWarning"] = "CandleCloseWarning"
    timestamp: datetime
    seconds_until_close: float
    candle_end: datetime


# ---------------------------------------------------------------------------
# REST API schemas (execution-services HTTP endpoints)
# ---------------------------------------------------------------------------


class ManualInstructionRequest(BaseModel):
    """POST /instructions body."""

    client_id: str
    strategy_id: str
    instruction_type: str
    venue: str
    instrument_id: str
    side: OrderSide
    quantity: Decimal
    price: Decimal | None = None
    algo: str | None = None
    algo_params: dict[str, str | int | float | bool | None] | None = None


class ManualInstructionResponse(BaseModel):
    instruction_id: str
    status: str
    message: str
    estimated_completion: str | None = None
    error: str | None = None
