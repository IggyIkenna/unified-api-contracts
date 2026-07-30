"""Trading-calendar SSOT — US market holidays + helpers.

Mirrors the sports-source-coverage pattern in
``unified_api_contracts.canonical.domain.sports.league_data`` (where
``clip_dates_to_source_coverage`` is an SSOT-level helper consumed by both
the orchestrator pre-flight skip and the data-status denominator).

For TradFi the equivalent registry of "we know this isn't a real
trading day" is the :data:`US_MARKET_HOLIDAYS` frozenset below plus
the weekday filter implemented in :func:`clip_dates_to_trading_days`.
``VenueMapping`` references the same set on the class side so a single
source of truth covers both call paths.

Consumers
---------
* ``market_tick_data_service.engine.orchestrator`` — pre-skips
  non-trading days at the venue-filter stage so the adapter never gets
  hit on a known holiday and no ``empty_confirmed`` manifest row gets
  written.
* ``deployment_api.services.data_status_service`` —
  ``_mtds_expected_dates_for_venue_dt`` calls
  :meth:`VenueMapping.get_expected_trading_dates` directly; that method
  in turn references :data:`US_MARKET_HOLIDAYS`, so any extension here
  propagates automatically.
* Ad-hoc probes (e.g. ``/tmp/tradfi_mvp_full_granular.py``) call
  :func:`clip_dates_to_trading_days` to compute honest expected
  denominators without re-implementing weekday/holiday logic.

Update annually — Good Friday tracks the moveable Easter date;
Juneteenth federal observance from 2021. Source: NYSE / NASDAQ official
holiday calendars; mirrors ``pandas_market_calendars.XNYS`` and
``CBOE_Index_Options``.
"""

from __future__ import annotations

import pandas as pd

from .market_data_categories import VENUE_TO_ASSET_GROUP

# fmt: off
# US market holidays — TradFi venues (NYSE/NASDAQ/CBOE-Index) and
# Polymarket UP_DOWN markets on traditional instruments don't list /
# don't trade on these days. SSOT — :class:`VenueMapping` references
# this set as its ``_US_MARKET_HOLIDAYS`` field so the holiday list is
# defined here exactly once.
US_MARKET_HOLIDAYS: frozenset[str] = frozenset({
    # 2020
    "2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10", "2020-05-25",
    "2020-07-03", "2020-09-07", "2020-11-26", "2020-12-25",
    # 2021
    "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31",
    "2021-07-05", "2021-09-06", "2021-11-25", "2021-12-24",
    # 2022
    "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20",
    "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26",
    # 2023
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29",
    "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    # 2025
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    # 2027
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
    "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
    # 2028  (Jan 1 falls Sat → no NYSE observance; 9 holidays this year)
    "2028-01-17", "2028-02-21", "2028-04-14", "2028-05-29", "2028-06-19",
    "2028-07-04", "2028-09-04", "2028-11-23", "2028-12-25",
})

# tradfi venues that are NOT equity/futures exchanges and therefore do NOT
# follow the NYSE/NASDAQ trading calendar, even though they share the
# 'tradfi' asset_group for routing purposes. FRED (Federal Reserve Economic
# Data) publishes on the federal government's own release schedule, not the
# stock market's — e.g. Good Friday closes NYSE but is NOT a federal holiday,
# so FRED series can have real observations on a date this SSOT's
# US_MARKET_HOLIDAYS would otherwise skip. Added 2026-07-30 after the FRED
# backfill's own smoke test caught it live: 2024-01-01 (the one date that
# happens to be a genuine federal holiday too) got silently stamped
# EXPECTED_HOLIDAY with zero fetch attempt, via the blanket
# asset_group=='tradfi' check below — harmless for that specific date, but
# the SAME mechanism would wrongly skip Good-Friday-class dates across the
# full 1962-2026 backfill window. See
# unified-trading-pm/plans/active/issues/macro_micro_econ_data_capture_audit_2026_06_05.md.
CALENDAR_EXEMPT_TRADFI_VENUES: frozenset[str] = frozenset({"FRED"})

# Prediction-market shards tied to traditional financial instruments —
# these only trade on US equity weekdays (no UP_DOWN market on weekends
# because the underlying doesn't move). Crypto shards trade 24/7.
WEEKDAY_ONLY_PREDICTION_SHARDS: frozenset[str] = frozenset({
    "POLYMARKET:SPX", "POLYMARKET:DJIA", "POLYMARKET:NDX",
    "POLYMARKET:CRUDE_OIL", "POLYMARKET:GOLD", "POLYMARKET:SILVER",
    "POLYMARKET:DAX", "POLYMARKET:FTSE", "POLYMARKET:NIKKEI",
    "POLYMARKET:HANG_SENG", "POLYMARKET:RUSSELL_2000",
    # Individual stocks
    "POLYMARKET:AAPL", "POLYMARKET:TSLA", "POLYMARKET:NVDA",
    "POLYMARKET:META", "POLYMARKET:MSFT", "POLYMARKET:GOOGL",
    "POLYMARKET:NFLX", "POLYMARKET:PLTR", "POLYMARKET:AMZN",
    "POLYMARKET:AMD",
})
# fmt: on


def get_us_market_holidays() -> frozenset[str]:
    """Return the frozenset of US-market-holiday ISO dates (read-only).

    Exposed for tooling (granular probes, audit scripts) that wants to
    cross-reference manifest rows against the SSOT.
    """
    return US_MARKET_HOLIDAYS


def _venue_excludes_weekends_holidays(venue: str) -> bool:
    """True if ``venue`` follows the US-equity weekday-and-holiday calendar.

    TradFi venues (asset_group=='tradfi') and the prediction-market
    shards in :data:`WEEKDAY_ONLY_PREDICTION_SHARDS` exclude weekends +
    US market holidays. Crypto venues trade 24/7. :data:`CALENDAR_EXEMPT_TRADFI_VENUES`
    carves out tradfi-routed venues (e.g. FRED) whose real-world release
    calendar is NOT the equity-market calendar — never gate them here.
    """
    if venue in CALENDAR_EXEMPT_TRADFI_VENUES:
        return False
    asset_group = VENUE_TO_ASSET_GROUP.get(venue, "")
    return asset_group == "tradfi" or venue in WEEKDAY_ONLY_PREDICTION_SHARDS


def clip_dates_to_trading_days(venue: str, start: str, end: str) -> list[str]:
    """Return the ordered list of trading-day ``YYYY-MM-DD`` strings in
    ``[start, end]`` inclusive for ``venue``.

    TradFi venues (asset_group ``tradfi``) and US-equity-tied prediction
    shards exclude weekends + :data:`US_MARKET_HOLIDAYS`; crypto venues
    return every calendar day. SSOT for the data-status denominator and
    any ad-hoc coverage probe so naive weekday counts don't inflate the
    "missing" tally with days the venue was never open on.

    Args:
        venue: Canonical venue name.
        start: ``YYYY-MM-DD`` (inclusive).
        end: ``YYYY-MM-DD`` (inclusive).

    Returns:
        List of ``YYYY-MM-DD`` strings (chronological).
    """
    all_dates = pd.date_range(start, end, freq="D")
    if _venue_excludes_weekends_holidays(venue):
        all_dates = all_dates[all_dates.weekday < 5]
        date_strs: list[str] = all_dates.strftime("%Y-%m-%d").tolist()
        return [d for d in date_strs if d not in US_MARKET_HOLIDAYS]
    return [d.strftime("%Y-%m-%d") for d in all_dates]


def is_non_trading_day(venue: str, iso_date: str) -> bool:
    """Return True if ``iso_date`` is NOT a trading day for ``venue``.

    Used by the MTDS orchestrator's pre-flight skip to avoid hitting
    Databento on weekends / US market holidays for TradFi venues — which
    would otherwise return empty and trigger an ``empty_confirmed`` row
    that pollutes coverage stats.

    For crypto venues (``cefi`` / ``defi`` / ``prediction`` crypto shards)
    this always returns False — those markets trade 24/7. Only TradFi
    venues and US-equity-tied prediction shards exclude weekends +
    holidays.

    Args:
        venue: Canonical venue name (``"CBOE"``, ``"CME"``, ``"NASDAQ"``,
            ``"BINANCE"``, ``"POLYMARKET:SPX"`` …).
        iso_date: ``YYYY-MM-DD``.

    Returns:
        True if the date is a known weekend / US market holiday for this
        venue (caller should skip without writing a manifest row); False
        if the date IS a trading day or the venue is unknown / 24/7.
    """
    if not _venue_excludes_weekends_holidays(venue):
        return False
    weekday = pd.Timestamp(iso_date).weekday()
    if weekday >= 5:
        return True
    return iso_date in US_MARKET_HOLIDAYS


def non_trading_day_reason(venue: str, iso_date: str) -> str | None:
    """Return the EXPECTED_* reason for a non-trading day, or None if trading.

    Discriminates ``EXPECTED_WEEKEND`` (Sat/Sun for closed-on-weekends venues)
    from ``EXPECTED_HOLIDAY`` (US-market-holiday weekday). Returns None for
    venues that are NOT calendar-bound (24/7 crypto / DeFi / prediction
    crypto shards) and for trading days on calendar-bound venues.

    Used by orchestrator pre-skip sites (MTDS / instruments-service) to feed
    ``ManifestWriter.record_expected_empty(reason=...)`` per writegate Phase
    2.E.2 so the manifest carries an EXPECTED_* row per (shard_key, day) in
    the expected universe instead of a bare empty_confirmed.
    """
    if not _venue_excludes_weekends_holidays(venue):
        return None
    weekday = pd.Timestamp(iso_date).weekday()
    if weekday >= 5:
        return "EXPECTED_WEEKEND"
    if iso_date in US_MARKET_HOLIDAYS:
        return "EXPECTED_HOLIDAY"
    return None
