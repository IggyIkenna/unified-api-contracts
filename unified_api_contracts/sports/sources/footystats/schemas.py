"""FootyStats source schemas — match, team, league, player, referee, BTTS, over/under, odds."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


class FootyStatsLeague(BaseModel):
    """FootyStats league data."""

    model_config = ConfigDict(frozen=True)

    league_id: int
    name: str
    english_name: str | None = None
    country: str | None = None
    season: str
    total_matches: int | None = None
    matches_completed: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class FootyStatsTeam(BaseModel):
    """FootyStats team data."""

    model_config = ConfigDict(frozen=True)

    team_id: int
    name: str
    clean_name: str | None = None
    english_name: str | None = None
    country: str | None = None
    season: str | None = None
    table_position: int | None = None
    performance_rank: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class FootyStatsPlayer(BaseModel):
    """FootyStats player data."""

    model_config = ConfigDict(frozen=True)

    player_id: int
    full_name: str
    position: str | None = None
    nationality: str | None = None
    age: int | None = None
    appearances_overall: int | None = None
    goals_overall: int | None = None
    assists_overall: int | None = None
    minutes_played_overall: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class FootyStatsReferee(BaseModel):
    """FootyStats referee data."""

    model_config = ConfigDict(frozen=True)

    referee_id: int
    full_name: str
    nationality: str | None = None
    appearances_overall: int | None = None
    cards_per_match_overall: float | None = None
    goals_per_match_overall: float | None = None
    btts_percentage: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class FootyStatsBTTS(BaseModel):
    """FootyStats both-teams-to-score statistics."""

    model_config = ConfigDict(frozen=True)

    match_id: int
    btts: bool
    btts_potential: int | None = None
    btts_fhg_potential: int | None = None
    btts_2hg_potential: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class FootyStatsOverUnder(BaseModel):
    """FootyStats over/under goal statistics."""

    model_config = ConfigDict(frozen=True)

    match_id: int
    over05: bool | None = None
    over15: bool | None = None
    over25: bool | None = None
    over35: bool | None = None
    over45: bool | None = None
    o25_potential: int | None = None
    o35_potential: int | None = None
    o45_potential: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class FootyStatsOdds(BaseModel):
    """FootyStats odds data from comparison table."""

    model_config = ConfigDict(frozen=True)

    match_id: int
    market_type: str
    market_option: str
    bookmaker: str
    odds_value: float

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class FootyStatsMatch(BaseModel):
    """FootyStats full match data."""

    model_config = ConfigDict(frozen=True)

    match_id: int
    date_unix: int
    competition_id: int
    season: str
    home_id: int
    away_id: int
    home_name: str
    away_name: str
    home_goals: int | None = None
    away_goals: int | None = None
    total_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    status: str | None = None
    game_week: int | None = None
    home_possession: int | None = None
    away_possession: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    odds_ft_1: float | None = None
    odds_ft_x: float | None = None
    odds_ft_2: float | None = None
    odds_btts_yes: float | None = None
    odds_btts_no: float | None = None
    odds_ft_over25: float | None = None
    odds_ft_under25: float | None = None
    created_at: datetime | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
