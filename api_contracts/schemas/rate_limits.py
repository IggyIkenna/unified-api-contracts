"""Standard HTTP rate limit headers across all APIs."""

from pydantic import BaseModel, Field


class HttpRateLimitHeaders(BaseModel):
    """Standard HTTP rate limit headers. Extract from response.headers."""

    x_ratelimit_limit: int | None = Field(None, description="Max requests per window")
    x_ratelimit_remaining: int | None = Field(None, description="Remaining requests")
    x_ratelimit_reset: int | None = Field(None, description="Unix timestamp")
    x_ratelimit_used: int | None = Field(None, description="Used in window")
    retry_after: int | None = Field(None, description="Seconds to wait")


class VenueRateLimitSpec(BaseModel):
    """Rate limit specification for a venue."""

    venue: str = Field(..., description="Venue identifier")
    requests_per_second: float | None = None
    requests_per_minute: int | None = None
    requests_per_day: int | None = None
    requests_per_month: int | None = None
    concurrent_connections: int | None = None
    rate_limit_endpoint: str | None = None
    rate_limit_header_format: str | None = None
    notes: str | None = None


VENUE_RATE_LIMITS: dict[str, VenueRateLimitSpec] = {
    "binance": VenueRateLimitSpec(
        venue="binance",
        requests_per_minute=2400,
        notes="2400 weight/min, 1200 orders/min",
    ),
    "bybit": VenueRateLimitSpec(
        venue="bybit",
        requests_per_second=24.0,
        notes="120/5s",
    ),
    "okx": VenueRateLimitSpec(
        venue="okx",
        requests_per_second=30.0,
        notes="60/2s varies by endpoint",
    ),
    "deribit": VenueRateLimitSpec(
        venue="deribit",
        requests_per_second=10.0,
        notes="No hard limit but 10 req/s recommended",
    ),
    "coinbase": VenueRateLimitSpec(
        venue="coinbase",
        requests_per_second=10.0,
        notes="10/s private",
    ),
    "hyperliquid": VenueRateLimitSpec(
        venue="hyperliquid",
        requests_per_second=10.0,
        notes="10/s info, 1/s actions",
    ),
    "kalshi": VenueRateLimitSpec(
        venue="kalshi",
        requests_per_second=2.0,
        notes="20/10 r/w basic, 400/400 prime",
    ),
    "polymarket": VenueRateLimitSpec(
        venue="polymarket",
        notes="No strict limit but respectful",
    ),
    "databento": VenueRateLimitSpec(
        venue="databento",
        notes="No req/s limit but daily quota",
    ),
    "glassnode": VenueRateLimitSpec(
        venue="glassnode",
        notes="Tier-dependent",
    ),
    "github": VenueRateLimitSpec(
        venue="github",
        requests_per_minute=5000,
        notes="5000/hr authenticated, 60/hr unauthenticated",
    ),
    "gcp_cloud_build": VenueRateLimitSpec(
        venue="gcp_cloud_build",
        notes="Concurrent builds depend on project quota",
    ),
    "api_football": VenueRateLimitSpec(
        venue="api_football",
        requests_per_day=100,
        notes="100/day free, 7500/day paid",
    ),
    "open_meteo": VenueRateLimitSpec(
        venue="open_meteo",
        requests_per_day=10000,
        notes="10000/day free, no auth",
    ),
}
