"""BetVictor sportsbook HTML scraper contracts (www.betvictor.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.betvictor.schemas import (
    BetVictorFixtureOdds,
    BetVictorMarket,
    BetVictorOutcome,
)

__all__ = ["BetVictorFixtureOdds", "BetVictorMarket", "BetVictorOutcome"]
