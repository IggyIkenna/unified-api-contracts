"""Soccer-Football-Info API schemas.

Ref: https://rapidapi.com/soccer-football-info-soccer-football-info-default/api/soccer-football-info
Auth: x-rapidapi-key, x-rapidapi-host headers (RapidAPI)
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


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


# =============================================================================
# Source schemas (merged from external/sports/sources/soccer_football_info/)
# =============================================================================

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


# ---------------------------------------------------------------------------
# Raw source schemas — mirror the legacy SF* SQLAlchemy tables from
# sports-betting-services-previous/footballbets/core/models.py.
# Used at the ingestion boundary; transformed into SFI* models downstream.
# ---------------------------------------------------------------------------

_RawFieldValue = str | int | float | bool | Decimal | None
"""Union accepted by ``from_raw`` classmethods on SF*Raw models."""


class SFLeagueRaw(BaseModel):
    """Raw league+season record from the Soccer Football Info API."""

    model_config = ConfigDict(frozen=True)

    sf_league_id: str
    sf_season_id: str
    league_name: str
    country_code: str | None = None
    has_image: bool | None = None
    important: bool | None = None
    season_name: str | None = None
    season_from: datetime | None = None
    season_to: datetime | None = None
    af_league_id: int | None = None
    af_season: int | None = None
    teams_fetched: bool | None = None
    matches_fetched: bool | None = None

    @classmethod
    def from_raw(cls, data: dict[str, _RawFieldValue]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class SFTeamRaw(BaseModel):
    """Raw team standings record from the Soccer Football Info API."""

    model_config = ConfigDict(frozen=True)

    sf_team_id: str
    sf_league_id: str
    sf_season_id: str
    team_name: str
    league_name: str | None = None
    league_country: str | None = None
    season_name: str | None = None
    group_name: str | None = None
    position: int | None = None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    points: int | None = None
    goals_scored: int | None = None
    goals_conceded: int | None = None
    af_league_id: int | None = None
    af_season: int | None = None
    af_team_id: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, _RawFieldValue]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class SFMatchRaw(BaseModel):
    """Raw full match record from the Soccer Football Info API.

    Contains score breakdown (FT/HT/OT/penalties), match stats, xG,
    pre-match odds (starting + kickoff) and cross-reference IDs.
    """

    model_config = ConfigDict(frozen=True)

    # Identifiers
    sf_match_id: str
    date: str
    status: str | None = None
    timer: str | None = None

    # League
    sf_league_id: str | None = None
    league_name: str | None = None

    # Home team
    sf_home_id: str
    home_name: str
    sf_home_manager_id: str | None = None
    home_manager_name: str | None = None

    # Home scores
    ft_home: int | None = None
    ht_home: int | None = None
    ot_home: int | None = None
    pen_home: int | None = None

    # Home stats
    home_possession: int | None = None
    home_attacks: int | None = None
    home_dangerous_attacks: int | None = None
    home_shots_total: int | None = None
    home_shots_on: int | None = None
    home_shots_off: int | None = None
    home_corners: int | None = None
    home_fouls: int | None = None
    home_yellow_cards: int | None = None
    home_red_cards: int | None = None
    home_substitutions: int | None = None
    home_throwins: int | None = None
    home_penalties: int | None = None
    home_xg_kickoff: float | None = None
    home_xg_live: float | None = None

    # Away team
    sf_away_id: str
    away_name: str
    sf_away_manager_id: str | None = None
    away_manager_name: str | None = None

    # Away scores
    ft_away: int | None = None
    ht_away: int | None = None
    ot_away: int | None = None
    pen_away: int | None = None

    # Away stats
    away_possession: int | None = None
    away_attacks: int | None = None
    away_dangerous_attacks: int | None = None
    away_shots_total: int | None = None
    away_shots_on: int | None = None
    away_shots_off: int | None = None
    away_corners: int | None = None
    away_fouls: int | None = None
    away_yellow_cards: int | None = None
    away_red_cards: int | None = None
    away_substitutions: int | None = None
    away_throwins: int | None = None
    away_penalties: int | None = None
    away_xg_kickoff: float | None = None
    away_xg_live: float | None = None

    # Officials / venue
    sf_referee_id: str | None = None
    referee_name: str | None = None
    sf_stadium_id: str | None = None
    stadium_name: str | None = None

    # Odds — starting (pre-match opening)
    odds_start_home: Decimal | None = None
    odds_start_draw: Decimal | None = None
    odds_start_away: Decimal | None = None
    odds_start_over: Decimal | None = None
    odds_start_under: Decimal | None = None
    odds_start_ou_line: Decimal | None = None
    odds_start_ah_home: Decimal | None = None
    odds_start_ah_away: Decimal | None = None
    odds_start_ah_line: str | None = None

    # Odds — kickoff (just before match starts)
    odds_kick_home: Decimal | None = None
    odds_kick_draw: Decimal | None = None
    odds_kick_away: Decimal | None = None
    odds_kick_over: Decimal | None = None
    odds_kick_under: Decimal | None = None
    odds_kick_ou_line: Decimal | None = None
    odds_kick_ah_home: Decimal | None = None
    odds_kick_ah_away: Decimal | None = None
    odds_kick_ah_line: str | None = None

    # Cross-reference
    af_match_id: int | None = None

    @classmethod
    def from_raw(cls, data: dict[str, _RawFieldValue]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class SFMatchEventRaw(BaseModel):
    """Raw match event record (goal, corner, card, etc.)."""

    model_config = ConfigDict(frozen=True)

    sf_match_id: str
    event_type: str
    timer: str
    team: str  # "A" (home) or "B" (away)

    @classmethod
    def from_raw(cls, data: dict[str, _RawFieldValue]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class SFMatchDominanceRaw(BaseModel):
    """Raw 30-second dominance index snapshot."""

    model_config = ConfigDict(frozen=True)

    sf_match_id: str
    timer: str
    team_a_dominance: float
    team_b_dominance: float

    @classmethod
    def from_raw(cls, data: dict[str, _RawFieldValue]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class SFMatchProgressiveStatsRaw(BaseModel):
    """Raw progressive match stats at 30-second intervals, per team."""

    model_config = ConfigDict(frozen=True)

    sf_match_id: str
    timer: str
    team: str  # "A" (home) or "B" (away)

    # Score & possession
    goals: int | None = None
    possession: int | None = None

    # Attacks
    attacks: int | None = None
    dangerous_attacks: int | None = None

    # Shots
    shots_total: int | None = None
    shots_on_target: int | None = None
    shots_off_target: int | None = None
    shots_goal_attempts: int | None = None

    # Set pieces & discipline
    penalties: int | None = None
    corners: int | None = None
    fouls: int | None = None
    yellow_cards: int | None = None
    yellow_then_red: int | None = None
    red_cards: int | None = None

    # Other
    substitutions: int | None = None
    throwins: int | None = None
    injuries: int | None = None
    offsides: int | None = None

    # Dominance
    dominance: float | None = None
    dominance_avg: float | None = None

    @classmethod
    def from_raw(cls, data: dict[str, _RawFieldValue]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)


class SFMatchProgressiveOddsRaw(BaseModel):
    """Raw progressive odds at 30-second intervals.

    All odds stored as Decimal for precision (no floating-point drift).
    """

    model_config = ConfigDict(frozen=True)

    sf_match_id: str
    timer: str

    # Full-time 1X2
    home_win: Decimal | None = None
    draw: Decimal | None = None
    away_win: Decimal | None = None

    # Full-time Asian Handicap
    ah_home: Decimal | None = None
    ah_away: Decimal | None = None
    ah_line: Decimal | None = None

    # Full-time Over/Under
    over: Decimal | None = None
    under: Decimal | None = None
    ou_line: Decimal | None = None

    # Asian Corner
    ac_over: Decimal | None = None
    ac_under: Decimal | None = None
    ac_line: Decimal | None = None

    # First-half 1X2
    h1_home_win: Decimal | None = None
    h1_draw: Decimal | None = None
    h1_away_win: Decimal | None = None

    # First-half Asian Handicap
    h1_ah_home: Decimal | None = None
    h1_ah_away: Decimal | None = None
    h1_ah_line: Decimal | None = None

    # First-half Over/Under
    h1_over: Decimal | None = None
    h1_under: Decimal | None = None
    h1_ou_line: Decimal | None = None

    # First-half Asian Corner
    h1_ac_over: Decimal | None = None
    h1_ac_under: Decimal | None = None
    h1_ac_line: Decimal | None = None

    @classmethod
    def from_raw(cls, data: dict[str, _RawFieldValue]) -> Self:
        """Construct from raw API/DB row."""
        return cls.model_validate(data)
