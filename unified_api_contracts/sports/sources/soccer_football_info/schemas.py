"""Soccer Football Info source schemas — match, team, league, dominance, progressive stats/odds."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


class SFILeague(BaseModel):
    """Soccer Football Info league data."""

    model_config = ConfigDict(frozen=True)

    league_id: str
    season_id: str
    league_name: str
    country_code: str | None = None
    season_name: str | None = None
    season_from: datetime | None = None
    season_to: datetime | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SFITeam(BaseModel):
    """Soccer Football Info team standings data."""

    model_config = ConfigDict(frozen=True)

    team_id: str
    team_name: str
    league_id: str
    season_id: str
    position: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    points: int | None = None
    goals_scored: int | None = None
    goals_conceded: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SFIMatchDominance(BaseModel):
    """Soccer Football Info 30-second dominance snapshot."""

    model_config = ConfigDict(frozen=True)

    match_id: str
    timer: str
    home_dominance: float
    away_dominance: float

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SFIMatchProgressiveStats(BaseModel):
    """Soccer Football Info progressive match stats at 30-second intervals."""

    model_config = ConfigDict(frozen=True)

    match_id: str
    timer: str
    team: str
    goals: int | None = None
    possession: int | None = None
    shots_total: int | None = None
    shots_on_target: int | None = None
    corners: int | None = None
    fouls: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    dangerous_attacks: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SFIMatchProgressiveOdds(BaseModel):
    """Soccer Football Info progressive odds at 30-second intervals."""

    model_config = ConfigDict(frozen=True)

    match_id: str
    timer: str
    odds_home: float | None = None
    odds_draw: float | None = None
    odds_away: float | None = None
    ah_home: float | None = None
    ah_away: float | None = None
    ah_line: float | None = None
    ou_over: float | None = None
    ou_under: float | None = None
    ou_line: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class SFIMatch(BaseModel):
    """Soccer Football Info full match data."""

    model_config = ConfigDict(frozen=True)

    match_id: str
    date: datetime
    status: str | None = None
    league_id: str | None = None
    league_name: str | None = None
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    home_score: int | None = None
    away_score: int | None = None
    home_xg_kickoff: float | None = None
    away_xg_kickoff: float | None = None
    home_xg_live: float | None = None
    away_xg_live: float | None = None
    home_possession: int | None = None
    away_possession: int | None = None
    referee_name: str | None = None
    stadium_name: str | None = None
    odds_start_home: float | None = None
    odds_start_draw: float | None = None
    odds_start_away: float | None = None
    odds_kick_home: float | None = None
    odds_kick_draw: float | None = None
    odds_kick_away: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
