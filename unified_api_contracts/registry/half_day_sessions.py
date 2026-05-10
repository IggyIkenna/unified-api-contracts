"""Half-day-session SSOT — calendar dates with shortened trading sessions.

Per writegate Phase 3.D.5 / wave3x_residual_ssots Track A. The ``EmptyConfirmedReason``
enum member ``EXPECTED_PARTIAL_HALF_DAY`` (UAC ``honest_coverage.py`` line 109) names this
module by path; the classifier (``unified_trading_library.legacy_reason_classifier``) reads
:data:`HALF_DAY_SESSIONS` to fire that reason on shards that fall on a published half-day.

Distinct from :mod:`venue_trading_calendar` (which lists FULL-day closures —
``US_MARKET_HOLIDAYS``); a half-day is a shortened-but-open session, not a closed day.
A shard whose timestamps fall WITHIN the shortened session window stays
``capture_status=captured``; a shard for the half-day that finds zero source rows gets
``empty_confirmed[reason=EXPECTED_PARTIAL_HALF_DAY]`` instead of the generic
``SOURCE_RETURNED_ZERO``.

Sources of truth (published exchange holiday calendars):

* CME holiday schedule: https://www.cmegroup.com/tools-information/holiday-calendar.html
* NYSE / NASDAQ holiday schedule: https://www.nyse.com/markets/hours-calendars
* CBOE holiday schedule: https://www.cboe.com/us/options/holidays/
* Eurex holiday schedule: https://www.eurex.com/ex-en/trade/trading-calendar

US equity / index venues share the same half-day list (NYSE / NASDAQ / CBOE / NYSE Arca).
CME futures runs an early-close on the same calendar dates with venue-specific close times.

Update annually — Black Friday tracks Thanksgiving (4th Thursday of November); July 3rd is
half-day when Independence Day (July 4) falls on a non-weekend trading day; Christmas Eve
(December 24) is half-day when it's a non-weekend trading day.

Composes with:

* :func:`unified_api_contracts.registry.venue_trading_calendar.is_non_trading_day` —
  full-day closure check; this module only fires when that returns False AND the day is
  on the half-day list.
* :func:`unified_api_contracts.registry.venue_session_hours.is_within_venue_session_hours`
  — intra-day session check; on a half-day the session window is shortened (the venue
  closes earlier) so the per-day open/close pair effectively narrows.
"""

from __future__ import annotations

from datetime import date

# fmt: off
# US equity / index venues — NYSE, NASDAQ, CBOE, NYSE Arca, AMEX. All share the same
# half-day list (Black Friday + Christmas Eve eligible years + July 3rd eligible years).
# Black Friday = day after Thanksgiving (always a Friday; if Thanksgiving is the 4th
# Thursday, Black Friday is the next day). Christmas Eve = December 24 when a weekday.
# July 3rd half-day fires when July 4 is on a non-weekend day.
_US_EQUITY_HALF_DAYS: frozenset[date] = frozenset({
    # 2020
    date(2020, 11, 27),  # Black Friday
    date(2020, 12, 24),  # Christmas Eve (Thursday)
    # 2021
    date(2021, 11, 26),  # Black Friday
    # 2021-07-02 (Friday before Sunday July 4) was full day; 2021-12-24 was Friday but Christmas observance moved to it.
    # 2022
    date(2022, 11, 25),  # Black Friday
    # 2022-07-04 was Monday (full holiday); 2022-12-24 was Saturday (no half-day).
    # 2023
    date(2023, 7, 3),    # Day before July 4 (Tuesday)
    date(2023, 11, 24),  # Black Friday
    # 2023-12-24 was Sunday (no half-day; Dec 25 Monday closed full).
    # 2024
    date(2024, 7, 3),    # Day before July 4 (Wednesday)
    date(2024, 11, 29),  # Black Friday
    date(2024, 12, 24),  # Christmas Eve (Tuesday)
    # 2025
    date(2025, 7, 3),    # Day before July 4 (Thursday)
    date(2025, 11, 28),  # Black Friday
    date(2025, 12, 24),  # Christmas Eve (Wednesday)
    # 2026
    date(2026, 11, 27),  # Black Friday
    date(2026, 12, 24),  # Christmas Eve (Thursday)
    # 2027
    date(2027, 11, 26),  # Black Friday
    # 2027-07-02 was Friday before Sunday July 4 (full day); 2027-12-24 Friday (Christmas observed Friday → full close).
    # 2028
    date(2028, 7, 3),    # Day before July 4 (Monday)
    date(2028, 11, 24),  # Black Friday
})

# CME futures (Globex / GLBX.MDP3 / equity-index futures + commodities) — same half-day
# calendar as the underlying US equity venues, with venue-specific early-close times.
_CME_HALF_DAYS: frozenset[date] = _US_EQUITY_HALF_DAYS

# Eurex (DTB) — Christmas Eve and New Year's Eve are half-day-equivalent (early close).
# Black Friday is a full trading day on Eurex.
_EUREX_HALF_DAYS: frozenset[date] = frozenset({
    date(2020, 12, 24), date(2020, 12, 31),
    date(2021, 12, 24), date(2021, 12, 31),
    # 2022 Dec 24 = Saturday, Dec 31 = Saturday → no half-days.
    # 2023 Dec 24 = Sunday, Dec 31 = Sunday → no half-days.
    date(2024, 12, 24), date(2024, 12, 31),
    date(2025, 12, 24), date(2025, 12, 31),
    date(2026, 12, 24), date(2026, 12, 31),
    # 2027 Dec 24 = Friday → half-day; Dec 31 = Friday → half-day.
    date(2027, 12, 24), date(2027, 12, 31),
})
# fmt: on

# Public SSOT — venue → frozenset of half-day dates. Keys are canonical UPPERCASE venue
# names (matching :data:`unified_api_contracts.registry.session_times._EXCHANGE_SESSIONS`
# and :data:`unified_api_contracts.registry.venue_trading_calendar` conventions).
HALF_DAY_SESSIONS: dict[str, frozenset[date]] = {
    "NYSE": _US_EQUITY_HALF_DAYS,
    "NASDAQ": _US_EQUITY_HALF_DAYS,
    "CBOE": _US_EQUITY_HALF_DAYS,
    "NYSE_ARCA": _US_EQUITY_HALF_DAYS,
    "AMEX": _US_EQUITY_HALF_DAYS,
    "CME": _CME_HALF_DAYS,
    "ICE": _US_EQUITY_HALF_DAYS,  # ICE US contracts follow NYSE calendar.
    "FX": _CME_HALF_DAYS,  # FX trades on CME Globex hours.
    "EUREX": _EUREX_HALF_DAYS,
    "DTB": _EUREX_HALF_DAYS,  # DTB = Eurex.
}


def is_half_day_session(venue: str, day: date) -> bool:
    """Return True if ``day`` is a published half-day session for ``venue``.

    Half-day means the venue is OPEN but with a shortened session window (e.g. early
    close at 13:00 ET on US equity Black Friday vs the normal 16:00 ET close). On
    half-days the venue still trades — shards with timestamps within the shortened
    window get ``record_captured``; shards that find zero source rows get
    ``empty_confirmed[reason=EXPECTED_PARTIAL_HALF_DAY]`` rather than the generic
    ``SOURCE_RETURNED_ZERO``.

    Returns False for venues not in :data:`HALF_DAY_SESSIONS` (24/7 crypto / DeFi /
    sports / prediction venues never have half-days). Returns False for full-trading-day
    dates on calendar-bound venues. Returns False for full-closure dates (those are
    captured by :func:`venue_trading_calendar.is_non_trading_day` instead).

    Args:
        venue: Canonical UPPERCASE venue name (``"NYSE"``, ``"CME"``, ``"CBOE"``, …).
        day: Calendar date to check.

    Returns:
        True if ``(venue, day)`` is on the published half-day list; False otherwise.
    """
    half_days = HALF_DAY_SESSIONS.get(venue.upper())
    if half_days is None:
        return False
    return day in half_days


def get_half_day_dates(venue: str) -> frozenset[date]:
    """Return the read-only frozenset of half-day dates for ``venue``.

    Used by data-status tooling and audit scripts to cross-reference manifest rows with
    the SSOT (e.g. for the
    ``instruments-service/scripts/reconcile_legacy_blank_to_typed_reason.py`` reconciler
    per Track C of wave3x_residual_ssots).

    Returns an empty frozenset for venues with no half-day calendar (24/7 venues or
    venues not yet seeded). Callers SHOULD NOT mutate the returned set.

    Args:
        venue: Canonical UPPERCASE venue name.

    Returns:
        Frozenset of dates (possibly empty).
    """
    return HALF_DAY_SESSIONS.get(venue.upper(), frozenset())
