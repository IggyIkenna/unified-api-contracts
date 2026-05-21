"""888sport sportsbook HTML scraper schemas (www.888sport.com/).

Scraping is Playwright-based (headless browser); no REST API.
Cassette recording requires Playwright session capture infrastructure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Bet888sportOutcome(BaseModel):
    """Single outcome (selection) from a 888sport market."""

    name: str | None = Field(None, description="Outcome label (e.g. team name, Over/Under)")
    odds: float | None = Field(None, description="Decimal odds")


class Bet888sportMarket(BaseModel):
    """Market (bet type) on a 888sport fixture."""

    market_type: str | None = Field(None, description="Market type (e.g. '1X2', 'Asian Handicap')")
    outcomes: list[Bet888sportOutcome] = Field(default_factory=list)


class Bet888sportFixtureOdds(BaseModel):
    """Odds for a single fixture scraped from 888sport."""

    fixture_id: str | None = Field(None, description="Internal fixture identifier")
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = Field(None, description="ISO8601 kickoff datetime")
    markets: list[Bet888sportMarket] = Field(default_factory=list)
