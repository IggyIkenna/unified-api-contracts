"""SharpAPI REST API schemas — GET /odds, /odds/best, /schedule, /events.

Ref: https://docs.sharpapi.io/api-reference/overview
Base URL: https://api.sharpapi.io/api/v1
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict

_RawDict = dict[str, str | int | float | bool | None]


# --- GET /odds, /odds/best response items ---


class SharpApiOddsItem(BaseModel):
    """Single odds entry from GET /odds or /odds/best."""

    model_config = ConfigDict(frozen=True)

    id: str
    sportsbook: str
    sportsbook_name: str
    sport: str
    home_team: str
    away_team: str
    market_type: str  # moneyline, spread, total
    selection: str
    odds_american: int | float
    odds_decimal: float
    probability: float
    is_live: bool = False

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# --- GET /events response (schedule = list of events) ---


class SharpApiEvent(BaseModel):
    """Event from GET /events (schedule/events list)."""

    model_config = ConfigDict(frozen=True)

    id: str
    sport: str
    home_team: str
    away_team: str
    start_time: datetime

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# --- Response envelope (data + meta) ---


class SharpApiPagination(BaseModel):
    """Pagination metadata from list responses."""

    model_config = ConfigDict(frozen=True)

    limit: int
    offset: int
    has_more: bool
    next_offset: int | None = None


class SharpApiMeta(BaseModel):
    """Meta envelope for list responses."""

    model_config = ConfigDict(frozen=True)

    count: int
    total: int
    pagination: SharpApiPagination | None = None
    updated_at: datetime | None = None
    filters: dict[str, str | list[str]] | None = None


class SharpApiOddsResponse(BaseModel):
    """GET /odds response envelope."""

    model_config = ConfigDict(frozen=True)

    data: list[SharpApiOddsItem]
    meta: SharpApiMeta

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SharpApiBestOddsResponse(BaseModel):
    """GET /odds/best response envelope."""

    model_config = ConfigDict(frozen=True)

    data: list[SharpApiOddsItem]
    meta: SharpApiMeta

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SharpApiScheduleResponse(BaseModel):
    """GET /schedule response — list of events (alias for events)."""

    model_config = ConfigDict(frozen=True)

    data: list[SharpApiEvent]
    meta: SharpApiMeta

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SharpApiEventsResponse(BaseModel):
    """GET /events response envelope."""

    model_config = ConfigDict(frozen=True)

    data: list[SharpApiEvent]
    meta: SharpApiMeta

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


# --- Error ---


class SharpApiError(BaseModel):
    """SharpAPI error envelope."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    docs: str | None = None
