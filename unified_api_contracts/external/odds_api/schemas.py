"""The Odds API: fixtures, bookmakers, markets, outcomes, historical odds, errors.

Ref: https://the-odds-api.com/liveapi/guides/v4/
"""

__api_version__ = "v4"  # matches provider_api_versions.yaml

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


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
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL
        return ErrorAction.FAIL


# =============================================================================
# Source schemas (merged from external/sports/sources/odds_api/)
# =============================================================================

# OddsApiOutcome, OddsApiMarket, OddsApiBookmaker, OddsApiEvent already defined
# above (authoritative versions). Only Decimal-based raw models below are new.

# ---------------------------------------------------------------------------
# Decimal-based raw source models (originally in sports-betting-services-previous)
# ---------------------------------------------------------------------------

_RawDict = dict[str, str | int | float | bool | None]


class ODOutcomeRaw(BaseModel):
    """Individual outcome from an Odds API v4 bookmaker market response."""

    model_config = ConfigDict(frozen=True)

    name: str
    price: Decimal
    point: Decimal | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response dict."""
        return cls.model_validate(data)


class ODMarketRaw(BaseModel):
    """Nested market response from an Odds API v4 bookmaker."""

    model_config = ConfigDict(frozen=True)

    market_key: str
    outcomes: tuple[ODOutcomeRaw, ...] = ()

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response dict."""
        return cls.model_validate(data)


class ODBookmakerRaw(BaseModel):
    """Nested bookmaker response from an Odds API v4 event."""

    model_config = ConfigDict(frozen=True)

    bookmaker_key: str
    bookmaker_title: str
    last_update: datetime | None = None
    markets: tuple[ODMarketRaw, ...] = ()

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response dict."""
        return cls.model_validate(data)


class ODEventRaw(BaseModel):
    """Full event response from Odds API v4 with nested bookmakers/markets/outcomes."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    sport_key: str
    sport_title: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmakers: tuple[ODBookmakerRaw, ...] = ()

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response dict."""
        return cls.model_validate(data)


class ODOddsRaw(BaseModel):
    """Source model for individual odds snapshots from The Odds API v4.

    Represents a single flattened odds measurement: one bookmaker, one market,
    one outcome, at one point in time.  Originally in the legacy ODOdds
    SQLAlchemy model in sports-betting-services-previous.
    """

    model_config = ConfigDict(frozen=True)

    od_fixture_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    measurement_time: datetime
    bookmaker_key: str
    market: str  # h2h, spreads, totals
    outcome_name: str  # home team name, away team name, "Draw", "Over", "Under"
    outcome_price: Decimal
    outcome_point: Decimal | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response / CSV row dict."""
        return cls.model_validate(data)


class ODTeamsRaw(BaseModel):
    """Maps Odds API team names to internal IDs.

    Originally in the legacy ODTeams SQLAlchemy model in
    sports-betting-services-previous.
    """

    model_config = ConfigDict(frozen=True)

    league_name: str
    af_league_id: int | None = None
    season: str
    od_team_id: str
    team_name: str

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw mapping dict."""
        return cls.model_validate(data)
