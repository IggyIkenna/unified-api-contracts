"""FootyStats (Football-Data-API) schemas.

Ref: https://api.football-data-api.com
Auth: key query parameter
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


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
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL
        return ErrorAction.FAIL


# =============================================================================
# Source schemas (merged from external/sports/sources/footystats/)
# =============================================================================

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


# =============================================================================
# RAW API RESPONSE SCHEMAS (FT*Raw)
#
# These mirror the FootyStats API JSON structure. All fields are optional with
# None defaults except primary identifiers. Used for ingestion before
# normalisation into canonical schemas above.
# =============================================================================


class FTTeamRaw(BaseModel):
    """Raw FootyStats team API response."""

    model_config = ConfigDict(frozen=True)

    ft_team_id: int
    name: str | None = None
    clean_name: str | None = None
    english_name: str | None = None
    short_hand: str | None = None
    full_name: str | None = None
    country: str | None = None
    continent: str | None = None
    founded: str | None = None
    image: str | None = None
    competition_id: int | None = None
    season: str | None = None
    season_clean: str | None = None
    table_position: int | None = None
    performance_rank: int | None = None
    risk: int | None = None
    url: str | None = None


class FTMatchRaw(BaseModel):
    """Raw FootyStats match API response (~80 most important fields).

    Fields are grouped by category for readability.
    """

    model_config = ConfigDict(frozen=True)

    # --- IDs & fixture info ---
    ft_match_id: int
    date_unix: int | None = None
    competition_id: int | None = None
    season: str | None = None
    status: str | None = None
    round_id: int | None = None
    game_week: int | None = None
    revised_game_week: int | None = None
    home_id: int | None = None
    away_id: int | None = None
    home_name: str | None = None
    away_name: str | None = None
    winning_team: int | None = None
    referee_id: int | None = None
    stadium_name: str | None = None
    attendance: int | None = None

    # --- Goals ---
    home_goal_count: int | None = None
    away_goal_count: int | None = None
    total_goal_count: int | None = None
    ht_goals_team_a: int | None = None
    ht_goals_team_b: int | None = None
    goals_2hg_team_a: int | None = None
    goals_2hg_team_b: int | None = None
    ht_goal_count: int | None = None
    goal_count_2hg: int | None = None

    # --- Possession ---
    team_a_possession: int | None = None
    team_b_possession: int | None = None

    # --- Shots ---
    team_a_shots: int | None = None
    team_b_shots: int | None = None
    team_a_shots_on_target: int | None = None
    team_b_shots_on_target: int | None = None
    team_a_shots_off_target: int | None = None
    team_b_shots_off_target: int | None = None

    # --- Corners ---
    team_a_corners: int | None = None
    team_b_corners: int | None = None
    total_corner_count: int | None = None
    team_a_fh_corners: int | None = None
    team_b_fh_corners: int | None = None
    team_a_2h_corners: int | None = None
    team_b_2h_corners: int | None = None

    # --- Cards ---
    team_a_yellow_cards: int | None = None
    team_b_yellow_cards: int | None = None
    team_a_red_cards: int | None = None
    team_b_red_cards: int | None = None
    team_a_cards_num: int | None = None
    team_b_cards_num: int | None = None

    # --- Fouls ---
    team_a_fouls: int | None = None
    team_b_fouls: int | None = None

    # --- xG ---
    team_a_xg: float | None = None
    team_b_xg: float | None = None
    total_xg: float | None = None
    team_a_xg_prematch: float | None = None
    team_b_xg_prematch: float | None = None
    total_xg_prematch: float | None = None

    # --- PPG (points per game) ---
    home_ppg: float | None = None
    away_ppg: float | None = None
    pre_match_home_ppg: float | None = None
    pre_match_away_ppg: float | None = None
    pre_match_team_a_overall_ppg: float | None = None
    pre_match_team_b_overall_ppg: float | None = None

    # --- BTTS & potentials ---
    btts: bool | None = None
    btts_potential: int | None = None
    btts_fhg_potential: int | None = None
    btts_2hg_potential: int | None = None
    o05_potential: int | None = None
    o15_potential: int | None = None
    o25_potential: int | None = None
    o35_potential: int | None = None
    o45_potential: int | None = None
    u05_potential: int | None = None
    u15_potential: int | None = None
    u25_potential: int | None = None
    u35_potential: int | None = None
    u45_potential: int | None = None
    corners_o85_potential: int | None = None
    corners_o95_potential: int | None = None
    corners_o105_potential: int | None = None
    avg_potential: int | None = None
    corners_potential: int | None = None
    cards_potential: int | None = None
    offsides_potential: int | None = None

    # --- Over/under flags ---
    over05: bool | None = None
    over15: bool | None = None
    over25: bool | None = None
    over35: bool | None = None
    over45: bool | None = None

    # --- Odds (most important ~20 fields) ---
    odds_ft_1: float | None = None
    odds_ft_x: float | None = None
    odds_ft_2: float | None = None
    odds_ft_over15: float | None = None
    odds_ft_over25: float | None = None
    odds_ft_over35: float | None = None
    odds_ft_under15: float | None = None
    odds_ft_under25: float | None = None
    odds_ft_under35: float | None = None
    odds_btts_yes: float | None = None
    odds_btts_no: float | None = None
    odds_doublechance_1x: float | None = None
    odds_doublechance_12: float | None = None
    odds_doublechance_x2: float | None = None
    odds_1st_half_result_1: float | None = None
    odds_1st_half_result_x: float | None = None
    odds_1st_half_result_2: float | None = None
    odds_dnb_1: float | None = None
    odds_dnb_2: float | None = None

    # --- Attacks & dangerous attacks ---
    team_a_dangerous_attacks: int | None = None
    team_b_dangerous_attacks: int | None = None
    team_a_attacks: int | None = None
    team_b_attacks: int | None = None

    # --- Offsides ---
    team_a_offsides: int | None = None
    team_b_offsides: int | None = None

    # --- Goal timings (serialised JSON strings from API) ---
    home_goals_timings: str | None = None
    away_goals_timings: str | None = None


class FTRefereeRaw(BaseModel):
    """Raw FootyStats referee API response (~20 most important fields)."""

    model_config = ConfigDict(frozen=True)

    ft_referee_id: int
    competition_id: int | None = None
    season: str | None = None
    full_name: str | None = None
    known_as: str | None = None
    nationality: str | None = None
    age: int | None = None
    league: str | None = None
    appearances_overall: int | None = None
    wins_home: int | None = None
    wins_away: int | None = None
    draws_overall: int | None = None
    btts_overall: int | None = None
    btts_percentage: int | None = None
    goals_per_match_overall: float | None = None
    cards_overall: int | None = None
    cards_per_match_overall: float | None = None
    yellow_cards_overall: int | None = None
    red_cards_overall: int | None = None
    penalties_given_overall: int | None = None
    min_per_card_overall: int | None = None


class FTLeagueStatsRaw(BaseModel):
    """Raw FootyStats league statistics API response (~30 most important fields)."""

    model_config = ConfigDict(frozen=True)

    ft_league_id: int
    season: str | None = None
    name: str | None = None
    english_name: str | None = None
    country: str | None = None
    division: int | None = None
    status: str | None = None
    total_matches: int | None = None
    matches_completed: int | None = None
    club_num: int | None = None
    # --- Goal averages ---
    total_goals: int | None = None
    season_avg_overall: float | None = None
    season_avg_home: float | None = None
    season_avg_away: float | None = None
    # --- BTTS ---
    btts_matches: int | None = None
    season_btts_percentage: int | None = None
    season_cs_percentage: int | None = None
    # --- Over/under percentages ---
    season_over15_percentage_overall: int | None = None
    season_over25_percentage_overall: int | None = None
    season_over35_percentage_overall: int | None = None
    # --- Corners ---
    corners_avg_overall: float | None = None
    corners_avg_home: float | None = None
    corners_avg_away: float | None = None
    corners_total_overall: int | None = None
    # --- Cards ---
    cards_avg_overall: float | None = None
    cards_avg_home: float | None = None
    cards_avg_away: float | None = None
    cards_total_overall: int | None = None
    # --- Shots ---
    shots_avg_overall: float | None = None
    shots_total_overall: int | None = None
    # --- Fouls ---
    fouls_avg_overall: float | None = None
    fouls_total_overall: int | None = None
    # --- Win distribution ---
    home_wins: int | None = None
    draws: int | None = None
    away_wins: int | None = None
    home_win_percentage: int | None = None
    draw_percentage: int | None = None
    away_win_percentage: int | None = None
    # --- xG ---
    xg_avg: float | None = None


class FTWeatherRaw(BaseModel):
    """Raw FootyStats weather API response for a match."""

    model_config = ConfigDict(frozen=True)

    ft_match_id: int
    wind_speed: str | None = None
    wind_degree: int | None = None
    lat: float | None = None
    lon: float | None = None
    weather_type: str | None = None
    weather_code: str | None = None
    temp_fahrenheit: float | None = None
    temp_celsius: float | None = None
    pressure: int | None = None
    clouds: str | None = None
    humidity: str | None = None


class FTOddsRaw(BaseModel):
    """Raw FootyStats odds comparison table entry."""

    model_config = ConfigDict(frozen=True)

    ft_match_id: int
    market_type: str | None = None
    market_option: str | None = None
    bookmaker: str | None = None
    odds_value: Decimal | None = None


class FTPlayerRaw(BaseModel):
    """Raw FootyStats player API response (~25 most important per-game stats)."""

    model_config = ConfigDict(frozen=True)

    ft_player_id: int
    competition_id: int | None = None
    season: str | None = None
    full_name: str | None = None
    known_as: str | None = None
    position: str | None = None
    nationality: str | None = None
    age: int | None = None
    club_team_id: int | None = None
    # --- Appearances ---
    appearances_overall: int | None = None
    appearances_home: int | None = None
    appearances_away: int | None = None
    minutes_played_overall: int | None = None
    # --- Goals ---
    goals_overall: int | None = None
    goals_home: int | None = None
    goals_away: int | None = None
    goals_per_90_overall: float | None = None
    # --- Assists ---
    assists_overall: int | None = None
    assists_per_90_overall: float | None = None
    goals_involved_per_90_overall: float | None = None
    # --- Defensive ---
    clean_sheets_overall: int | None = None
    conceded_overall: int | None = None
    conceded_per_90_overall: float | None = None
    # --- Cards ---
    cards_overall: int | None = None
    yellow_cards_overall: int | None = None
    red_cards_overall: int | None = None
    cards_per_90_overall: float | None = None
    # --- Penalties ---
    penalty_goals: int | None = None
    penalty_misses: int | None = None
    # --- Rankings ---
    rank_in_league_top_attackers: int | None = None
    rank_in_club_top_scorer: int | None = None


class FTLineupRaw(BaseModel):
    """Raw FootyStats lineup entry for a match."""

    model_config = ConfigDict(frozen=True)

    ft_match_id: int
    ft_team_id: int | None = None
    ft_player_id: int | None = None
    shirt_number: int | None = None
    is_starting: bool | None = None
    ft_player_out_id: int | None = None
    player_out_time: str | None = None


class FTLineupEventRaw(BaseModel):
    """Raw FootyStats lineup event (goal, card, etc.) for a player in a match."""

    model_config = ConfigDict(frozen=True)

    ft_match_id: int
    ft_team_id: int | None = None
    ft_player_id: int | None = None
    event_type: str | None = None
    event_time: str | None = None
