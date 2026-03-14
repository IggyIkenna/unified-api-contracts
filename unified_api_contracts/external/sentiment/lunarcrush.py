"""Pydantic schemas for LunarCrush social sentiment API.

Source: https://lunarcrush.com/developers/docs
Free API key available at lunarcrush.com. Rate limits: 50 requests/day (free tier).

Used by unified-market-interface for social media sentiment, influencer tracking, and social volume metrics.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from datetime import datetime

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction

# API Constants
LUNARCRUSH_BASE_URL = "https://api.lunarcrush.com/v2"
LUNARCRUSH_RATE_LIMIT_FREE = 50  # requests per day
LUNARCRUSH_RATE_LIMIT_PRO = 1000  # requests per day


class LunarCrushAssetMetrics(BaseModel):
    """Social metrics for a single asset."""

    id: int = Field(..., description="LunarCrush asset ID")
    symbol: str = Field(..., description="Asset symbol (e.g., BTC, ETH)")
    name: str = Field(..., description="Asset name")
    price: float = Field(..., description="Current price in USD")
    price_btc: float | None = Field(None, description="Price in BTC")
    volume_24h: float = Field(..., description="24h trading volume in USD")
    market_cap: float | None = Field(None, description="Market capitalization in USD")
    percent_change_24h: float | None = Field(None, description="24h price change percentage")
    galaxy_score: float = Field(..., ge=0, le=100, description="LunarCrush proprietary score (0-100)")
    alt_rank: int | None = Field(None, description="Rank among all altcoins")
    social_volume: int = Field(..., description="Total social media mentions")
    social_volume_24h_change: float | None = Field(None, description="24h change in social volume %")
    social_score: float = Field(..., ge=0, le=100, description="Social sentiment score (0-100)")
    social_dominance: float | None = Field(None, description="% of total crypto social volume")
    sentiment: float = Field(..., ge=0, le=5, description="Sentiment score (0=very bearish, 5=very bullish)")
    news: int | None = Field(None, description="Number of news articles")
    spam: int | None = Field(None, description="Number of spam posts detected")
    contributors: int | None = Field(None, description="Number of unique contributors")
    average_sentiment: float | None = Field(None, ge=0, le=5, description="Average sentiment (0-5)")
    sentiment_absolute: int | None = Field(None, description="Absolute sentiment count")
    sentiment_relative: float | None = Field(None, description="Relative sentiment score")
    url_shares: int | None = Field(None, description="Number of URL shares")
    unique_url_shares: int | None = Field(None, description="Number of unique URL shares")
    reddit_posts: int | None = Field(None, description="Number of Reddit posts")
    reddit_posts_24h_change: float | None = Field(None, description="24h change in Reddit posts %")
    reddit_comments: int | None = Field(None, description="Number of Reddit comments")
    reddit_comments_24h_change: float | None = Field(None, description="24h change in Reddit comments %")
    tweets: int | None = Field(None, description="Number of tweets")
    tweets_24h_change: float | None = Field(None, description="24h change in tweets %")
    tweet_spam: int | None = Field(None, description="Number of spam tweets")
    tweet_followers: int | None = Field(None, description="Total followers of tweet authors")
    tweet_quotes: int | None = Field(None, description="Number of tweet quotes")
    tweet_retweets: int | None = Field(None, description="Number of retweets")
    tweet_replies: int | None = Field(None, description="Number of tweet replies")
    tweet_favorites: int | None = Field(None, description="Number of tweet favorites")
    tweet_sentiment1: float | None = Field(None, description="Sentiment from source 1 (0-5)")
    tweet_sentiment2: float | None = Field(None, description="Sentiment from source 2 (0-5)")
    tweet_sentiment3: float | None = Field(None, description="Sentiment from source 3 (0-5)")
    tweet_sentiment4: float | None = Field(None, description="Sentiment from source 4 (0-5)")
    tweet_sentiment5: float | None = Field(None, description="Sentiment from source 5 (0-5)")
    tweet_sentiment_impact1: float | None = Field(None, description="Sentiment impact 1")
    tweet_sentiment_impact2: float | None = Field(None, description="Sentiment impact 2")
    tweet_sentiment_impact3: float | None = Field(None, description="Sentiment impact 3")
    tweet_sentiment_impact4: float | None = Field(None, description="Sentiment impact 4")
    tweet_sentiment_impact5: float | None = Field(None, description="Sentiment impact 5")
    time: int = Field(..., description="Unix timestamp (seconds)")
    time_series: list[dict[str, float | int]] | None = Field(
        None, alias="timeSeries", description="Historical time series data"
    )


class LunarCrushAssetsResponse(BaseModel):
    """Response from /assets endpoint."""

    data: list[LunarCrushAssetMetrics] = Field(..., description="List of asset metrics")


class LunarCrushInfluencer(BaseModel):
    """Social media influencer data."""

    id: str = Field(..., description="Influencer ID")
    name: str = Field(..., description="Influencer name/handle")
    screen_name: str = Field(..., description="Social media screen name")
    followers: int = Field(..., description="Number of followers")
    influencer_score: float = Field(..., ge=0, le=100, description="Influencer score (0-100)")
    posts: int | None = Field(None, description="Number of posts")
    engagement: int | None = Field(None, description="Total engagement count")
    sentiment: float | None = Field(None, ge=0, le=5, description="Average sentiment (0-5)")


class LunarCrushInfluencersResponse(BaseModel):
    """Response from /influencers endpoint."""

    data: list[LunarCrushInfluencer] = Field(..., description="List of influencers")


class LunarCrushFeed(BaseModel):
    """Social media feed post."""

    id: str = Field(..., description="Post ID")
    time: int = Field(..., description="Unix timestamp (seconds)")
    created_at: datetime = Field(..., description="Post creation timestamp (UTC)")
    title: str | None = Field(None, description="Post title")
    body: str = Field(..., description="Post content")
    type: str = Field(..., description="Post type: tweet, reddit, news, article")
    url: str | None = Field(None, description="Post URL")
    interactions: int | None = Field(None, description="Total interactions (likes, retweets, comments)")
    sentiment: float | None = Field(None, ge=0, le=5, description="Sentiment score (0-5)")
    spam: bool = Field(default=False, description="Whether post is flagged as spam")


class LunarCrushFeedResponse(BaseModel):
    """Response from /feeds endpoint."""

    data: list[LunarCrushFeed] = Field(..., description="List of social media posts")


class LunarCrushError(BaseModel):
    """LunarCrush API error."""

    error: str | None = Field(None, description="Error message")
    status_code: int | None = Field(None, description="HTTP status code")

    @classmethod
    def classify(cls, status_code: int | None = None) -> ErrorAction:
        """Map LunarCrush error to retry action."""
        if status_code == 429:
            return ErrorAction.RETRY
        if status_code is not None and status_code >= 500:
            return ErrorAction.RETRY
        if status_code == 401:
            return ErrorAction.FAIL  # Invalid API key
        if status_code == 403:
            return ErrorAction.FAIL  # Rate limit exceeded (free tier)
        return ErrorAction.FAIL


class LunarCrushRequestParams(BaseModel):
    """Request parameters for LunarCrush API endpoints."""

    key: str = Field(..., description="API key")
    symbol: str | None = Field(None, description="Asset symbol (e.g., BTC)")
    data: str | None = Field(None, description="Data type: assets, market, global, feeds, influencers, galaxy-score")
    interval: str | None = Field(None, description="Time interval: day, week, month, 1 year, 2 years")
    change: str | None = Field(None, description="Change period: 1h, 24h, 7d, 30d, 3m, 1y")
    sort: str | None = Field(None, description="Sort field: galaxy_score, social_volume, price, etc.")
    limit: int | None = Field(None, ge=1, le=1000, description="Number of results to return")
    start: int | None = Field(None, description="Start timestamp (Unix seconds)")
    end: int | None = Field(None, description="End timestamp (Unix seconds)")


# Sentiment scoring constants
LUNARCRUSH_SENTIMENT_BEARISH = 2.0  # sentiment < 2.0 = bearish
LUNARCRUSH_SENTIMENT_NEUTRAL_LOW = 2.0  # neutral range: 2.0 - 3.0
LUNARCRUSH_SENTIMENT_NEUTRAL_HIGH = 3.0
LUNARCRUSH_SENTIMENT_BULLISH = 3.0  # sentiment > 3.0 = bullish
LUNARCRUSH_GALAXY_SCORE_STRONG = 75.0  # galaxy_score > 75 = strong signal
LUNARCRUSH_GALAXY_SCORE_WEAK = 50.0  # galaxy_score < 50 = weak signal
