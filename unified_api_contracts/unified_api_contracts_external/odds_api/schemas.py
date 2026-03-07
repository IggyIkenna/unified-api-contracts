"""The Odds API: fixtures, bookmakers, markets, outcomes, historical odds, errors.

Ref: https://the-odds-api.com/liveapi/guides/v4/
"""

__api_version__ = "v4"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field

from unified_api_contracts import ErrorAction


class OddsApiOutcome(BaseModel):
    """Outcome in a market."""

    name: str | None = None
    price: float | None = None
    point: float | None = None


class OddsApiMarket(BaseModel):
    """Market from The Odds API."""

    key: str | None = None
    last_update: str | None = Field(None, alias="lastUpdate")
    outcomes: list[OddsApiOutcome] | None = None


class OddsApiBookmaker(BaseModel):
    """Bookmaker from The Odds API."""

    key: str | None = None
    title: str | None = None
    last_update: str | None = Field(None, alias="lastUpdate")
    markets: list[OddsApiMarket] | None = None


class OddsApiFixture(BaseModel):
    """Fixture from The Odds API."""

    id: str | None = None
    sport_key: str | None = Field(None, alias="sportKey")
    sport_title: str | None = Field(None, alias="sportTitle")
    commence_time: str | None = Field(None, alias="commenceTime")
    home_team: str | None = Field(None, alias="homeTeam")
    away_team: str | None = Field(None, alias="awayTeam")
    bookmakers: list[OddsApiBookmaker] | None = None


class OddsApiHistoricalOdds(BaseModel):
    """Historical odds from The Odds API."""

    sport_key: str | None = Field(None, alias="sportKey")
    sport_title: str | None = Field(None, alias="sportTitle")
    commence_time: str | None = Field(None, alias="commenceTime")
    home_team: str | None = Field(None, alias="homeTeam")
    away_team: str | None = Field(None, alias="awayTeam")
    bookmakers: list[OddsApiBookmaker] | None = None


class OddsApiEvent(BaseModel, frozen=True):
    """Event from The Odds API (execution adapter shape — frozen, non-optional)."""

    id: str = ""
    home_team: str = ""
    away_team: str = ""
    bookmakers: list[OddsApiBookmaker] = []


class OddsApiError(BaseModel):
    """The Odds API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Odds API error to retry action."""
        if code == 429 or (error and "quota" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
