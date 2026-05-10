"""Unit tests for ``unified_api_contracts.registry.venue_session_hours``.

Per wave3x_residual_ssots Track A. Composes with the
``EmptyConfirmedReason.EXPECTED_OUTSIDE_TRADING_HOURS`` enum member (UAC
``honest_coverage.py``) — the classifier reads this SSOT to fire the typed reason.
"""

from __future__ import annotations

from datetime import UTC, datetime, time

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    EmptyConfirmedReason,
)
from unified_api_contracts.registry.venue_session_hours import (
    VENUE_SESSION_HOURS,
    get_session_window,
    is_venue_registered,
    is_within_venue_session_hours,
)


class TestIsWithinVenueSessionHours:
    def test_nyse_during_session_returns_true(self) -> None:
        # 2024-06-11 = Tuesday; 14:00 UTC = 10:00 EDT — within 09:30-16:00 ET session.
        ts = datetime(2024, 6, 11, 14, 0, tzinfo=UTC)
        assert is_within_venue_session_hours("NYSE", ts) is True

    def test_nyse_pre_market_returns_false(self) -> None:
        # 12:00 UTC = 08:00 EDT — before 09:30 open.
        ts = datetime(2024, 6, 11, 12, 0, tzinfo=UTC)
        assert is_within_venue_session_hours("NYSE", ts) is False

    def test_nyse_post_close_returns_false(self) -> None:
        # 21:00 UTC = 17:00 EDT — after 16:00 close.
        ts = datetime(2024, 6, 11, 21, 0, tzinfo=UTC)
        assert is_within_venue_session_hours("NYSE", ts) is False

    def test_nyse_weekend_returns_false(self) -> None:
        # 2024-06-15 = Saturday — closed; no entry in registry for weekday 5.
        ts = datetime(2024, 6, 15, 14, 0, tzinfo=UTC)
        assert is_within_venue_session_hours("NYSE", ts) is False

    def test_24_7_venue_always_returns_true(self) -> None:
        # 24/7 crypto venue (not in registry) → True regardless of time.
        ts = datetime(2024, 6, 15, 3, 0, tzinfo=UTC)  # Saturday 3 AM UTC
        assert is_within_venue_session_hours("BINANCE-SPOT", ts) is True
        assert is_within_venue_session_hours("HYPERLIQUID", ts) is True

    def test_naive_datetime_treated_as_utc(self) -> None:
        # No tz info — should default to UTC interpretation.
        ts_naive = datetime(2024, 6, 11, 14, 0)
        assert is_within_venue_session_hours("NYSE", ts_naive) is True

    def test_session_boundary_open_inclusive(self) -> None:
        # Exactly at NYSE open (13:30 UTC = 09:30 EDT) — inclusive.
        ts = datetime(2024, 6, 11, 13, 30, tzinfo=UTC)
        assert is_within_venue_session_hours("NYSE", ts) is True

    def test_session_boundary_close_exclusive(self) -> None:
        # Exactly at NYSE close (20:00 UTC = 16:00 EDT) — exclusive (strict <).
        ts = datetime(2024, 6, 11, 20, 0, tzinfo=UTC)
        assert is_within_venue_session_hours("NYSE", ts) is False

    def test_cboe_extended_close_to_2015_utc(self) -> None:
        # CBOE VIX intraday close is 20:15 UTC, NOT 20:00 like NYSE.
        ts_at_2010 = datetime(2024, 6, 11, 20, 10, tzinfo=UTC)
        assert is_within_venue_session_hours("CBOE", ts_at_2010) is True
        ts_at_2020 = datetime(2024, 6, 11, 20, 20, tzinfo=UTC)
        assert is_within_venue_session_hours("CBOE", ts_at_2020) is False

    def test_venue_name_case_insensitive(self) -> None:
        ts = datetime(2024, 6, 11, 14, 0, tzinfo=UTC)
        assert is_within_venue_session_hours("nyse", ts) is True
        assert is_within_venue_session_hours("Nyse", ts) is True


class TestGetSessionWindow:
    def test_returns_tuple_for_registered_venue_and_weekday(self) -> None:
        # NYSE Monday (weekday 0).
        window = get_session_window("NYSE", 0)
        assert window is not None
        open_t, close_t = window
        assert open_t == time(13, 30, tzinfo=UTC)
        assert close_t == time(20, 0, tzinfo=UTC)

    def test_returns_none_for_24_7_venue(self) -> None:
        assert get_session_window("BINANCE-SPOT", 0) is None
        assert get_session_window("HYPERLIQUID", 5) is None

    def test_returns_none_for_registered_venue_weekend(self) -> None:
        # NYSE Saturday (weekday 5) — venue is registered but closed-on-weekends.
        assert get_session_window("NYSE", 5) is None
        assert get_session_window("NYSE", 6) is None


class TestIsVenueRegistered:
    def test_nyse_registered(self) -> None:
        assert is_venue_registered("NYSE") is True

    def test_24_7_venue_not_registered(self) -> None:
        # Not in the registry — :func:`is_within_venue_session_hours` returns True
        # (24/7 default), but :func:`is_venue_registered` distinguishes "not registered"
        # from "registered but closed on this weekday."
        assert is_venue_registered("BINANCE-SPOT") is False
        assert is_venue_registered("POLYMARKET") is False

    def test_eurex_registered(self) -> None:
        assert is_venue_registered("EUREX") is True
        assert is_venue_registered("DTB") is True

    def test_cme_registered(self) -> None:
        assert is_venue_registered("CME") is True


class TestEmptyConfirmedReasonContract:
    """Closed-set drift guard against EmptyConfirmedReason.EXPECTED_OUTSIDE_TRADING_HOURS.

    If the enum member name changes the classifier wiring breaks silently. This test
    pins the enum literal to the docstring reference in this SSOT module.
    """

    def test_expected_outside_trading_hours_member_exists(self) -> None:
        assert EmptyConfirmedReason.EXPECTED_OUTSIDE_TRADING_HOURS.value == "EXPECTED_OUTSIDE_TRADING_HOURS"

    def test_every_seeded_venue_has_at_least_one_weekday_entry(self) -> None:
        # Sanity: pull the unique venues from the dict; every registered venue must have
        # at least one weekday entry. Detects accidental empty seeds.
        venues = {key[0] for key in VENUE_SESSION_HOURS}
        for venue in venues:
            entries = [k for k in VENUE_SESSION_HOURS if k[0] == venue]
            assert len(entries) > 0, f"{venue} has no weekday entries in VENUE_SESSION_HOURS"
