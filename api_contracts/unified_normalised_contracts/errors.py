"""Canonical error schemas — grouped, human-readable.

Phase 1: Thin wrapper over VenueErrorClassification and ErrorAction.
Phase 2: Full CanonicalError, CanonicalRateLimitError with venue-agnostic codes.
"""

from api_contracts.schemas.errors import (
    ErrorAction,
    VenueErrorClassification,
)


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
