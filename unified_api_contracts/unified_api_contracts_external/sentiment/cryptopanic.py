"""Pydantic schemas for CryptoPanic sentiment API.

Source: https://cryptopanic.com/developers/api/
Free API key available at cryptopanic.com. Rate limits: 20 requests/minute (free tier).

Used by unified-market-interface for crypto news sentiment and social media aggregation.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction

# API Constants
CRYPTOPANIC_BASE_URL = "https://cryptopanic.com/api/v1"
CRYPTOPANIC_RATE_LIMIT_FREE = 20  # requests per minute
CRYPTOPANIC_RATE_LIMIT_PRO = 3000  # requests per minute


class CryptoPanicCurrency(BaseModel):
    """Currency/coin mentioned in a news post."""

    code: str = Field(..., description="Currency code (e.g., BTC, ETH)")
    title: str = Field(..., description="Full currency name")
    slug: str = Field(..., description="URL slug")
    url: str = Field(..., description="CryptoPanic currency page URL")


class CryptoPanicVote(BaseModel):
    """Vote counts for a news post."""

    negative: int = Field(default=0, description="Number of negative votes")
    positive: int = Field(default=0, description="Number of positive votes")
    important: int = Field(default=0, description="Number of important votes")
    liked: int = Field(default=0, description="Number of likes")
    disliked: int = Field(default=0, description="Number of dislikes")
    lol: int = Field(default=0, description="Number of lol reactions")
    toxic: int = Field(default=0, description="Number of toxic flags")
    saved: int = Field(default=0, description="Number of saves")
    comments: int = Field(default=0, description="Number of comments")


class CryptoPanicPost(BaseModel):
    """Single news post from CryptoPanic API."""

    id: int = Field(..., description="Unique post ID")
    title: str = Field(..., description="News headline")
    url: str = Field(..., description="Original news article URL")
    source: dict[str, str] = Field(..., description="Source metadata (title, region, domain)")
    published_at: datetime = Field(..., description="Publication timestamp (UTC)")
    created_at: datetime = Field(..., description="CryptoPanic ingestion timestamp (UTC)")
    kind: str = Field(..., description="Post type: news, media, blog")
    domain: str = Field(..., description="Source domain (e.g., coindesk.com)")
    votes: CryptoPanicVote = Field(default_factory=CryptoPanicVote, description="Vote counts")
    currencies: list[CryptoPanicCurrency] = Field(default_factory=list, description="Currencies mentioned in post")
    metadata: dict[str, str | int | bool] | None = Field(None, description="Additional metadata")


class CryptoPanicPostsResponse(BaseModel):
    """Response from /posts/ endpoint."""

    count: int = Field(..., description="Total number of posts matching filter")
    next: str | None = Field(None, description="URL for next page of results")
    previous: str | None = Field(None, description="URL for previous page of results")
    results: list[CryptoPanicPost] = Field(..., description="List of news posts")


class CryptoPanicError(BaseModel):
    """CryptoPanic API error."""

    detail: str | None = Field(None, description="Error message")
    status_code: int | None = Field(None, description="HTTP status code")

    @classmethod
    def classify(cls, status_code: int | None = None) -> ErrorAction:
        """Map CryptoPanic error to retry action."""
        if status_code == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        if status_code is not None and status_code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if status_code == 401:
            return ErrorAction.FAIL_HARD  # Invalid API key
        if status_code == 403:
            return ErrorAction.FAIL_HARD  # Forbidden
        return ErrorAction.FAIL_HARD


class CryptoPanicRequestParams(BaseModel):
    """Request parameters for /posts/ endpoint."""

    auth_token: str = Field(..., description="API key")
    public: bool = Field(default=True, description="Include public posts only")
    kind: str | None = Field(None, description="Filter by kind: news, media, blog, all")
    currencies: str | None = Field(None, description="Comma-separated currency codes (e.g., BTC,ETH)")
    regions: str | None = Field(None, description="Filter by region: en, de, es, fr, nl, it, pt, ru")
    filter: str | None = Field(None, description="Filter: rising, hot, bullish, bearish, important, saved, lol")
    page: int = Field(default=1, ge=1, description="Page number for pagination")


# Sentiment scoring constants (derived from vote ratios)
SENTIMENT_POSITIVE_THRESHOLD = 0.6  # positive/(positive+negative) > 0.6 = bullish
SENTIMENT_NEGATIVE_THRESHOLD = 0.4  # positive/(positive+negative) < 0.4 = bearish
SENTIMENT_NEUTRAL_RANGE = (0.4, 0.6)  # neutral sentiment range
