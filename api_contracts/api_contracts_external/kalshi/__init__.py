"""Kalshi prediction exchange API contracts.

API hierarchy: Series → Event → Market.
Base URL: https://trading-api.kalshi.com/trade-api/v2
WebSocket: wss://trading-api.kalshi.com/trade-api/ws/v2
"""

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

__all__ = [
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
]
