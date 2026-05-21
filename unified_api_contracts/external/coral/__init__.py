"""Coral sportsbook HTML scraper contracts (sports.coral.co.uk/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.coral.schemas import (
    CoralFixtureOdds,
    CoralMarket,
    CoralOutcome,
)

__all__ = ["CoralFixtureOdds", "CoralMarket", "CoralOutcome"]
