"""Understat source schemas — xG data, shots, player seasons, team history."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


class UnderstatXGData(BaseModel):
    """Understat xG summary for a match."""

    model_config = ConfigDict(frozen=True)

    fixture_id: int
    home_xg: float
    away_xg: float
    home_npxg: float | None = None
    away_npxg: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class UnderstatShot(BaseModel):
    """Understat individual shot data with xG."""

    model_config = ConfigDict(frozen=True)

    shot_id: int
    fixture_id: int
    player_id: int
    player_name: str
    minute: int
    result: str
    x: float
    y: float
    xg: float
    situation: str | None = None
    shot_type: str | None = None
    home_away: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    last_action: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class UnderstatPlayerSeason(BaseModel):
    """Understat player season aggregates."""

    model_config = ConfigDict(frozen=True)

    player_id: int
    season: int
    league: str
    team: str | None = None
    games: int | None = None
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    xg: float | None = None
    xa: float | None = None
    npxg: float | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class UnderstatTeamHistory(BaseModel):
    """Understat team per-match advanced stats."""

    model_config = ConfigDict(frozen=True)

    team_id: int
    team_name: str
    league: str
    season: int
    match_date: datetime
    home_away: str
    xg: float
    xga: float
    npxg: float | None = None
    npxga: float | None = None
    scored: int
    conceded: int
    result: str
    pts: int
    xpts: float | None = None
    ppda_att: int | None = None
    ppda_def: int | None = None
    deep: int | None = None
    deep_allowed: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class UnderstatMatch(BaseModel):
    """Understat full match data with xG and forecasts."""

    model_config = ConfigDict(frozen=True)

    fixture_id: int
    date: datetime
    league: str
    season: int
    is_result: bool
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    forecast_win: float | None = None
    forecast_draw: float | None = None
    forecast_loss: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
