"""FootyStats (Football-Data-API) schemas.

Ref: https://api.football-data-api.com
Auth: key query parameter
"""

from pydantic import BaseModel

from unified_api_contracts.shared import ErrorAction


class FootystatsLeague(BaseModel):
    """League from FootyStats."""

    id: int | None = None
    name: str | None = None
    country: str | None = None
    season: str | None = None
    year: int | None = None


class FootystatsTeam(BaseModel):
    """Team from FootyStats."""

    id: int | None = None
    clean_name: str | None = None
    english_name: str | None = None
    country: str | None = None


class FootystatsMatch(BaseModel):
    """Match from FootyStats."""

    id: int | None = None
    home_id: int | None = None
    away_id: int | None = None
    home_goal_count: int | None = None
    away_goal_count: int | None = None
    date_unix: int | None = None
    status: str | None = None
    competition_id: int | None = None
    btts_potential: float | None = None
    over25_potential: float | None = None
    ov35_potential: float | None = None
    corner_total: int | None = None
    btts: bool | None = None
    over05: bool | None = None
    over15: bool | None = None
    over25: bool | None = None
    over35: bool | None = None
    over45: bool | None = None
    over55: bool | None = None


class FootystatsPlayer(BaseModel):
    """Player from FootyStats."""

    id: int | None = None
    full_name: str | None = None
    team_id: int | None = None
    season: str | None = None
    goals_overall: int | None = None
    assists_overall: int | None = None
    minutes_played: int | None = None


class FootystatsMatchStats(BaseModel):
    """Match statistics from FootyStats."""

    id: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None


class FootystatsStandings(BaseModel):
    """League standings from FootyStats."""

    position: int | None = None
    team_id: int | None = None
    team_name: str | None = None
    played: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    points: int | None = None


class FootystatsError(BaseModel):
    """FootyStats error response."""

    error: str | None = None
    success: bool | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map FootyStats error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
