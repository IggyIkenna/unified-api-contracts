"""Canonical sports feature vector — ML feature schema for a single fixture."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SportsFeatureVector(BaseModel):
    """Complete ML feature vector for a single fixture."""

    model_config = ConfigDict(frozen=False)

    fixture_id: str
    computed_at_utc: datetime

    # ── Team features (TeamFeatureCalculator) ──
    # Form (points per game over rolling windows)
    home_form_5: float | None = None
    away_form_5: float | None = None
    home_ppg_last3: float | None = None
    away_ppg_last3: float | None = None
    home_ppg_season: float | None = None
    away_ppg_season: float | None = None
    # Win / draw / loss rates
    home_win_rate_season: float | None = None
    away_win_rate_season: float | None = None
    home_win_rate_last5: float | None = None
    away_win_rate_last5: float | None = None
    # Goals
    home_goals_scored_avg: float | None = None
    away_goals_scored_avg: float | None = None
    home_goals_conceded_avg: float | None = None
    away_goals_conceded_avg: float | None = None
    home_goal_diff_season: float | None = None
    away_goal_diff_season: float | None = None
    # xG (team-level rolling averages)
    home_xg_season: float | None = None
    away_xg_season: float | None = None
    home_xg_conceded_season: float | None = None
    away_xg_conceded_season: float | None = None
    # Home advantage
    home_home_advantage_factor: float | None = None
    # Rest & congestion
    home_rest_days: int | None = None
    away_rest_days: int | None = None
    home_congestion_score: float | None = None
    away_congestion_score: float | None = None
    # Streaks
    home_current_streak: int | None = None
    away_current_streak: int | None = None
    home_unbeaten_run: int | None = None
    away_unbeaten_run: int | None = None
    # Clean sheets & BTTS
    home_clean_sheet_rate: float | None = None
    away_clean_sheet_rate: float | None = None
    home_btts_rate: float | None = None
    away_btts_rate: float | None = None
    # Over/Under
    home_over_25_rate: float | None = None
    away_over_25_rate: float | None = None
    # Consistency
    home_goal_variance: float | None = None
    away_goal_variance: float | None = None

    # ── H2H features (H2HFeatureCalculator) ──
    h2h_home_wins: int | None = None
    h2h_draws: int | None = None
    h2h_away_wins: int | None = None
    h2h_avg_goals: float | None = None
    h2h_matches_played: int | None = None
    h2h_home_goals_avg: float | None = None
    h2h_away_goals_avg: float | None = None
    h2h_btts_rate: float | None = None
    h2h_over_25_rate: float | None = None

    # ── League features (LeagueFeatureCalculator) ──
    league_avg_goals_per_game: float | None = None
    league_home_win_rate: float | None = None
    league_btts_rate: float | None = None
    league_over_25_rate: float | None = None
    league_draw_rate: float | None = None
    league_avg_cards_per_game: float | None = None
    league_avg_corners_per_game: float | None = None

    # ── Halftime features (HalfTimeFeatureCalculator) ──
    home_ht_goal_rate: float | None = None
    away_ht_goal_rate: float | None = None
    home_ht_concede_rate: float | None = None
    away_ht_concede_rate: float | None = None
    home_ht_lead_rate: float | None = None
    away_ht_lead_rate: float | None = None

    # ── Goal timing features (GoalTimingFeatureCalculator) ──
    home_early_goal_rate: float | None = None
    home_late_goal_rate: float | None = None
    away_early_goal_rate: float | None = None
    away_late_concede_rate: float | None = None
    home_first_goal_rate: float | None = None
    away_first_goal_rate: float | None = None

    # ── Season context (SeasonContextFeatureCalculator) ──
    match_week: int | None = None
    season_stage: str | None = None
    home_relegation_pressure: float | None = None
    away_relegation_pressure: float | None = None
    home_title_pressure: float | None = None
    season_progress_pct: float | None = None

    # ── Venue context (VenueContextFeatureCalculator) ──
    venue_capacity: int | None = None
    venue_altitude_m: float | None = None
    venue_surface: str | None = None
    attendance_rate: float | None = None
    venue_home_win_rate: float | None = None
    venue_avg_goals: float | None = None

    # ── Referee features (RefereeFeatureCalculator) ──
    ref_cards_per_game: float | None = None
    ref_penalty_rate: float | None = None
    ref_home_bias_score: float | None = None
    ref_fouls_per_game: float | None = None
    ref_avg_added_time: float | None = None
    ref_matches_count: int | None = None

    # ── Player lineup features (PlayerLineupFeatureCalculator) ──
    home_key_player_absent: bool | None = None
    away_key_player_absent: bool | None = None
    home_lineup_strength: float | None = None
    away_lineup_strength: float | None = None
    home_missing_key_players: int | None = None
    away_missing_key_players: int | None = None

    # ── Odds features (OddsFeatureCalculator) ──
    market_home_implied_prob: float | None = None
    market_draw_implied_prob: float | None = None
    market_away_implied_prob: float | None = None
    market_overround: float | None = None
    market_consensus_home_prob: float | None = None
    market_vig_pct: float | None = None
    market_num_bookmakers: int | None = None

    # ── xG features (MultiSourceXGFeatureCalculator + PoissonXGFeatureCalculator) ──
    understat_home_xg: float | None = None
    understat_away_xg: float | None = None
    footystats_home_xg: float | None = None
    footystats_away_xg: float | None = None
    consensus_home_xg: float | None = None
    consensus_away_xg: float | None = None
    poisson_home_win_prob: float | None = None
    poisson_draw_prob: float | None = None
    poisson_away_win_prob: float | None = None
    poisson_over_25_prob: float | None = None
    poisson_btts_prob: float | None = None

    # ── Advanced stats (AdvancedStatsFeatureCalculator) ──
    home_shots_on_target_avg: float | None = None
    away_shots_on_target_avg: float | None = None
    home_total_shots_avg: float | None = None
    away_total_shots_avg: float | None = None
    home_shot_accuracy: float | None = None
    away_shot_accuracy: float | None = None
    home_corners_avg: float | None = None
    away_corners_avg: float | None = None
    home_possession_avg: float | None = None
    away_possession_avg: float | None = None
    home_fouls_avg: float | None = None
    away_fouls_avg: float | None = None
    home_yellow_cards_avg: float | None = None
    away_yellow_cards_avg: float | None = None

    # ── Weather features (WeatherFeatureCalculator) ──
    weather_temp_c: float | None = None
    weather_wind_speed_ms: float | None = None
    weather_precipitation_mm: float | None = None
    weather_condition: str | None = None
