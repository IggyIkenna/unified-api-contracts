"""Yahoo granularity/lookback GUARDRAIL — durable QG enforcement (GENERAL).

A request that reaches FURTHER BACK than a Yahoo interval's granularity/lookback
limit, OR a single intraday request WIDER than the per-request cap, MUST raise
(clamp) — never silently return empty. These tests pin the MEASURED-live limits
(2026-06-24, tickers 005930.KS / 005380.KS / 000660.KS) so a too-old / too-fine /
too-wide request is rejected, and so the guardrail map stays the SSOT that both
the adapter and the venue/source parity gate read.

MEASURED 2026-06-24 (corrects the prior assumed ladder):
  * 1m  : 8 days PER REQUEST ("Only 8 days worth ... per request"); ~30d total.
  * 15m : 60 days (NOT 89) — 59d OK, 60d+ → 422.
  * 1h  : 730 days — <730d OK, exactly-730d fails.
  * 1d  : unbounded lookback; clamped to YAHOO_DAILY_BACKFILL_FLOOR (2019-01-01).
"""

from __future__ import annotations

import datetime as dt

import pytest

from unified_api_contracts.registry import (
    YAHOO_DAILY_BACKFILL_FLOOR,
    YAHOO_INTRADAY_LOOKBACK_DAYS,
    YAHOO_INTRADAY_MAX_REQUEST_DAYS,
    YahooLookbackExceededError,
    YahooRequestTooWideError,
    assert_yahoo_intraday_within_limit,
    assert_yahoo_request_width_ok,
)

_TODAY = dt.date(2026, 6, 24)


class TestYahooIntradayLookbackLimits:
    """The MEASURED-live limit ladder is the SSOT (operator 2026-06-24)."""

    def test_probed_limit_ladder(self) -> None:
        # The MEASURED ladder (probed live 2026-06-24 on the 3 KRX tickers).
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["1m"] == 30  # ~30d total; per-request cap 8d
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["15m"] == 60  # 59d OK, 60d+ → 422
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["1h"] == 730
        assert YAHOO_INTRADAY_LOOKBACK_DAYS["1d"] is None  # unbounded (clamped to floor)
        assert dt.date(2019, 1, 1) == YAHOO_DAILY_BACKFILL_FLOOR
        assert YAHOO_INTRADAY_MAX_REQUEST_DAYS["1m"] == 8  # 8 days per request

    def test_within_limit_does_not_raise(self) -> None:
        # One day INSIDE each bounded limit → allowed.
        assert_yahoo_intraday_within_limit("1m", _TODAY - dt.timedelta(days=29), today=_TODAY)
        assert_yahoo_intraday_within_limit("15m", _TODAY - dt.timedelta(days=59), today=_TODAY)
        assert_yahoo_intraday_within_limit("1h", _TODAY - dt.timedelta(days=729), today=_TODAY)

    def test_beyond_limit_raises(self) -> None:
        # One day PAST each bounded limit → fail-closed raise (never silent-empty).
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("1m", _TODAY - dt.timedelta(days=31), today=_TODAY)
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("15m", _TODAY - dt.timedelta(days=61), today=_TODAY)
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("1h", _TODAY - dt.timedelta(days=731), today=_TODAY)

    def test_daily_clamps_to_backfill_floor(self) -> None:
        # 1d is unbounded by Yahoo, but the GENERAL guardrail clamps to the
        # operator backfill floor (2019-01-01) — before it RAISES, on/after is OK.
        assert_yahoo_intraday_within_limit("1d", YAHOO_DAILY_BACKFILL_FLOOR, today=_TODAY)  # inclusive
        assert_yahoo_intraday_within_limit("1d", dt.date(2020, 1, 1), today=_TODAY)
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("1d", dt.date(2018, 12, 31), today=_TODAY)
        # weekly/monthly share the unbounded-clamp behaviour
        with pytest.raises(YahooLookbackExceededError):
            assert_yahoo_intraday_within_limit("1wk", dt.date(1990, 1, 1), today=_TODAY)

    def test_unknown_interval_raises_keyerror(self) -> None:
        # An interval not in the ladder is a programming error, not a silent pass.
        with pytest.raises(KeyError):
            assert_yahoo_intraday_within_limit("7m", _TODAY, today=_TODAY)

    def test_exact_boundary_day_is_allowed(self) -> None:
        # start_date == floor (today - limit) is allowed (inclusive boundary).
        for interval, limit in (("1m", 30), ("15m", 60), ("1h", 730)):
            floor = _TODAY - dt.timedelta(days=limit)
            assert_yahoo_intraday_within_limit(interval, floor, today=_TODAY)


class TestYahooPerRequestWidthCap:
    """1m is bounded to 8 days PER REQUEST — a wider single request must raise."""

    def test_within_request_width_ok(self) -> None:
        assert_yahoo_request_width_ok("1m", dt.date(2026, 6, 1), dt.date(2026, 6, 8))  # 7d
        assert_yahoo_request_width_ok("1m", dt.date(2026, 6, 1), dt.date(2026, 6, 9))  # 8d (cap, inclusive)

    def test_too_wide_request_raises(self) -> None:
        with pytest.raises(YahooRequestTooWideError):
            assert_yahoo_request_width_ok("1m", dt.date(2026, 6, 1), dt.date(2026, 6, 20))  # 19d > 8

    def test_unbounded_interval_no_width_cap(self) -> None:
        # 1d has no per-request width cap → never raises regardless of span.
        assert_yahoo_request_width_ok("1d", dt.date(2019, 1, 1), dt.date(2026, 6, 24))
