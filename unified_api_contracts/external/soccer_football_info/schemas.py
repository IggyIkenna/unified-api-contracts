"""Soccer-Football-Info API schemas.

Ref: https://rapidapi.com/soccer-football-info-soccer-football-info-default/api/soccer-football-info
Auth: x-rapidapi-key, x-rapidapi-host headers (RapidAPI)
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel

from unified_api_contracts.canonical.errors import ErrorAction


class SoccerFootballChampionship(BaseModel):
    """Championship/league from Soccer-Football-Info."""

    id: str | None = None
    name: str | None = None
    country: str | None = None
    has_image: bool | None = None
    important: bool | None = None


class SoccerFootballTeam(BaseModel):
    """Team from Soccer-Football-Info."""

    id: str | None = None
    name: str | None = None
    country: str | None = None
    has_image: bool | None = None


class SoccerFootballPlayer(BaseModel):
    """Player from Soccer-Football-Info."""

    id: str | None = None
    name: str | None = None
    country: str | None = None
    has_image: bool | None = None
    team_id: str | None = None


class SoccerFootballManager(BaseModel):
    """Manager from Soccer-Football-Info."""

    id: str | None = None
    name: str | None = None
    country: str | None = None


class SoccerFootballReferee(BaseModel):
    """Referee from Soccer-Football-Info."""

    id: str | None = None
    name: str | None = None
    country: str | None = None


class SoccerFootballStadium(BaseModel):
    """Stadium from Soccer-Football-Info."""

    id: str | None = None
    name: str | None = None
    city: str | None = None
    country: str | None = None
    capacity: int | None = None


class SoccerFootballCountry(BaseModel):
    """Country from Soccer-Football-Info."""

    code: str | None = None
    name: str | None = None


class SoccerFootballMatch(BaseModel):
    """Match from Soccer-Football-Info."""

    id: str | None = None
    home_team_id: str | None = None
    away_team_id: str | None = None
    championship_id: str | None = None
    date: str | None = None
    time: str | None = None
    status: str | None = None
    home_score: int | None = None
    away_score: int | None = None


class SoccerFootballError(BaseModel):
    """Soccer-Football-Info error response."""

    error: str | None = None
    message: str | None = None
    status: int | None = None
    errors: list[str] | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Soccer-Football-Info error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL
        return ErrorAction.FAIL
