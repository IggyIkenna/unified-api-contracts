"""Understat source schemas — xG data, shots, player seasons, team history.

Includes both normalised Understat* models and raw US*Raw models migrated from
sports-betting-services-previous USTeam/USMatch/USPlayer/etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Normalised Understat schemas (pre-existing)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Raw US* schemas — migrated from sports-betting-services-previous
# ---------------------------------------------------------------------------


class USTeamRaw(BaseModel):
    """Raw Understat team record per league-season."""

    model_config = ConfigDict(frozen=True)

    us_team_id: int
    team_name: str
    league: str
    season: str
    matches_fetched: bool | None = None
    roster_fetched: bool | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USTeamHistoryRaw(BaseModel):
    """Raw Understat team per-match advanced stats from league endpoint."""

    model_config = ConfigDict(frozen=True)

    us_team_id: int
    league: str
    season: str
    match_date: str
    # xG stats
    xg: float | None = None
    xga: float | None = None
    npxg: float | None = None
    npxga: float | None = None
    npxgd: float | None = None
    # Actual results
    scored: int | float | None = None
    missed: int | float | None = None
    pts: int | float | None = None
    xpts: int | float | None = None
    # PPDA (Passes Per Defensive Action) — pressing intensity
    ppda_att: float | None = None
    ppda_def: float | None = None
    ppda_allowed_att: float | None = None
    ppda_allowed_def: float | None = None
    # Deep passes
    deep: int | None = None
    deep_allowed: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USMatchRaw(BaseModel):
    """Raw Understat match record with xG and forecast probabilities."""

    model_config = ConfigDict(frozen=True)

    us_fixture_id: int
    home_team: str
    away_team: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    forecast_home: float | None = None
    forecast_draw: float | None = None
    forecast_away: float | None = None
    league: str
    season: str

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USPlayerRaw(BaseModel):
    """Raw Understat player aggregated stats per league-season."""

    model_config = ConfigDict(frozen=True)

    us_player_id: int
    team_name: str
    position: str | None = None
    # Counting stats
    games: int | None = None
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    shots: int | None = None
    key_passes: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    # Expected stats
    xg: float | None = None
    xa: float | None = None
    npg: float | None = None
    npxg: float | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USMatchShotRaw(BaseModel):
    """Raw Understat shot-level data with xG per shot in a match."""

    model_config = ConfigDict(frozen=True)

    us_fixture_id: int
    us_shot_id: int
    minute: int
    result: str
    x: float
    y: float
    xg: float | None = None
    player_name: str | None = None
    situation: str | None = None
    shot_type: str | None = None
    last_action: str | None = None
    team: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USMatchRosterRaw(BaseModel):
    """Raw Understat match roster entry — player stats per match."""

    model_config = ConfigDict(frozen=True)

    us_fixture_id: int
    us_player_id: int
    position: str | None = None
    minutes: int | None = None
    # Counting stats
    goals: int | None = None
    assists: int | None = None
    shots: int | None = None
    key_passes: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    # xG stats
    xg: float | None = None
    xa: float | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None
    # Substitution info
    sub_in: int | None = None
    sub_out: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USPlayerShotRaw(BaseModel):
    """Raw Understat player shot — career shot data for a player."""

    model_config = ConfigDict(frozen=True)

    us_player_id: int
    us_shot_id: int
    us_fixture_id: int
    minute: int
    result: str
    x: float
    y: float
    xg: float | None = None
    situation: str | None = None
    shot_type: str | None = None
    season: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USPlayerMatchRaw(BaseModel):
    """Raw Understat per-match stats for a player."""

    model_config = ConfigDict(frozen=True)

    us_player_id: int
    us_fixture_id: int
    position: str | None = None
    # Counting stats
    games: int | None = None
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    shots: int | None = None
    key_passes: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    # Expected stats
    xg: float | None = None
    xa: float | None = None
    npg: float | None = None
    npxg: float | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class USPlayerSeasonRaw(BaseModel):
    """Raw Understat player season-aggregated xG/xA stats."""

    model_config = ConfigDict(frozen=True)

    us_player_id: int
    season: str
    league: str
    team: str | None = None
    # Counting stats
    games: int | None = None
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    shots: int | None = None
    key_passes: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    # xG stats
    xg: float | None = None
    xa: float | None = None
    npg: float | None = None
    npxg: float | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)
