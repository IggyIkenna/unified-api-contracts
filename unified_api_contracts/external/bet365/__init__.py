"""Bet365 sportsbook HTML scraper contracts (www.bet365.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.bet365.schemas import (
    Bet365FixtureOdds,
    Bet365Market,
    Bet365Outcome,
)

__all__ = ["Bet365FixtureOdds", "Bet365Market", "Bet365Outcome"]
