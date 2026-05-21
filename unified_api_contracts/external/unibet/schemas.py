"""Unibet sportsbook HTML scraper schemas (www.unibet.co.uk/).

Scraping is Playwright-based (headless browser); no REST API.
Cassette recording requires Playwright session capture infrastructure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UnibetOutcome(BaseModel):
    """Single outcome (selection) from a Unibet market."""

    name: str | None = Field(None, description="Outcome label (e.g. team name, Over/Under)")
    odds: float | None = Field(None, description="Decimal odds")


class UnibetMarket(BaseModel):
    """Market (bet type) on a Unibet fixture."""

    market_type: str | None = Field(None, description="Market type (e.g. '1X2', 'Asian Handicap')")
    outcomes: list[UnibetOutcome] = Field(default_factory=list)


class UnibetFixtureOdds(BaseModel):
    """Odds for a single fixture scraped from Unibet."""

    fixture_id: str | None = Field(None, description="Internal fixture identifier")
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = Field(None, description="ISO8601 kickoff datetime")
    markets: list[UnibetMarket] = Field(default_factory=list)
