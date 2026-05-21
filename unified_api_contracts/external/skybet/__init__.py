"""Sky Bet sportsbook HTML scraper contracts (www.skybet.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.skybet.schemas import (
    SkyBetFixtureOdds,
    SkyBetMarket,
    SkyBetOutcome,
)

__all__ = ["SkyBetFixtureOdds", "SkyBetMarket", "SkyBetOutcome"]
