"""William Hill sportsbook HTML scraper contracts (sports.williamhill.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.williamhill.schemas import (
    WilliamHillFixtureOdds,
    WilliamHillMarket,
    WilliamHillOutcome,
)

__all__ = ["WilliamHillFixtureOdds", "WilliamHillMarket", "WilliamHillOutcome"]
