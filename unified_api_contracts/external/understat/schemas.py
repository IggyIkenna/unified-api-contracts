"""Understat xG (expected goals) data schemas.

Ref: https://understat.com
Auth: None (public AJAX endpoints, browser-like headers)
Leagues: EPL, La_Liga, Bundesliga, Serie_A, Ligue_1, RFPL
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel

from unified_api_contracts.canonical.errors import ErrorAction


class UnderstatLeague(BaseModel):
    """Understat league identifier.

    Options: EPL, La_Liga, Bundesliga, Serie_A, Ligue_1, RFPL.
    """

    id: str | None = None
    name: str | None = None
    season: str | int | None = None


class UnderstatTeamHistoryEntry(BaseModel):
    """Per-match team history (xG, PPDA, etc.)."""

    date: str | None = None
    h_a: str | None = None
    xg: float | None = None
    xga: float | None = None
    npxg: float | None = None
    npxga: float | None = None
    scored: int | None = None
    missed: int | None = None
    result: str | None = None
    pts: int | None = None
    xpts: float | None = None
    wins: int | None = None
    draws: int | None = None
    loses: int | None = None
    deep: int | None = None
    deep_allowed: int | None = None


class UnderstatTeam(BaseModel):
    """Team from Understat with xG history."""

    id: int | None = None
    title: str | None = None
    short_title: str | None = None
    history: list[UnderstatTeamHistoryEntry] | None = None


class UnderstatMatchTeam(BaseModel):
    """Home or away team in match."""

    id: int | None = None
    title: str | None = None
    short_title: str | None = None


class UnderstatMatch(BaseModel):
    """Match from Understat with xG."""

    id: int | str | None = None
    h: UnderstatMatchTeam | dict[str, object] | None = None
    a: UnderstatMatchTeam | dict[str, object] | None = None
    goals_h: int | None = None
    goals_a: int | None = None
    xg_h: float | None = None
    xg_a: float | None = None
    datetime: str | None = None
    is_result: bool | None = None
    side: str | None = None


class UnderstatPlayer(BaseModel):
    """Player from Understat with xG stats."""

    id: int | str | None = None
    player_name: str | None = None
    team_title: str | None = None
    games: int | None = None
    time: int | None = None
    goals: int | None = None
    xg: float | None = None
    assists: int | None = None
    xa: float | None = None
    npg: int | None = None
    npxg: float | None = None
    xg_chain: float | None = None
    xg_buildup: float | None = None


class UnderstatShot(BaseModel):
    """Shot from Understat with xG."""

    id: int | str | None = None
    minute: int | None = None
    result: str | None = None
    x: float | None = None
    y: float | None = None
    xg: float | None = None
    player: str | None = None
    situation: str | None = None
    match_id: int | str | None = None
    h_a: str | None = None
    player_id: int | str | None = None
    last_action: str | None = None
    period: int | None = None
    shot_type: str | None = None


class UnderstatError(BaseModel):
    """Understat error response."""

    error: str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Understat error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        return ErrorAction.FAIL
