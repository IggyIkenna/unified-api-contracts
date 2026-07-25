"""Venue, referee, player-lineup, odds and basic xG feature groups for SportsFeatureVector."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VenueContextFeaturesMixin(BaseModel):
    """Venue context feature fields (VenueContextFeatureCalculator)."""

    model_config = ConfigDict(frozen=False)

    venue_capacity: int | None = None
    venue_altitude_m: float | None = None
    venue_surface: str | None = None
    attendance_rate: float | None = None
    venue_home_win_rate: float | None = None
    venue_avg_goals: float | None = None

    # -- Venue Context Extended (VenueContextFeatureCalculator) --
    attendance_pct_capacity: float | None = None
    expected_attendance: float | None = None
    is_derby: bool | None = None
    is_european_spot_contest: bool | None = None
    is_relegation_battle: bool | None = None
    is_sellout_expected: bool | None = None
    is_title_decider: bool | None = None
    kickoff_day_of_week: int | None = None
    kickoff_hour: int | None = None
    kickoff_is_afternoon: bool | None = None
    kickoff_is_early: bool | None = None
    kickoff_is_evening: bool | None = None
    kickoff_is_midweek: bool | None = None
    kickoff_is_weekend: bool | None = None
    match_importance_away: float | None = None
    match_importance_home: float | None = None
    stakes_differential: float | None = None
    venue_age: int | None = None
    venue_altitude_meters: float | None = None
    venue_avg_attendance_season: float | None = None
    venue_has_roof: bool | None = None
    venue_is_artificial_turf: bool | None = None
    venue_is_high_altitude: bool | None = None
    venue_pitch_length: float | None = None
    venue_pitch_size: float | None = None
    venue_pitch_width: float | None = None
    venue_surface_type: str | None = None


class RefereeFeaturesMixin(BaseModel):
    """Referee feature fields (RefereeFeatureCalculator)."""

    model_config = ConfigDict(frozen=False)

    ref_cards_per_game: float | None = None
    ref_penalty_rate: float | None = None
    ref_home_bias_score: float | None = None
    ref_fouls_per_game: float | None = None
    ref_avg_added_time: float | None = None
    ref_matches_count: int | None = None

    # -- Referee Extended (RefereeFeatureCalculator) --
    referee_fouls_per_game: float | None = None
    referee_games_with_away_team: int | None = None
    referee_games_with_home_team: int | None = None
    referee_has_red_card_rate: float | None = None
    referee_home_foul_bias: float | None = None
    referee_home_penalty_bias: float | None = None
    referee_home_team_win_rate: float | None = None
    referee_home_yellow_card_bias: float | None = None
    referee_is_lenient: bool | None = None
    referee_is_strict: bool | None = None
    referee_penalties_per_game: float | None = None
    referee_penalty_rate_season: float | None = None
    referee_red_cards_per_game: float | None = None
    referee_red_cards_season: int | None = None
    referee_total_cards_per_game: float | None = None
    referee_yellow_card_rate: float | None = None
    referee_yellow_cards_per_game: float | None = None
    referee_yellow_cards_season: int | None = None

    # -- Referee Interaction (RefereeInteractionFeatureCalculator) --
    away_card_diff_under_ref: float | None = None
    away_cards_under_ref: float | None = None
    away_discipline_risk: float | None = None
    away_pen_attack_style: float | None = None
    away_penalty_propensity: float | None = None
    away_reds_under_ref: float | None = None
    away_ref_foul_rate: float | None = None
    away_ref_home_bias: float | None = None
    away_ref_penalty_rate: float | None = None
    away_ref_style_match: float | None = None
    away_yellows_under_ref: float | None = None
    home_card_diff_under_ref: float | None = None
    home_cards_under_ref: float | None = None
    home_discipline_risk: float | None = None
    home_pen_attack_style: float | None = None
    home_penalty_propensity: float | None = None
    home_reds_under_ref: float | None = None
    home_ref_foul_rate: float | None = None
    home_ref_home_bias: float | None = None
    home_ref_penalty_rate: float | None = None
    home_ref_style_match: float | None = None
    home_yellows_under_ref: float | None = None


class PlayerLineupFeaturesMixin(BaseModel):
    """Player lineup feature fields (PlayerLineupFeatureCalculator)."""

    model_config = ConfigDict(frozen=False)

    home_key_player_absent: bool | None = None
    away_key_player_absent: bool | None = None
    home_lineup_strength: float | None = None
    away_lineup_strength: float | None = None
    home_missing_key_players: int | None = None
    away_missing_key_players: int | None = None

    # -- Player Lineup Extended (PlayerLineupFeatureCalculator) --
    away_bench_avg_rating: float | None = None
    away_formation_consistency: float | None = None
    away_gk_clean_sheet_rate: float | None = None
    away_gk_save_percentage: float | None = None
    away_gk_saves_per_game: float | None = None
    away_goal_concentration: float | None = None
    away_injured_players_count: int | None = None
    away_key_players_available: int | None = None
    away_key_players_missing: int | None = None
    away_lineup_changes_from_last: int | None = None
    away_players_on_yellow_card_warning: int | None = None
    away_squad_depth_score: float | None = None
    away_suspended_players_count: int | None = None
    away_top_assist_provider_assists: int | None = None
    away_top_scorer_available: bool | None = None
    away_top_scorer_form_last5: int | None = None
    away_top_scorer_goals: int | None = None
    away_top_scorer_goals_per_game: float | None = None
    away_xi_avg_age: float | None = None
    away_xi_avg_appearances: float | None = None
    away_xi_avg_goals_per_game: float | None = None
    away_xi_avg_rating: float | None = None
    away_xi_interceptions_per_game: float | None = None
    away_xi_key_passes_per_game: float | None = None
    away_xi_tackles_per_game: float | None = None
    away_xi_total_assists: int | None = None
    away_xi_yellow_cards_season: int | None = None
    home_bench_avg_rating: float | None = None
    home_formation_consistency: float | None = None
    home_gk_clean_sheet_rate: float | None = None
    home_gk_save_percentage: float | None = None
    home_gk_saves_per_game: float | None = None
    home_goal_concentration: float | None = None
    home_injured_players_count: int | None = None
    home_key_players_available: int | None = None
    home_key_players_missing: int | None = None
    home_lineup_changes_from_last: int | None = None
    home_players_on_yellow_card_warning: int | None = None
    home_squad_depth_score: float | None = None
    home_suspended_players_count: int | None = None
    home_top_assist_provider_assists: int | None = None
    home_top_scorer_available: bool | None = None
    home_top_scorer_form_last5: int | None = None
    home_top_scorer_goals: int | None = None
    home_top_scorer_goals_per_game: float | None = None
    home_xi_avg_age: float | None = None
    home_xi_avg_appearances: float | None = None
    home_xi_avg_goals_per_game: float | None = None
    home_xi_avg_rating: float | None = None
    home_xi_interceptions_per_game: float | None = None
    home_xi_key_passes_per_game: float | None = None
    home_xi_tackles_per_game: float | None = None
    home_xi_total_assists: int | None = None
    home_xi_yellow_cards_season: int | None = None


class OddsFeaturesMixin(BaseModel):
    """Odds feature fields (OddsFeatureCalculator).

    Field names follow the operator-decided scheme (2026-07-23, DECIDED todo 1
    in sports_odds_feature_naming_canonicalization_2026_07_21.md):
    ``<category>_<metric>[_<outcome>][_<venue>]``, outcome in {home, draw, away}.
    Renamed 2026-07-25 from the pre-scheme names, cross-checked against
    ``features-service``'s ``odds_calculator.py``/``odds_velocity.py`` (which producer
    columns are actually live) and downstream consumers (``strategy-service`` already
    expects ``prob_implied_*``/``prob_fair_*``/``odds_decimal_*``).

    ``market_home_odds_best``/``market_away_odds_best`` win the ``odds_decimal_``
    (consensus/best) slot -- that is this scheme's own worked example
    (``best_odds_home`` -> ``odds_decimal_home``) and what
    ``SportsValueBettingEngine`` needs. ``odds_home_win``/``odds_draw``/``odds_away_win``
    (a DIFFERENT, currently-live FSS column under the exact same old name) get the
    distinct ``odds_moneyline_`` metric instead of colliding with it.
    ``market_home_away_odds_ratio``/``odds_home_away_ratio`` are disambiguated the
    same way (``consensus`` qualifier on the schema-only one).

    Left UNCHANGED despite being scheme-adjacent, not scheme-exact:
    ``odds_sharp_money_on_home``/``_away`` -- exact-string match to a currently-live
    FSS producer column; renaming would zero out ``SportsFeatureLoaderMixin``'s
    producer/consumer overlap check for this field ahead of the FSS-side migration
    (features_service/sports/calculators/odds_columns.py`` migration todo, P2 in the
    same plan) with no compensating benefit today. The over/under fixed-line fields
    (``odds_over_2_5`` etc.) are likewise left unchanged -- already ``odds_<market>_``
    compliant per this scheme's own alternate-market rule, and schema-only today (no
    live FSS producer under ANY name for the fixed-line variants).
    """

    model_config = ConfigDict(frozen=False)

    # Implied probabilities
    prob_implied_home: float | None = None
    prob_implied_draw: float | None = None
    prob_implied_away: float | None = None
    # Market efficiency
    odds_market_overround: float | None = None
    prob_fair_home: float | None = None
    prob_fair_draw: float | None = None
    prob_fair_away: float | None = None
    odds_market_vig_pct: float | None = None
    odds_book_count_total: int | None = None
    # Raw 1X2 odds
    odds_moneyline_home: float | None = None
    odds_moneyline_draw: float | None = None
    odds_moneyline_away: float | None = None
    odds_market_home_away_ratio: float | None = None
    odds_market_consensus_home_away_ratio: float | None = None
    # Over/Under lines (schema-only today; FSS's real OU support is a single dynamic
    # line, not fixed 1.5/2.5/3.5 columns -- already odds_<market>_ compliant, unchanged)
    odds_over_2_5: float | None = None
    odds_under_2_5: float | None = None
    prob_implied_over_2_5: float | None = None
    prob_implied_under_2_5: float | None = None
    odds_over_1_5: float | None = None
    odds_under_1_5: float | None = None
    odds_over_3_5: float | None = None
    odds_under_3_5: float | None = None
    # Market consensus (cross-bookmaker)
    odds_decimal_home: float | None = None
    odds_decimal_away: float | None = None
    odds_variance_home: float | None = None
    odds_variance_away: float | None = None
    # Odds movement (opening / closing)
    odds_opening_home: float | None = None
    odds_closing_home: float | None = None
    odds_movement_home: float | None = None
    odds_movement_pct_home: float | None = None
    odds_opening_away: float | None = None
    odds_closing_away: float | None = None
    odds_movement_away: float | None = None
    odds_movement_pct_away: float | None = None
    # Sharp money indicators -- unchanged, see class docstring
    odds_sharp_money_on_home: int | None = None
    odds_sharp_money_on_away: int | None = None

    # -- Odds Extended (OddsFeatureCalculator) --
    odds_asian_handicap_line: float | None = None
    odds_ev_away: float | None = None
    odds_ev_home: float | None = None
    prob_implied_btts_no: float | None = None
    prob_implied_btts_yes: float | None = None
    odds_asian_handicap_away: float | None = None
    odds_asian_handicap_home: float | None = None
    odds_btts_no: float | None = None
    odds_btts_yes: float | None = None
    odds_value_away: float | None = None
    odds_value_btts: float | None = None
    odds_value_home: float | None = None
    odds_value_over_2_5: float | None = None
