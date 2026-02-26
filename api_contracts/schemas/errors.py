"""Error classification schemas for venue-specific API errors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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


DATABENTO_ERROR_MAP: dict[str, DatabentoError] = {
    "RATE_LIMIT": DatabentoError("RATE_LIMIT", "Rate limit exceeded", retry_safe=True, reconnect=False),
    "AUTH_FAILURE": DatabentoError("AUTH_FAILURE", "Authentication failed", retry_safe=False, reconnect=False),
    "CONNECTION_RESET": DatabentoError("CONNECTION_RESET", "Connection reset", retry_safe=True, reconnect=True),
    "SUBSCRIPTION_ERROR": DatabentoError("SUBSCRIPTION_ERROR", "Subscription failed", retry_safe=True, reconnect=False),
}

VENUE_ERROR_MAP: dict[str, list[VenueErrorClassification]] = {
    "binance": [
        VenueErrorClassification(
            "binance",
            "-1003",
            retry_safe=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            description="Too many requests",
        ),
        VenueErrorClassification(
            "binance",
            "-1021",
            retry_safe=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            description="Timestamp out of recv window",
        ),
    ],
    "bybit": [
        VenueErrorClassification(
            "bybit",
            "10006",
            retry_safe=True,
            reconnect=False,
            action=ErrorAction.RETRY,
            description="Rate limit exceeded",
        ),
    ],
    "okx": [
        VenueErrorClassification(
            "okx",
            "50004",
            retry_safe=True,
            reconnect=True,
            action=ErrorAction.RECONNECT,
            description="WebSocket connection closed",
        ),
    ],
}
