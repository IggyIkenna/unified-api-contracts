"""Yahoo intraday lookback guardrail — durable QG enforcement.

A request that reaches FURTHER BACK than a Yahoo interval's granularity/lookback
limit MUST raise (clamp), never silently return empty. These tests pin the
probed-live limits (2026-06-24) so a too-old/too-fine request is rejected and so
the guardrail map stays the SSOT both the adapter and the venue/source parity
gate read.
"""

from __future__ import annotations

import datetime as dt

import pytest

from unified_api_contracts.registry import (
    YAHOO_INTRADAY_LOOKBACK_DAYS,
    YahooLookbackExceededError,
    assert_yahoo_intraday_within_limit,
)

_TODAY = dt.date(2026, 6, 24)


class TestYahooIntradayLookbackLimits:
    """The probed-live limit ladder is the SSOT (operator 2026-06-24)."""

    def test_probed_limit_ladder(self) -> None:
        # The operator's confirmed ladder (probed live 2026-06-24, 005930.KS).
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["1m"] == 28
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["15m"] == 89
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["1h"] == 730
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["1d"] is None  # unbounded (full history)

    def test_within_limit_does_not_raise(self) -> None:
        # One day INSIDE each bounded limit → allowed.
        assert_yahoo_intraday_within_limit("1m", _TODAY - dt.timedelta(days=27), today=_TODAY)
        assert_yahoo_intraday_within_limit("15m", _TODAY - dt.timedelta(days=88), today=_TODAY)
        assert_yahoo_intraday_within_limit("1h", _TODAY - dt.timedelta(days=729), today=_TODAY)

    def test_beyond_limit_raises(self) -> None:
        # One day PAST each bounded limit → fail-closed raise (never silent-empty).
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("1m", _TODAY - dt.timedelta(days=29), today=_TODAY)
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("15m", _TODAY - dt.timedelta(days=90), today=_TODAY)
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("1h", _TODAY - dt.timedelta(days=731), today=_TODAY)

    def test_daily_is_unbounded(self) -> None:
        # 1d / weekly / monthly intervals serve full history → never raise.
        assert_yahoo_intraday_within_limit("1d", dt.date(2000, 1, 1), today=_TODAY)
        assert_yahoo_intraday_within_limit("1wk", dt.date(1990, 1, 1), today=_TODAY)
        assert_yahoo_intraday_within_limit("1mo", dt.date(1980, 1, 1), today=_TODAY)

    def test_unknown_interval_raises_keyerror(self) -> None:
        # An interval not in the ladder is a programming error, not a silent pass.
        with pytest.raises(KeyError):
            assert_yahoo_intraday_within_limit("7m", _TODAY, today=_TODAY)

    def test_exact_boundary_day_is_allowed(self) -> None:
        # start_date == floor (today - limit) is allowed (inclusive boundary).
        for interval, limit in (("1m", 28), ("15m", 89), ("1h", 730)):
            floor = _TODAY - dt.timedelta(days=limit)
            assert_yahoo_intraday_within_limit(interval, floor, today=_TODAY)
