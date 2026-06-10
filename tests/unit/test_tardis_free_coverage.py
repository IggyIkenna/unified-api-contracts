"""Tests for registry/tardis_free_coverage.py — free-tier date rules."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from unified_api_contracts.registry.tardis_free_coverage import (
    TARDIS_FREE_ROLLING_WINDOW_DAYS,
    free_dates_in_range,
    is_tardis_free_date,
)


class TestIsTardisFreeDateFirstOfMonth:
    def test_jan_1_is_free(self) -> None:
        assert is_tardis_free_date(date(2024, 1, 1)) is True

    def test_feb_1_is_free(self) -> None:
        assert is_tardis_free_date(date(2024, 2, 1)) is True

    def test_dec_1_is_free(self) -> None:
        assert is_tardis_free_date(date(2023, 12, 1)) is True

    def test_first_of_month_is_always_free_regardless_of_age(self) -> None:
        assert is_tardis_free_date(date(2020, 6, 1)) is True


class TestIsTardisFreeDateRollingWindow:
    def test_today_is_free(self) -> None:
        today = date(2026, 6, 10)
        assert is_tardis_free_date(today, as_of=today) is True

    def test_yesterday_is_free(self) -> None:
        today = date(2026, 6, 10)
        yesterday = today - timedelta(days=1)
        assert is_tardis_free_date(yesterday, as_of=today) is True

    def test_at_cutoff_boundary_is_free(self) -> None:
        today = date(2026, 6, 10)
        cutoff = today - timedelta(days=TARDIS_FREE_ROLLING_WINDOW_DAYS)
        assert is_tardis_free_date(cutoff, as_of=today) is True

    def test_beyond_cutoff_not_free(self) -> None:
        today = date(2026, 6, 10)
        old_date = today - timedelta(days=TARDIS_FREE_ROLLING_WINDOW_DAYS + 5)
        if old_date.day != 1:
            assert is_tardis_free_date(old_date, as_of=today) is False

    def test_mid_month_old_date_not_free(self) -> None:
        today = date(2026, 6, 10)
        assert is_tardis_free_date(date(2025, 1, 15), as_of=today) is False

    def test_string_input_iso_format(self) -> None:
        today = date(2026, 6, 10)
        result = is_tardis_free_date("2026-06-10", as_of=today)
        assert result is True

    def test_string_input_first_of_month(self) -> None:
        assert is_tardis_free_date("2024-03-01") is True

    def test_string_input_old_mid_month(self) -> None:
        today = date(2026, 6, 10)
        result = is_tardis_free_date("2020-05-15", as_of=today)
        assert result is False

    def test_default_as_of_uses_utc_today(self) -> None:
        result = is_tardis_free_date(date(2020, 1, 1))
        assert result is True


class TestFreeDatesInRange:
    def test_single_month_includes_first(self) -> None:
        today = date(2026, 6, 10)
        result = free_dates_in_range(date(2024, 1, 1), date(2024, 1, 31), as_of=today)
        assert date(2024, 1, 1) in result

    def test_single_month_excludes_mid_month_old_dates(self) -> None:
        today = date(2026, 6, 10)
        result = free_dates_in_range(date(2024, 1, 1), date(2024, 1, 31), as_of=today)
        assert date(2024, 1, 15) not in result
        assert date(2024, 1, 31) not in result

    def test_range_of_recent_dates_is_all_free(self) -> None:
        today = date(2026, 6, 10)
        start = today - timedelta(days=3)
        end = today
        result = free_dates_in_range(start, end, as_of=today)
        assert len(result) == 4

    def test_string_inputs_accepted(self) -> None:
        today = date(2026, 6, 10)
        result = free_dates_in_range("2024-01-01", "2024-01-05", as_of=today)
        assert date(2024, 1, 1) in result

    def test_empty_range_when_start_after_end(self) -> None:
        result = free_dates_in_range(date(2024, 1, 31), date(2024, 1, 1))
        assert result == []

    def test_multi_month_catches_all_first_days(self) -> None:
        today = date(2026, 6, 10)
        result = free_dates_in_range(date(2024, 1, 1), date(2024, 3, 31), as_of=today)
        assert date(2024, 1, 1) in result
        assert date(2024, 2, 1) in result
        assert date(2024, 3, 1) in result

    def test_return_type_is_list_of_dates(self) -> None:
        today = date(2026, 6, 10)
        result = free_dates_in_range(date(2024, 1, 1), date(2024, 1, 5), as_of=today)
        assert all(isinstance(d, date) for d in result)

    def test_constant_value(self) -> None:
        assert TARDIS_FREE_ROLLING_WINDOW_DAYS == 7


@pytest.mark.parametrize(
    ("target", "as_of", "expected"),
    [
        (date(2024, 1, 1), date(2026, 6, 10), True),  # first of month
        (date(2024, 1, 15), date(2026, 6, 10), False),  # old non-first
        (date(2026, 6, 10), date(2026, 6, 10), True),  # today
        (date(2026, 6, 4), date(2026, 6, 10), True),  # within rolling window
        (date(2026, 6, 2), date(2026, 6, 10), False),  # outside window (>7 days ago), day≠1
    ],
)
def test_is_tardis_free_date_parametrized(target: date, as_of: date, expected: bool) -> None:
    assert is_tardis_free_date(target, as_of=as_of) is expected
