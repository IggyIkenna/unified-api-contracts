"""The Odds API v4 source schemas — events, bookmakers, markets, outcomes."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


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
