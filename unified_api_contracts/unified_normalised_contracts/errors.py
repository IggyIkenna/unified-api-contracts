"""Canonical error schemas — self-contained (no internal or schemas imports)."""

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


class CanonicalError:
    """Canonical error (grouped from venue-specific errors). Phase 1 placeholder."""

    def __init__(
        self,
        code: str,
        message: str,
        action: ErrorAction,
        venue: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.action = action
        self.venue = venue


class CanonicalRateLimitError(CanonicalError):
    """Canonical rate limit error (retry with backoff)."""

    def __init__(self, message: str = "Rate limit exceeded", venue: str | None = None) -> None:
        super().__init__(
            code="RATE_LIMIT",
            message=message,
            action=ErrorAction.RETRY,
            venue=venue,
        )


__all__ = [
    "CanonicalError",
    "CanonicalRateLimitError",
    "ErrorAction",
    "VenueErrorClassification",
]
