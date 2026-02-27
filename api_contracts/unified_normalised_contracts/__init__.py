"""Canonical normalised schemas: one-hop normalisation from raw venue responses.

Domain: CanonicalOrderBook, CanonicalTrade, InstrumentRecord, etc.
Execution: CanonicalOrder, CanonicalFill, ExecutionInstruction, etc.
Errors: CanonicalError, CanonicalRateLimitError (grouped).

Re-exports from internal during Phase 1; will be extracted in Phase 2.
"""

from .domain import (
    CanonicalOrderBook,
    CanonicalTrade,
    InstrumentRecord,
    InstrumentType,
    MarketTrade,
    OrderBookSnapshot5,
    ProcessedCandle,
)
from .errors import CanonicalError, CanonicalRateLimitError
from .execution import (
    CanonicalFill,
    CanonicalOrder,
    ExecutionInstruction,
    ExecutionResult,
    OrderSide,
    OrderStatus,
    OrderType,
)

__all__ = [
    "CanonicalError",
    "CanonicalFill",
    "CanonicalOrder",
    "CanonicalOrderBook",
    "CanonicalRateLimitError",
    "CanonicalTrade",
    "ExecutionInstruction",
    "ExecutionResult",
    "InstrumentRecord",
    "InstrumentType",
    "MarketTrade",
    "OrderBookSnapshot5",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "ProcessedCandle",
]
