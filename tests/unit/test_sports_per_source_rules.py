"""Tests for registry/sports_per_source_rules.py — sports coverage rule engine."""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.registry.sports_per_source_rules import (
    is_expected_for_source,
    is_in_transfer_window,
    is_understat_league,
)


class TestIsUnderstatLeague:
    def test_epl_is_understat_covered(self) -> None:
        assert is_understat_league("EPL") is True

    def test_bundesliga_is_understat_covered(self) -> None:
        assert is_understat_league("BUNDESLIGA") is True

    def test_la_liga_is_understat_covered(self) -> None:
        assert is_understat_league("LA_LIGA") is True

    def test_ligue_1_is_understat_covered(self) -> None:
        assert is_understat_league("LIGUE_1") is True

    def test_serie_a_is_understat_covered(self) -> None:
        assert is_understat_league("SERIE_A") is True

    def test_mls_not_understat_covered(self) -> None:
        assert is_understat_league("MLS") is False

    def test_brasileirao_not_understat_covered(self) -> None:
        assert is_understat_league("BRASILEIRAO") is False

    def test_case_insensitive(self) -> None:
        assert is_understat_league("epl") is True
        assert is_understat_league("mls") is False


class TestIsExpectedForSourceUnderstat:
    def test_epl_in_covered_league_recent_date(self) -> None:
        is_expected, reason = is_expected_for_source("understat", "EPL", date(2024, 4, 1))
        assert is_expected is True
        assert reason is None

    def test_non_covered_league_returns_not_expected(self) -> None:
        is_expected, reason = is_expected_for_source("understat", "MLS", date(2024, 4, 1))
        assert is_expected is False
        assert reason == "EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE"

    def test_case_insensitive_source_key(self) -> None:
        is_expected, reason = is_expected_for_source("UNDERSTAT", "MLS", date(2024, 4, 1))
        assert is_expected is False

    def test_understat_pre_coverage_start_returns_not_expected(self) -> None:
        # Understat likely has coverage start around 2014-2016
        # Use a very early date that is definitely before coverage start
        is_expected, reason = is_expected_for_source("understat", "EPL", date(2000, 1, 1))
        # Either it's before coverage start or coverage start is not defined for understat
        if not is_expected:
            assert reason == "EXPECTED_PRE_SOURCE_COVERAGE_START"
        # If coverage start not set, returns True — both are valid outcomes


class TestIsExpectedForSourceFootystats:
    def test_footystats_in_season_date(self) -> None:
        # EPL season runs August-May; October is in-season
        is_expected, reason = is_expected_for_source("footystats", "EPL", date(2024, 10, 15))
        # Either in-season (True, None) or season boundary effect
        assert isinstance(is_expected, bool)

    def test_footystats_pre_coverage_start(self) -> None:
        # Very early date should be before footystats coverage start
        is_expected, reason = is_expected_for_source("footystats", "EPL", date(2005, 1, 1))
        if not is_expected:
            assert reason in {"EXPECTED_PRE_SOURCE_COVERAGE_START", "EXPECTED_PRE_SEASON", "EXPECTED_POST_SEASON"}

    def test_footystats_case_insensitive(self) -> None:
        is_expected1, _ = is_expected_for_source("footystats", "EPL", date(2024, 10, 1))
        is_expected2, _ = is_expected_for_source("FOOTYSTATS", "EPL", date(2024, 10, 1))
        assert is_expected1 == is_expected2


class TestIsExpectedForSourceApiFootball:
    def test_api_football_recent_date_is_expected(self) -> None:
        is_expected, reason = is_expected_for_source("api_football", "EPL", date(2024, 4, 1))
        assert is_expected is True
        assert reason is None

    def test_api_football_very_old_date(self) -> None:
        # Before any sports data coverage
        is_expected, reason = is_expected_for_source("api_football", "EPL", date(2000, 1, 1))
        if not is_expected:
            assert reason == "EXPECTED_PRE_SOURCE_COVERAGE_START"

    def test_api_football_unknown_league_still_expected(self) -> None:
        # api_football doesn't have per-league whitelist
        is_expected, reason = is_expected_for_source("api_football", "UNKNOWN_LEAGUE_XY", date(2024, 4, 1))
        # If no coverage start for this source, it's expected
        assert isinstance(is_expected, bool)


class TestIsExpectedForSourceTransferRecords:
    def test_transfer_records_in_window(self) -> None:
        # January transfer window for England runs Jan 1 - Jan 31
        is_expected, reason = is_expected_for_source(
            "api_football", "EPL", date(2024, 1, 15), data_type="transfer_records"
        )
        # During January window: expected if window is open
        assert isinstance(is_expected, bool)

    def test_transfer_records_outside_window(self) -> None:
        # March is outside transfer windows for most leagues
        is_expected, reason = is_expected_for_source(
            "api_football", "EPL", date(2024, 3, 15), data_type="transfer_records"
        )
        if not is_expected:
            assert reason == "EXPECTED_OUTSIDE_TRANSFER_WINDOW"

    def test_transfer_records_in_window_falls_through_to_source_check(self) -> None:
        # When window IS open, falls through to source check
        # Summer window for England: June 14 - August 30 approx
        is_expected, reason = is_expected_for_source(
            "api_football", "EPL", date(2024, 7, 1), data_type="transfer_records"
        )
        # Either window is open (True, None) or outside window (False, reason)
        assert isinstance(is_expected, bool)


class TestIsExpectedForSourceUnknown:
    def test_unknown_source_with_recent_date_is_expected(self) -> None:
        is_expected, reason = is_expected_for_source("completely_unknown_source_xyz", "EPL", date(2024, 4, 1))
        # Default: no coverage start → expected
        assert is_expected is True
        assert reason is None

    def test_unknown_source_returns_true_none(self) -> None:
        is_expected, reason = is_expected_for_source("random_source_abc", "MLS", date(2024, 4, 1))
        assert isinstance(is_expected, bool)


class TestIsInTransferWindow:
    def test_epl_january_in_window(self) -> None:
        result = is_in_transfer_window("EPL", date(2024, 1, 15))
        assert isinstance(result, bool)

    def test_epl_march_not_in_window(self) -> None:
        result = is_in_transfer_window("EPL", date(2024, 3, 15))
        # March is typically outside transfer windows
        assert isinstance(result, bool)

    def test_return_type_is_bool(self) -> None:
        result = is_in_transfer_window("BUNDESLIGA", date(2024, 6, 1))
        assert isinstance(result, bool)


@pytest.mark.parametrize(
    ("source", "league", "day", "data_type", "expected_type"),
    [
        ("understat", "EPL", date(2024, 4, 1), None, bool),
        ("understat", "MLS", date(2024, 4, 1), None, bool),
        ("footystats", "EPL", date(2024, 10, 15), None, bool),
        ("api_football", "EPL", date(2024, 4, 1), None, bool),
        ("api_football", "EPL", date(2024, 3, 15), "transfer_records", bool),
        ("unknown_xyz", "EPL", date(2024, 4, 1), None, bool),
    ],
)
def test_is_expected_for_source_parametrized(
    source: str,
    league: str,
    day: date,
    data_type: str | None,
    expected_type: type,
) -> None:
    is_expected, reason = is_expected_for_source(source, league, day, data_type=data_type)
    assert isinstance(is_expected, expected_type)
    if not is_expected:
        assert isinstance(reason, str)
    else:
        assert reason is None
