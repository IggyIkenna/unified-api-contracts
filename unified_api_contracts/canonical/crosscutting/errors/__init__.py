"""Canonical error schemas and venue error classification maps."""

from ._canonical import *
from ._canonical import ErrorAction, UnsupportedCapabilityError
from ._types import (
    DATABENTO_ERROR_MAP,
    DatabentoError,
    RateLimitResponse,
    VenueErrorClassification,
    WebSocketCloseInfo,
    ve,
)
from .altdata import VENUE_ERRORS_ALTDATA
from .cefi import VENUE_ERRORS_CEFI
from .defi import VENUE_ERRORS_DEFI, DefiAlertType, DefiErrorCode, OracleDeviationError, OracleStaleError
from .infra import INFRA_ERRORS
from .onchain_perps import VENUE_ERRORS_ONCHAIN_PERPS
from .sports import VENUE_ERRORS_SPORTS
from .tradfi import VENUE_ERRORS_TRADFI


def _merge_venue_error_maps(
    *maps: dict[str, list[VenueErrorClassification]],
) -> dict[str, list[VenueErrorClassification]]:
    """Merge venue error maps, combining lists for duplicate venue keys."""
    result: dict[str, list[VenueErrorClassification]] = {}
    for m in maps:
        for venue, codes in m.items():
            if venue in result:
                result[venue] = result[venue] + codes
            else:
                result[venue] = list(codes)
    return result


VENUE_ERROR_MAP: dict[str, list[VenueErrorClassification]] = _merge_venue_error_maps(
    VENUE_ERRORS_CEFI,
    VENUE_ERRORS_ALTDATA,
    VENUE_ERRORS_DEFI,
    VENUE_ERRORS_SPORTS,
    VENUE_ERRORS_TRADFI,
    VENUE_ERRORS_ONCHAIN_PERPS,
    INFRA_ERRORS,
)


def classify_venue_error(venue: str, error_code: str) -> VenueErrorClassification | None:
    """Classify a venue error code using normalized VENUE_ERROR_MAP."""
    venue_key = venue.lower()
    classifications = VENUE_ERROR_MAP.get(venue_key, [])
    code_str = str(error_code)
    for c in classifications:
        if c.error_code == code_str:
            return c
    return None


__all__ = [
    "DATABENTO_ERROR_MAP",
    "INFRA_ERRORS",
    "VENUE_ERRORS_ALTDATA",
    "VENUE_ERRORS_CEFI",
    "VENUE_ERRORS_DEFI",
    "VENUE_ERRORS_ONCHAIN_PERPS",
    "VENUE_ERRORS_SPORTS",
    "VENUE_ERRORS_TRADFI",
    "VENUE_ERROR_MAP",
    "DatabentoError",
    "DefiAlertType",
    "DefiErrorCode",
    "ErrorAction",
    "OracleDeviationError",
    "OracleStaleError",
    "RateLimitResponse",
    "UnsupportedCapabilityError",
    "VenueErrorClassification",
    "WebSocketCloseInfo",
    "classify_venue_error",
    "ve",
]
