"""Bwin sportsbook HTML scraper contracts (sports.bwin.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.bwin.schemas import (
    BwinFixtureOdds,
    BwinMarket,
    BwinOutcome,
)

__all__ = ["BwinFixtureOdds", "BwinMarket", "BwinOutcome"]
