"""Canonical normalised schemas: one-hop normalisation from raw venue responses.

Domain: CanonicalOrderBook, CanonicalTrade, InstrumentWarehouseRow, etc.
Execution: CanonicalOrder, CanonicalFill, ExecutionInstruction, etc.
Errors: CanonicalError, CanonicalRateLimitError (grouped).

Self-contained: no imports from unified_api_contracts.internal.

Note: InstrumentWarehouseRow was renamed from InstrumentRecord to avoid collision
with UIC's InstrumentRecord (31-field, Decimal, normalized adapter contract).
"""

from ..canonical import (
    CanonicalBalance,
    CanonicalError,
    CanonicalFill,
    CanonicalFundingRate,
    CanonicalLiquidation,
    CanonicalOrder,
    CanonicalOrderBook,
    CanonicalPosition,
    CanonicalRateLimitError,
    CanonicalTicker,
    CanonicalTrade,
    ExecutionInstruction,
    ExecutionResult,
    InstrumentType,
    InstrumentWarehouseRow,
    MarketTrade,
    OrderBookSnapshot5,
    OrderSide,
    OrderStatus,
    OrderType,
)

__all__ = [
    "CanonicalBalance",
    "CanonicalError",
    "CanonicalFill",
    "CanonicalFundingRate",
    "CanonicalLiquidation",
    "CanonicalOrder",
    "CanonicalOrderBook",
    "CanonicalPosition",
    "CanonicalRateLimitError",
    "CanonicalTicker",
    "CanonicalTrade",
    "ExecutionInstruction",
    "ExecutionResult",
    "InstrumentType",
    # InstrumentWarehouseRow — renamed from InstrumentRecord to avoid collision with UIC's InstrumentRecord
    "InstrumentWarehouseRow",
    "MarketTrade",
    "OrderBookSnapshot5",
    "OrderSide",
    "OrderStatus",
    "OrderType",
]
