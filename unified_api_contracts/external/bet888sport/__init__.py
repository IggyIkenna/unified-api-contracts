"""888sport sportsbook HTML scraper contracts (www.888sport.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.bet888sport.schemas import (
    888sportFixtureOdds,
    888sportMarket,
    888sportOutcome,
)

__all__ = ["888sportFixtureOdds", "888sportMarket", "888sportOutcome"]
