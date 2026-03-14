"""Kraken exchange API contracts (CeFi, spot + derivatives)."""

from unified_api_contracts.external.kraken.schemas import (
    KrakenFill,
    KrakenOrder,
    KrakenOrderBook,
    KrakenOrderBook_WS,
    KrakenOrderBookLevel,
    KrakenOrderBookWS,
    KrakenTicker,
    KrakenTrade,
    KrakenTradeDescr,
)

__all__ = [
    "KrakenFill",
    "KrakenOrder",
    "KrakenOrderBook",
    "KrakenOrderBookLevel",
    "KrakenOrderBookWS",
    "KrakenOrderBook_WS",  # underscore name for Kraken WS API consumers
    "KrakenTicker",
    "KrakenTrade",
    "KrakenTradeDescr",
]
