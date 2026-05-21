"""Paddy Power sportsbook HTML scraper contracts (www.paddypower.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.paddypower.schemas import (
    PaddyPowerFixtureOdds,
    PaddyPowerMarket,
    PaddyPowerOutcome,
)

__all__ = ["PaddyPowerFixtureOdds", "PaddyPowerMarket", "PaddyPowerOutcome"]
