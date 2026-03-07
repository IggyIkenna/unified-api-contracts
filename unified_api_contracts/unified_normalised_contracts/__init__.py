"""Canonical normalised schemas: one-hop normalisation from raw venue responses.

Domain: CanonicalOrderBook, CanonicalTrade, InstrumentWarehouseRow, etc.
Execution: CanonicalOrder, CanonicalFill, ExecutionInstruction, etc.
Errors: CanonicalError, CanonicalRateLimitError (grouped).

Self-contained: no imports from unified_api_contracts.internal.

Note: InstrumentWarehouseRow was renamed from InstrumentRecord to avoid collision
with UIC's InstrumentRecord (31-field, Decimal, normalized adapter contract).
"""

from .domain import (
    CanonicalAccountSnapshot,
    CanonicalBalance,
    CanonicalDerivativeTicker,
    CanonicalFundingRate,
    CanonicalLiquidation,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalPosition,
    CanonicalSettlement,
    CanonicalTicker,
    CanonicalTrade,
    InstrumentType,
    InstrumentWarehouseRow,
    MarketTrade,
    OrderBookSnapshot5,
    ProcessedCandle,
)
from .errors import CanonicalError, CanonicalRateLimitError
from .execution import (
    CanonicalAccountState,
    CanonicalFill,
    CanonicalMarginState,
    CanonicalOrder,
    CanonicalOrderAmendment,
    CanonicalOrderRejection,
    ExecutionInstruction,
    ExecutionResult,
    OrderSide,
    OrderStatus,
    OrderType,
)

__all__ = [
    "CanonicalAccountSnapshot",
    "CanonicalAccountState",
    "CanonicalBalance",
    "CanonicalDerivativeTicker",
    "CanonicalError",
    "CanonicalFill",
    "CanonicalFundingRate",
    "CanonicalLiquidation",
    "CanonicalMarginState",
    "CanonicalOhlcvBar",
    "CanonicalOrder",
    "CanonicalOrderAmendment",
    "CanonicalOrderBook",
    "CanonicalOrderRejection",
    "CanonicalPosition",
    "CanonicalRateLimitError",
    "CanonicalSettlement",
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
    "ProcessedCandle",
]
