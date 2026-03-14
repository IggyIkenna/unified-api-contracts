"""Bitget exchange API contracts (CeFi, spot + futures + copy trading)."""

from unified_api_contracts.external.bitget.schemas import (
    BitgetFeeDetail,
    BitgetFill,
    BitgetOrder,
    BitgetOrderBook,
    BitgetTicker,
    BitgetTrade,
)

__all__ = [
    "BitgetFeeDetail",
    "BitgetFill",
    "BitgetOrder",
    "BitgetOrderBook",
    "BitgetTicker",
    "BitgetTrade",
]
