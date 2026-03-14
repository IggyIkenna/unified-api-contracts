"""Bitstamp exchange API contracts (CeFi, spot)."""

from unified_api_contracts.external.bitstamp.schemas import (
    BitstampFill,
    BitstampOrder,
    BitstampOrderBook,
    BitstampTicker,
    BitstampTrade,
)

__all__ = [
    "BitstampFill",
    "BitstampOrder",
    "BitstampOrderBook",
    "BitstampTicker",
    "BitstampTrade",
]
