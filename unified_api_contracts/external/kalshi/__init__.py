"""Kalshi prediction exchange API contracts.

API hierarchy: Series → Event → Market.
Base URL: https://trading-api.kalshi.com/trade-api/v2
WebSocket: wss://trading-api.kalshi.com/trade-api/ws/v2
"""

from .crypto_macro_mappings import (
    KALSHI_CRYPTO_SERIES,
    KALSHI_MACRO_SERIES,
    build_kalshi_crypto_ticker,
    build_kalshi_macro_ticker,
    parse_kalshi_ticker,
)
from .schemas import (
    KalshiBalance,
    KalshiCandlestick,
    KalshiError,
    KalshiEvent,
    KalshiFill,
    KalshiHistoricalCutoff,
    KalshiMarket,
    KalshiOrder,
    KalshiOrderBook,
    KalshiPosition,
    KalshiSeries,
    KalshiTrade,
)
from .sports_mappings import (
    KALSHI_SPORTS_TICKER_PREFIXES,
    build_kalshi_sports_ticker,
    parse_kalshi_sports_ticker,
)

__all__ = [
    "KALSHI_CRYPTO_SERIES",
    "KALSHI_MACRO_SERIES",
    "KALSHI_SPORTS_TICKER_PREFIXES",
    "KalshiBalance",
    "KalshiCandlestick",
    "KalshiError",
    "KalshiEvent",
    "KalshiFill",
    "KalshiHistoricalCutoff",
    "KalshiMarket",
    "KalshiOrder",
    "KalshiOrderBook",
    "KalshiPosition",
    "KalshiSeries",
    "KalshiTrade",
    "build_kalshi_crypto_ticker",
    "build_kalshi_macro_ticker",
    "build_kalshi_sports_ticker",
    "parse_kalshi_sports_ticker",
    "parse_kalshi_ticker",
]
