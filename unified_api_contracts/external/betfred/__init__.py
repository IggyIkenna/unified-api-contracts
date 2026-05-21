"""Betfred sportsbook HTML scraper contracts (www.betfred.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.betfred.schemas import (
    BetfredFixtureOdds,
    BetfredMarket,
    BetfredOutcome,
)

__all__ = ["BetfredFixtureOdds", "BetfredMarket", "BetfredOutcome"]
