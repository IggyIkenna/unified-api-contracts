"""Unit tests for OddsFeaturesMixin/SportsFeatureVector field naming.

Regression guard for the 2026-07-23 DECIDED naming scheme
(sports_odds_feature_naming_canonicalization_2026_07_21.md): every RENAMED odds
feature field is `<category>_<metric>[_<outcome>][_<venue>]`, category in
{prob_implied, prob_fair, odds_market, odds_decimal, odds_moneyline,
odds_variance, odds_movement, odds_opening, odds_closing, odds_ev, odds_value,
odds_asian_handicap, odds_btts, odds_book_count}, outcome in {home, draw, away}
lowercase where applicable. A small set of fields (`odds_sharp_money_on_*`, the
fixed-line over/under fields) were deliberately left UNCHANGED -- see
OddsFeaturesMixin's class docstring for why.
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.features_sports import (
    OddsFeaturesMixin,
    SportsFeatureVector,
)

_EXPECTED_FIELDS = frozenset(
    {
        "prob_implied_home",
        "prob_implied_draw",
        "prob_implied_away",
        "odds_market_overround",
        "prob_fair_home",
        "prob_fair_draw",
        "prob_fair_away",
        "odds_market_vig_pct",
        "odds_book_count_total",
        "odds_moneyline_home",
        "odds_moneyline_draw",
        "odds_moneyline_away",
        "odds_market_home_away_ratio",
        "odds_market_consensus_home_away_ratio",
        "odds_over_2_5",
        "odds_under_2_5",
        "prob_implied_over_2_5",
        "prob_implied_under_2_5",
        "odds_over_1_5",
        "odds_under_1_5",
        "odds_over_3_5",
        "odds_under_3_5",
        "odds_decimal_home",
        "odds_decimal_away",
        "odds_variance_home",
        "odds_variance_away",
        "odds_opening_home",
        "odds_closing_home",
        "odds_movement_home",
        "odds_movement_pct_home",
        "odds_opening_away",
        "odds_closing_away",
        "odds_movement_away",
        "odds_movement_pct_away",
        "odds_sharp_money_on_home",
        "odds_sharp_money_on_away",
        "odds_asian_handicap_line",
        "odds_ev_away",
        "odds_ev_home",
        "prob_implied_btts_no",
        "prob_implied_btts_yes",
        "odds_asian_handicap_away",
        "odds_asian_handicap_home",
        "odds_btts_no",
        "odds_btts_yes",
        "odds_value_away",
        "odds_value_btts",
        "odds_value_home",
        "odds_value_over_2_5",
    }
)

# Pre-2026-07-25 field names that were RENAMED -- must never reappear as a live
# field on the mixin. Deliberately-unchanged fields (odds_sharp_money_on_*, the
# fixed-line over/under fields, odds_asian_handicap_*, odds_btts_*) are correctly
# absent from this set -- they are the SAME string before and after.
_RETIRED_FIELDS = frozenset(
    {
        "market_home_implied_prob",
        "market_draw_implied_prob",
        "market_away_implied_prob",
        "market_overround",
        "market_consensus_home_prob",
        "market_consensus_draw_prob",
        "market_consensus_away_prob",
        "market_vig_pct",
        "market_num_bookmakers",
        "odds_home_win",
        "odds_draw",
        "odds_away_win",
        "odds_home_away_ratio",
        "market_home_away_odds_ratio",
        "market_over_25_implied_prob",
        "market_under_25_implied_prob",
        "market_home_odds_best",
        "market_away_odds_best",
        "market_home_odds_variance",
        "market_away_odds_variance",
        "odds_home_opening",
        "odds_home_closing",
        "odds_home_movement",
        "odds_home_movement_pct",
        "odds_away_opening",
        "odds_away_closing",
        "odds_away_movement",
        "odds_away_movement_pct",
        "asian_handicap_line",
        "ev_away_win",
        "ev_home_win",
        "implied_prob_btts_no",
        "implied_prob_btts_yes",
        "value_away_win",
        "value_btts",
        "value_home_win",
        "value_over_2_5",
    }
)

# Deliberately unchanged (exact match to a currently-live FSS producer column
# today) -- must remain present under the SAME name, not touched by the rename.
_DELIBERATELY_UNCHANGED = frozenset(
    {
        "odds_sharp_money_on_home",
        "odds_sharp_money_on_away",
        "odds_over_2_5",
        "odds_under_2_5",
        "odds_over_1_5",
        "odds_under_1_5",
        "odds_over_3_5",
        "odds_under_3_5",
        "odds_asian_handicap_away",
        "odds_asian_handicap_home",
        "odds_btts_no",
        "odds_btts_yes",
    }
)


class TestOddsFeaturesMixinNaming:
    """OddsFeaturesMixin's field set must match the decided scheme exactly."""

    def test_field_set_matches_decided_scheme(self) -> None:
        actual = frozenset(OddsFeaturesMixin.model_fields.keys())
        assert actual == _EXPECTED_FIELDS, f"missing={_EXPECTED_FIELDS - actual} unexpected={actual - _EXPECTED_FIELDS}"

    def test_retired_names_are_gone(self) -> None:
        actual = frozenset(OddsFeaturesMixin.model_fields.keys())
        collision = actual & _RETIRED_FIELDS
        assert not collision, f"retired pre-scheme names still present: {collision}"

    def test_deliberately_unchanged_fields_are_still_present(self) -> None:
        actual = frozenset(OddsFeaturesMixin.model_fields.keys())
        assert actual >= _DELIBERATELY_UNCHANGED

    def test_every_field_carries_a_scheme_category_prefix(self) -> None:
        for name in OddsFeaturesMixin.model_fields:
            assert name.startswith(("odds_", "prob_")), f"{name} has no odds_/prob_ category prefix"


class TestSportsFeatureVectorInheritsOddsFields:
    """SportsFeatureVector composes OddsFeaturesMixin -- the renamed fields must
    reach the top-level ML feature schema, not just the mixin in isolation."""

    def test_vector_carries_renamed_odds_fields(self) -> None:
        vector_fields = frozenset(SportsFeatureVector.model_fields.keys())
        assert vector_fields >= _EXPECTED_FIELDS

    def test_vector_has_no_retired_odds_field(self) -> None:
        vector_fields = frozenset(SportsFeatureVector.model_fields.keys())
        assert not (vector_fields & _RETIRED_FIELDS)
