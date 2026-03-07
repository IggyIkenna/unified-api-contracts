"""Matchbook error normalizer — kept in its own module to preserve errors_alt.py size limit."""

from __future__ import annotations

from collections.abc import Callable

from ..errors import (
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

_MATCHBOOK_MAP: dict[str, Callable[..., CanonicalError]] = {
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


def _from_http_status(status: int, message: str, venue: str) -> CanonicalError:
    if status == 400:
        return CanonicalInvalidRequestError(message=message, venue=venue)
    if status == 401:
        return CanonicalAuthenticationError(message=message, venue=venue)
    if status == 403:
        return CanonicalAuthorizationError(message=message, venue=venue)
    if status == 429:
        return CanonicalRateLimitError(message=message, venue=venue)
    if status == 503:
        return CanonicalServiceUnavailableError(message=message, venue=venue)
    if status >= 500:
        return CanonicalInternalServerError(message=message, venue=venue)
    return CanonicalError(code=str(status), message=message, action=ErrorAction.FAIL, venue=venue)


def normalize_matchbook_error(
    error_code: str | int,
    message: str = "",
    venue: str = "matchbook",
) -> CanonicalError:
    """Map a Matchbook REST error code to a CanonicalError subclass."""
    code = str(error_code).upper()
    cls = _MATCHBOOK_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    # Numeric codes: try original string form for exact match
    cls = _MATCHBOOK_MAP.get(str(error_code))
    if cls is not None:
        return cls(message=message or str(error_code), venue=venue)
    try:
        status = int(str(error_code))
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=str(error_code), message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = ["normalize_matchbook_error"]
