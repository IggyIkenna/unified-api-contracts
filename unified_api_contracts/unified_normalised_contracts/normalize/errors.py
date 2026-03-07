"""Per-venue error normalizers — convert raw venue error codes to CanonicalError subclasses.

Provides:
- extract_rate_limit_headers: parse Retry-After / X-RateLimit-* from HTTP response headers
- normalize_<venue>_error: map a venue error code + message to the right CanonicalError subclass
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import re
from collections.abc import Callable
from email.utils import parsedate_to_datetime

from ..errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalContractExpiredError,
    CanonicalDuplicateOrderError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInsufficientMarginError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalMarketClosedError,
    CanonicalNetworkError,
    CanonicalOrderRejectedError,
    CanonicalPositionLimitExceededError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    CanonicalSizeLimitError,
    ErrorAction,
    RateLimitInfo,
)

# ---------------------------------------------------------------------------
# Header extraction
# ---------------------------------------------------------------------------

_HTTP_DATE_PATTERN = re.compile(r"[A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}")


def _parse_retry_after(value: str) -> float | None:
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
        pass
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
        retry_after = _parse_retry_after(raw_retry)

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
                pass

    return RateLimitInfo(
        retry_after=retry_after,
        limit=limit,
        remaining=remaining,
        reset=reset,
        endpoint=endpoint or None,
        venue=venue or None,
    )


# ---------------------------------------------------------------------------
# Generic HTTP status-code fallback helper
# ---------------------------------------------------------------------------


def _from_http_status(status: int, message: str, venue: str) -> CanonicalError:
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

_BINANCE_MAP: dict[str, Callable[..., CanonicalError]] = {
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


def normalize_binance_error(
    error_code: str | int,
    message: str = "",
    venue: str = "binance",
) -> CanonicalError:
    """Map a Binance REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BINANCE_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Bybit
# ---------------------------------------------------------------------------

_BYBIT_MAP: dict[str, Callable[..., CanonicalError]] = {
    "10006": CanonicalRateLimitError,
    "10001": CanonicalAuthenticationError,
    "10002": CanonicalAuthenticationError,
    "33004": CanonicalAuthenticationError,  # API key invalid
    "10000": CanonicalInternalServerError,
    "10019": CanonicalServiceUnavailableError,  # WS restarting
    "30086": CanonicalInsufficientBalanceError,
    "30088": CanonicalInsufficientBalanceError,
    "30032": CanonicalOrderRejectedError,
    "30037": CanonicalContractExpiredError,
    "110007": CanonicalInsufficientMarginError,
    "110043": CanonicalPositionLimitExceededError,
}


def normalize_bybit_error(
    error_code: str | int,
    message: str = "",
    venue: str = "bybit",
) -> CanonicalError:
    """Map a Bybit REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BYBIT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# OKX
# ---------------------------------------------------------------------------

_OKX_MAP: dict[str, Callable[..., CanonicalError]] = {
    "50011": CanonicalRateLimitError,
    "50013": CanonicalServiceUnavailableError,
    "50014": CanonicalInvalidRequestError,
    "50015": CanonicalInvalidRequestError,
    "50004": CanonicalServiceUnavailableError,  # WS closed
    "50026": CanonicalServiceUnavailableError,  # system busy
    "51000": CanonicalInvalidRequestError,
    "51008": CanonicalInsufficientBalanceError,
    "51010": CanonicalAuthorizationError,
    "50111": CanonicalAuthenticationError,
    "50112": CanonicalAuthenticationError,
}


def normalize_okx_error(
    error_code: str | int,
    message: str = "",
    venue: str = "okx",
) -> CanonicalError:
    """Map an OKX REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _OKX_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Deribit
# ---------------------------------------------------------------------------

_DERIBIT_MAP: dict[str, Callable[..., CanonicalError]] = {
    "10028": CanonicalRateLimitError,
    "10040": CanonicalRateLimitError,
    "13009": CanonicalInsufficientMarginError,
    "10009": CanonicalOrderRejectedError,
    "11044": CanonicalInsufficientBalanceError,
    "13010": CanonicalAuthenticationError,  # token revoked
    "13004": CanonicalAuthenticationError,  # invalid credentials
    "11028": CanonicalInvalidRequestError,
    "10010": CanonicalContractExpiredError,
}


def normalize_deribit_error(
    error_code: str | int,
    message: str = "",
    venue: str = "deribit",
) -> CanonicalError:
    """Map a Deribit JSON-RPC error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _DERIBIT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Coinbase
# ---------------------------------------------------------------------------

_COINBASE_MAP: dict[str, Callable[..., CanonicalError]] = {
    "RATE_LIMIT_EXCEEDED": CanonicalRateLimitError,
    "UNAUTHORIZED": CanonicalAuthorizationError,
    "INTERNAL_SERVICE_ERROR": CanonicalInternalServerError,
    "TEMPORARILY_UNAVAILABLE": CanonicalServiceUnavailableError,
    "INVALID_ARGUMENT": CanonicalInvalidRequestError,
    "INSUFFICIENT_FUND": CanonicalInsufficientBalanceError,
    "ORDER_REJECTED": CanonicalOrderRejectedError,
}


def normalize_coinbase_error(
    error_code: str | int,
    message: str = "",
    venue: str = "coinbase",
) -> CanonicalError:
    """Map a Coinbase Advanced Trade API error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _COINBASE_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Hyperliquid
# ---------------------------------------------------------------------------

_HYPERLIQUID_MAP: dict[str, Callable[..., CanonicalError]] = {
    "RATE_LIMIT": CanonicalRateLimitError,
    "INSUFFICIENT_MARGIN": CanonicalInsufficientMarginError,
    "ORDER_REJECTED": CanonicalOrderRejectedError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_hyperliquid_error(
    error_code: str | int,
    message: str = "",
    venue: str = "hyperliquid",
) -> CanonicalError:
    """Map a Hyperliquid error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _HYPERLIQUID_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# CCXT (generic unified exchange library)
# ---------------------------------------------------------------------------

_CCXT_MAP: dict[str, Callable[..., CanonicalError]] = {
    "RateLimitExceeded": CanonicalRateLimitError,
    "AuthenticationError": CanonicalAuthenticationError,
    "PermissionDenied": CanonicalAuthorizationError,
    "InsufficientFunds": CanonicalInsufficientBalanceError,
    "InvalidOrder": CanonicalOrderRejectedError,
    "OrderNotFound": CanonicalOrderRejectedError,
    "ExchangeNotAvailable": CanonicalServiceUnavailableError,
    "NetworkError": CanonicalNetworkError,
    "ExchangeError": CanonicalInternalServerError,
    "DDoSProtection": CanonicalRateLimitError,
    "BadSymbol": CanonicalInvalidRequestError,
    "BadRequest": CanonicalInvalidRequestError,
    "MarginModeAlreadySet": CanonicalInvalidRequestError,
    "InsufficientMargin": CanonicalInsufficientMarginError,
}


def normalize_ccxt_error(
    error_code: str | int,
    message: str = "",
    venue: str = "ccxt",
) -> CanonicalError:
    """Map a CCXT exception class name to a CanonicalError subclass."""
    code = str(error_code)
    cls = _CCXT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Tardis
# ---------------------------------------------------------------------------

_TARDIS_MAP: dict[str, Callable[..., CanonicalError]] = {
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_tardis_error(
    error_code: str | int,
    message: str = "",
    venue: str = "tardis",
) -> CanonicalError:
    """Map a Tardis HTTP status code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _TARDIS_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    # Fallback to generic HTTP status mapping for numeric codes
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Upbit
# ---------------------------------------------------------------------------

_UPBIT_MAP: dict[str, Callable[..., CanonicalError]] = {
    "too_many_requests": CanonicalRateLimitError,
    "invalid_access_key": CanonicalAuthenticationError,
    "invalid_query_payload": CanonicalInvalidRequestError,
    "jwt_verification": CanonicalAuthenticationError,
    "expired_access_key": CanonicalAuthenticationError,
    "nonce_used": CanonicalDuplicateOrderError,
    "no_authorization_i_p": CanonicalAuthorizationError,
    "out_of_scope": CanonicalAuthorizationError,
}


def normalize_upbit_error(
    error_code: str | int,
    message: str = "",
    venue: str = "upbit",
) -> CanonicalError:
    """Map an Upbit error name to a CanonicalError subclass."""
    code = str(error_code)
    cls = _UPBIT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Alchemy (Web3 / on-chain RPC)
# ---------------------------------------------------------------------------

_ALCHEMY_MAP: dict[str, Callable[..., CanonicalError]] = {
    "-32600": CanonicalInvalidRequestError,  # Invalid request
    "-32601": CanonicalInvalidRequestError,  # Method not found
    "-32602": CanonicalInvalidRequestError,  # Invalid params
    "-32603": CanonicalInternalServerError,  # Internal error
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
}


def normalize_alchemy_error(
    error_code: str | int,
    message: str = "",
    venue: str = "alchemy",
) -> CanonicalError:
    """Map an Alchemy RPC or HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _ALCHEMY_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# IBKR (Interactive Brokers)
# ---------------------------------------------------------------------------

_IBKR_MAP: dict[str, Callable[..., CanonicalError]] = {
    "100": CanonicalServiceUnavailableError,  # market data farm disconnected
    "1100": CanonicalNetworkError,  # connectivity lost
    "1300": CanonicalOrderRejectedError,  # order rejected
    "200": CanonicalInvalidRequestError,  # no security definition
    "201": CanonicalOrderRejectedError,  # order rejected
    "2110": CanonicalServiceUnavailableError,  # connectivity between IB and TWS broken
    "10147": CanonicalOrderRejectedError,  # OrderId is not permissioned
    "10148": CanonicalInvalidRequestError,  # OrderId that has been cancelled
}


def normalize_ibkr_error(
    error_code: str | int,
    message: str = "",
    venue: str = "ibkr",
) -> CanonicalError:
    """Map an IBKR TWS/Gateway error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _IBKR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Kalshi (US prediction market)
# ---------------------------------------------------------------------------

_KALSHI_MAP: dict[str, Callable[..., CanonicalError]] = {
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "400": CanonicalInvalidRequestError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "MARKET_CLOSED": CanonicalMarketClosedError,
    "ORDER_REJECTED": CanonicalOrderRejectedError,
}


def normalize_kalshi_error(
    error_code: str | int,
    message: str = "",
    venue: str = "kalshi",
) -> CanonicalError:
    """Map a Kalshi HTTP status or error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _KALSHI_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Polymarket (DeFi prediction market)
# ---------------------------------------------------------------------------

_POLYMARKET_MAP: dict[str, Callable[..., CanonicalError]] = {
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "400": CanonicalInvalidRequestError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
    "RATE_LIMIT": CanonicalRateLimitError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "MARKET_CLOSED": CanonicalMarketClosedError,
}


def normalize_polymarket_error(
    error_code: str | int,
    message: str = "",
    venue: str = "polymarket",
) -> CanonicalError:
    """Map a Polymarket HTTP status or error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _POLYMARKET_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Betfair (sports betting exchange)
# ---------------------------------------------------------------------------

_BETFAIR_MAP: dict[str, Callable[..., CanonicalError]] = {
    "TOO_MANY_REQUESTS": CanonicalRateLimitError,
    "ANGX-0001": CanonicalRateLimitError,  # Exceeded throttle limit
    "INVALID_SESSION_INFORMATION": CanonicalAuthenticationError,
    "NO_APP_KEY": CanonicalAuthenticationError,
    "INVALID_APP_KEY": CanonicalAuthenticationError,
    "SERVICE_BUSY": CanonicalServiceUnavailableError,
    "TIMEOUT_ERROR": CanonicalServiceUnavailableError,
    "MARKET_CLOSED": CanonicalMarketClosedError,
    "MARKET_SUSPENDED": CanonicalMarketClosedError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "INVALID_BET_SIZE": CanonicalSizeLimitError,
    "BET_OUTSIDE_PRICE_BOUNDS": CanonicalInvalidRequestError,
    "INVALID_PROFIT_RATIO": CanonicalInvalidRequestError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
}


def normalize_betfair_error(
    error_code: str | int,
    message: str = "",
    venue: str = "betfair",
) -> CanonicalError:
    """Map a Betfair JSON-RPC or HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BETFAIR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Versifi (DeFi/on-chain venue; HTTP-status driven)
# ---------------------------------------------------------------------------


def normalize_versifi_error(
    error_code: str | int,
    message: str = "",
    venue: str = "versifi",
) -> CanonicalError:
    """Map a Versifi HTTP status code to a CanonicalError subclass.

    Versifi follows standard HTTP semantics without proprietary error codes.
    """
    code = str(error_code)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Kraken
# ---------------------------------------------------------------------------

_KRAKEN_MAP: dict[str, Callable[..., CanonicalError]] = {
    "EGeneral:Too many requests": CanonicalRateLimitError,
    "EAPI:Rate limit exceeded": CanonicalRateLimitError,
    "EAPI:Invalid key": CanonicalAuthenticationError,
    "EAPI:Invalid signature": CanonicalAuthenticationError,
    "EAPI:Invalid nonce": CanonicalAuthenticationError,
    "EOrder:Insufficient funds": CanonicalInsufficientBalanceError,
    "EOrder:Order minimum not met": CanonicalSizeLimitError,
    "EOrder:Orders limit exceeded": CanonicalRateLimitError,
    "EOrder:Rate limit exceeded": CanonicalRateLimitError,
    "EOrder:Unknown order": CanonicalOrderRejectedError,
    "EOrder:Cannot open position": CanonicalOrderRejectedError,
    "EService:Unavailable": CanonicalServiceUnavailableError,
    "EService:Busy": CanonicalServiceUnavailableError,
    "EService:Market in cancel_only mode": CanonicalMarketClosedError,
    "EService:Market in post_only mode": CanonicalMarketClosedError,
    "EService:Deadline elapsed": CanonicalServiceUnavailableError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
}


def normalize_kraken_error(
    error_code: str | int,
    message: str = "",
    venue: str = "kraken",
) -> CanonicalError:
    """Map a Kraken REST/WS error string or HTTP status to a CanonicalError subclass."""
    code = str(error_code)
    cls = _KRAKEN_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# KuCoin
# ---------------------------------------------------------------------------

_KUCOIN_MAP: dict[str, Callable[..., CanonicalError]] = {
    "200004": CanonicalInsufficientBalanceError,  # Insufficient balance
    "900001": CanonicalInvalidRequestError,  # Invalid parameter
    "400100": CanonicalInvalidRequestError,  # Invalid parameter
    "400200": CanonicalInvalidRequestError,  # Forbidden, user not allowed
    "400500": CanonicalOrderRejectedError,  # Your order is below minimum order size
    "400700": CanonicalSizeLimitError,  # Order size limit
    "401000": CanonicalRateLimitError,  # Rate limit exceeded
    "411100": CanonicalMarketClosedError,  # User is frozen
    "500000": CanonicalInternalServerError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
}


def normalize_kucoin_error(
    error_code: str | int,
    message: str = "",
    venue: str = "kucoin",
) -> CanonicalError:
    """Map a KuCoin REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _KUCOIN_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# MEXC
# ---------------------------------------------------------------------------

_MEXC_MAP: dict[str, Callable[..., CanonicalError]] = {
    "10072": CanonicalAuthenticationError,  # Invalid access key
    "10073": CanonicalAuthenticationError,  # Signature mismatch
    "10074": CanonicalAuthenticationError,  # Signature expired
    "10076": CanonicalAuthorizationError,  # IP not whitelisted
    "30004": CanonicalInsufficientBalanceError,
    "30005": CanonicalInvalidRequestError,  # Price invalid
    "30016": CanonicalOrderRejectedError,  # Order not found
    "30018": CanonicalSizeLimitError,  # Below min amount
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_mexc_error(
    error_code: str | int,
    message: str = "",
    venue: str = "mexc",
) -> CanonicalError:
    """Map a MEXC REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _MEXC_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Huobi / HTX
# ---------------------------------------------------------------------------

_HUOBI_MAP: dict[str, Callable[..., CanonicalError]] = {
    "api-signature-not-valid": CanonicalAuthenticationError,
    "api-not-support": CanonicalAuthorizationError,
    "gateway-internal-error": CanonicalInternalServerError,
    "too-many-requests": CanonicalRateLimitError,
    "account-frozen-balance-insufficient-error": CanonicalInsufficientBalanceError,
    "order-limitorder-amount-min-error": CanonicalSizeLimitError,
    "order-limitorder-order-id-not-exist": CanonicalOrderRejectedError,
    "base-symbol-error": CanonicalInvalidRequestError,
    "system-maintenance": CanonicalServiceUnavailableError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_huobi_error(
    error_code: str | int,
    message: str = "",
    venue: str = "huobi",
) -> CanonicalError:
    """Map a Huobi/HTX REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _HUOBI_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Part 2 venues — imported from errors_alt to keep this file under 900 lines
# ---------------------------------------------------------------------------

from .errors_alt import (  # noqa: E402
    normalize_api_football_error,
    normalize_arkham_error,
    normalize_aster_error,
    normalize_betdaq_error,
    normalize_bitfinex_error,
    normalize_bitget_error,
    normalize_bitstamp_error,
    normalize_bloxroute_error,
    normalize_cloud_sdks_error,
    normalize_databento_error,
    normalize_defillama_error,
    normalize_dydx_error,
    normalize_fix_error,
    normalize_footystats_error,
    normalize_gateio_error,
    normalize_github_error,
    normalize_glassnode_error,
    normalize_manifold_error,
    normalize_metabet_error,
    normalize_nautilus_error,
    normalize_odds_api_error,
    normalize_odds_engine_error,
    normalize_open_meteo_error,
    normalize_pinnacle_error,
    normalize_prime_broker_error,
    normalize_regulatory_error,
    normalize_sharpapi_error,
    normalize_smarkets_error,
    normalize_sports_error,
    normalize_thegraph_error,
    normalize_transfermarkt_error,
    normalize_understat_error,
    normalize_yahoo_finance_error,
)
from .errors_matchbook import normalize_matchbook_error  # noqa: E402

# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------

__all__ = [
    "extract_rate_limit_headers",
    "normalize_alchemy_error",
    "normalize_api_football_error",
    "normalize_arkham_error",
    "normalize_aster_error",
    "normalize_betdaq_error",
    "normalize_betfair_error",
    "normalize_binance_error",
    "normalize_bitfinex_error",
    "normalize_bitget_error",
    "normalize_bitstamp_error",
    "normalize_bloxroute_error",
    "normalize_bybit_error",
    "normalize_ccxt_error",
    "normalize_cloud_sdks_error",
    "normalize_coinbase_error",
    "normalize_databento_error",
    "normalize_defillama_error",
    "normalize_deribit_error",
    "normalize_dydx_error",
    "normalize_fix_error",
    "normalize_footystats_error",
    "normalize_gateio_error",
    "normalize_github_error",
    "normalize_glassnode_error",
    "normalize_huobi_error",
    "normalize_hyperliquid_error",
    "normalize_ibkr_error",
    "normalize_kalshi_error",
    "normalize_kraken_error",
    "normalize_kucoin_error",
    "normalize_manifold_error",
    "normalize_matchbook_error",
    "normalize_metabet_error",
    "normalize_mexc_error",
    "normalize_nautilus_error",
    "normalize_odds_api_error",
    "normalize_odds_engine_error",
    "normalize_okx_error",
    "normalize_open_meteo_error",
    "normalize_pinnacle_error",
    "normalize_polymarket_error",
    "normalize_prime_broker_error",
    "normalize_regulatory_error",
    "normalize_sharpapi_error",
    "normalize_smarkets_error",
    "normalize_sports_error",
    "normalize_tardis_error",
    "normalize_thegraph_error",
    "normalize_transfermarkt_error",
    "normalize_understat_error",
    "normalize_upbit_error",
    "normalize_versifi_error",
    "normalize_yahoo_finance_error",
]
