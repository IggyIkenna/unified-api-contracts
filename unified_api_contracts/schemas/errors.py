"""Error classification schemas for venue-specific API errors.

Type definitions live in _errors_types.py.
Venue error data is split across four private modules by category:
  _venue_errors_cefi.py     — CeFi exchanges (binance, bybit, okx, ...)
  _venue_errors_altdata.py  — Alt-data providers and DeFi infra (hyperliquid, aave_v3, ...)
  _venue_errors_defi.py     — DeFi protocols (balancer, curve, morpho, ...)
  _venue_errors_sports.py   — Prediction markets and sports (betfair, kalshi, ...)
"""

from __future__ import annotations

from unified_api_contracts.schemas._errors_types import (
    DATABENTO_ERROR_MAP,
    DatabentoError,
    ErrorAction,
    RateLimitResponse,
    VenueErrorClassification,
    WebSocketCloseInfo,
)
from unified_api_contracts.schemas._venue_errors_altdata import VENUE_ERRORS_ALTDATA
from unified_api_contracts.schemas._venue_errors_cefi import VENUE_ERRORS_CEFI
from unified_api_contracts.schemas._venue_errors_defi import VENUE_ERRORS_DEFI
from unified_api_contracts.schemas._venue_errors_sports import VENUE_ERRORS_SPORTS

# Merged venue error map — all categories combined into one lookup table.
VENUE_ERROR_MAP: dict[str, list[VenueErrorClassification]] = {
    **VENUE_ERRORS_CEFI,
    **VENUE_ERRORS_ALTDATA,
    **VENUE_ERRORS_DEFI,
    **VENUE_ERRORS_SPORTS,
}

__all__ = [
    "DATABENTO_ERROR_MAP",
    "VENUE_ERROR_MAP",
    "DatabentoError",
    "ErrorAction",
    "RateLimitResponse",
    "VenueErrorClassification",
    "WebSocketCloseInfo",
    "classify_venue_error",
]


def classify_venue_error(venue: str, error_code: str) -> VenueErrorClassification | None:
    """Classify a venue error code using normalized VENUE_ERROR_MAP.

    Returns VenueErrorClassification with retry_safe, reconnect, action, or
    None when the code is not found in the map.  Callers that receive None
    must emit UNKNOWN_VENUE_ERROR_RECEIVED and raise CanonicalUnknownVenueError
    so the ops backlog can track novel codes.
    """
    venue_key = venue.lower()
    classifications = VENUE_ERROR_MAP.get(venue_key, [])
    code_str = str(error_code)
    for c in classifications:
        if c.error_code == code_str:
            return c
    return None
