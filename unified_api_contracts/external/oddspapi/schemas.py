"""OddsPapi historical odds API schemas (api.oddspapi.io/v4/).

Requires API key (apiKey= query parameter). Used by
e2e-testing/scripts/sports/oddspapi_historical_backfill.py for
soccer historical odds ingestion into GCS.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OddspapiFixture(BaseModel):
    """Single fixture from GET /v4/fixtures."""

    id: int = Field(..., description="Fixture ID")
    tournamentId: int = Field(..., description="Tournament ID")
    homeTeam: str | None = Field(None, description="Home team name")
    awayTeam: str | None = Field(None, description="Away team name")
    startDate: str | None = Field(None, description="ISO8601 kickoff datetime")
    status: str | None = Field(None, description="Fixture status (e.g. scheduled, finished)")


class OddspapiOdds(BaseModel):
    """Odds entry for a selection from GET /v4/odds."""

    fixtureId: int = Field(..., description="Fixture ID")
    marketType: str | None = Field(None, description="Market type (e.g. 1X2, Asian Handicap)")
    selection: str | None = Field(None, description="Selection name (e.g. Home, Away, Over 2.5)")
    odds: float | None = Field(None, description="Decimal odds")
    bookmaker: str | None = Field(None, description="Bookmaker identifier")
