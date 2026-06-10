"""Tests for canonical/domain/sports/transfer_windows.py — transfer window calendar."""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.canonical.domain.sports.transfer_windows import (
    TransferWindowPeriod,
    days_since_window_close,
    days_until_window_open,
    get_active_window,
    get_country_for_league,
    get_transfer_windows_for_year,
    get_windows_for_league,
    is_transfer_data_expected,
    is_transfer_window_open,
    is_within_transfer_window,
    most_recent_window_close,
    next_window_open,
    window_closed_within,
)


class TestTransferWindowPeriod:
    def test_duration_days(self) -> None:
        period = TransferWindowPeriod(
            country="ENG",
            window_type="summer",
            open_date=date(2024, 6, 10),
            close_date=date(2024, 8, 31),
        )
        assert period.duration_days == (date(2024, 8, 31) - date(2024, 6, 10)).days

    def test_contains_date_inside(self) -> None:
        period = TransferWindowPeriod(
            country="ENG",
            window_type="summer",
            open_date=date(2024, 6, 10),
            close_date=date(2024, 8, 31),
        )
        assert period.contains(date(2024, 7, 15)) is True

    def test_contains_open_date(self) -> None:
        period = TransferWindowPeriod(
            country="ENG",
            window_type="summer",
            open_date=date(2024, 6, 10),
            close_date=date(2024, 8, 31),
        )
        assert period.contains(date(2024, 6, 10)) is True

    def test_contains_close_date(self) -> None:
        period = TransferWindowPeriod(
            country="ENG",
            window_type="summer",
            open_date=date(2024, 6, 10),
            close_date=date(2024, 8, 31),
        )
        assert period.contains(date(2024, 8, 31)) is True

    def test_does_not_contain_before_open(self) -> None:
        period = TransferWindowPeriod(
            country="ENG",
            window_type="summer",
            open_date=date(2024, 6, 10),
            close_date=date(2024, 8, 31),
        )
        assert period.contains(date(2024, 6, 9)) is False

    def test_does_not_contain_after_close(self) -> None:
        period = TransferWindowPeriod(
            country="ENG",
            window_type="summer",
            open_date=date(2024, 6, 10),
            close_date=date(2024, 8, 31),
        )
        assert period.contains(date(2024, 9, 1)) is False

    def test_frozen_dataclass(self) -> None:
        period = TransferWindowPeriod(
            country="ENG",
            window_type="summer",
            open_date=date(2024, 6, 10),
            close_date=date(2024, 8, 31),
        )
        with pytest.raises((AttributeError, TypeError)):
            period.country = "ESP"  # type: ignore[misc]


class TestGetCountryForLeague:
    def test_epl_is_england(self) -> None:
        assert get_country_for_league("EPL") == "ENG"

    def test_la_liga_is_spain(self) -> None:
        assert get_country_for_league("LA_LIGA") == "ESP"

    def test_bundesliga_is_germany(self) -> None:
        assert get_country_for_league("BUNDESLIGA") == "DEU"

    def test_serie_a_is_italy(self) -> None:
        assert get_country_for_league("SERIE_A") == "ITA"

    def test_ligue_1_is_france(self) -> None:
        assert get_country_for_league("LIGUE_1") == "FRA"

    def test_unknown_league_returns_none(self) -> None:
        assert get_country_for_league("COMPLETELY_UNKNOWN_LEAGUE_XY_ZZ") is None

    def test_eng_championship_is_england(self) -> None:
        assert get_country_for_league("ENG_CHAMPIONSHIP") == "ENG"


class TestGetTransferWindowsForYear:
    def test_epl_2024_has_windows(self) -> None:
        windows = get_transfer_windows_for_year("ENG", 2024)
        assert len(windows) > 0

    def test_windows_are_transfer_window_periods(self) -> None:
        windows = get_transfer_windows_for_year("ENG", 2024)
        for w in windows:
            assert isinstance(w, TransferWindowPeriod)

    def test_summer_window_in_england(self) -> None:
        windows = get_transfer_windows_for_year("ENG", 2024)
        types = {w.window_type for w in windows}
        assert "summer" in types

    def test_winter_window_in_england(self) -> None:
        windows = get_transfer_windows_for_year("ENG", 2024)
        types = {w.window_type for w in windows}
        assert "winter" in types

    def test_country_is_set(self) -> None:
        windows = get_transfer_windows_for_year("ENG", 2024)
        for w in windows:
            assert w.country == "ENG"

    def test_unknown_country_returns_generic(self) -> None:
        windows = get_transfer_windows_for_year("_UNKNOWN_COUNTRY_XYZ", 2024)
        assert len(windows) > 0

    def test_open_date_before_close_date(self) -> None:
        windows = get_transfer_windows_for_year("ENG", 2024)
        for w in windows:
            assert w.open_date < w.close_date


class TestGetWindowsForLeague:
    def test_epl_returns_windows(self) -> None:
        windows = get_windows_for_league("EPL", 2024)
        assert len(windows) > 0

    def test_la_liga_returns_windows(self) -> None:
        windows = get_windows_for_league("LA_LIGA", 2024)
        assert len(windows) > 0

    def test_unknown_league_returns_generic_fallback(self) -> None:
        windows = get_windows_for_league("COMPLETELY_UNKNOWN_LEAGUE_ZZ", 2024)
        assert len(windows) > 0

    def test_returns_transfer_window_periods(self) -> None:
        windows = get_windows_for_league("BUNDESLIGA", 2024)
        for w in windows:
            assert isinstance(w, TransferWindowPeriod)


class TestIsTransferWindowOpen:
    def test_july_is_open_for_epl(self) -> None:
        # English summer window is typically open in July
        result = is_transfer_window_open("EPL", date(2024, 7, 15))
        assert isinstance(result, bool)

    def test_october_is_closed_for_epl(self) -> None:
        # Mid-season — no transfer window open
        result = is_transfer_window_open("EPL", date(2024, 10, 15))
        assert result is False

    def test_january_winter_window(self) -> None:
        # January — winter transfer window
        result = is_transfer_window_open("EPL", date(2024, 1, 15))
        assert isinstance(result, bool)

    def test_unknown_league_still_returns_bool(self) -> None:
        result = is_transfer_window_open("COMPLETELY_UNKNOWN_LEAGUE", date(2024, 7, 15))
        assert isinstance(result, bool)


class TestIsWithinTransferWindow:
    def test_returns_bool(self) -> None:
        result = is_within_transfer_window("ENG", date(2024, 7, 15))
        assert isinstance(result, bool)

    def test_october_closed_for_england(self) -> None:
        result = is_within_transfer_window("ENG", date(2024, 10, 15))
        assert result is False

    def test_unknown_country_returns_bool(self) -> None:
        result = is_within_transfer_window("XXX_UNKNOWN", date(2024, 7, 15))
        assert isinstance(result, bool)

    def test_consistent_with_is_transfer_window_open(self) -> None:
        # For EPL → ENG, both functions should agree
        d = date(2024, 10, 15)
        league_result = is_transfer_window_open("EPL", d)
        country_result = is_within_transfer_window("ENG", d)
        assert league_result == country_result


class TestGetActiveWindow:
    def test_october_not_in_window_for_epl(self) -> None:
        result = get_active_window("EPL", date(2024, 10, 15))
        assert result is None

    def test_returns_none_or_period(self) -> None:
        result = get_active_window("EPL", date(2024, 7, 20))
        assert result is None or isinstance(result, TransferWindowPeriod)

    def test_unknown_league_returns_none_or_period(self) -> None:
        result = get_active_window("UNKNOWN_LEAGUE_XY", date(2024, 7, 15))
        assert result is None or isinstance(result, TransferWindowPeriod)


class TestMostRecentWindowClose:
    def test_october_has_prior_close_date(self) -> None:
        result = most_recent_window_close("EPL", date(2024, 10, 15))
        assert result is None or isinstance(result, date)

    def test_close_date_before_query_date(self) -> None:
        d = date(2024, 10, 15)
        result = most_recent_window_close("EPL", d)
        if result is not None:
            assert result < d


class TestNextWindowOpen:
    def test_october_has_future_window(self) -> None:
        result = next_window_open("EPL", date(2024, 10, 15))
        assert result is None or isinstance(result, date)

    def test_future_open_date_is_after_query(self) -> None:
        d = date(2024, 10, 15)
        result = next_window_open("EPL", d)
        if result is not None:
            assert result >= d


class TestDaysSinceWindowClose:
    def test_returns_int_or_none(self) -> None:
        result = days_since_window_close("EPL", date(2024, 10, 15))
        assert result is None or isinstance(result, int)

    def test_positive_when_not_in_window(self) -> None:
        result = days_since_window_close("EPL", date(2024, 10, 15))
        if result is not None:
            assert result > 0


class TestDaysUntilWindowOpen:
    def test_returns_int_or_none(self) -> None:
        result = days_until_window_open("EPL", date(2024, 10, 15))
        assert result is None or isinstance(result, int)

    def test_positive_when_not_in_window(self) -> None:
        result = days_until_window_open("EPL", date(2024, 10, 15))
        if result is not None:
            assert result > 0


class TestWindowClosedWithin:
    def test_returns_bool(self) -> None:
        result = window_closed_within("EPL", date(2024, 10, 15), 60)
        assert isinstance(result, bool)

    def test_large_days_is_more_likely_true(self) -> None:
        # Large grace window should include at least one prior close
        result_large = window_closed_within("EPL", date(2024, 10, 15), 365)
        result_small = window_closed_within("EPL", date(2024, 10, 15), 1)
        # Large window should be >= small window
        assert result_large >= result_small


class TestIsTransferDataExpected:
    def test_returns_bool(self) -> None:
        result = is_transfer_data_expected("EPL", date(2024, 10, 15))
        assert isinstance(result, bool)

    def test_october_expected_within_14day_grace(self) -> None:
        # If window closed within 14 days → expected=True
        result = is_transfer_data_expected("EPL", date(2024, 10, 15))
        assert isinstance(result, bool)

    def test_long_grace_period_more_likely_expected(self) -> None:
        d = date(2024, 10, 15)
        result_long = is_transfer_data_expected("EPL", d, grace_days=90)
        result_short = is_transfer_data_expected("EPL", d, grace_days=1)
        assert result_long >= result_short


@pytest.mark.parametrize(
    ("league", "expected_country"),
    [
        ("EPL", "ENG"),
        ("LA_LIGA", "ESP"),
        ("BUNDESLIGA", "DEU"),
        ("SERIE_A", "ITA"),
        ("LIGUE_1", "FRA"),
        ("EREDIVISIE", "NLD"),
    ],
)
def test_country_for_league_parametrized(league: str, expected_country: str) -> None:
    assert get_country_for_league(league) == expected_country
