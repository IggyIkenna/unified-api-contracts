"""MEXC Global exchange API contracts (CeFi, spot + futures)."""

from unified_api_contracts.unified_api_contracts_external.mexc.schemas import (
    MexcFill,
    MexcOrder,
    MexcOrderBook,
    MexcTicker,
    MexcTrade,
)

__all__ = [
    "MexcFill",
    "MexcOrder",
    "MexcOrderBook",
    "MexcTicker",
    "MexcTrade",
]
