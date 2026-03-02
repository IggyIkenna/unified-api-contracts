"""alternative.me Fear and Greed Index for crypto markets.

Free, no auth. Updates daily at midnight UTC.
Endpoint: https://api.alternative.me/fng/?limit=N
Note: crypto-specific, different from CNN Money stock Fear and Greed.
"""

from enum import StrEnum

from pydantic import BaseModel

from unified_api_contracts.shared import ErrorAction


class FearGreedClassification(StrEnum):
    """Score ranges: 0-24, 25-49, 50, 51-74, 75-100."""

    EXTREME_FEAR = "Extreme Fear"
    FEAR = "Fear"
    NEUTRAL = "Neutral"
    GREED = "Greed"
    EXTREME_GREED = "Extreme Greed"


class FearGreedReading(BaseModel):
    """Single reading from Fear and Greed API."""

    value: int | None = None
    value_classification: FearGreedClassification | None = None
    timestamp: str | None = None  # Unix epoch string
    time_until_update: str | None = None  # seconds until next (only on limit=1)


class FearGreedResponse(BaseModel):
    """Response from alternative.me Fear and Greed API."""

    name: str | None = None
    data: list[FearGreedReading] | None = None
    metadata: dict[str, str | None] | None = None


class FearGreedError(BaseModel):
    """Fear and Greed API error."""

    message: str | None = None

    @classmethod
    def classify(cls, http_status: int | None = None) -> ErrorAction:
        """5xx->RETRY_WITH_BACKOFF, otherwise FAIL_HARD."""
        if http_status and 500 <= http_status < 600:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
