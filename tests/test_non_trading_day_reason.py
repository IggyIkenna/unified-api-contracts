"""Unit tests for `non_trading_day_reason` (writegate Phase 2.E.2 helper)."""

from __future__ import annotations

import pytest

from unified_api_contracts.registry import is_non_trading_day, non_trading_day_reason


@pytest.mark.parametrize(
    "venue,iso_date",
    [
        ("CME", "2024-01-06"),  # Saturday
        ("NASDAQ", "2024-01-07"),  # Sunday
        ("NYSE", "2024-01-13"),  # Saturday
    ],
)
def test_weekend_returns_expected_weekend(venue: str, iso_date: str) -> None:
    """Sat/Sun on calendar-bound venues → EXPECTED_WEEKEND."""
    assert is_non_trading_day(venue, iso_date)
    assert non_trading_day_reason(venue, iso_date) == "EXPECTED_WEEKEND"


def test_us_market_holiday_weekday_returns_expected_holiday() -> None:
    """US market holiday on a weekday → EXPECTED_HOLIDAY (e.g. Christmas Day 2024)."""
    # 2024-12-25 is a Wednesday; full US-market holiday.
    iso_date = "2024-12-25"
    assert is_non_trading_day("NYSE", iso_date)
    assert non_trading_day_reason("NYSE", iso_date) == "EXPECTED_HOLIDAY"


def test_trading_weekday_returns_none() -> None:
    """Regular trading weekday → None (caller should NOT emit an EXPECTED_* row)."""
    # 2024-01-08 = Monday, no US holiday.
    iso_date = "2024-01-08"
    assert not is_non_trading_day("NYSE", iso_date)
    assert non_trading_day_reason("NYSE", iso_date) is None


def test_crypto_venue_always_returns_none() -> None:
    """24/7 crypto venues are not calendar-bound → always None, even on weekend."""
    iso_date = "2024-01-06"  # Saturday
    assert not is_non_trading_day("BINANCE", iso_date)
    assert non_trading_day_reason("BINANCE", iso_date) is None


def test_unknown_venue_returns_none() -> None:
    """Venues not registered as calendar-bound → None (assume always trading)."""
    assert non_trading_day_reason("SOME_UNKNOWN_VENUE", "2024-01-06") is None


@pytest.mark.parametrize("iso_date", ["2024-01-06", "2024-12-25"])
def test_returns_only_closed_set_values(iso_date: str) -> None:
    """The result is one of {None, EXPECTED_HOLIDAY, EXPECTED_WEEKEND} — closed set."""
    result = non_trading_day_reason("NYSE", iso_date)
    assert result in {None, "EXPECTED_HOLIDAY", "EXPECTED_WEEKEND"}


@pytest.mark.parametrize(
    "iso_date",
    [
        "2024-03-29",  # Good Friday — a US_MARKET_HOLIDAY, NOT a federal holiday
        "2024-01-06",  # Saturday
        "2024-01-07",  # Sunday
    ],
)
def test_fred_calendar_exempt_venue_never_non_trading(iso_date: str) -> None:
    """FRED is asset_group=='tradfi' but is release-schedule-driven, not equity-market-driven —
    CALENDAR_EXEMPT_TRADFI_VENUES must keep it out of the weekend/US_MARKET_HOLIDAYS gate
    entirely (2026-07-30 fix: 2024-01-01 was silently stamped EXPECTED_HOLIDAY with zero
    fetch attempt before this; Good Friday closes NYSE but not the Fed/BLS)."""
    assert not is_non_trading_day("FRED", iso_date)
    assert non_trading_day_reason("FRED", iso_date) is None


def test_calendar_exempt_venue_does_not_affect_sibling_tradfi_venues() -> None:
    """The FRED exemption must not leak into other tradfi venues on the same holiday."""
    iso_date = "2024-03-29"  # Good Friday
    assert is_non_trading_day("NYSE", iso_date)
    assert is_non_trading_day("CME", iso_date)
