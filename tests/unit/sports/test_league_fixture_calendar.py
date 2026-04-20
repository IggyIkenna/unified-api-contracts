"""Tests for league fixture calendar and prediction league ID helpers."""

from __future__ import annotations

from unified_api_contracts.canonical.domain.sports.league_data import (
    get_all_prediction_league_ids,
    get_expected_leagues_for_source,
    get_league_fixture_calendar,
    get_prediction_leagues,
)


class TestGetAllPredictionLeagueIds:
    """Tests for get_all_prediction_league_ids()."""

    def test_returns_list_of_strings(self) -> None:
        ids = get_all_prediction_league_ids()
        assert isinstance(ids, list)
        assert all(isinstance(lid, str) for lid in ids)

    def test_matches_prediction_leagues(self) -> None:
        ids = get_all_prediction_league_ids()
        leagues = get_prediction_leagues()
        assert len(ids) == len(leagues)
        assert set(ids) == {league.league_id for league in leagues}

    def test_non_empty(self) -> None:
        ids = get_all_prediction_league_ids()
        assert len(ids) > 10, f"Expected >10 prediction leagues, got {len(ids)}"


class TestGetLeagueFixtureCalendar:
    """Tests for get_league_fixture_calendar()."""

    def test_epl_in_season_returns_dates(self) -> None:
        """EPL season is Aug-May. October should be in-season."""
        dates = get_league_fixture_calendar("EPL", "2025-10-01", "2025-10-31")
        assert len(dates) == 31
        assert dates[0] == "2025-10-01"
        assert dates[-1] == "2025-10-31"

    def test_epl_off_season_returns_empty(self) -> None:
        """EPL is off-season in June-July."""
        dates = get_league_fixture_calendar("EPL", "2025-06-15", "2025-07-15")
        assert dates == []

    def test_epl_partial_overlap(self) -> None:
        """Range spanning season boundary — May is in, June/July out, Aug in."""
        dates = get_league_fixture_calendar("EPL", "2025-05-25", "2025-08-05")
        may_dates = [d for d in dates if d.startswith("2025-05")]
        jun_dates = [d for d in dates if d.startswith("2025-06")]
        jul_dates = [d for d in dates if d.startswith("2025-07")]
        aug_dates = [d for d in dates if d.startswith("2025-08")]
        assert len(may_dates) == 7  # May 25-31
        assert len(jun_dates) == 0
        assert len(jul_dates) == 0
        assert len(aug_dates) == 5  # Aug 1-5

    def test_calendar_year_league(self) -> None:
        """MLS (US) season is Feb-Nov. Jan should be off-season."""
        dates = get_league_fixture_calendar("MLS", "2025-01-01", "2025-01-31")
        assert dates == []

        dates = get_league_fixture_calendar("MLS", "2025-06-01", "2025-06-30")
        assert len(dates) == 30

    def test_unknown_league_returns_empty(self) -> None:
        dates = get_league_fixture_calendar("NONEXISTENT_LEAGUE", "2025-01-01", "2025-12-31")
        assert dates == []

    def test_single_day_in_season(self) -> None:
        dates = get_league_fixture_calendar("EPL", "2025-09-15", "2025-09-15")
        assert dates == ["2025-09-15"]

    def test_single_day_off_season(self) -> None:
        dates = get_league_fixture_calendar("EPL", "2025-07-01", "2025-07-01")
        assert dates == []

    def test_dates_are_sorted(self) -> None:
        dates = get_league_fixture_calendar("EPL", "2025-09-01", "2025-09-30")
        assert dates == sorted(dates)

    def test_bundesliga_in_season(self) -> None:
        """BUNDESLIGA (DE) season is Aug-May, same as EPL."""
        dates = get_league_fixture_calendar("BUNDESLIGA", "2025-12-01", "2025-12-31")
        assert len(dates) == 31

    def test_brasileirao_season(self) -> None:
        """BRASILEIRAO (BR) season is Apr-Dec."""
        jan_dates = get_league_fixture_calendar("BRASILEIRAO", "2025-01-01", "2025-01-31")
        assert jan_dates == []

        may_dates = get_league_fixture_calendar("BRASILEIRAO", "2025-05-01", "2025-05-31")
        assert len(may_dates) == 31


class TestGetExpectedLeaguesForSource:
    """Tests for get_expected_leagues_for_source() — SSOT: sports-data-source-coverage-matrix.md."""

    def test_api_football_covers_widest_set(self) -> None:
        """API-Football is the T0 source — covers every non-NON_FOOTBALL league."""
        leagues = get_expected_leagues_for_source("api_football")
        assert len(leagues) >= 90, "API-Football should cover Prediction + Features + Reference leagues"
        classifications = {lg.classification for lg in leagues}
        assert {"Prediction", "Features", "Reference"}.issubset(classifications)

    def test_understat_narrow_set(self) -> None:
        """Understat only provides xG for 5 top-5 European leagues."""
        leagues = get_expected_leagues_for_source("understat")
        assert len(leagues) == 5
        ids = {lg.league_id for lg in leagues}
        assert ids == {"EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"}

    def test_footystats_prediction_and_features_only(self) -> None:
        """FootyStats covers Prediction + Features, never Reference."""
        leagues = get_expected_leagues_for_source("footystats")
        classifications = {lg.classification for lg in leagues}
        assert "Reference" not in classifications
        assert "Prediction" in classifications

    def test_classification_filter_prediction_only(self) -> None:
        leagues = get_expected_leagues_for_source("api_football", classifications=["Prediction"])
        assert all(lg.classification == "Prediction" for lg in leagues)
        # Must match get_prediction_leagues()
        pred_ids = {lg.league_id for lg in get_prediction_leagues()}
        got_ids = {lg.league_id for lg in leagues}
        # Prediction leagues all carry api_football in data_sources
        assert pred_ids == got_ids

    def test_classification_filter_reference_only(self) -> None:
        leagues = get_expected_leagues_for_source("api_football", classifications=["Reference"])
        assert all(lg.classification == "Reference" for lg in leagues)
        assert len(leagues) > 0

    def test_classification_filter_multiple(self) -> None:
        leagues = get_expected_leagues_for_source("api_football", classifications=["Prediction", "Features"])
        classifications = {lg.classification for lg in leagues}
        assert classifications == {"Prediction", "Features"}

    def test_unknown_source_returns_empty(self) -> None:
        assert get_expected_leagues_for_source("nonexistent_source") == []

    def test_case_insensitive_classification_filter(self) -> None:
        """Classification filter is case-insensitive (e.g. 'prediction' == 'Prediction')."""
        lower = get_expected_leagues_for_source("api_football", classifications=["prediction"])
        upper = get_expected_leagues_for_source("api_football", classifications=["Prediction"])
        assert {lg.league_id for lg in lower} == {lg.league_id for lg in upper}

    def test_all_returned_leagues_carry_source_key(self) -> None:
        for src in ("api_football", "footystats", "transfermarkt", "open_meteo"):
            leagues = get_expected_leagues_for_source(src)
            assert all(src in lg.data_sources for lg in leagues), (
                f"get_expected_leagues_for_source({src!r}) returned a league missing {src!r}"
            )

    def test_odds_api_is_prediction_only(self) -> None:
        """Odds-API, open_meteo, and SFI currently scope to PREDICTION leagues only."""
        for src in ("odds_api", "open_meteo", "soccer_football_info"):
            leagues = get_expected_leagues_for_source(src)
            assert all(lg.classification == "Prediction" for lg in leagues), (
                f"{src} has a non-Prediction league in coverage set"
            )
