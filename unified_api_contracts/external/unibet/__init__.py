"""Unibet sportsbook HTML scraper contracts (www.unibet.co.uk/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.unibet.schemas import (
    UnibetFixtureOdds,
    UnibetMarket,
    UnibetOutcome,
)

__all__ = ["UnibetFixtureOdds", "UnibetMarket", "UnibetOutcome"]
