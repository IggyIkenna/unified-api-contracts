"""Betfred sportsbook HTML scraper schemas (www.betfred.com/).

Scraping is Playwright-based (headless browser); no REST API.
Cassette recording requires Playwright session capture infrastructure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BetfredOutcome(BaseModel):
    """Single outcome (selection) from a Betfred market."""

    name: str | None = Field(None, description="Outcome label (e.g. team name, Over/Under)")
    odds: float | None = Field(None, description="Decimal odds")


class BetfredMarket(BaseModel):
    """Market (bet type) on a Betfred fixture."""

    market_type: str | None = Field(None, description="Market type (e.g. '1X2', 'Asian Handicap')")
    outcomes: list[BetfredOutcome] = Field(default_factory=list)


class BetfredFixtureOdds(BaseModel):
    """Odds for a single fixture scraped from Betfred."""

    fixture_id: str | None = Field(None, description="Internal fixture identifier")
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = Field(None, description="ISO8601 kickoff datetime")
    markets: list[BetfredMarket] = Field(default_factory=list)
