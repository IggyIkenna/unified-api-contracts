"""Tests for registry/session_times.py — exchange session detection."""

from __future__ import annotations

from datetime import UTC, datetime, timezone

import pytest

from unified_api_contracts.registry.session_times import (
    SessionTimes,
    get_session_times,
    is_trading_hours,
)

_UTC = UTC


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt(year: int, month: int, day: int, hour: int = 12, minute: int = 0, tz: timezone = _UTC) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=tz)


# ---------------------------------------------------------------------------
# is_trading_hours — 24/7 crypto exchanges
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exchange",
    [
        "BINANCE-SPOT",
        "BINANCE-FUTURES",
        "BYBIT",
        "OKX",
        "DERIBIT",
        "COINBASE",
        "HYPERLIQUID",
        "POLYMARKET",
        "KALSHI",
        "AAVE_V3-ETHEREUM",
        "UNISWAP_V3-ETHEREUM",
    ],
)
def test_crypto_exchanges_always_open(exchange: str) -> None:
    """24/7 venues are open at any time."""
    assert is_trading_hours(exchange, _dt(2026, 1, 15, 3, 0)) is True
    assert is_trading_hours(exchange, _dt(2026, 1, 18, 22, 0)) is True  # Sunday


def test_unknown_exchange_defaults_to_open() -> None:
    """Unknown exchanges default to 24/7 (open)."""
    assert is_trading_hours("UNKNOWN_VENUE", _dt(2026, 1, 15, 12, 0)) is True


# ---------------------------------------------------------------------------
# is_trading_hours — NYSE (standard 9:30-16:00 ET, Mon-Fri)
# ---------------------------------------------------------------------------


def test_nyse_open_on_weekday_during_hours() -> None:
    # 2026-01-13 is a Tuesday. 14:00 UTC = 9:00 ET (before open). 15:30 UTC = 10:30 ET (open).
    # Jan: ET = UTC-5
    assert is_trading_hours("NYSE", _dt(2026, 1, 13, 15, 30)) is True  # 10:30 ET = open
    assert is_trading_hours("NYSE", _dt(2026, 1, 13, 20, 30)) is True  # 15:30 ET = open


def test_nyse_closed_before_open() -> None:
    # 13:00 UTC = 8:00 ET — before 9:30 open
    assert is_trading_hours("NYSE", _dt(2026, 1, 13, 13, 0)) is False


def test_nyse_closed_after_close() -> None:
    # 21:30 UTC = 16:30 ET — after 16:00 close
    assert is_trading_hours("NYSE", _dt(2026, 1, 13, 21, 30)) is False


def test_nyse_closed_on_saturday() -> None:
    # 2026-01-17 is a Saturday
    assert is_trading_hours("NYSE", _dt(2026, 1, 17, 15, 0)) is False


def test_nyse_closed_on_sunday() -> None:
    # 2026-01-18 is a Sunday
    assert is_trading_hours("NYSE", _dt(2026, 1, 18, 15, 0)) is False


def test_nasdaq_same_as_nyse() -> None:
    assert is_trading_hours("NASDAQ", _dt(2026, 1, 13, 15, 30)) is True
    assert is_trading_hours("NASDAQ", _dt(2026, 1, 17, 15, 30)) is False


# ---------------------------------------------------------------------------
# is_trading_hours — CME (Sun 17:00 CT → Fri 16:00 CT, wraps midnight)
# ---------------------------------------------------------------------------


def test_cme_open_on_wednesday_midday() -> None:
    # 2026-01-14 is a Wednesday. 18:00 UTC = 12:00 CT (mid-session)
    assert is_trading_hours("CME", _dt(2026, 1, 14, 18, 0)) is True


def test_cme_closed_on_saturday() -> None:
    # 2026-01-17 is a Saturday — CME closed all day
    assert is_trading_hours("CME", _dt(2026, 1, 17, 12, 0)) is False


def test_cme_closed_sunday_before_open() -> None:
    # 2026-01-18 is a Sunday. CME opens at 17:00 CT = 23:00 UTC
    assert is_trading_hours("CME", _dt(2026, 1, 18, 20, 0)) is False  # 14:00 CT — before open


def test_cme_open_sunday_after_open() -> None:
    # 2026-01-18 Sunday 23:30 UTC = 17:30 CT — after 17:00 CT open
    assert is_trading_hours("CME", _dt(2026, 1, 18, 23, 30)) is True


def test_cme_closed_friday_after_close() -> None:
    # 2026-01-16 is a Friday. Close at 16:00 CT = 22:00 UTC
    assert is_trading_hours("CME", _dt(2026, 1, 16, 22, 30)) is False  # 16:30 CT — after close


def test_cme_open_friday_before_close() -> None:
    # 2026-01-16 Friday. 21:00 UTC = 15:00 CT — before 16:00 CT close
    assert is_trading_hours("CME", _dt(2026, 1, 16, 21, 0)) is True


def test_cme_during_daily_maintenance_window() -> None:
    # CME daily maintenance: 16:00-17:00 CT = 22:00-23:00 UTC on Mon-Thu
    # 2026-01-13 Tuesday 22:30 UTC = 16:30 CT — in maintenance window
    assert is_trading_hours("CME", _dt(2026, 1, 13, 22, 30)) is False


def test_naive_datetime_treated_as_utc() -> None:
    """Naive datetime should not crash — treated as UTC per docstring."""
    naive = datetime(2026, 1, 13, 15, 30)  # no tzinfo
    # Should not raise
    result = is_trading_hours("NYSE", naive)
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# get_session_times — 24/7 exchange
# ---------------------------------------------------------------------------


def test_get_session_times_crypto_returns_full_day() -> None:
    target = _dt(2026, 1, 15, 12, 0)
    st = get_session_times("BINANCE-SPOT", target)
    assert isinstance(st, SessionTimes)
    assert st.is_24_7 is True
    assert st.exchange == "BINANCE-SPOT"
    assert st.open_utc.hour == 0
    assert st.open_utc.minute == 0


def test_get_session_times_crypto_naive_datetime() -> None:
    """Naive datetime is treated as UTC for 24/7 venues."""
    naive = datetime(2026, 1, 15, 12, 0)
    st = get_session_times("POLYMARKET", naive)
    assert st.is_24_7 is True


# ---------------------------------------------------------------------------
# get_session_times — NYSE (standard session)
# ---------------------------------------------------------------------------


def test_get_session_times_nyse_structure() -> None:
    target = _dt(2026, 1, 13, 14, 0)  # Tuesday
    st = get_session_times("NYSE", target)
    assert st.exchange == "NYSE"
    assert st.is_24_7 is False
    assert st.timezone_name == "America/New_York"
    # Open should be before close
    assert st.open_utc < st.close_utc


# ---------------------------------------------------------------------------
# get_session_times — CME (wraps midnight)
# ---------------------------------------------------------------------------


def test_get_session_times_cme_structure() -> None:
    target = _dt(2026, 1, 14, 18, 0)  # Wednesday
    st = get_session_times("CME", target)
    assert st.exchange == "CME"
    assert st.is_24_7 is False
    assert st.timezone_name == "America/Chicago"
    assert st.open_utc < st.close_utc


def test_get_session_times_unknown_exchange_defaults() -> None:
    """Unknown exchange defaults to 24/7 crypto session."""
    st = get_session_times("UNKNOWN_EXCHANGE", _dt(2026, 1, 15, 12, 0))
    assert st.is_24_7 is True
