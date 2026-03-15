"""Matchbook normalizers — all normalize_matchbook_* functions.

Extracted from normalize_utils/ modules (instruments, errors).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from ...canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from ...canonical.domain import CanonicalInstrument
from ...normalize_utils.errors._utils import from_http_status
from .schemas import MatchbookMarket

# ---------------------------------------------------------------------------
# Instrument normalizer (from normalize_utils/instruments.py)
# ---------------------------------------------------------------------------


def normalize_matchbook_market(
    raw: MatchbookMarket,
    venue: str = "matchbook",
) -> CanonicalInstrument:
    """Normalize MatchbookMarket to CanonicalInstrument."""
    sym = str(raw.id or "")
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


# ---------------------------------------------------------------------------
# Error normalizer (from normalize_utils/errors/_normalize_b.py)
# ---------------------------------------------------------------------------


MATCHBOOK_MAP: dict[str, Callable[..., CanonicalError]] = {
    "UNAUTHORIZED": CanonicalAuthenticationError,
    "FORBIDDEN": CanonicalAuthorizationError,
    "BAD_REQUEST": CanonicalInvalidRequestError,
    "NOT_FOUND": CanonicalOrderRejectedError,
    "TOO_MANY_REQUESTS": CanonicalRateLimitError,
    "SERVICE_UNAVAILABLE": CanonicalServiceUnavailableError,
    "INTERNAL_SERVER_ERROR": CanonicalInternalServerError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_matchbook_error(
    error_code: str | int,
    message: str = "",
    venue: str = "matchbook",
) -> CanonicalError:
    """Map a Matchbook REST error code to a CanonicalError subclass."""
    code = str(error_code).upper()
    cls = MATCHBOOK_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    # Numeric codes: try original string form for exact match
    cls = MATCHBOOK_MAP.get(str(error_code))
    if cls is not None:
        return cls(message=message or str(error_code), venue=venue)
    try:
        status = int(str(error_code))
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=str(error_code), message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_matchbook_error",
    "normalize_matchbook_market",
]
