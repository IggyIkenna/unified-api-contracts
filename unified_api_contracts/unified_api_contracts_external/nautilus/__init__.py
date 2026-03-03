"""NautilusTrader schemas, mocks, and data schemas.

Execution testing: Order, Position, Instrument, Fill, Account + MockCache/MockClock.
Data schemas: NautilusTrader-optimized column schemas + instrument ID conversion.

Usage:
    from unified_api_contracts.unified_api_contracts_external.nautilus import Order, Position, MockCache, mock_order, mock_cache
    from unified_api_contracts.unified_api_contracts_external.nautilus.data_schemas import NAUTILUS_TRADES_SCHEMA, convert_to_nautilus_instrument_id
"""

from .cache import Cache, MockCache
from .clock import Clock, MockClock
from .data_schemas import (
    EXCHANGE_NAME_MAP,
    INSTRUMENT_TYPE_SUFFIX_MAP,
    NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA,
    NAUTILUS_DERIVATIVE_TICKER_SCHEMA,
    NAUTILUS_LIQUIDATIONS_SCHEMA,
    NAUTILUS_LIQUIDITY_SNAPSHOTS_SCHEMA,
    NAUTILUS_SCHEMA_MAP,
    NAUTILUS_TRADES_SCHEMA,
    convert_from_nautilus_instrument_id,
    convert_to_nautilus_instrument_id,
    get_nautilus_schema,
)
from .mocks import (
    mock_account,
    mock_cache,
    mock_clock,
    mock_fill,
    mock_instrument,
    mock_order,
    mock_position,
)
from .schemas import Account, Fill, Instrument, Order, Position

__all__ = [
    "EXCHANGE_NAME_MAP",
    "INSTRUMENT_TYPE_SUFFIX_MAP",
    "NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA",
    "NAUTILUS_DERIVATIVE_TICKER_SCHEMA",
    "NAUTILUS_LIQUIDATIONS_SCHEMA",
    "NAUTILUS_LIQUIDITY_SNAPSHOTS_SCHEMA",
    "NAUTILUS_SCHEMA_MAP",
    "NAUTILUS_TRADES_SCHEMA",
    "Account",
    "Cache",
    "Clock",
    "Fill",
    "Instrument",
    "MockCache",
    "MockClock",
    "Order",
    "Position",
    "convert_from_nautilus_instrument_id",
    "convert_to_nautilus_instrument_id",
    "get_nautilus_schema",
    "mock_account",
    "mock_cache",
    "mock_clock",
    "mock_fill",
    "mock_instrument",
    "mock_order",
    "mock_position",
]
