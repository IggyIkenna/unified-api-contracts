"""Betway sportsbook HTML scraper contracts (betway.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.betway.schemas import (
    BetwayFixtureOdds,
    BetwayMarket,
    BetwayOutcome,
)

__all__ = ["BetwayFixtureOdds", "BetwayMarket", "BetwayOutcome"]
