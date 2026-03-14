"""Pinnacle source schemas — odds, lines, events, matchups."""

from __future__ import annotations

__api_version__ = "v3"  # matches provider_api_versions.yaml

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict


class PinnacleEvent(BaseModel):
    """Pinnacle sports event."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    sport_id: int
    league_id: int
    starts: datetime
    home: str
    away: str
    live_status: int | None = None
    status: str | None = None
    parent_id: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class PinnacleLine(BaseModel):
    """Pinnacle odds line for a specific market."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    period_number: int
    line_id: int
    market_type: str
    home_odds: Decimal | None = None
    draw_odds: Decimal | None = None
    away_odds: Decimal | None = None
    handicap: Decimal | None = None
    over_odds: Decimal | None = None
    under_odds: Decimal | None = None
    total_points: Decimal | None = None
    max_bet: Decimal | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class PinnacleMatchup(BaseModel):
    """Pinnacle matchup with combined event and line data."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    starts: datetime
    home: str
    away: str
    league_id: int
    moneyline_home: Decimal | None = None
    moneyline_draw: Decimal | None = None
    moneyline_away: Decimal | None = None
    spread_home: Decimal | None = None
    spread_away: Decimal | None = None
    spread_handicap: Decimal | None = None
    total_over: Decimal | None = None
    total_under: Decimal | None = None
    total_points: Decimal | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class PinnacleOdds(BaseModel):
    """Pinnacle aggregated odds for a match."""

    model_config = ConfigDict(frozen=True)

    event_id: int
    home: str
    away: str
    starts: datetime
    lines: list[PinnacleLine]

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
