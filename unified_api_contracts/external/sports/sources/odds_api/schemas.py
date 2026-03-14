"""The Odds API v4 source schemas — events, bookmakers, markets, outcomes.

Includes both the original float-based convenience wrappers (OddsApiOutcome, etc.)
and the new Decimal-based raw source models (ODOutcomeRaw, etc.) originally in
sports-betting-services-previous.
"""

from __future__ import annotations

__api_version__ = "v4"  # matches provider_api_versions.yaml

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Original convenience schemas (float-based, list collections)
# ---------------------------------------------------------------------------


class OddsApiOutcome(BaseModel):
    """A single outcome within an Odds API market."""

    model_config = ConfigDict(frozen=True)

    name: str
    price: float
    point: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsApiMarket(BaseModel):
    """An Odds API market (h2h, spreads, totals)."""

    model_config = ConfigDict(frozen=True)

    key: str
    last_update: datetime
    outcomes: list[OddsApiOutcome]

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsApiBookmaker(BaseModel):
    """An Odds API bookmaker entry with markets."""

    model_config = ConfigDict(frozen=True)

    key: str
    title: str
    last_update: datetime
    markets: list[OddsApiMarket]

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsApiEvent(BaseModel):
    """An Odds API event with odds from multiple bookmakers."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    sport_key: str
    sport_title: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmakers: list[OddsApiBookmaker]

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# ---------------------------------------------------------------------------
# New Decimal-based raw source models (originally in sports-betting-services-previous)
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
