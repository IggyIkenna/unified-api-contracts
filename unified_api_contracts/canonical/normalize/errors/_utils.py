"""Per-venue error normalizers — convert raw venue error codes to CanonicalError subclasses.

Provides:
- extract_rate_limit_headers: parse Retry-After / X-RateLimit-* from HTTP response headers
- normalize_<venue>_error: map a venue error code + message to the right CanonicalError subclass
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import logging
import re
from collections.abc import Callable
from email.utils import parsedate_to_datetime

from unified_api_contracts.canonical.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
    RateLimitInfo,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Header extraction
# ---------------------------------------------------------------------------

_HTTP_DATE_PATTERN = re.compile(r"[A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}")


def parse_retry_after(value: str) -> float | None:
    """Parse Retry-After header value.

    Accepts either an integer number of seconds or an HTTP-date string.
    Returns seconds as float, or None if unparseable.
    """
    stripped = value.strip()
    if stripped.isdigit():
        return float(stripped)
    try:
        # Attempt to parse integer seconds (may have decimals)
        return float(stripped)
    except ValueError:
        _logger.debug("Retry-After value %r is not a float; trying HTTP-date parse", stripped)
    try:
        # Attempt HTTP-date (RFC 7231)
        dt = parsedate_to_datetime(stripped)
        now = _dt.datetime.now(tz=_dt.UTC)
        delta = (dt - now).total_seconds()
        return max(0.0, delta)
    except (ValueError, OverflowError, TypeError, OSError):
        return None


def extract_rate_limit_headers(
    headers: dict[str, str],
    venue: str = "",
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit metadata from HTTP response headers.

    Parses (case-insensitive lookup):
    - Retry-After           → retry_after (seconds)
    - X-RateLimit-Limit     → limit
    - X-RateLimit-Remaining → remaining
    - X-RateLimit-Reset     → reset (unix timestamp)
    - X-RateLimit-Used      → (used; computed remaining = limit - used if remaining absent)

    Returns a RateLimitInfo dataclass.
    """
    # Normalise header keys to lower-case for case-insensitive lookup
    lower: dict[str, str] = {k.lower(): v for k, v in headers.items()}

    retry_after: float | None = None
    raw_retry = lower.get("retry-after")
    if raw_retry is not None:
        retry_after = parse_retry_after(raw_retry)

    limit: int | None = None
    raw_limit = lower.get("x-ratelimit-limit")
    if raw_limit is not None:
        with contextlib.suppress(ValueError):
            limit = int(raw_limit)

    remaining: int | None = None
    raw_remaining = lower.get("x-ratelimit-remaining")
    if raw_remaining is not None:
        with contextlib.suppress(ValueError):
            remaining = int(raw_remaining)

    reset: float | None = None
    raw_reset = lower.get("x-ratelimit-reset")
    if raw_reset is not None:
        with contextlib.suppress(ValueError):
            reset = float(raw_reset)

    # If remaining is absent but used + limit are available, compute it
    if remaining is None and limit is not None:
        raw_used = lower.get("x-ratelimit-used")
        if raw_used is not None:
            try:
                used = int(raw_used)
                remaining = max(0, limit - used)
            except ValueError:
                _logger.debug("X-RateLimit-Used header %r is not an integer; skipping computed remaining", raw_used)

    retry_after_val: float | None = retry_after
    return RateLimitInfo(
        retry_after=retry_after_val,
        limit=limit,
        remaining=remaining,
        reset=reset,
        endpoint=endpoint or None,
        venue=venue or None,
    )


# ---------------------------------------------------------------------------
# Generic HTTP status-code fallback helper
# ---------------------------------------------------------------------------


def from_http_status(status: int, message: str, venue: str) -> CanonicalError:
    """Map an HTTP status code to the closest CanonicalError subclass."""
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


# ---------------------------------------------------------------------------
# Binance
# ---------------------------------------------------------------------------

BINANCE_MAP: dict[str, Callable[..., CanonicalError]] = {
    "-1003": CanonicalRateLimitError,
    "-1015": CanonicalRateLimitError,
    "418": CanonicalRateLimitError,  # IP banned after too many 429s
    "-1013": CanonicalInvalidRequestError,
    "-1111": CanonicalInvalidRequestError,
    "-2010": CanonicalOrderRejectedError,
    "-2011": CanonicalOrderRejectedError,
    "-2018": CanonicalInsufficientBalanceError,
    "-2019": CanonicalInsufficientBalanceError,
    "-1100": CanonicalInvalidRequestError,
    "-1102": CanonicalInvalidRequestError,
    "-1121": CanonicalInvalidRequestError,  # invalid symbol
    "-2013": CanonicalOrderRejectedError,  # order does not exist
    "-1022": CanonicalAuthenticationError,  # invalid signature
    "-2014": CanonicalAuthenticationError,  # API-key format invalid
    "-2015": CanonicalAuthorizationError,  # invalid API-key, IP, or permissions
}
