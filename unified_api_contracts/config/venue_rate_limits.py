"""Venue rate limit configuration data."""

from unified_api_contracts.canonical.domain.rate_limits import VenueRateLimitSpec

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
