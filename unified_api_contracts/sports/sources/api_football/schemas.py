"""API-Football source schemas — raw API response types."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict


class APIFootballVenue(BaseModel):
    """API-Football venue data."""

    model_config = ConfigDict(frozen=True)

    venue_id: int
    name: str
    address: str | None = None
    city: str | None = None
    country: str | None = None
    capacity: int | None = None
    surface: str | None = None
    image: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballReferee(BaseModel):
    """API-Football referee data."""

    model_config = ConfigDict(frozen=True)

    name: str
    nationality: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballLeague(BaseModel):
    """API-Football league data."""

    model_config = ConfigDict(frozen=True)

    league_id: int
    name: str
    country: str
    league_type: str | None = None
    season: int
    logo: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballTeam(BaseModel):
    """API-Football team data."""

    model_config = ConfigDict(frozen=True)

    team_id: int
    name: str
    code: str | None = None
    country: str | None = None
    founded: int | None = None
    national: bool | None = None
    logo: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballPlayer(BaseModel):
    """API-Football player data."""

    model_config = ConfigDict(frozen=True)

    player_id: int
    name: str
    firstname: str | None = None
    lastname: str | None = None
    age: int | None = None
    nationality: str | None = None
    height: str | None = None
    weight: str | None = None
    position: str | None = None
    photo: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballStats(BaseModel):
    """API-Football fixture team statistics."""

    model_config = ConfigDict(frozen=True)

    team_id: int
    fixture_id: int
    shots_on_goal: int | None = None
    shots_off_goal: int | None = None
    total_shots: int | None = None
    blocked_shots: int | None = None
    corner_kicks: int | None = None
    offsides: int | None = None
    ball_possession: int | None = None
    fouls: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    total_passes: int | None = None
    passes_accurate: int | None = None
    expected_goals: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballLineup(BaseModel):
    """API-Football lineup entry."""

    model_config = ConfigDict(frozen=True)

    fixture_id: int
    team_id: int
    player_id: int | None = None
    player_number: int | None = None
    player_position: str | None = None
    player_grid: str | None = None
    substitute: bool = False

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballEvent(BaseModel):
    """API-Football fixture event (goal, card, substitution)."""

    model_config = ConfigDict(frozen=True)

    fixture_id: int
    team_id: int | None = None
    player_id: int | None = None
    time_elapsed: int | None = None
    time_extra: int | None = None
    event_type: str
    detail: str | None = None
    comments: str | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballOdds(BaseModel):
    """API-Football pre-match odds."""

    model_config = ConfigDict(frozen=True)

    fixture_id: int
    league_id: int
    bookmaker_id: int
    bookmaker_name: str
    market_name: str
    value_name: str
    odd: str

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class APIFootballFixture(BaseModel):
    """API-Football full fixture response."""

    model_config = ConfigDict(frozen=True)

    fixture_id: int
    referee: str | None = None
    date: datetime
    venue_id: int | None = None
    venue_name: str | None = None
    venue_city: str | None = None
    status_long: str | None = None
    status_short: str | None = None
    status_elapsed: int | None = None
    league_id: int
    league_name: str
    league_country: str
    season: int
    round_name: str | None = None
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_score_halftime: int | None = None
    away_score_halftime: int | None = None
    home_score_fulltime: int | None = None
    away_score_fulltime: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
