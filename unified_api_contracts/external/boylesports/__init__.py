"""BoyleSports sportsbook HTML scraper contracts (www.boylesports.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.boylesports.schemas import (
    BoyleSportsFixtureOdds,
    BoyleSportsMarket,
    BoyleSportsOutcome,
)

__all__ = ["BoyleSportsFixtureOdds", "BoyleSportsMarket", "BoyleSportsOutcome"]
