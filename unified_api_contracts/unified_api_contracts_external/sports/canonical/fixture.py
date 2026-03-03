"""Canonical fixture, team, league, player, venue, and referee schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


class CanonicalVenue(BaseModel):
    """Normalised venue/stadium across all data sources."""

    model_config = ConfigDict(frozen=True)

    venue_id: str
    name: str
    city: str | None = None
    country: str | None = None
    capacity: int | None = None
    surface: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class CanonicalReferee(BaseModel):
    """Normalised referee across all data sources."""

    model_config = ConfigDict(frozen=True)

    referee_id: str
    name: str
    nationality: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class CanonicalPlayer(BaseModel):
    """Normalised player across all data sources."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    nationality: str | None = None
    position: str | None = None
    date_of_birth: str | None = None
    height_cm: int | None = None
    weight_kg: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class CanonicalTeam(BaseModel):
    """Normalised team across all data sources."""

    model_config = ConfigDict(frozen=True)

    team_id: str
    name: str
    short_name: str | None = None
    country: str | None = None
    founded: int | None = None
    logo_url: str | None = None
    venue: CanonicalVenue | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class CanonicalLeague(BaseModel):
    """Normalised league/competition across all data sources."""

    model_config = ConfigDict(frozen=True)

    league_id: str
    name: str
    country: str
    league_type: str | None = None
    logo_url: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class CanonicalFixture(BaseModel):
    """Normalised fixture/match across all data sources."""

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    home_team: CanonicalTeam
    away_team: CanonicalTeam
    league: CanonicalLeague
    kickoff_utc: datetime
    venue: CanonicalVenue | None = None
    referee: CanonicalReferee | None = None
    season: str
    match_week: int | None = None
    source: str

    # Match status (e.g. "Match Finished", "Not Started", "1H", "HT", "2H")
    status: str | None = None

    # Result fields (populated after match finishes)
    home_goals: int | None = None
    away_goals: int | None = None
    home_goals_halftime: int | None = None
    away_goals_halftime: int | None = None

    # Basic match statistics (from API-Football fixture_stats or equivalent)
    home_xg: float | None = None
    away_xg: float | None = None
    home_shots_on_target: int | None = None
    away_shots_on_target: int | None = None
    home_total_shots: int | None = None
    away_total_shots: int | None = None
    home_possession: int | None = None
    away_possession: int | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    home_fouls: int | None = None
    away_fouls: int | None = None
    home_yellow_cards: int | None = None
    away_yellow_cards: int | None = None
    home_red_cards: int | None = None
    away_red_cards: int | None = None

    # Extended match statistics (shots blocked, offsides, passing)
    home_shots_blocked: int | None = None
    away_shots_blocked: int | None = None
    home_offsides: int | None = None
    away_offsides: int | None = None
    home_passes_total: int | None = None
    away_passes_total: int | None = None
    home_passes_accuracy: int | None = None
    away_passes_accuracy: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a nested dictionary."""
        return cls.model_validate(data)
