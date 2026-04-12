"""Tests for league fixture calendar and prediction league ID helpers."""

from __future__ import annotations

from unified_api_contracts.canonical.domain.sports.league_data import (
    get_all_prediction_league_ids,
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
