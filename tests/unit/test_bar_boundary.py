"""Unit tests for the bar_boundary SSOT module.

The four contract clauses (closed-set timeframe / midnight-aligned t_close /
half-open window of width == timeframe / available_at == t_close) each get a
positive + negative test case. Idempotency is covered by the worked examples
in the module docstring + the round-trip test below.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from unified_api_contracts.canonical.crosscutting.bar_boundary import (
    BAR_TIMEFRAME_SECONDS,
    BAR_TIMEFRAMES,
    BarBoundaryViolationError,
    assert_bar_boundary_contract,
    bar_window_for_close,
)


def _utc(year: int, month: int, day: int, h: int = 0, m: int = 0, s: int = 0) -> datetime:
    return datetime(year, month, day, h, m, s, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Closed-set timeframe (clause 1).
# ---------------------------------------------------------------------------


def test_bar_timeframes_is_the_expected_closed_set() -> None:
    """Locking the set itself: adding a timeframe must be deliberate."""
    assert BAR_TIMEFRAMES == ("1s", "15s", "1m", "5m", "15m", "30m", "1h", "4h", "1d")


def test_bar_timeframe_seconds_aligned_to_day() -> None:
    """Every timeframe divides evenly into 86400s (one UTC day) — the
    midnight-aligned grid only works if this invariant holds."""
    for tf, secs in BAR_TIMEFRAME_SECONDS.items():
        assert 86_400 % secs == 0, f"{tf} ({secs}s) does not divide 86400s"


def test_unknown_timeframe_raises() -> None:
    t_close = _utc(2026, 4, 29, 14, 30)
    with pytest.raises(BarBoundaryViolationError, match="not in the closed set"):
        assert_bar_boundary_contract(
            t_open=t_close - timedelta(minutes=7),
            t_close=t_close,
            available_at=t_close,
            timeframe="7m",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# UTC-midnight-aligned boundaries (clause 2).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "timeframe,t_close",
    [
        ("1s", _utc(2026, 4, 29, 14, 30, 0)),
        ("1s", _utc(2026, 4, 29, 14, 30, 1)),
        ("15s", _utc(2026, 4, 29, 14, 30, 0)),
        ("15s", _utc(2026, 4, 29, 14, 30, 15)),
        ("1m", _utc(2026, 4, 29, 14, 30, 0)),
        ("5m", _utc(2026, 4, 29, 14, 35, 0)),
        ("15m", _utc(2026, 4, 29, 14, 30, 0)),
        ("30m", _utc(2026, 4, 29, 14, 30, 0)),
        ("1h", _utc(2026, 4, 29, 14, 0, 0)),
        ("4h", _utc(2026, 4, 29, 16, 0, 0)),
        ("1d", _utc(2026, 4, 30, 0, 0, 0)),
    ],
)
def test_aligned_t_close_passes(timeframe: str, t_close: datetime) -> None:
    bar_window_for_close(t_close, timeframe)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "timeframe,t_close",
    [
        ("15m", _utc(2026, 4, 29, 14, 23, 47)),  # 14:23:47 ∉ 15m grid
        ("1h", _utc(2026, 4, 29, 14, 30, 0)),  # 14:30:00 ∉ 1h grid
        ("1d", _utc(2026, 4, 29, 12, 0, 0)),  # 12:00:00 ∉ 1d grid
        ("4h", _utc(2026, 4, 29, 14, 0, 0)),  # 14:00:00 ∉ 4h grid (15h is)
        ("5m", _utc(2026, 4, 29, 14, 32, 0)),  # 14:32:00 ∉ 5m grid
    ],
)
def test_misaligned_t_close_raises(timeframe: str, t_close: datetime) -> None:
    with pytest.raises(BarBoundaryViolationError, match="not aligned"):
        bar_window_for_close(t_close, timeframe)  # type: ignore[arg-type]


def test_sub_second_precision_rejected() -> None:
    """Microsecond-level offsets count as misalignment — every supported
    timeframe is whole seconds, so any microsecond component on t_close is
    a contract violation."""
    t_close = _utc(2026, 4, 29, 14, 30).replace(microsecond=1)
    with pytest.raises(BarBoundaryViolationError, match="not aligned"):
        bar_window_for_close(t_close, "15m")


# ---------------------------------------------------------------------------
# Window width == timeframe (clause 3).
# ---------------------------------------------------------------------------


def test_window_width_must_match_timeframe() -> None:
    t_close = _utc(2026, 4, 29, 14, 30)
    bad_open = t_close - timedelta(minutes=5)  # 5m window labelled as 15m
    with pytest.raises(BarBoundaryViolationError, match="does not equal timeframe"):
        assert_bar_boundary_contract(
            t_open=bad_open,
            t_close=t_close,
            available_at=t_close,
            timeframe="15m",
        )


# ---------------------------------------------------------------------------
# available_at >= t_close (clause 4 — amended 2026-05-11 per the MDPS audit).
#
# The canonical Live=batch form is `t_close + emission_latency_ms_for_source`,
# i.e. `available_at >= t_close` with the per-source latency added on top.
# Earlier-than-close is BANNED (leak); 25h+ past close is BANNED (catches the
# pre-2026-05-11 MDPS `t_close + tf + latency` overshoot for 1d candles).
# ---------------------------------------------------------------------------


def test_available_at_below_t_close_raises() -> None:
    """available_at < t_close = leak — banned."""
    t_close = _utc(2026, 4, 29, 14, 30)
    t_open = t_close - timedelta(minutes=15)
    with pytest.raises(BarBoundaryViolationError, match=r"available_at=.*< t_close"):
        assert_bar_boundary_contract(
            t_open=t_open,
            t_close=t_close,
            available_at=t_close - timedelta(seconds=1),
            timeframe="15m",
        )


def test_available_at_equal_to_t_close_passes_degenerate_no_latency() -> None:
    """available_at == t_close: degenerate no-latency form (valid)."""
    t_close = _utc(2026, 4, 29, 14, 30)
    t_open = t_close - timedelta(minutes=15)
    # Should not raise — t_close + 0ms latency is the synthetic / unit-test form.
    assert_bar_boundary_contract(
        t_open=t_open,
        t_close=t_close,
        available_at=t_close,
        timeframe="15m",
    )


def test_available_at_plus_typical_emission_latency_passes() -> None:
    """available_at = t_close + emission_latency (the canonical Live=batch form)."""
    t_close = _utc(2026, 4, 29, 14, 30)
    t_open = t_close - timedelta(minutes=15)
    # Per UAC EMISSION_LATENCY_MS_BY_SOURCE: tardis=50ms, databento=10ms,
    # onchain_subgraph=60s, transfermarkt=24h. All within the [t_close, t_close+25h)
    # canonical window.
    for latency in (
        timedelta(milliseconds=10),  # databento
        timedelta(milliseconds=50),  # tardis
        timedelta(milliseconds=200),  # polymarket_clob
        timedelta(seconds=60),  # onchain_subgraph
        timedelta(hours=2),  # understat post-match
        timedelta(hours=24),  # transfermarkt
    ):
        assert_bar_boundary_contract(
            t_open=t_open,
            t_close=t_close,
            available_at=t_close + latency,
            timeframe="15m",
        )


def test_available_at_25h_past_t_close_raises_overshoot_guard() -> None:
    """available_at >25h past t_close — catches the pre-2026-05-11 overshoot bug."""
    t_close = _utc(2026, 4, 29, 14, 30)
    t_open = t_close - timedelta(minutes=15)
    # 25h + 1s past t_close — exceeds the 24h transfermarkt cap.
    with pytest.raises(BarBoundaryViolationError, match=r"more than 25h past t_close"):
        assert_bar_boundary_contract(
            t_open=t_open,
            t_close=t_close,
            available_at=t_close + timedelta(hours=25, seconds=1),
            timeframe="15m",
        )


# ---------------------------------------------------------------------------
# tz-awareness prerequisite (clause 2 enforcement).
# ---------------------------------------------------------------------------


def test_naive_datetime_rejected() -> None:
    naive_close = datetime(2026, 4, 29, 14, 30)  # no tzinfo
    with pytest.raises(BarBoundaryViolationError, match="must be tz-aware UTC"):
        bar_window_for_close(naive_close, "15m")


def test_non_utc_datetime_rejected() -> None:
    """Even tz-aware non-UTC violates clause 2 — bars are always UTC."""
    plus_one = timezone(timedelta(hours=1))
    non_utc_close = datetime(2026, 4, 29, 15, 30, tzinfo=plus_one)  # would be 14:30 UTC
    with pytest.raises(BarBoundaryViolationError, match="must be UTC"):
        bar_window_for_close(non_utc_close, "15m")


# ---------------------------------------------------------------------------
# Round-trip + idempotency.
# ---------------------------------------------------------------------------


def test_bar_window_for_close_round_trip() -> None:
    """Worked example from the module docstring."""
    t_close = _utc(2026, 4, 29, 14, 30)
    t_open, returned_close, available_at = bar_window_for_close(t_close, "15m")
    assert t_open == _utc(2026, 4, 29, 14, 15)
    assert returned_close == t_close
    assert available_at == t_close


def test_daily_bar_window() -> None:
    """Daily bar spanning all of 2026-04-29 closes at 04-30 00:00 UTC."""
    t_close = _utc(2026, 4, 30, 0, 0, 0)
    t_open, returned_close, available_at = bar_window_for_close(t_close, "1d")
    assert t_open == _utc(2026, 4, 29, 0, 0, 0)
    assert returned_close == t_close
    assert available_at == t_close
