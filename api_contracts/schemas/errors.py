"""Error classification schemas for venue-specific API errors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class ErrorAction(StrEnum):
    RETRY = "retry"
    RECONNECT = "reconnect"
    SKIP = "skip"
    FAIL = "fail"


@dataclass
class VenueErrorClassification:
    venue: str
    error_code: str
    retry_safe: bool
    reconnect: bool
    action: ErrorAction
    description: str | None = None


@dataclass
class DatabentoError:
    code: str
    message: str
    retry_safe: bool
    reconnect: bool


class RateLimitResponse(BaseModel):
    """HTTP 429 rate limit response schema (REST venues).

    Common headers: Retry-After (seconds or HTTP-date), X-RateLimit-Limit,
    X-RateLimit-Remaining, X-RateLimit-Reset (Unix timestamp).
    """

    retry_after: int | None = Field(None, description="Seconds to wait (Retry-After header)")
    x_rate_limit_limit: int | None = Field(None, alias="X-RateLimit-Limit")
    x_rate_limit_remaining: int | None = Field(None, alias="X-RateLimit-Remaining")
    x_rate_limit_reset: int | None = Field(None, alias="X-RateLimit-Reset")
    message: str | None = None
    code: str | int | None = None

    model_config = {"populate_by_name": True}


class WebSocketCloseInfo(BaseModel):
    """WebSocket close frame (RFC 6455): code + reason.

    Common codes: 1000=normal, 1006=abnormal, 1008=policy, 1011=server error.
    """

    code: int = Field(..., description="Close code (1000-1015)")
    reason: str | None = Field(None, description="Close reason string")
    message: str | None = None


DATABENTO_ERROR_MAP: dict[str, DatabentoError] = {
    "RATE_LIMIT": DatabentoError("RATE_LIMIT", "Rate limit exceeded", retry_safe=True, reconnect=False),
    "AUTH_FAILURE": DatabentoError("AUTH_FAILURE", "Authentication failed", retry_safe=False, reconnect=False),
    "CONNECTION_RESET": DatabentoError("CONNECTION_RESET", "Connection reset", retry_safe=True, reconnect=True),
    "SUBSCRIPTION_ERROR": DatabentoError("SUBSCRIPTION_ERROR", "Subscription failed", retry_safe=True, reconnect=False),
}


def _v(
    venue: str, code: str, *, retry: bool, reconnect: bool, action: ErrorAction, desc: str
) -> VenueErrorClassification:
    return VenueErrorClassification(venue, code, retry_safe=retry, reconnect=reconnect, action=action, description=desc)


VENUE_ERROR_MAP: dict[str, list[VenueErrorClassification]] = {
    "binance": [
        _v("binance", "-1003", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Too many requests"),
        _v("binance", "-1021", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Timestamp recv window"),
        _v("binance", "-1000", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Unknown error"),
        _v("binance", "-1006", retry=True, reconnect=True, action=ErrorAction.RECONNECT, desc="Connection closed"),
        _v("binance", "-2011", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Unknown order"),
        _v("binance", "-1013", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Invalid lot size"),
    ],
    "bybit": [
        _v("bybit", "10006", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
        _v("bybit", "10000", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Internal error"),
        _v("bybit", "10001", retry=True, reconnect=True, action=ErrorAction.RECONNECT, desc="Parameter error"),
        _v("bybit", "10019", retry=True, reconnect=True, action=ErrorAction.RECONNECT, desc="WS restarting"),
        _v("bybit", "33004", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="API key invalid"),
    ],
    "okx": [
        _v("okx", "50004", retry=True, reconnect=True, action=ErrorAction.RECONNECT, desc="WebSocket closed"),
        _v("okx", "50011", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
        _v("okx", "50026", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="System busy"),
        _v("okx", "51008", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Insufficient funds"),
    ],
    "deribit": [
        _v("deribit", "10028", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Too many requests"),
        _v("deribit", "10040", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Too many requests"),
        _v("deribit", "11044", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Not enough funds"),
        _v("deribit", "13009", retry=False, reconnect=True, action=ErrorAction.RECONNECT, desc="Invalid token"),
        _v("deribit", "13010", retry=False, reconnect=True, action=ErrorAction.RECONNECT, desc="Token revoked"),
    ],
    "coinbase": [
        _v("coinbase", "RATE_LIMIT_EXCEEDED", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit"),
        _v("coinbase", "INTERNAL_SERVICE_ERROR", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Server"),
        _v("coinbase", "TEMPORARILY_UNAVAILABLE", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Temp"),
    ],
    "tardis": [
        _v("tardis", "401", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Unauthorized"),
        _v("tardis", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
        _v("tardis", "500", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Server error"),
    ],
    "alchemy": [
        _v("alchemy", "-32600", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Invalid request"),
        _v("alchemy", "-32603", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Internal error"),
        _v("alchemy", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
    ],
    "yahoo_finance": [
        _v("yahoo_finance", "RATE_LIMIT_EXCEEDED", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate"),
        _v("yahoo_finance", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Too many requests"),
    ],
    "upbit": [
        _v("upbit", "invalid_access_key", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Invalid key"),
        _v("upbit", "invalid_query_payload", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Invalid"),
        _v("upbit", "too_many_requests", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit"),
    ],
    "ibkr": [
        _v("ibkr", "100", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Market data farm"),
        _v("ibkr", "1100", retry=True, reconnect=True, action=ErrorAction.RECONNECT, desc="Connectivity lost"),
        _v("ibkr", "1300", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Order rejected"),
    ],
    "thegraph": [
        _v("thegraph", "Subgraph not found", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Not found"),
        _v("thegraph", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
    ],
    "ccxt": [
        _v("ccxt", "RateLimitExceeded", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit"),
        _v("ccxt", "ExchangeNotAvailable", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Unavail"),
        _v("ccxt", "ExchangeError", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Transient"),
    ],
    "databento": [
        _v("databento", "RATE_LIMIT", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit"),
        _v("databento", "AUTH_FAILURE", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Auth failed"),
        _v("databento", "CONNECTION_RESET", retry=True, reconnect=True, action=ErrorAction.RECONNECT, desc="Reset"),
    ],
    "hyperliquid": [
        _v("hyperliquid", "500", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Server error"),
        _v("hyperliquid", "503", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Unavailable"),
        _v("hyperliquid", "RATE_LIMIT", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit"),
        _v("hyperliquid", "INSUFFICIENT_MARGIN", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Margin"),
    ],
    "aster": [
        _v("aster", "-1003", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Too many requests"),
        _v("aster", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
        _v("aster", "503", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Service unavailable"),
    ],
    "bloxroute": [
        _v("bloxroute", "-32600", retry=False, reconnect=False, action=ErrorAction.FAIL, desc="Invalid request"),
        _v("bloxroute", "-32603", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Internal error"),
        _v("bloxroute", "429", retry=True, reconnect=False, action=ErrorAction.RETRY, desc="Rate limit exceeded"),
    ],
}


def classify_venue_error(venue: str, error_code: str) -> VenueErrorClassification:
    """Classify a venue error code using normalized VENUE_ERROR_MAP.

    Returns VenueErrorClassification with retry_safe, reconnect, action.
    Unknown errors default to FAIL with retry_safe=False, reconnect=False.
    """
    venue_key = venue.lower()
    classifications = VENUE_ERROR_MAP.get(venue_key, [])
    code_str = str(error_code)
    for c in classifications:
        if c.error_code == code_str:
            return c
    return VenueErrorClassification(
        venue=venue_key,
        error_code=code_str,
        retry_safe=False,
        reconnect=False,
        action=ErrorAction.FAIL,
        description="Unknown error",
    )
