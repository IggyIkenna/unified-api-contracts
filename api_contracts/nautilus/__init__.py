"""NautilusTrader-like Pydantic schemas and mocks for execution-services testing.

Provides Order, Position, Instrument, Fill, Account schemas plus MockCache and MockClock
for testing without the full nautilus-trader dependency.

Usage:
    from api_contracts.nautilus import Order, Position, MockCache, mock_order, mock_cache
"""

from api_contracts.nautilus.cache import Cache, MockCache
from api_contracts.nautilus.clock import Clock, MockClock
from api_contracts.nautilus.mocks import (
    mock_account,
    mock_cache,
    mock_clock,
    mock_fill,
    mock_instrument,
    mock_order,
    mock_position,
)
from api_contracts.nautilus.schemas import Account, Fill, Instrument, Order, Position

__all__ = [
    "Account",
    "Cache",
    "Clock",
    "Fill",
    "Instrument",
    "MockCache",
    "MockClock",
    "Order",
    "Position",
    "mock_account",
    "mock_cache",
    "mock_clock",
    "mock_fill",
    "mock_instrument",
    "mock_order",
    "mock_position",
]
