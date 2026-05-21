"""Paddy Power sportsbook HTML scraper schemas (www.paddypower.com/).

Scraping is Playwright-based (headless browser); no REST API.
Cassette recording requires Playwright session capture infrastructure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaddyPowerOutcome(BaseModel):
    """Single outcome (selection) from a Paddy Power market."""

    name: str | None = Field(None, description="Outcome label (e.g. team name, Over/Under)")
    odds: float | None = Field(None, description="Decimal odds")


class PaddyPowerMarket(BaseModel):
    """Market (bet type) on a Paddy Power fixture."""

    market_type: str | None = Field(None, description="Market type (e.g. '1X2', 'Asian Handicap')")
    outcomes: list[PaddyPowerOutcome] = Field(default_factory=list)


class PaddyPowerFixtureOdds(BaseModel):
    """Odds for a single fixture scraped from Paddy Power."""

    fixture_id: str | None = Field(None, description="Internal fixture identifier")
    home_team: str | None = None
    away_team: str | None = None
    kickoff: str | None = Field(None, description="ISO8601 kickoff datetime")
    markets: list[PaddyPowerMarket] = Field(default_factory=list)
