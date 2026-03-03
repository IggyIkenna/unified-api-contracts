"""Canonical normalised schemas: one-hop normalisation from raw venue responses.

Domain: CanonicalOrderBook, CanonicalTrade, InstrumentRecord, etc.
Execution: CanonicalOrder, CanonicalFill, ExecutionInstruction, etc.
Errors: CanonicalError, CanonicalRateLimitError (grouped).

Self-contained: no imports from unified_api_contracts.internal.
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
