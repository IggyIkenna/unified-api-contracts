"""TradFi market-session SSOT — enums + per-venue session schedule registry.

Cross-cutting closed sets for venue session classification. Every TradFi bar /
tick MUST be stamped with both `session: MarketSession` and `phase: SessionPhase`
at write-time, per CLAUDE.md "batch=live unified pipeline" rule.

## Why this exists

Pre-market / post-market / overnight bars behave very differently from regular-
session bars (different volume curves, different microstructure, different
liquidity baselines). Without a session-type axis, downstream consumers conflate
these regimes — features fit on regular-session distributions but include
overnight thin-volume rows in training data; strategies place orders in
pre-market by accident; liquidity baselines mix regimes.

## Architecture

- `MarketSession` (closed set, 6 values): regime axis
- `SessionPhase` (closed set, 5 values): intra-session phase axis
- `SessionWindow`: dataclass holding (session, phase, weekday_mask, start_time,
  end_time, tz)
- `VENUE_SESSION_SCHEDULE: dict[str, list[SessionWindow]]`: per-venue windows
  in priority order (more specific windows first; first match wins)
- `classify_session(venue, dt)`: returns `(session, phase)` for any timestamp

Schedules sourced from each venue's own published docs (CME Globex hours, NYSE
trading sessions, Nasdaq, ICE Futures, CBOE). Per-venue PRs land iteratively;
the enum SSOT is the gate-keeper, schedules backfill behind.

## Coordination

- Cross-plan banner: liquidity baselines (mdps_liquidity_baseline_and_live_tick
  _staleness_2026_05_08) MUST be axis-typed by `session` — landing baseline
  computation without session-axis is a known bug class.
- Downstream consumers (features-*, strategy-service allowed_sessions,
  execution-service `OutOfSessionOrderError`) wire in parallel; no need to gate
  them on full venue coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class MarketSession(StrEnum):
    """Closed-set session-regime classification.

    Values represent the regime a venue is in at a given timestamp. Used as a
    column axis on every TradFi bar / tick row + as a filter axis on features-*
    + strategy-service `allowed_sessions`.
    """

    REGULAR = "regular"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    OVERNIGHT = "overnight"
    HALTED = "halted"
    CLOSED = "closed"


class SessionPhase(StrEnum):
    """Closed-set intra-session phase classification.

    Phases are sub-divisions of a session — e.g. the opening auction is a
    distinct phase within `REGULAR` session with different microstructure
    (single-price auction vs continuous matching).
    """

    OPEN_AUCTION = "open_auction"
    CONTINUOUS = "continuous"
    CLOSE_AUCTION = "close_auction"
    AFTER_HOURS_AUCTION = "after_hours_auction"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class SessionWindow:
    """A single (session, phase) time window for a venue.

    Windows are evaluated in the order they appear in `VENUE_SESSION_SCHEDULE`;
    the first window whose (weekday, time-of-day, tz) matches a given timestamp
    wins. Cross-midnight windows (e.g. CME Globex 17:00 Sun → 16:00 Mon) are
    represented with `end_time < start_time` semantically meaning "wraps next
    day" — `_in_window()` handles the wrap correctly.

    Attributes:
        session: The regime this window represents.
        phase: The intra-session phase.
        weekday_mask: Set of weekday indices (0=Monday, 6=Sunday) on which this
            window applies. Use frozenset for hashability.
        start_time: Local start time (in `tz`).
        end_time: Local end time (in `tz`). May be < start_time for cross-
            midnight windows; in that case the window applies from start_time
            on weekday W until end_time on weekday W+1.
        tz: IANA timezone name (e.g. "America/Chicago", "America/New_York",
            "Europe/London").
    """

    session: MarketSession
    phase: SessionPhase
    weekday_mask: frozenset[int]
    start_time: time
    end_time: time
    tz: str


# ---------------------------------------------------------------------------
# Per-venue session schedules
# ---------------------------------------------------------------------------
# Sourced from each venue's own published docs. Half-day / holiday / DST
# adjustments are NOT encoded here — they require operator confirmation on a
# per-case basis (see DEFERRED notes below). Regular-week schedule only.

# Common weekday masks
_MON_FRI = frozenset({0, 1, 2, 3, 4})
_MON_THU = frozenset({0, 1, 2, 3})  # Sunday-evening through Thursday-evening Globex sessions
_SUN_THU = frozenset({6, 0, 1, 2, 3})
_SUN = frozenset({6})

# Timezone constants
_TZ_CT = "America/Chicago"  # CME Globex
_TZ_ET = "America/New_York"  # NYSE / Nasdaq / ICE NY / CBOE
_TZ_LONDON = "Europe/London"  # ICE Brent (informational; not encoded yet)


VENUE_SESSION_SCHEDULE: dict[str, list[SessionWindow]] = {
    # ─────────────────────────────────────────────────────────────────────
    # CME Globex (futures: ES, NQ, CL, GC, etc.)
    #
    # Source: https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.html
    # Globex trading hours: Sunday 17:00 CT → Friday 16:00 CT with a daily
    # 60-minute maintenance break 16:00-17:00 CT Mon-Thu.
    #
    # Within each session, CME treats the bulk of time as CONTINUOUS regular
    # trading. There is no explicit pre/post-market split for futures —
    # everything outside the maintenance window is REGULAR.
    # ─────────────────────────────────────────────────────────────────────
    "CME": [
        # Sunday evening open: 17:00 CT Sun → 00:00 CT Mon (cross-midnight)
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_SUN,
            start_time=time(17, 0),
            end_time=time(23, 59, 59),
            tz=_TZ_CT,
        ),
        # Mon-Thu: 00:00-16:00 CT (regular) + 17:00-23:59 CT (regular continued)
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_THU,
            start_time=time(0, 0),
            end_time=time(16, 0),
            tz=_TZ_CT,
        ),
        # Mon-Thu maintenance window: 16:00-17:00 CT
        SessionWindow(
            session=MarketSession.CLOSED,
            phase=SessionPhase.NONE,
            weekday_mask=_MON_THU,
            start_time=time(16, 0),
            end_time=time(17, 0),
            tz=_TZ_CT,
        ),
        # Mon-Thu post-maintenance reopen: 17:00-23:59 CT
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_THU,
            start_time=time(17, 0),
            end_time=time(23, 59, 59),
            tz=_TZ_CT,
        ),
        # Friday: 00:00-16:00 CT (regular), close at 16:00 CT for the week
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=frozenset({4}),
            start_time=time(0, 0),
            end_time=time(16, 0),
            tz=_TZ_CT,
        ),
    ],
    # ─────────────────────────────────────────────────────────────────────
    # NYSE (equities: NYSE-listed common stocks, ETFs)
    #
    # Source: https://www.nyse.com/markets/hours-calendars
    # Pre-market: 04:00-09:30 ET (NYSE Arca / off-exchange ECNs)
    # Open auction: 09:30 ET (single-price match)
    # Regular continuous: 09:30-16:00 ET
    # Close auction: 16:00 ET (MOC / LOC / Closing Cross)
    # After-hours: 16:00-20:00 ET
    # ─────────────────────────────────────────────────────────────────────
    "NYSE": [
        SessionWindow(
            session=MarketSession.PRE_MARKET,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(4, 0),
            end_time=time(9, 30),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.OPEN_AUCTION,
            weekday_mask=_MON_FRI,
            start_time=time(9, 30),
            end_time=time(9, 30, 30),  # 30-second auction window approximation
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(9, 30, 30),
            end_time=time(15, 50),
            tz=_TZ_ET,
        ),
        # Close auction begins at 15:50 ET (imbalance feed cutoff)
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CLOSE_AUCTION,
            weekday_mask=_MON_FRI,
            start_time=time(15, 50),
            end_time=time(16, 0),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.POST_MARKET,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(16, 0),
            end_time=time(20, 0),
            tz=_TZ_ET,
        ),
    ],
    # ─────────────────────────────────────────────────────────────────────
    # Nasdaq (equities: Nasdaq-listed common stocks, ETFs)
    #
    # Source: https://www.nasdaq.com/market-activity/stock-market-trading-hours
    # Same as NYSE for pre/regular/post; Nasdaq Closing Cross runs at 16:00 ET.
    # ─────────────────────────────────────────────────────────────────────
    "NASDAQ": [
        SessionWindow(
            session=MarketSession.PRE_MARKET,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(4, 0),
            end_time=time(9, 30),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.OPEN_AUCTION,
            weekday_mask=_MON_FRI,
            start_time=time(9, 30),
            end_time=time(9, 30, 30),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(9, 30, 30),
            end_time=time(15, 50),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CLOSE_AUCTION,
            weekday_mask=_MON_FRI,
            start_time=time(15, 50),
            end_time=time(16, 0),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.POST_MARKET,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(16, 0),
            end_time=time(20, 0),
            tz=_TZ_ET,
        ),
    ],
    # ─────────────────────────────────────────────────────────────────────
    # ICE Futures US (NY) — energy + softs (e.g. WTI, BRN-CSO, sugar)
    #
    # Source: https://www.theice.com/products/Futures-Options/Energy
    # For NY-traded energy contracts: Sunday 18:00 ET → Friday 17:00 ET with
    # a daily 60-minute settlement break around 17:00-18:00 ET.
    #
    # ICE Brent (London) runs different hours (Europe/London tz) — DEFERRED
    # pending operator confirmation for the canonical Brent schedule.
    # ─────────────────────────────────────────────────────────────────────
    "ICE": [
        # Sunday evening open: 18:00 ET Sun → 23:59:59 ET Sun
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_SUN,
            start_time=time(18, 0),
            end_time=time(23, 59, 59),
            tz=_TZ_ET,
        ),
        # Mon-Thu: 00:00-17:00 ET (regular continued)
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_THU,
            start_time=time(0, 0),
            end_time=time(17, 0),
            tz=_TZ_ET,
        ),
        # Mon-Thu settlement break: 17:00-18:00 ET
        SessionWindow(
            session=MarketSession.CLOSED,
            phase=SessionPhase.NONE,
            weekday_mask=_MON_THU,
            start_time=time(17, 0),
            end_time=time(18, 0),
            tz=_TZ_ET,
        ),
        # Mon-Thu post-break reopen: 18:00-23:59 ET
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_THU,
            start_time=time(18, 0),
            end_time=time(23, 59, 59),
            tz=_TZ_ET,
        ),
        # Friday: 00:00-17:00 ET, close at 17:00 ET for the week
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=frozenset({4}),
            start_time=time(0, 0),
            end_time=time(17, 0),
            tz=_TZ_ET,
        ),
    ],
    # ─────────────────────────────────────────────────────────────────────
    # CBOE (VIX options + SPX options)
    #
    # Source: https://www.cboe.com/about/hours/
    # SPX/VIX options have an overnight Global Trading Hours session:
    #   02:15-09:15 ET Mon-Fri (overnight session, thin liquidity)
    # Regular session:
    #   09:30-16:15 ET Mon-Fri (SPX/VIX close at 16:15 — later than equities)
    # ─────────────────────────────────────────────────────────────────────
    "CBOE": [
        SessionWindow(
            session=MarketSession.OVERNIGHT,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(2, 15),
            end_time=time(9, 15),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.OPEN_AUCTION,
            weekday_mask=_MON_FRI,
            start_time=time(9, 30),
            end_time=time(9, 30, 30),
            tz=_TZ_ET,
        ),
        SessionWindow(
            session=MarketSession.REGULAR,
            phase=SessionPhase.CONTINUOUS,
            weekday_mask=_MON_FRI,
            start_time=time(9, 30, 30),
            end_time=time(16, 15),
            tz=_TZ_ET,
        ),
    ],
}

# ---------------------------------------------------------------------------
# DEFERRED — needs operator confirmation
# ---------------------------------------------------------------------------
# - **CME half-day rollover** (e.g. Christmas Eve, Black Friday): CME closes at
#   12:00 CT for index futures on certain US holidays. Currently NOT encoded —
#   classify_session() returns the regular-week classification on these days.
#   Need explicit half-day calendar.
# - **NYSE / Nasdaq half-days**: 13:00 ET early close on day after Thanksgiving
#   + Christmas Eve. NOT encoded.
# - **ICE Brent (London)** session schedule: needs operator confirmation
#   (Europe/London tz, different boundaries). Currently absent from registry.
# - **Auction phase boundaries**: opening / closing auction window durations
#   are approximations (30s window). True boundaries are venue-specific imbalance
#   feed cutoffs and may be off by 1-2 minutes. Acceptable for classification
#   coarseness; not acceptable for auction microstructure features.


# ---------------------------------------------------------------------------
# Classification helper
# ---------------------------------------------------------------------------


def _in_window(window: SessionWindow, local_dt: datetime) -> bool:
    """Return True if `local_dt` falls within `window`.

    Handles cross-midnight windows: if `end_time < start_time`, the window is
    interpreted as start_time today through end_time tomorrow.
    """
    wd = local_dt.weekday()
    t = local_dt.time()

    if window.end_time >= window.start_time:
        # Same-day window
        if wd not in window.weekday_mask:
            return False
        return window.start_time <= t < window.end_time

    # Cross-midnight window — split into two same-day checks
    # Part A: start_time → end of day on weekday W
    if wd in window.weekday_mask and t >= window.start_time:
        return True
    # Part B: start of day → end_time on weekday W+1
    prev_wd = (wd - 1) % 7
    return prev_wd in window.weekday_mask and t < window.end_time


def classify_session(venue: str, dt: datetime) -> tuple[MarketSession, SessionPhase]:
    """Classify a UTC timestamp into (session, phase) for the given venue.

    Args:
        venue: Venue code matching a key in `VENUE_SESSION_SCHEDULE`
            (e.g. "CME", "NYSE", "NASDAQ", "ICE", "CBOE").
        dt: Timezone-aware datetime (any tz; will be converted to venue-local).

    Returns:
        Tuple of `(MarketSession, SessionPhase)`. If `dt` falls outside every
        window in the venue's schedule, returns `(CLOSED, NONE)`.

    Raises:
        ValueError: If `venue` is not in the registry or `dt` is naive.
    """
    if dt.tzinfo is None:
        raise ValueError(f"classify_session requires tz-aware datetime; got naive {dt}")

    if venue not in VENUE_SESSION_SCHEDULE:
        raise ValueError(f"Unknown venue {venue!r}; known venues: {sorted(VENUE_SESSION_SCHEDULE.keys())}")

    windows = VENUE_SESSION_SCHEDULE[venue]
    # All windows in a venue use the same tz; pick the first window's tz.
    tz_name = windows[0].tz
    local_dt = dt.astimezone(ZoneInfo(tz_name))

    for window in windows:
        if _in_window(window, local_dt):
            return (window.session, window.phase)

    return (MarketSession.CLOSED, SessionPhase.NONE)


__all__ = [
    "VENUE_SESSION_SCHEDULE",
    "MarketSession",
    "SessionPhase",
    "SessionWindow",
    "classify_session",
]


# Suppress unused-import warning for `date` / `timedelta` which may be needed
# by downstream consumers but aren't used in this module directly.
_ = (date, timedelta)
