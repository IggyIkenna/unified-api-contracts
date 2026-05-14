"""Per-venue unit tests for market-session classification.

Covers each venue in VENUE_SESSION_SCHEDULE with:
- Regular session day (clear in-session timestamps)
- Boundary edges (pre/regular/post transitions)
- Cross-midnight windows (CME Globex Sunday open, ICE energy)
- Daylight-saving transitions (Spring forward / Fall back)
- Known-good half-day / holiday: marked DEFERRED (not yet encoded; tested for
  the current "returns regular-week classification" behavior — when half-day
  calendar lands, these tests will need updating).

Per operator direction: correctness > speed; prefer tested schedules even if
slow. Half-day / holiday calendars are DEFERRED with explicit annotations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from unified_api_contracts.canonical.crosscutting.market_session import (
    VENUE_SESSION_SCHEDULE,
    MarketSession,
    SessionPhase,
    SessionWindow,
    classify_session,
)


def _dt(year: int, month: int, day: int, hour: int, minute: int, tz: str) -> datetime:
    """Build a tz-aware datetime in the given timezone."""
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))


# ---------------------------------------------------------------------------
# Module-level sanity
# ---------------------------------------------------------------------------


def test_market_session_enum_closed_set():
    """MarketSession is a closed set of exactly 6 values."""
    expected = {"regular", "pre_market", "post_market", "overnight", "halted", "closed"}
    assert {m.value for m in MarketSession} == expected


def test_session_phase_enum_closed_set():
    """SessionPhase is a closed set of exactly 5 values."""
    expected = {"open_auction", "continuous", "close_auction", "after_hours_auction", "none"}
    assert {p.value for p in SessionPhase} == expected


def test_venue_session_schedule_known_venues():
    """All 5 expected venues registered."""
    assert set(VENUE_SESSION_SCHEDULE.keys()) == {"CME", "NYSE", "NASDAQ", "ICE", "CBOE"}


def test_session_window_frozen():
    """SessionWindow is frozen (immutable) — required for hashability + dict keys."""
    from dataclasses import FrozenInstanceError

    w = SessionWindow(
        session=MarketSession.REGULAR,
        phase=SessionPhase.CONTINUOUS,
        weekday_mask=frozenset({0}),
        start_time=datetime(2026, 1, 1, 9, 30).time(),
        end_time=datetime(2026, 1, 1, 16, 0).time(),
        tz="America/New_York",
    )
    with pytest.raises(FrozenInstanceError):
        w.session = MarketSession.PRE_MARKET  # type: ignore[misc]


def test_classify_session_rejects_naive_datetime():
    """Naive datetime is rejected with ValueError."""
    with pytest.raises(ValueError, match="tz-aware"):
        classify_session("NYSE", datetime(2026, 1, 5, 10, 0))


def test_classify_session_rejects_unknown_venue():
    """Unknown venue is rejected with ValueError listing known venues."""
    with pytest.raises(ValueError, match="Unknown venue"):
        classify_session("BOGUS", datetime(2026, 1, 5, 10, 0, tzinfo=UTC))


# ---------------------------------------------------------------------------
# NYSE — Monday 2026-01-05 regular trading day (no DST, no holiday)
# ---------------------------------------------------------------------------


def test_nyse_pre_market_8am_et():
    """08:00 ET on a regular Monday → PRE_MARKET continuous."""
    dt = _dt(2026, 1, 5, 8, 0, "America/New_York")
    assert classify_session("NYSE", dt) == (MarketSession.PRE_MARKET, SessionPhase.CONTINUOUS)


def test_nyse_open_auction_at_930_et():
    """09:30 ET sharp → REGULAR open_auction (single-price match)."""
    dt = _dt(2026, 1, 5, 9, 30, "America/New_York")
    assert classify_session("NYSE", dt) == (MarketSession.REGULAR, SessionPhase.OPEN_AUCTION)


def test_nyse_continuous_at_10am_et():
    """10:00 ET → REGULAR continuous."""
    dt = _dt(2026, 1, 5, 10, 0, "America/New_York")
    assert classify_session("NYSE", dt) == (MarketSession.REGULAR, SessionPhase.CONTINUOUS)


def test_nyse_close_auction_at_1555_et():
    """15:55 ET → REGULAR close_auction (imbalance window)."""
    dt = _dt(2026, 1, 5, 15, 55, "America/New_York")
    assert classify_session("NYSE", dt) == (MarketSession.REGULAR, SessionPhase.CLOSE_AUCTION)


def test_nyse_post_market_at_17_et():
    """17:00 ET → POST_MARKET continuous."""
    dt = _dt(2026, 1, 5, 17, 0, "America/New_York")
    assert classify_session("NYSE", dt) == (MarketSession.POST_MARKET, SessionPhase.CONTINUOUS)


def test_nyse_closed_at_22_et():
    """22:00 ET → CLOSED (post-market ends at 20:00 ET)."""
    dt = _dt(2026, 1, 5, 22, 0, "America/New_York")
    assert classify_session("NYSE", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


def test_nyse_closed_on_saturday():
    """Saturday → CLOSED regardless of time-of-day."""
    dt = _dt(2026, 1, 3, 10, 0, "America/New_York")  # Saturday
    assert classify_session("NYSE", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


# ---------------------------------------------------------------------------
# Nasdaq — same hours as NYSE (verify parity)
# ---------------------------------------------------------------------------


def test_nasdaq_open_auction():
    """Nasdaq open auction at 09:30 ET (matches NYSE shape)."""
    dt = _dt(2026, 1, 5, 9, 30, "America/New_York")
    assert classify_session("NASDAQ", dt) == (MarketSession.REGULAR, SessionPhase.OPEN_AUCTION)


def test_nasdaq_post_market_19_et():
    """19:00 ET → POST_MARKET (NASDAQ matches NYSE 16:00-20:00 ET)."""
    dt = _dt(2026, 1, 5, 19, 0, "America/New_York")
    assert classify_session("NASDAQ", dt) == (MarketSession.POST_MARKET, SessionPhase.CONTINUOUS)


# ---------------------------------------------------------------------------
# CME Globex — Sunday 2026-01-04 evening + Monday 2026-01-05 daytime
# ---------------------------------------------------------------------------


def test_cme_sunday_evening_open_at_17_ct():
    """17:00 CT Sunday → REGULAR continuous (weekly open)."""
    dt = _dt(2026, 1, 4, 17, 0, "America/Chicago")  # Sunday
    assert classify_session("CME", dt) == (MarketSession.REGULAR, SessionPhase.CONTINUOUS)


def test_cme_monday_morning_continuous():
    """09:00 CT Monday → REGULAR continuous (no maintenance break)."""
    dt = _dt(2026, 1, 5, 9, 0, "America/Chicago")
    assert classify_session("CME", dt) == (MarketSession.REGULAR, SessionPhase.CONTINUOUS)


def test_cme_monday_maintenance_break_at_1630_ct():
    """16:30 CT Monday → CLOSED (16:00-17:00 CT maintenance break)."""
    dt = _dt(2026, 1, 5, 16, 30, "America/Chicago")
    assert classify_session("CME", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


def test_cme_monday_post_maintenance_reopen_at_17_ct():
    """17:00 CT Monday → REGULAR (post-maintenance reopen)."""
    dt = _dt(2026, 1, 5, 17, 0, "America/Chicago")
    assert classify_session("CME", dt) == (MarketSession.REGULAR, SessionPhase.CONTINUOUS)


def test_cme_friday_close_at_16_ct():
    """Friday 16:00 CT → no longer in any regular window (weekly close)."""
    # 16:00 CT exactly is the close — past this is CLOSED until Sunday 17:00 CT
    dt = _dt(2026, 1, 9, 16, 30, "America/Chicago")  # Friday 16:30 CT
    assert classify_session("CME", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


def test_cme_saturday_closed():
    """Saturday → CLOSED entirely (no Globex trading)."""
    dt = _dt(2026, 1, 10, 10, 0, "America/Chicago")  # Saturday
    assert classify_session("CME", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


# ---------------------------------------------------------------------------
# ICE — Sunday evening through Friday close
# ---------------------------------------------------------------------------


def test_ice_sunday_evening_open_at_18_et():
    """18:00 ET Sunday → REGULAR continuous (weekly open)."""
    dt = _dt(2026, 1, 4, 18, 0, "America/New_York")  # Sunday
    assert classify_session("ICE", dt) == (MarketSession.REGULAR, SessionPhase.CONTINUOUS)


def test_ice_monday_settlement_break_at_1730_et():
    """17:30 ET Monday → CLOSED (17:00-18:00 ET settlement break)."""
    dt = _dt(2026, 1, 5, 17, 30, "America/New_York")
    assert classify_session("ICE", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


def test_ice_friday_weekly_close_at_18_et():
    """Friday 18:00 ET → CLOSED (week ends at 17:00 ET Friday; no reopen)."""
    dt = _dt(2026, 1, 9, 18, 0, "America/New_York")  # Friday
    assert classify_session("ICE", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


# ---------------------------------------------------------------------------
# CBOE — Global Trading Hours + regular SPX/VIX
# ---------------------------------------------------------------------------


def test_cboe_overnight_session_at_5am_et():
    """05:00 ET Monday → OVERNIGHT (GTH session 02:15-09:15 ET)."""
    dt = _dt(2026, 1, 5, 5, 0, "America/New_York")
    assert classify_session("CBOE", dt) == (MarketSession.OVERNIGHT, SessionPhase.CONTINUOUS)


def test_cboe_gap_between_overnight_and_regular():
    """09:20 ET Monday → CLOSED (gap between overnight close 09:15 + regular open 09:30)."""
    dt = _dt(2026, 1, 5, 9, 20, "America/New_York")
    assert classify_session("CBOE", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


def test_cboe_regular_continuous():
    """12:00 ET Monday → REGULAR continuous."""
    dt = _dt(2026, 1, 5, 12, 0, "America/New_York")
    assert classify_session("CBOE", dt) == (MarketSession.REGULAR, SessionPhase.CONTINUOUS)


def test_cboe_regular_close_at_1615_et():
    """16:15 ET Monday → CLOSED (SPX/VIX close at 16:15, later than NYSE)."""
    dt = _dt(2026, 1, 5, 16, 15, "America/New_York")
    assert classify_session("CBOE", dt) == (MarketSession.CLOSED, SessionPhase.NONE)


# ---------------------------------------------------------------------------
# Daylight Saving Time transitions — verify schedule survives clock change
# ---------------------------------------------------------------------------


def test_nyse_dst_spring_forward_2026():
    """Sunday 2026-03-08 = US DST spring forward; Monday 2026-03-09 09:30 ET
    must still open. Verify the local-time semantics survive UTC shift."""
    dt_local = _dt(2026, 3, 9, 9, 30, "America/New_York")  # Monday after DST
    assert classify_session("NYSE", dt_local) == (MarketSession.REGULAR, SessionPhase.OPEN_AUCTION)


def test_nyse_dst_fall_back_2026():
    """Sunday 2026-11-01 = US DST fall back; Monday 2026-11-02 09:30 ET still opens."""
    dt_local = _dt(2026, 11, 2, 9, 30, "America/New_York")  # Monday after DST
    assert classify_session("NYSE", dt_local) == (MarketSession.REGULAR, SessionPhase.OPEN_AUCTION)


def test_classify_session_accepts_utc_input():
    """UTC input is correctly converted to venue-local for classification."""
    # 14:30 UTC on Mon 2026-01-05 = 09:30 ET (winter, EST = UTC-5)
    dt_utc = datetime(2026, 1, 5, 14, 30, tzinfo=UTC)
    assert classify_session("NYSE", dt_utc) == (MarketSession.REGULAR, SessionPhase.OPEN_AUCTION)


# ---------------------------------------------------------------------------
# DEFERRED — half-day calendars not yet encoded
# ---------------------------------------------------------------------------
# When half-day calendar lands, these tests should be updated to expect the
# half-day-specific behavior.


def test_nyse_christmas_eve_currently_regular_classification():
    """DEFERRED: 13:30 ET on 2026-12-24 (Christmas Eve half-day) currently
    classifies as REGULAR continuous because half-day calendar is not encoded.
    When half-day calendar lands, this test should assert CLOSED post-13:00."""
    dt = _dt(2026, 12, 24, 13, 30, "America/New_York")  # Thursday
    # Current (intentional) behavior: regular classification, NOT half-day-aware
    assert classify_session("NYSE", dt) == (MarketSession.REGULAR, SessionPhase.CONTINUOUS)


def test_cme_holiday_currently_regular_classification():
    """DEFERRED: weekday US holiday (e.g. New Year's Day Thursday 2026-01-01)
    currently classifies as REGULAR continuous because holiday calendar is not
    encoded. When holiday calendar lands, this test should assert CLOSED."""
    dt_weekday_holiday = _dt(2026, 1, 1, 10, 0, "America/Chicago")  # New Year's Day, Thursday
    # Current (intentional) behavior: regular classification
    assert classify_session("CME", dt_weekday_holiday) == (
        MarketSession.REGULAR,
        SessionPhase.CONTINUOUS,
    )
