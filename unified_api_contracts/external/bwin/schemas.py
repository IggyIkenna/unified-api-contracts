"""Bwin sportsbook HTML scraper schemas (sports.bwin.com/).

Scraping is Playwright-based (headless browser); no REST API.
Cassette recording requires Playwright session capture infrastructure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BwinOutcome(BaseModel):
    """Single outcome (selection) from a Bwin market."""

    name: str | None = Field(None, description="Outcome label (e.g. team name, Over/Under)")
    odds: float | None = Field(None, description="Decimal odds")


class BwinMarket(BaseModel):
    """Market (bet type) on a Bwin fixture."""

    market_type: str | None = Field(None, description="Market type (e.g. '1X2', 'Asian Handicap')")
    outcomes: list[BwinOutcome] = Field(default_factory=list)


class BwinFixtureOdds(BaseModel):
    """Odds for a single fixture scraped from Bwin."""

    fixture_id: str | None = Field(None, description="Internal fixture identifier")
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = Field(None, description="ISO8601 kickoff datetime")
    markets: list[BwinMarket] = Field(default_factory=list)
