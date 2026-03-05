"""MetaBet REST API schemas — odds, events, schedule.

Ref: https://www.metabet.io/products (Real-Time Odds API, Dynamic Odds)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

_RawDict = dict[str, str | int | float | bool | None]


# --- Odds ---


class MetabetOutcome(BaseModel):
    """Single outcome within a market."""

    model_config = ConfigDict(frozen=True)

    name: str
    price: Decimal | float
    point: Decimal | float | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class MetabetMarket(BaseModel):
    """Market (moneyline, spread, total, etc.)."""

    model_config = ConfigDict(frozen=True)

    market: str
    outcomes: list[MetabetOutcome] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class MetabetBookmaker(BaseModel):
    """Bookmaker with markets."""

    model_config = ConfigDict(frozen=True)

    book: str
    markets: list[MetabetMarket] = Field(default_factory=list)


class MetabetOddsItem(BaseModel):
    """Odds for a single event from a bookmaker."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    home_team: str
    away_team: str
    commence_time: datetime | str
    bookmaker: str
    markets: list[MetabetMarket] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# --- Events / schedule ---


class MetabetEvent(BaseModel):
    """Event from schedule/events list."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    home_team: str
    away_team: str
    commence_time: datetime | str
    league: str | None = None
    sport: str | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class MetabetOddsResponse(BaseModel):
    """GET /odds response envelope."""

    model_config = ConfigDict(frozen=True)

    data: list[MetabetOddsItem]


class MetabetEventsResponse(BaseModel):
    """GET /events or /schedule response envelope."""

    model_config = ConfigDict(frozen=True)

    data: list[MetabetEvent]


# --- Error ---


class MetabetError(BaseModel):
    """MetaBet error response."""

    model_config = ConfigDict(frozen=True)

    code: str | None = None
    message: str
