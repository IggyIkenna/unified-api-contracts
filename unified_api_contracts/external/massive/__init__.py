"""Massive (Polygon.io-compatible) external reference-data schemas + normalisers."""

from unified_api_contracts.external.massive.normalize import (
    MASSIVE_EQUITY_MIC_TO_VENUE,
    MASSIVE_FUTURES_MIC_TO_VENUE,
    normalize_massive_equity,
    normalize_massive_futures,
    normalize_massive_fx,
    normalize_massive_index,
    normalize_massive_option,
    venue_for_equity_mic,
    venue_for_futures_mic,
)
from unified_api_contracts.external.massive.schemas import (
    MassiveFuturesContract,
    MassiveFuturesContractsResponse,
    MassiveFuturesProduct,
    MassiveFuturesProductsResponse,
    MassiveOptionContract,
    MassiveOptionContractsResponse,
    MassiveTicker,
    MassiveTickersResponse,
)

__all__ = [
    "MASSIVE_EQUITY_MIC_TO_VENUE",
    "MASSIVE_FUTURES_MIC_TO_VENUE",
    "MassiveFuturesContract",
    "MassiveFuturesContractsResponse",
    "MassiveFuturesProduct",
    "MassiveFuturesProductsResponse",
    "MassiveOptionContract",
    "MassiveOptionContractsResponse",
    "MassiveTicker",
    "MassiveTickersResponse",
    "normalize_massive_equity",
    "normalize_massive_futures",
    "normalize_massive_fx",
    "normalize_massive_index",
    "normalize_massive_option",
    "venue_for_equity_mic",
    "venue_for_futures_mic",
]
