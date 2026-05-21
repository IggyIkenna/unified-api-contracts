"""SBOBET sportsbook HTML scraper contracts (www.sbobet.com/).

Scraped via Playwright headless browser in execution-service.
Stub cassette documents the base URL; real recording deferred pending
Playwright session capture infrastructure.
"""

from unified_api_contracts.external.sbobet.schemas import (
    SBOBETFixtureOdds,
    SBOBETMarket,
    SBOBETOutcome,
)

__all__ = ["SBOBETFixtureOdds", "SBOBETMarket", "SBOBETOutcome"]
