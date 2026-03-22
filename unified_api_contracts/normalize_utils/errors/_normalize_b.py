"""Error normalizers (auto-split from errors.py)."""

from __future__ import annotations

from collections.abc import Callable

from unified_api_contracts.canonical.crosscutting.errors import (
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
from unified_api_contracts.normalize_utils.errors._utils import (
    from_http_status,
)


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
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Nautilus Trader
# ---------------------------------------------------------------------------

NAUTILUS_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = NAUTILUS_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Betdaq
# ---------------------------------------------------------------------------

BETDAQ_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = BETDAQ_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Smarkets
# ---------------------------------------------------------------------------

SMARKETS_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = SMARKETS_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Pinnacle
# ---------------------------------------------------------------------------

PINNACLE_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = PINNACLE_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
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
        return from_http_status(status, message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


GITHUB_MAP: dict[
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
    cls = GITHUB_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
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
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Bitstamp
# ---------------------------------------------------------------------------

BITSTAMP_MAP: dict[str, Callable[..., CanonicalError]] = {
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
    cls = BITSTAMP_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


# ---------------------------------------------------------------------------
# Matchbook
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
