"""Bet365 sportsbook HTML scraper schemas (www.bet365.com/).

Scraping is Playwright-based (headless browser); no REST API.
Cassette recording requires Playwright session capture infrastructure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Bet365Outcome(BaseModel):
    """Single outcome (selection) from a Bet365 market."""

    name: str | None = Field(None, description="Outcome label (e.g. team name, Over/Under)")
    odds: float | None = Field(None, description="Decimal odds")


class Bet365Market(BaseModel):
    """Market (bet type) on a Bet365 fixture."""

    market_type: str | None = Field(None, description="Market type (e.g. '1X2', 'Asian Handicap')")
    outcomes: list[Bet365Outcome] = Field(default_factory=list)


class Bet365FixtureOdds(BaseModel):
    """Odds for a single fixture scraped from Bet365."""

    fixture_id: str | None = Field(None, description="Internal fixture identifier")
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = Field(None, description="ISO8601 kickoff datetime")
    markets: list[Bet365Market] = Field(default_factory=list)
