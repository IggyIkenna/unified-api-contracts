"""Ladbrokes sportsbook HTML scraper contracts (sports.ladbrokes.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.ladbrokes.schemas import (
    LadbrokesFixtureOdds,
    LadbrokesMarket,
    LadbrokesOutcome,
)

__all__ = ["LadbrokesFixtureOdds", "LadbrokesMarket", "LadbrokesOutcome"]
