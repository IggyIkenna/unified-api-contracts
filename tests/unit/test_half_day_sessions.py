"""Unit tests for ``unified_api_contracts.registry.half_day_sessions``.

Per wave3x_residual_ssots Track A. Composes with the
``EmptyConfirmedReason.EXPECTED_PARTIAL_HALF_DAY`` enum member (UAC
``honest_coverage.py``) — the classifier reads this SSOT to fire the typed reason.
"""

from __future__ import annotations

from datetime import date

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    EmptyConfirmedReason,
)
from unified_api_contracts.registry.half_day_sessions import (
    HALF_DAY_SESSIONS,
    get_half_day_dates,
    is_half_day_session,
)


class TestIsHalfDaySession:
    def test_known_us_equity_half_day_returns_true(self) -> None:
        # 2024-11-29 = Black Friday (US equity venues close early).
        assert is_half_day_session("NYSE", date(2024, 11, 29)) is True
        assert is_half_day_session("NASDAQ", date(2024, 11, 29)) is True
        assert is_half_day_session("CBOE", date(2024, 11, 29)) is True

    def test_christmas_eve_2025_is_half_day_for_us_equity(self) -> None:
        # 2025-12-24 = Wednesday → published half-day for US equity venues.
        assert is_half_day_session("NYSE", date(2025, 12, 24)) is True

    def test_july_3_2025_is_half_day_when_july_4_is_friday(self) -> None:
        # 2025-07-04 = Friday (full holiday); 2025-07-03 = Thursday (half-day).
        assert is_half_day_session("NYSE", date(2025, 7, 3)) is True

    def test_regular_trading_day_returns_false(self) -> None:
        # Random Tuesday — should NOT be a half-day.
        assert is_half_day_session("NYSE", date(2024, 6, 11)) is False

    def test_full_holiday_is_not_half_day(self) -> None:
        # 2024-12-25 = Christmas Day → full closure, NOT a half-day.
        # The full-day-closure rule is the SSOT; this module returns False so the
        # caller's check_order is `is_non_trading_day → is_half_day_session` (priority).
        assert is_half_day_session("NYSE", date(2024, 12, 25)) is False

    def test_unknown_venue_returns_false(self) -> None:
        # 24/7 crypto venues never have half-days.
        assert is_half_day_session("BINANCE-SPOT", date(2024, 11, 29)) is False
        assert is_half_day_session("HYPERLIQUID", date(2024, 12, 24)) is False

    def test_venue_name_is_case_insensitive(self) -> None:
        assert is_half_day_session("nyse", date(2024, 11, 29)) is True
        assert is_half_day_session("Nyse", date(2024, 11, 29)) is True

    def test_eurex_christmas_eve_is_half_day(self) -> None:
        # Eurex carries Christmas Eve + New Year's Eve half-days on its own calendar.
        assert is_half_day_session("EUREX", date(2024, 12, 24)) is True
        assert is_half_day_session("EUREX", date(2024, 12, 31)) is True
        # Eurex does NOT do Black Friday.
        assert is_half_day_session("EUREX", date(2024, 11, 29)) is False

    def test_cme_uses_us_equity_half_day_calendar(self) -> None:
        assert is_half_day_session("CME", date(2024, 11, 29)) is True
        assert is_half_day_session("CME", date(2025, 12, 24)) is True


class TestGetHalfDayDates:
    def test_returns_frozenset_for_known_venue(self) -> None:
        nyse_days = get_half_day_dates("NYSE")
        assert isinstance(nyse_days, frozenset)
        assert date(2024, 11, 29) in nyse_days

    def test_returns_empty_frozenset_for_unknown_venue(self) -> None:
        result = get_half_day_dates("BINANCE-SPOT")
        assert result == frozenset()

    def test_returned_set_is_immutable(self) -> None:
        nyse_days = get_half_day_dates("NYSE")
        # frozenset is immutable — can't add or remove. Verify the type to lock the
        # contract for callers.
        assert isinstance(nyse_days, frozenset)


class TestEmptyConfirmedReasonContract:
    """Closed-set drift guard against EmptyConfirmedReason.EXPECTED_PARTIAL_HALF_DAY.

    If the enum member name changes the classifier wiring breaks silently. This test
    pins the enum literal to the docstring reference in this SSOT module.
    """

    def test_expected_partial_half_day_member_exists(self) -> None:
        assert EmptyConfirmedReason.EXPECTED_PARTIAL_HALF_DAY.value == "EXPECTED_PARTIAL_HALF_DAY"

    def test_half_day_sessions_seeded_for_every_us_equity_venue(self) -> None:
        # If a new US-equity venue is added to the workspace it MUST also get a
        # half-day calendar entry; without this the classifier will fire
        # SOURCE_RETURNED_ZERO instead of EXPECTED_PARTIAL_HALF_DAY for that venue's
        # Black Friday / Christmas Eve / July 3 shards.
        for venue in ("NYSE", "NASDAQ", "CBOE", "NYSE_ARCA", "AMEX"):
            assert venue in HALF_DAY_SESSIONS, f"{venue} missing from HALF_DAY_SESSIONS"
            # Must be non-empty (sanity — confirms seed data is correct).
            assert len(HALF_DAY_SESSIONS[venue]) > 0
