"""Venue-session-hours SSOT — per-(venue, weekday) UTC open/close timestamp ranges.

Per writegate Phase 3.D.5 / wave3x_residual_ssots Track A. The ``EmptyConfirmedReason``
enum member ``EXPECTED_OUTSIDE_TRADING_HOURS`` (UAC ``honest_coverage.py`` line 114) names
this module by path; the classifier (``unified_trading_library.legacy_reason_classifier``)
reads :data:`VENUE_SESSION_HOURS` to fire that reason on intraday shards whose timestamp
falls outside the venue's published session for that weekday.

Distinct from :mod:`session_times` which carries per-venue session rules in a different
shape (``SessionWindow`` dataclass with optional cross-midnight wrap). This module exposes
a flat dict keyed by ``(venue, weekday_iso_0_to_6)`` with already-resolved UTC times so
the classifier (and any audit tool) can do a constant-time lookup without re-deriving DST
or weekday-specific overrides.

The flat dict is the right shape for the reason-classifier hot path (one lookup per
shard); the richer dataclass in ``session_times`` remains the right shape for the MTDS
orchestrator that needs to compute per-day open/close datetimes given a target date. Both
modules co-exist; this is NOT double-SSOT — they serve different read patterns.

Half-day shortening: when a calendar date is in
:data:`unified_api_contracts.registry.half_day_sessions.HALF_DAY_SESSIONS` the published
close time is earlier than the normal weekday close. The classifier composes:
``is_within_venue_session_hours`` checks the normal hours; for half-day dates the caller
should additionally narrow the close time per the published early-close calendar (varies
by event — Black Friday closes 13:00 ET on US equities, Christmas Eve 13:00 ET, etc.).
This module returns the NORMAL session window; half-day adjustments are the caller's
responsibility because they vary by year / event.

Sources of truth (published exchange trading-hours pages):

* CME GLBX (electronic): https://www.cmegroup.com/markets/equities.html (Sun 17:00 CT
  open through Fri 16:00 CT close, with daily 16:00-17:00 maintenance break).
* NYSE / NASDAQ regular session: https://www.nyse.com/markets/hours-calendars
  (09:30-16:00 ET = 13:30-20:00 UTC during EDT / 14:30-21:00 UTC during EST).
* CBOE VIX intraday: https://www.cboe.com/tradable_products/vix/
  (08:30-15:15 CT = 13:30-20:15 UTC during CDT). Note: extended hours run beyond this.
* Eurex (DTB): https://www.eurex.com/ex-en/trade/trading-calendar
  (08:00-22:00 CET for futures, longer for options).

24/7 venues (CeFi spot/perp, DeFi protocols, sports/prediction sources) skip this module
entirely — the helpers below return ``True`` (always within session) for any venue not in
the registry, matching the ``session_times.is_trading_hours`` 24/7 default.
"""

from __future__ import annotations

from datetime import UTC, datetime, time

# Type alias for the flat-keyed registry — (venue_uppercase, iso_weekday_0_to_6_mon_to_sun)
# → (open_utc, close_utc). Cross-midnight sessions (CME futures Sun-evening through
# Fri-evening) use multiple weekday entries with the appropriate slice; the caller
# composes them.
_VenueWeekdayKey = tuple[str, int]
_VenueWeekdayValue = tuple[time, time]

# fmt: off
# US equity / index venues — NYSE / NASDAQ / CBOE / NYSE Arca / AMEX. Regular session
# 09:30-16:00 ET. Times here are UTC under EDT (UTC-4); during EST (UTC-5) the same local
# 09:30-16:00 is 14:30-21:00 UTC. We seed UTC times under EDT (the more common case across
# most of the trading year — Mar to Nov); callers needing exact DST-corrected times should
# consume :func:`unified_api_contracts.registry.session_times.get_session_times` instead
# (which uses ``zoneinfo`` for DST). The classifier's "outside-trading-hours" check is
# coarse-grained — a ±1h DST drift at session-boundary minutes is acceptable noise (the
# alternative reasons EXPECTED_HOLIDAY / EXPECTED_WEEKEND fire first for the bigger gaps).
_NYSE_OPEN = time(13, 30, tzinfo=UTC)   # 09:30 EDT
_NYSE_CLOSE = time(20, 0, tzinfo=UTC)   # 16:00 EDT

# CBOE VIX intraday: 08:30-15:15 CT during CDT = 13:30-20:15 UTC.
_CBOE_OPEN = time(13, 30, tzinfo=UTC)
_CBOE_CLOSE = time(20, 15, tzinfo=UTC)

# CME Globex futures (GLBX.MDP3): Sun 17:00 CT through Fri 16:00 CT with daily 16:00-17:00
# CT maintenance break. CDT (Mar-Nov) → 22:00 UTC open, 21:00 UTC close + maintenance.
# Per-weekday split: Sun 22:00-23:59:59, Mon-Thu 00:00-21:00 + 22:00-23:59:59, Fri 00:00-21:00.
_CME_PRE_MIDNIGHT = (time(22, 0, tzinfo=UTC), time(23, 59, 59, tzinfo=UTC))
_CME_POST_MIDNIGHT = (time(0, 0, tzinfo=UTC), time(21, 0, tzinfo=UTC))

# Eurex regular hours: 08:00-22:00 CET = 06:00-20:00 UTC during CET (Oct-Mar) / 07:00-20:00
# UTC during CEST (Mar-Oct). Seeded for CEST (more common case).
_EUREX_OPEN = time(7, 0, tzinfo=UTC)
_EUREX_CLOSE = time(20, 0, tzinfo=UTC)
# fmt: on


# Public SSOT — (venue, iso_weekday) → (open_utc, close_utc).
# iso_weekday: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun (matches Python
# ``datetime.weekday()`` convention; differs from :func:`datetime.isoweekday` which is
# 1-7 Mon-Sun. Using 0-6 to match the standard ``.weekday()`` callers).
# Saturday and Sunday entries are OMITTED for venues that close on weekends — callers
# should treat absence-from-dict as "venue closed this weekday" (composes with the
# closed-on-weekends rule from :mod:`venue_trading_calendar`).
VENUE_SESSION_HOURS: dict[_VenueWeekdayKey, _VenueWeekdayValue] = {}

# Seed US equity venues (NYSE / NASDAQ / CBOE / NYSE Arca / AMEX) — Mon-Fri only.
for _venue in ("NYSE", "NASDAQ", "NYSE_ARCA", "AMEX"):
    for _wd in range(5):  # Mon-Fri (0-4)
        VENUE_SESSION_HOURS[(_venue, _wd)] = (_NYSE_OPEN, _NYSE_CLOSE)

for _wd in range(5):
    VENUE_SESSION_HOURS[("CBOE", _wd)] = (_CBOE_OPEN, _CBOE_CLOSE)

# CME GLBX — split into pre-midnight + post-midnight per weekday.
# Sun 22:00 UTC open through Fri 21:00 UTC close.
# We model the "primary" daily window per weekday (the post-midnight window for Mon-Fri,
# the pre-midnight window for Sun). Callers needing the full session shape should consume
# :mod:`session_times` which has the cross-midnight wrap dataclass.
VENUE_SESSION_HOURS[("CME", 6)] = _CME_PRE_MIDNIGHT  # Sun 22:00-23:59:59 UTC
for _wd in range(5):  # Mon-Fri post-midnight window
    VENUE_SESSION_HOURS[("CME", _wd)] = _CME_POST_MIDNIGHT
# Mon-Thu also have a pre-midnight window (post-maintenance reopen 22:00 UTC). The flat
# dict can only carry ONE tuple per key; the classifier composes the post-midnight tuple
# with the pre-midnight CME constant when checking late-evening shards. For boundary
# correctness use :mod:`session_times` (its ``is_trading_hours`` handles the wrap).

# Aliases for venues that share a calendar.
for _wd in range(5):
    VENUE_SESSION_HOURS[("ICE", _wd)] = (_NYSE_OPEN, _NYSE_CLOSE)
    VENUE_SESSION_HOURS[("FX", _wd)] = _CME_POST_MIDNIGHT
VENUE_SESSION_HOURS[("FX", 6)] = _CME_PRE_MIDNIGHT

# Eurex / DTB — Mon-Fri 07:00-20:00 UTC (CEST seed).
for _venue in ("EUREX", "DTB"):
    for _wd in range(5):
        VENUE_SESSION_HOURS[(_venue, _wd)] = (_EUREX_OPEN, _EUREX_CLOSE)


def is_within_venue_session_hours(venue: str, ts: datetime) -> bool:
    """Return True if ``ts`` (UTC) falls within ``venue``'s published session hours.

    Returns ``True`` for venues NOT in :data:`VENUE_SESSION_HOURS` (24/7 crypto / DeFi /
    sports / prediction venues are always "in session" — match
    :func:`session_times.is_trading_hours` 24/7 default).

    Returns ``False`` for venues in the registry where:

    * The shard's weekday has no entry (closed-on-weekends venue, weekend day) — caller
      should typically use :func:`venue_trading_calendar.is_non_trading_day` first to
      catch this with the more specific ``EXPECTED_WEEKEND`` reason.
    * The shard's UTC time-of-day falls outside the seeded ``(open_utc, close_utc)``
      window for that weekday.

    For CME-style cross-midnight sessions the post-midnight window (Mon-Fri 00:00-21:00
    UTC) is the seeded entry; the pre-midnight window (Sun-Thu 22:00-23:59:59 UTC) needs
    a second check the caller composes by querying ``(venue, prior_weekday)`` against the
    pre-midnight constants. For exact boundary correctness use
    :func:`unified_api_contracts.registry.session_times.is_trading_hours` instead — that
    function handles the wrap natively via the ``SessionWindow`` dataclass.

    Args:
        venue: Canonical UPPERCASE venue name.
        ts: Timestamp to check. Naive datetimes are treated as UTC.

    Returns:
        True if within session, False if outside.
    """
    venue_upper = venue.upper()
    ts = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)

    weekday = ts.weekday()  # 0=Mon..6=Sun
    key: _VenueWeekdayKey = (venue_upper, weekday)
    window = VENUE_SESSION_HOURS.get(key)
    if window is None:
        # Venue not in registry → 24/7 default. Closed-on-this-weekday on a registry venue
        # is also caught here; caller should pre-filter via venue_trading_calendar for the
        # more-specific EXPECTED_WEEKEND reason.
        return bool(not _venue_is_registered(venue_upper))

    open_utc, close_utc = window
    ts_time = ts.timetz()
    return open_utc <= ts_time < close_utc


def get_session_window(venue: str, weekday: int) -> _VenueWeekdayValue | None:
    """Return the ``(open_utc, close_utc)`` tuple for ``(venue, weekday)``, or None.

    None means either (a) the venue is not in :data:`VENUE_SESSION_HOURS` (treat as
    24/7), or (b) the venue is registered but this weekday has no session (typically a
    closed-on-weekends venue queried for Sat/Sun). Callers MUST distinguish these two
    cases via :func:`is_venue_registered` if they need to.

    Args:
        venue: Canonical UPPERCASE venue name.
        weekday: ISO weekday 0-6 (0=Mon..6=Sun, matching ``datetime.weekday()``).

    Returns:
        ``(open_utc, close_utc)`` tuple of ``datetime.time`` (UTC tz-aware), or None.
    """
    return VENUE_SESSION_HOURS.get((venue.upper(), weekday))


def is_venue_registered(venue: str) -> bool:
    """Return True if ``venue`` has any entry in :data:`VENUE_SESSION_HOURS`.

    Distinguishes "venue is 24/7 (no entries needed)" from "venue is registered but
    closed on this specific weekday." Used by classifiers that need to fire the right
    reason (24/7 → no EXPECTED_OUTSIDE_TRADING_HOURS ever; registered → fire on the
    right weekdays only).

    Args:
        venue: Canonical UPPERCASE venue name.

    Returns:
        True if any ``(venue, weekday)`` key is in the registry.
    """
    return _venue_is_registered(venue.upper())


def _venue_is_registered(venue_upper: str) -> bool:
    """Internal helper: True if any weekday entry exists for the upper-cased venue."""
    return any(key[0] == venue_upper for key in VENUE_SESSION_HOURS)
