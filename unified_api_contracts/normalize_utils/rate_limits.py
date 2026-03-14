"""Rate limit header extraction and venue-specific rate limit normalizers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from ..canonical.crosscutting.errors import RateLimitInfo

_logger = logging.getLogger(__name__)


def extract_rate_limit_headers(
    headers: dict[str, str],
    venue: str = "",
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from HTTP response headers.

    Handles: Retry-After (seconds or HTTP-date), X-RateLimit-Limit,
    X-RateLimit-Remaining, X-RateLimit-Reset, X-RateLimit-Used.
    Also handles X-Rate-Limit-* variants.
    """
    h = {k.lower(): v for k, v in headers.items()}

    retry_after: float | None = None
    raw_retry = h.get("retry-after")
    if raw_retry is not None:
        try:
            retry_after = float(raw_retry)
        except ValueError:
            try:
                dt = parsedate_to_datetime(raw_retry)
                retry_after = max(0.0, (dt - datetime.now(UTC)).total_seconds())
            except (ValueError, OverflowError, TypeError, OSError):
                retry_after = None

    def _int(key: str) -> int | None:
        v = h.get(key)
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def _float(key: str) -> float | None:
        v = h.get(key) or h.get(key.replace("-", "_"))
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    limit = _int("x-ratelimit-limit") or _int("x-rate-limit-limit")
    remaining = _int("x-ratelimit-remaining") or _int("x-rate-limit-remaining")
    reset = _float("x-ratelimit-reset") or _float("x-rate-limit-reset")

    return RateLimitInfo(
        retry_after=retry_after,
        limit=limit,
        remaining=remaining,
        reset=reset,
        endpoint=endpoint or None,
        venue=venue or None,
    )


def extract_binance_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from Binance HTTP response headers.

    Binance uses X-MBX-USED-WEIGHT-1M (spot/derivatives weight usage) and
    X-MBX-ORDER-COUNT-10S (order count limit). Falls back to generic headers.
    Default spot weight limit is 6000/min (Binance Spot API v3 as of 2025).
    """
    info = extract_rate_limit_headers(headers, venue="binance", endpoint=endpoint)
    if info.limit is None:
        h = {k.lower(): v for k, v in headers.items()}
        weight_used = h.get("x-mbx-used-weight-1m")
        if weight_used is not None:
            try:
                used = int(weight_used)
                # Binance Spot API default: 6000 weight per minute
                limit = 6000
                info = RateLimitInfo(
                    retry_after=info.retry_after,
                    limit=limit,
                    remaining=limit - used,
                    reset=info.reset,
                    endpoint=endpoint or None,
                    venue="binance",
                )
            except (ValueError, TypeError):
                _logger.debug(
                    "Binance X-MBX-USED-WEIGHT-1M header %r is not a valid integer; skipping rate limit enrichment",
                    weight_used,
                )
    return info


def extract_bybit_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from Bybit HTTP response headers.

    Bybit uses X-Bapi-Limit (total limit), X-Bapi-Limit-Status (remaining),
    and X-Bapi-Limit-Reset-Timestamp (reset epoch ms).
    """
    h = {k.lower(): v for k, v in headers.items()}

    def _int(k: str) -> int | None:
        val = h.get(k)
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def _float(k: str) -> float | None:
        val = h.get(k)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    retry_after = extract_rate_limit_headers(headers).retry_after

    return RateLimitInfo(
        retry_after=retry_after,
        limit=_int("x-bapi-limit"),
        remaining=_int("x-bapi-limit-status"),
        reset=_float("x-bapi-limit-reset-timestamp"),
        endpoint=endpoint or None,
        venue="bybit",
    )


def extract_okx_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from OKX HTTP response headers.

    OKX uses standard X-RateLimit-* headers.
    """
    return extract_rate_limit_headers(headers, venue="okx", endpoint=endpoint)


def extract_deribit_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from Deribit HTTP response headers.

    Deribit uses standard X-RateLimit-* headers.
    """
    return extract_rate_limit_headers(headers, venue="deribit", endpoint=endpoint)


def extract_coinbase_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from Coinbase HTTP response headers.

    Coinbase Advanced Trade API uses standard X-RateLimit-* headers
    plus Retry-After on 429.
    """
    return extract_rate_limit_headers(headers, venue="coinbase", endpoint=endpoint)


def extract_hyperliquid_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from Hyperliquid HTTP response headers.

    Hyperliquid uses standard Retry-After on 429; no documented custom headers.
    """
    return extract_rate_limit_headers(headers, venue="hyperliquid", endpoint=endpoint)


def extract_tardis_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from Tardis HTTP response headers.

    Tardis uses standard X-RateLimit-* headers and Retry-After on 429.
    """
    return extract_rate_limit_headers(headers, venue="tardis", endpoint=endpoint)


def extract_deribit_ws_rate_limit(
    error_data: dict[str, str | int | None],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from a Deribit WS error response.

    Deribit can send rate limit errors over WebSocket; error.data may contain
    retry_after (seconds) as an integer or string.
    """
    retry_after: float | None = None
    raw = error_data.get("retry_after") or error_data.get("retryAfter")
    if raw is not None:
        try:
            retry_after = float(str(raw))
        except (ValueError, TypeError):
            retry_after = None
    return RateLimitInfo(
        retry_after=retry_after,
        limit=None,
        remaining=None,
        reset=None,
        endpoint=endpoint or None,
        venue="deribit",
    )


def extract_api_football_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from API-Football response headers.

    API-Football uses x-ratelimit-requests-limit and x-ratelimit-requests-remaining.
    """
    h = {k.lower(): v for k, v in headers.items()}

    def _int(key: str) -> int | None:
        val = h.get(key)
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    limit = _int("x-ratelimit-requests-limit") or _int("x-ratelimit-limit")
    remaining = _int("x-ratelimit-requests-remaining") or _int("x-ratelimit-remaining")
    retry_after = extract_rate_limit_headers(headers).retry_after

    return RateLimitInfo(
        retry_after=retry_after,
        limit=limit,
        remaining=remaining,
        reset=None,
        endpoint=endpoint or None,
        venue="api_football",
    )


def extract_github_rate_limit(
    headers: dict[str, str],
    endpoint: str = "",
) -> RateLimitInfo:
    """Extract rate limit info from GitHub API response headers.

    GitHub uses x-ratelimit-limit, x-ratelimit-remaining, x-ratelimit-reset,
    and x-ratelimit-used.
    """
    return extract_rate_limit_headers(headers, venue="github", endpoint=endpoint)


__all__ = [
    "extract_api_football_rate_limit",
    "extract_binance_rate_limit",
    "extract_bybit_rate_limit",
    "extract_coinbase_rate_limit",
    "extract_deribit_rate_limit",
    "extract_deribit_ws_rate_limit",
    "extract_github_rate_limit",
    "extract_hyperliquid_rate_limit",
    "extract_okx_rate_limit",
    "extract_rate_limit_headers",
    "extract_tardis_rate_limit",
]
