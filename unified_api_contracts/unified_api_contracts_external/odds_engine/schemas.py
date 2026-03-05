"""Odds Engine REST API schemas — OpenAPI 3.0 style.

Ref: https://api.oddsengine.dev/docs
Base URL: https://api.oddsengine.dev/v1
"""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

_RawDict = dict[str, str | int | float | bool | None]


# --- Nested models ---


class OddsEngineBookOdds(BaseModel):
    """Single bookmaker odds within a market."""

    model_config = ConfigDict(frozen=True)

    book: str
    home: int | float | None = None  # American odds
    away: int | float | None = None
    draw: int | float | None = None
    over: int | float | None = None
    under: int | float | None = None
    line: float | None = None  # for spread/totals

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsEngineMarket(BaseModel):
    """Market with bookmaker odds (Moneyline, Spread, Totals, Props)."""

    model_config = ConfigDict(frozen=True)

    market: str
    books: list[OddsEngineBookOdds] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# --- GET /odds response ---


class OddsEngineOddsData(BaseModel):
    """Data payload for GET /odds response."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    event: str
    event_start: datetime | str
    home_team: str
    away_team: str
    league: str
    markets: list[OddsEngineMarket] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsEngineMeta(BaseModel):
    """Meta envelope (OpenAPI 3.0 style)."""

    model_config = ConfigDict(frozen=True)

    response_ms: int | None = None


class OddsEngineOddsResponse(BaseModel):
    """GET /odds response envelope."""

    model_config = ConfigDict(frozen=True)

    data: OddsEngineOddsData
    meta: OddsEngineMeta | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# --- Events / schedule (OpenAPI 3.0 list pattern) ---


class OddsEngineEvent(BaseModel):
    """Event from events/schedule list."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    event: str
    event_start: datetime | str
    home_team: str
    away_team: str
    league: str

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsEngineEventsResponse(BaseModel):
    """GET /events response envelope."""

    model_config = ConfigDict(frozen=True)

    data: list[OddsEngineEvent]
    meta: OddsEngineMeta | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# --- Error ---


class OddsEngineError(BaseModel):
    """Odds Engine error response."""

    model_config = ConfigDict(frozen=True)

    code: str | None = None
    message: str
    detail: str | None = None
