"""Error normalizers (auto-split from errors.py)."""

from __future__ import annotations

from collections.abc import Callable

from unified_api_contracts.canonical.crosscutting.errors import (
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
)
from unified_api_contracts.normalize_utils.errors._utils import (
    BINANCE_MAP,
    from_http_status,
)


def normalize_binance_error(
    error_code: str | int,
    message: str = "",
    venue: str = "binance",
) -> CanonicalError:
    """Map a Binance REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = BINANCE_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Bitfinex
# ---------------------------------------------------------------------------

BITFINEX_MAP: dict[str, Callable[..., CanonicalError]] = {
    "10001": CanonicalAuthenticationError,  # Invalid API key
    "10020": CanonicalRateLimitError,  # Too many requests
    "10028": CanonicalInvalidRequestError,  # Invalid parameters
    "11000": CanonicalInsufficientBalanceError,  # Insufficient balance
    "11010": CanonicalOrderRejectedError,  # Order would immediately fill
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "429": CanonicalRateLimitError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_bitfinex_error(
    error_code: str | int,
    message: str = "",
    venue: str = "bitfinex",
) -> CanonicalError:
    """Map a Bitfinex REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = BITFINEX_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Bybit
# ---------------------------------------------------------------------------

BYBIT_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = BYBIT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# OKX
# ---------------------------------------------------------------------------

OKX_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = OKX_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Deribit
# ---------------------------------------------------------------------------

DERIBIT_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = DERIBIT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Coinbase
# ---------------------------------------------------------------------------

COINBASE_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = COINBASE_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Hyperliquid
# ---------------------------------------------------------------------------

HYPERLIQUID_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = HYPERLIQUID_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# CCXT (generic unified exchange library)
# ---------------------------------------------------------------------------

CCXT_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = CCXT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Tardis
# ---------------------------------------------------------------------------

TARDIS_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = TARDIS_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    # Fallback to generic HTTP status mapping for numeric codes
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Upbit
# ---------------------------------------------------------------------------

UPBIT_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = UPBIT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Alchemy (Web3 / on-chain RPC)
# ---------------------------------------------------------------------------

ALCHEMY_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = ALCHEMY_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# IBKR (Interactive Brokers)
# ---------------------------------------------------------------------------

IBKR_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = IBKR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Kalshi (US prediction market)
# ---------------------------------------------------------------------------

KALSHI_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = KALSHI_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Polymarket (DeFi prediction market)
# ---------------------------------------------------------------------------

POLYMARKET_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = POLYMARKET_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Betfair (sports betting exchange)
# ---------------------------------------------------------------------------

BETFAIR_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = BETFAIR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
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
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# KuCoin
# ---------------------------------------------------------------------------

KUCOIN_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = KUCOIN_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# MEXC
# ---------------------------------------------------------------------------

MEXC_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = MEXC_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Bitget
# ---------------------------------------------------------------------------

BITGET_MAP: dict[str, Callable[..., CanonicalError]] = {
    "40001": CanonicalAuthenticationError,  # ACCESS_KEY cannot be empty
    "40002": CanonicalAuthenticationError,  # SIGN cannot be empty
    "40003": CanonicalAuthenticationError,  # TIMESTAMP cannot be empty
    "40004": CanonicalAuthenticationError,  # Request timestamp too old
    "40005": CanonicalAuthenticationError,  # Invalid ACCESS_KEY
    "40006": CanonicalAuthenticationError,  # Invalid SIGN
    "40007": CanonicalAuthorizationError,  # IP not in whitelist
    "40018": CanonicalRateLimitError,  # Request frequency limit
    "43001": CanonicalInsufficientBalanceError,
    "45001": CanonicalOrderRejectedError,  # Order cancelled
    "45010": CanonicalSizeLimitError,  # Size too small
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_bitget_error(
    error_code: str | int,
    message: str = "",
    venue: str = "bitget",
) -> CanonicalError:
    """Map a Bitget REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = BITGET_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Databento
# ---------------------------------------------------------------------------


def normalize_databento_error(
    error_code: str | int,
    message: str = "",
    venue: str = "databento",
) -> CanonicalError:
    """Map a Databento HTTP status to a CanonicalError subclass.

    Databento uses standard HTTP semantics; no proprietary error codes.
    """
    code = str(error_code)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Aster
# ---------------------------------------------------------------------------

ASTER_MAP: dict[str, Callable[..., CanonicalError]] = {
    "RATE_LIMIT_EXCEEDED": CanonicalRateLimitError,
    "UNAUTHORIZED": CanonicalAuthenticationError,
    "FORBIDDEN": CanonicalAuthorizationError,
    "INVALID_ARGUMENT": CanonicalInvalidRequestError,
    "INSUFFICIENT_BALANCE": CanonicalInsufficientBalanceError,
    "ORDER_REJECTED": CanonicalOrderRejectedError,
    "MARKET_CLOSED": CanonicalMarketClosedError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_aster_error(
    error_code: str | int,
    message: str = "",
    venue: str = "aster",
) -> CanonicalError:
    """Map an Aster REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = ASTER_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# FIX protocol
# ---------------------------------------------------------------------------

FIX_MAP: dict[str, Callable[..., CanonicalError]] = {
    "0": CanonicalOrderRejectedError,  # OrdRejReason=0 (broker/exchange option)
    "1": CanonicalOrderRejectedError,  # OrdRejReason=1 (unknown symbol)
    "3": CanonicalOrderRejectedError,  # OrdRejReason=3 (order exceeds limit)
    "4": CanonicalInsufficientBalanceError,  # OrdRejReason=4 (too late to enter)
    "5": CanonicalOrderRejectedError,  # OrdRejReason=5 (unknown order)
    "6": CanonicalDuplicateOrderError,  # OrdRejReason=6 (duplicate order)
    "14": CanonicalSizeLimitError,  # OrdRejReason=14 (incorrect quantity)
    "15": CanonicalInvalidRequestError,  # OrdRejReason=15 (unknown account)
    "8": CanonicalMarketClosedError,  # ExecType=8 (rejected), OrdStatus=8
    "SESSION_REJECTED": CanonicalAuthenticationError,
    "LOGON_REJECTED": CanonicalAuthenticationError,
}


def normalize_fix_error(
    error_code: str | int,
    message: str = "",
    venue: str = "fix",
) -> CanonicalError:
    """Map a FIX protocol OrdRejReason or session error to a CanonicalError subclass."""
    code = str(error_code)
    cls = FIX_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Prime Broker
# ---------------------------------------------------------------------------
