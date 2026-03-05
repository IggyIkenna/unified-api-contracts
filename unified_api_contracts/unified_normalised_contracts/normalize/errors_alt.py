"""Per-venue error normalizers — part 2 (bitget through yahoo_finance).

Continued from errors.py. Imported and re-exported by errors.py so consumers
always import from the top-level ``normalize.errors`` module.
"""

from __future__ import annotations

from collections.abc import Callable

from ..errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalDuplicateOrderError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInsufficientMarginError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalMarketClosedError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    CanonicalSizeLimitError,
    ErrorAction,
)


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
# Bitget
# ---------------------------------------------------------------------------

_BITGET_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = _BITGET_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# dYdX v4
# ---------------------------------------------------------------------------

_DYDX_MAP: dict[str, Callable[..., CanonicalError]] = {
    "INVALID_ARGUMENT": CanonicalInvalidRequestError,
    "NOT_FOUND": CanonicalOrderRejectedError,
    "ALREADY_EXISTS": CanonicalDuplicateOrderError,
    "PERMISSION_DENIED": CanonicalAuthorizationError,
    "UNAUTHENTICATED": CanonicalAuthenticationError,
    "RESOURCE_EXHAUSTED": CanonicalRateLimitError,
    "INTERNAL": CanonicalInternalServerError,
    "UNAVAILABLE": CanonicalServiceUnavailableError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_dydx_error(
    error_code: str | int,
    message: str = "",
    venue: str = "dydx",
) -> CanonicalError:
    """Map a dYdX v4 gRPC/HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _DYDX_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
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
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Aster
# ---------------------------------------------------------------------------

_ASTER_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = _ASTER_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# FIX protocol
# ---------------------------------------------------------------------------

_FIX_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = _FIX_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Prime Broker
# ---------------------------------------------------------------------------


def normalize_prime_broker_error(
    error_code: str | int,
    message: str = "",
    venue: str = "prime_broker",
) -> CanonicalError:
    """Map a prime broker HTTP status to a CanonicalError subclass.

    Prime brokers typically use standard HTTP semantics.
    """
    code = str(error_code)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Nautilus Trader
# ---------------------------------------------------------------------------

_NAUTILUS_MAP: dict[str, Callable[..., CanonicalError]] = {
    "ORDER_DENIED": CanonicalOrderRejectedError,
    "POSITION_NOT_FOUND": CanonicalOrderRejectedError,
    "INSUFFICIENT_MARGIN": CanonicalInsufficientMarginError,
    "ACCOUNT_NOT_FOUND": CanonicalInvalidRequestError,
    "INVALID_QUANTITY": CanonicalSizeLimitError,
    "VENUE_NOT_AVAILABLE": CanonicalServiceUnavailableError,
}


def normalize_nautilus_error(
    error_code: str | int,
    message: str = "",
    venue: str = "nautilus",
) -> CanonicalError:
    """Map a Nautilus Trader error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _NAUTILUS_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Betdaq
# ---------------------------------------------------------------------------

_BETDAQ_MAP: dict[str, Callable[..., CanonicalError]] = {
    "6": CanonicalAuthenticationError,  # AccountSuspended
    "8": CanonicalAuthenticationError,  # InvalidCredentials
    "17": CanonicalOrderRejectedError,  # OrderDoesNotExist
    "40": CanonicalInsufficientBalanceError,  # InsufficientFunds
    "41": CanonicalSizeLimitError,  # BelowMinimumStake
    "42": CanonicalSizeLimitError,  # AboveMaximumStake
    "1001": CanonicalRateLimitError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_betdaq_error(
    error_code: str | int,
    message: str = "",
    venue: str = "betdaq",
) -> CanonicalError:
    """Map a Betdaq SOAP/REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BETDAQ_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Smarkets
# ---------------------------------------------------------------------------

_SMARKETS_MAP: dict[str, Callable[..., CanonicalError]] = {
    "unauthorized": CanonicalAuthenticationError,
    "forbidden": CanonicalAuthorizationError,
    "bad_request": CanonicalInvalidRequestError,
    "not_found": CanonicalOrderRejectedError,
    "too_many_requests": CanonicalRateLimitError,
    "service_unavailable": CanonicalServiceUnavailableError,
    "internal_server_error": CanonicalInternalServerError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_smarkets_error(
    error_code: str | int,
    message: str = "",
    venue: str = "smarkets",
) -> CanonicalError:
    """Map a Smarkets REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _SMARKETS_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Pinnacle
# ---------------------------------------------------------------------------

_PINNACLE_MAP: dict[str, Callable[..., CanonicalError]] = {
    "ACCOUNT_PROBLEM": CanonicalAuthorizationError,
    "ABOVE_MAX_BET_AMOUNT": CanonicalSizeLimitError,
    "BELOW_MIN_BET_AMOUNT": CanonicalSizeLimitError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "LINE_CHANGED": CanonicalOrderRejectedError,
    "ODDS_CHANGED": CanonicalOrderRejectedError,
    "PAST_CUTOFFTIME": CanonicalMarketClosedError,
    "DUPLICATE_UNIQUE_REQUEST_ID": CanonicalDuplicateOrderError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_pinnacle_error(
    error_code: str | int,
    message: str = "",
    venue: str = "pinnacle",
) -> CanonicalError:
    """Map a Pinnacle REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _PINNACLE_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Manifold Markets
# ---------------------------------------------------------------------------


def normalize_manifold_error(
    error_code: str | int,
    message: str = "",
    venue: str = "manifold",
) -> CanonicalError:
    """Map a Manifold Markets HTTP status to a CanonicalError subclass."""
    code = str(error_code)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# API-Football
# ---------------------------------------------------------------------------


def normalize_api_football_error(
    error_code: str | int,
    message: str = "",
    venue: str = "api_football",
) -> CanonicalError:
    """Map an API-Football error code to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Arkham Intelligence
# ---------------------------------------------------------------------------


def normalize_arkham_error(
    error_code: str | int,
    message: str = "",
    venue: str = "arkham",
) -> CanonicalError:
    """Map an Arkham API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# bloXroute (JSON-RPC error codes)
# ---------------------------------------------------------------------------


_BLOXROUTE_MAP: dict[str, type[CanonicalInvalidRequestError | CanonicalInternalServerError]] = {
    "-32600": CanonicalInvalidRequestError,  # Invalid Request
    "-32601": CanonicalInvalidRequestError,  # Method not found
    "-32602": CanonicalInvalidRequestError,  # Invalid params
    "-32603": CanonicalInternalServerError,  # Internal error
    "-32700": CanonicalInvalidRequestError,  # Parse error
}


def normalize_bloxroute_error(
    error_code: str | int,
    message: str = "",
    venue: str = "bloxroute",
) -> CanonicalError:
    """Map a bloXroute JSON-RPC error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BLOXROUTE_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Cloud SDKs (IAM / OAuth2)
# ---------------------------------------------------------------------------


def normalize_cloud_sdks_error(
    error_code: str | int,
    message: str = "",
    venue: str = "cloud_sdks",
) -> CanonicalError:
    """Map a cloud SDK (IAM/OAuth2) error to a CanonicalError subclass."""
    code = str(error_code).lower()
    if code in ("unauthorized", "401"):
        return CanonicalAuthenticationError(message=message, venue=venue)
    if code in ("forbidden", "403"):
        return CanonicalAuthorizationError(message=message, venue=venue)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# DefiLlama
# ---------------------------------------------------------------------------


def normalize_defillama_error(
    error_code: str | int,
    message: str = "",
    venue: str = "defillama",
) -> CanonicalError:
    """Map a DefiLlama HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Footystats
# ---------------------------------------------------------------------------


def normalize_footystats_error(
    error_code: str | int,
    message: str = "",
    venue: str = "footystats",
) -> CanonicalError:
    """Map a Footystats API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


_GITHUB_MAP: dict[
    str,
    type[
        CanonicalAuthenticationError
        | CanonicalAuthorizationError
        | CanonicalInvalidRequestError
        | CanonicalRateLimitError
        | CanonicalServiceUnavailableError
    ],
] = {
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "422": CanonicalInvalidRequestError,
    "429": CanonicalRateLimitError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_github_error(
    error_code: str | int,
    message: str = "",
    venue: str = "github",
) -> CanonicalError:
    """Map a GitHub API error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _GITHUB_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Glassnode
# ---------------------------------------------------------------------------


def normalize_glassnode_error(
    error_code: str | int,
    message: str = "",
    venue: str = "glassnode",
) -> CanonicalError:
    """Map a Glassnode HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Metabet
# ---------------------------------------------------------------------------


def normalize_metabet_error(
    error_code: str | int,
    message: str = "",
    venue: str = "metabet",
) -> CanonicalError:
    """Map a Metabet API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Odds API
# ---------------------------------------------------------------------------


def normalize_odds_api_error(
    error_code: str | int,
    message: str = "",
    venue: str = "odds_api",
) -> CanonicalError:
    """Map an Odds API error code to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# OddsEngine
# ---------------------------------------------------------------------------


def normalize_odds_engine_error(
    error_code: str | int,
    message: str = "",
    venue: str = "odds_engine",
) -> CanonicalError:
    """Map an OddsEngine API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Open-Meteo
# ---------------------------------------------------------------------------


def normalize_open_meteo_error(
    error_code: str | int,
    message: str = "",
    venue: str = "open_meteo",
) -> CanonicalError:
    """Map an Open-Meteo API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Regulatory (trade reporting)
# ---------------------------------------------------------------------------


def normalize_regulatory_error(
    error_code: str | int,
    message: str = "",
    venue: str = "regulatory",
) -> CanonicalError:
    """Map a trade-reporting / regulatory API error to a CanonicalError subclass."""
    code = str(error_code)
    if code.startswith("VALIDATION"):
        return CanonicalInvalidRequestError(message=message, venue=venue)
    if code.startswith("AUTH"):
        return CanonicalAuthorizationError(message=message, venue=venue)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# SharpAPI
# ---------------------------------------------------------------------------


def normalize_sharpapi_error(
    error_code: str | int,
    message: str = "",
    venue: str = "sharpapi",
) -> CanonicalError:
    """Map a SharpAPI error code to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Sports (generic)
# ---------------------------------------------------------------------------


def normalize_sports_error(
    error_code: str | int,
    message: str = "",
    venue: str = "sports",
) -> CanonicalError:
    """Map a generic sports-data / bookmaker API error to a CanonicalError subclass."""
    code = str(error_code).lower()
    if "unavailable" in code or "suspended" in code:
        return CanonicalServiceUnavailableError(message=message, venue=venue)
    if "closed" in code:
        return CanonicalMarketClosedError(message=message, venue=venue)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# The Graph (GraphQL)
# ---------------------------------------------------------------------------


def normalize_thegraph_error(
    error_code: str | int,
    message: str = "",
    venue: str = "thegraph",
) -> CanonicalError:
    """Map a The Graph / GraphQL error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Transfermarkt
# ---------------------------------------------------------------------------


def normalize_transfermarkt_error(
    error_code: str | int,
    message: str = "",
    venue: str = "transfermarkt",
) -> CanonicalError:
    """Map a Transfermarkt API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Understat
# ---------------------------------------------------------------------------


def normalize_understat_error(
    error_code: str | int,
    message: str = "",
    venue: str = "understat",
) -> CanonicalError:
    """Map an Understat API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------


def normalize_yahoo_finance_error(
    error_code: str | int,
    message: str = "",
    venue: str = "yahoo_finance",
) -> CanonicalError:
    """Map a Yahoo Finance API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return _from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Gate.io
# ---------------------------------------------------------------------------

_GATEIO_MAP: dict[str, Callable[..., CanonicalError]] = {
    "INVALID_PARAM_VALUE": CanonicalInvalidRequestError,
    "INVALID_PROTOCOL": CanonicalInvalidRequestError,
    "INVALID_ARGUMENT": CanonicalInvalidRequestError,
    "MISSING_PARAM": CanonicalInvalidRequestError,
    "INVALID_REQUEST_BODY": CanonicalInvalidRequestError,
    "INVALID_AUTH": CanonicalAuthenticationError,
    "INVALID_KEY": CanonicalAuthenticationError,
    "USER_NOT_FOUND": CanonicalAuthenticationError,
    "REQUEST_EXPIRED": CanonicalAuthenticationError,
    "BALANCE_NOT_ENOUGH": CanonicalInsufficientBalanceError,
    "ORDER_NOT_FOUND": CanonicalOrderRejectedError,
    "ORDER_TOO_SMALL": CanonicalSizeLimitError,
    "RATE_LIMIT": CanonicalRateLimitError,
    "TOO_BUSY": CanonicalServiceUnavailableError,
    "SERVER_ERROR": CanonicalInternalServerError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_gateio_error(
    error_code: str | int,
    message: str = "",
    venue: str = "gateio",
) -> CanonicalError:
    """Map a Gate.io REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _GATEIO_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Bitfinex
# ---------------------------------------------------------------------------

_BITFINEX_MAP: dict[str, Callable[..., CanonicalError]] = {
    "ERR_RATE_LIMIT": CanonicalRateLimitError,
    "ERR_API_KEY_NOT_FOUND": CanonicalAuthenticationError,
    "ERR_AUTH_FAILED": CanonicalAuthenticationError,
    "ERR_AUTH_NONCE": CanonicalAuthenticationError,
    "ERR_NOT_ENOUGH_BALANCE": CanonicalInsufficientBalanceError,
    "ERR_MARGIN_BALANCE": CanonicalInsufficientMarginError,
    "ERR_UNKNOWN": CanonicalInternalServerError,
    "ERR_SERVER": CanonicalInternalServerError,
    "ERR_ORDER": CanonicalOrderRejectedError,
    "10020": CanonicalSizeLimitError,  # Minimum order size
    "10021": CanonicalSizeLimitError,  # Maximum order size
    "10114": CanonicalDuplicateOrderError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


def normalize_bitfinex_error(
    error_code: str | int,
    message: str = "",
    venue: str = "bitfinex",
) -> CanonicalError:
    """Map a Bitfinex REST/WS error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BITFINEX_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Bitstamp
# ---------------------------------------------------------------------------

_BITSTAMP_MAP: dict[str, Callable[..., CanonicalError]] = {
    "API0001": CanonicalInvalidRequestError,
    "API0002": CanonicalAuthenticationError,  # Authentication failed
    "API0005": CanonicalAuthenticationError,  # Invalid signature
    "API0006": CanonicalAuthenticationError,  # Nonce too small
    "API0008": CanonicalInvalidRequestError,  # Wrong nonce
    "UAPI0001": CanonicalInsufficientBalanceError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


def normalize_bitstamp_error(
    error_code: str | int,
    message: str = "",
    venue: str = "bitstamp",
) -> CanonicalError:
    """Map a Bitstamp REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BITSTAMP_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return _from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)
