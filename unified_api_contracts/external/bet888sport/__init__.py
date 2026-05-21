"""888sport sportsbook HTML scraper contracts (www.888sport.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.bet888sport.schemas import (
    Bet888sportFixtureOdds,
    Bet888sportMarket,
    Bet888sportOutcome,
)

__all__ = ["Bet888sportFixtureOdds", "Bet888sportMarket", "Bet888sportOutcome"]
