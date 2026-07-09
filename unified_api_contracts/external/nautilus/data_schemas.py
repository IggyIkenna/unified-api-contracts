"""NautilusTrader-optimized data schemas and instrument ID conversion.

Raw column schemas for trades, book snapshots, liquidations, derivative tickers,
and liquidity snapshots. Zero-conversion format for NautilusTrader backtesting.

Key differences from raw Tardis format:
1. Timestamps: us -> ns (ts_event, ts_init)
2. Side: string -> int (aggressor_side: 1=buy, 2=sell)
3. Column renames: amount->size, id->trade_id
4. Instrument ID: canonical -> NautilusTrader format (BTCUSDT-PERP.BINANCE)
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Schema definitions
# =============================================================================

NAUTILUS_TRADES_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "instrument_key",
        "type": "string",
        "required": True,
        "description": "Canonical instrument ID (e.g., BINANCE-FUTURES:PERPETUAL:BTC-USDT)",
    },
    {"name": "price", "type": "float64", "required": True, "description": "Trade price"},
    {
        "name": "size",
        "type": "float64",
        "required": True,
        "description": "Trade size/quantity (renamed from 'amount')",
    },
    {
        "name": "aggressor_side",
        "type": "int8",
        "required": True,
        "description": "Aggressor side: 1=buyer, 2=seller (converted from 'buy'/'sell')",
    },
    {
        "name": "trade_id",
        "type": "string",
        "required": True,
        "description": "Trade ID (renamed from 'id')",
    },
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Event timestamp in nanoseconds (converted from microseconds)",
    },
    {
        "name": "ts_init",
        "type": "int64",
        "required": True,
        "description": "Init/local timestamp in nanoseconds (converted from microseconds)",
    },
]

NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "instrument_key",
        "type": "string",
        "required": True,
        "description": "Canonical instrument ID",
    },
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Event timestamp in nanoseconds",
    },
    {
        "name": "ts_init",
        "type": "int64",
        "required": True,
        "description": "Init/local timestamp in nanoseconds",
    },
    *[
        {
            "name": f"bid_price_{i}",
            "type": "float64",
            "required": False,
            "description": f"Bid price level {i}",
        }
        for i in range(5)
    ],
    *[
        {
            "name": f"bid_size_{i}",
            "type": "float64",
            "required": False,
            "description": f"Bid size level {i}",
        }
        for i in range(5)
    ],
    *[
        {
            "name": f"ask_price_{i}",
            "type": "float64",
            "required": False,
            "description": f"Ask price level {i}",
        }
        for i in range(5)
    ],
    *[
        {
            "name": f"ask_size_{i}",
            "type": "float64",
            "required": False,
            "description": f"Ask size level {i}",
        }
        for i in range(5)
    ],
]

NAUTILUS_LIQUIDATIONS_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "instrument_key",
        "type": "string",
        "required": True,
        "description": "Canonical instrument ID",
    },
    {"name": "price", "type": "float64", "required": True, "description": "Liquidation price"},
    {"name": "size", "type": "float64", "required": True, "description": "Liquidation size"},
    {
        "name": "aggressor_side",
        "type": "int8",
        "required": True,
        "description": "Side: 1=buy, 2=sell",
    },
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Event timestamp in nanoseconds",
    },
    {
        "name": "ts_init",
        "type": "int64",
        "required": True,
        "description": "Init timestamp in nanoseconds",
    },
]

NAUTILUS_DERIVATIVE_TICKER_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "instrument_key",
        "type": "string",
        "required": True,
        "description": "Canonical instrument ID",
    },
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Event timestamp in nanoseconds",
    },
    {
        "name": "ts_init",
        "type": "int64",
        "required": True,
        "description": "Init timestamp in nanoseconds",
    },
    {"name": "funding_rate", "type": "float64", "required": False, "description": "Funding rate"},
    {"name": "index_price", "type": "float64", "required": False, "description": "Index price"},
    {"name": "mark_price", "type": "float64", "required": False, "description": "Mark price"},
    {"name": "open_interest", "type": "float64", "required": False, "description": "Open interest"},
]

NAUTILUS_LIQUIDITY_SNAPSHOTS_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "instrument_key",
        "type": "string",
        "required": True,
        "description": "Pool instrument key (VENUE:POOL:PAIR@CHAIN)",
    },
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Snapshot timestamp in nanoseconds (UTC)",
    },
    {
        "name": "ts_init",
        "type": "int64",
        "required": True,
        "description": "Init timestamp in nanoseconds (UTC)",
    },
    {
        "name": "liquidity",
        "type": "string",
        "required": True,
        "description": "In-range liquidity (bigint as string)",
    },
    {
        "name": "sqrt_price_x96",
        "type": "string",
        "required": True,
        "description": "sqrt(price) * 2^96 (bigint as string)",
    },
    {
        "name": "token0_price",
        "type": "float64",
        "required": True,
        "description": "Price of token0 in terms of token1",
    },
    {
        "name": "token1_price",
        "type": "float64",
        "required": True,
        "description": "Price of token1 in terms of token0",
    },
    {
        "name": "tick",
        "type": "int64",
        "required": False,
        "description": "Current tick (Uniswap V3)",
    },
    {
        "name": "tvl_usd",
        "type": "float64",
        "required": False,
        "description": "Total value locked in USD",
    },
    {
        "name": "volume_token0",
        "type": "float64",
        "required": False,
        "description": "Volume of token0 for the hour",
    },
    {
        "name": "volume_token1",
        "type": "float64",
        "required": False,
        "description": "Volume of token1 for the hour",
    },
    {
        "name": "volume_usd",
        "type": "float64",
        "required": False,
        "description": "Volume in USD for the hour",
    },
    {
        "name": "fees_usd",
        "type": "float64",
        "required": False,
        "description": "Fees collected in USD for the hour",
    },
]

NAUTILUS_SCHEMA_MAP: dict[str, list[dict[str, str | bool]]] = {
    "trades": NAUTILUS_TRADES_SCHEMA,
    "book_snapshot_5": NAUTILUS_BOOK_SNAPSHOT_5_SCHEMA,
    "liquidations": NAUTILUS_LIQUIDATIONS_SCHEMA,
    "derivative_ticker": NAUTILUS_DERIVATIVE_TICKER_SCHEMA,
    "liquidity_snapshots": NAUTILUS_LIQUIDITY_SNAPSHOTS_SCHEMA,
}


def get_nautilus_schema(data_type: str) -> list[dict[str, str | bool]] | None:
    """Get NautilusTrader schema for a data type."""
    return NAUTILUS_SCHEMA_MAP.get(data_type)


# =============================================================================
# Instrument ID conversion
# =============================================================================

EXCHANGE_NAME_MAP: dict[str, str] = {
    # Values are NautilusTrader venue names (bare "BINANCE" is correct for Nautilus)
    "binance-futures": "BINANCE",
    "binance_futures": "BINANCE",
    "binance": "BINANCE",
    "bybit": "BYBIT",
    "deribit": "DERIBIT",
    "okx": "OKX",
    "okex": "OKX",
    "coinbase": "COINBASE",
    "upbit": "UPBIT",
    "ftx": "FTX",
    "kucoin": "KUCOIN",
    "gate": "GATE",
    "bitget": "BITGET",
}

INSTRUMENT_TYPE_SUFFIX_MAP: dict[str, str] = {
    "PERPETUAL": "PERP",
    "FUTURE": "FUT",
    "FUT": "FUT",
    "SPOT_PAIR": "SPOT",
    "OPTION": "OPT",
    "OPT": "OPT",
}


def convert_to_nautilus_instrument_id(canonical_id: str) -> str:
    """Convert canonical instrument ID to NautilusTrader format.

    Examples:
        BINANCE-FUTURES:PERPETUAL:BTC-USDT -> BTCUSDT-PERP.BINANCE
        BYBIT:PERPETUAL:ETH-USDT -> ETHUSDT-PERP.BYBIT
        OKX:SPOT:BTC-USDT -> BTCUSDT-SPOT.OKX
    """
    canonical_id = canonical_id.split("@")[0]

    parts = canonical_id.split(":")
    if len(parts) < 3:
        logger.warning("Invalid canonical ID format: %s", canonical_id)
        return canonical_id

    exchange = parts[0]
    instrument_type = parts[1]
    symbol = parts[2]

    exchange_clean = EXCHANGE_NAME_MAP.get(exchange.lower(), exchange.split("-")[0].upper())
    type_suffix = INSTRUMENT_TYPE_SUFFIX_MAP.get(instrument_type.upper(), instrument_type[:4].upper())
    symbol_clean = symbol.replace("-", "")

    return f"{symbol_clean}-{type_suffix}.{exchange_clean}"


def convert_from_nautilus_instrument_id(nautilus_id: str) -> str:
    """Convert NautilusTrader instrument ID back to canonical format.

    Examples:
        BTCUSDT-PERP.BINANCE -> BINANCE-FUTURES:PERPETUAL:BTC-USDT
    """
    try:
        symbol_type, exchange = nautilus_id.rsplit(".", 1)
        symbol, type_suffix = symbol_type.rsplit("-", 1)

        type_map_reverse = {v: k for k, v in INSTRUMENT_TYPE_SUFFIX_MAP.items()}
        instrument_type = type_map_reverse.get(type_suffix, type_suffix)

        if instrument_type == "PERPETUAL":
            exchange = f"{exchange}-FUTURES"

        for quote in ["USDT", "USD", "USDC", "BUSD", "EUR", "GBP"]:
            if symbol.endswith(quote) and len(symbol) > len(quote):
                base = symbol[: -len(quote)]
                symbol = f"{base}-{quote}"
                break

        return f"{exchange}:{instrument_type}:{symbol}"
    except (OSError, PermissionError, ValueError):
        logger.warning("Failed to convert NautilusTrader ID: %s", nautilus_id)
        return nautilus_id
