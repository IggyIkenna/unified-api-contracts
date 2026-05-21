"""Betway sportsbook HTML scraper schemas (betway.com/).

Scraping is Playwright-based (headless browser); no REST API.
Cassette recording requires Playwright session capture infrastructure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BetwayOutcome(BaseModel):
    """Single outcome (selection) from a Betway market."""

    name: str | None = Field(None, description="Outcome label (e.g. team name, Over/Under)")
    odds: float | None = Field(None, description="Decimal odds")


class BetwayMarket(BaseModel):
    """Market (bet type) on a Betway fixture."""

    market_type: str | None = Field(None, description="Market type (e.g. '1X2', 'Asian Handicap')")
    outcomes: list[BetwayOutcome] = Field(default_factory=list)


class BetwayFixtureOdds(BaseModel):
    """Odds for a single fixture scraped from Betway."""

    fixture_id: str | None = Field(None, description="Internal fixture identifier")
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = Field(None, description="ISO8601 kickoff datetime")
    markets: list[BetwayMarket] = Field(default_factory=list)
