"""Internal signal schemas — strategy instructions, DeFi signals, GCS output records."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


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


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TWAP = "twap"
    VWAP = "vwap"


class BenchmarkType(StrEnum):
    ARRIVAL = "arrival"
    VWAP = "vwap"
    TWAP = "twap"
    CLOSE = "close"
    MID = "mid"


class StrategyInstruction(BaseModel):
    """Single instruction produced by strategy-service (StrategyInstruction model)."""

    instruction_id: str
    strategy_id: str
    timestamp: datetime
    operation: OperationType
    instrument_id: str | None = None
    from_venue: str | None = None
    to_venue: str | None = None
    token_in: str | None = None
    amount: Decimal | None = None
    token_out: str | None = None
    direction: str | None = None
    target_position: Decimal | None = None
    benchmark_price: Decimal | None = None
    benchmark_type: BenchmarkType | None = None
    limit_price: Decimal | None = None
    order_type: OrderType | None = None
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    max_slippage_bps: int | None = None
    allowed_venues: list[str] = Field(default_factory=list)
    gas_limit: int | None = None
    priority_fee_gwei: float | None = None
    deadline_timestamp: datetime | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class DeFiSignal(BaseModel):
    """A batch of atomic instructions forming one logical DeFi strategy signal."""

    signal_id: str
    strategy_id: str
    timestamp: datetime
    is_atomic: bool = False
    instructions: list[StrategyInstruction] = Field(default_factory=list)
    expected_apy: float | None = None
    ethena_benchmark_apy: float | None = None
    max_total_slippage_bps: int | None = None
    total_gas_budget: int | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class InstructionRecord(BaseModel):
    """GCS parquet row written by strategy-service (INSTRUCTIONS_SCHEMA)."""

    timestamp: datetime
    strategy_id: str
    instrument_id: str
    side: str
    quantity: Decimal | None = None
    order_type: str | None = None
    limit_price: Decimal | None = None
    benchmark_price: Decimal | None = None
    take_profit_price: Decimal | None = None
    stop_loss_price: Decimal | None = None
    max_slippage_bps: int | None = None
    instruction_id: str | None = None


class DeFiSignalRecord(BaseModel):
    """GCS parquet row for a DeFi signal (DEFI_SIGNAL_SCHEMA)."""

    ts_event: int = Field(description="nanoseconds UTC")
    ts_init: int
    signal_id: str
    strategy_id: str
    is_atomic: bool
    instructions_json: str = Field(description="JSON-serialised list of StrategyInstruction dicts")
    expected_apy: float | None = None
    ethena_benchmark_apy: float | None = None
    max_total_slippage_bps: int | None = None
    total_gas_budget: int | None = None
