"""Data source continuity registry (SSOT).

Documents which data source covers which date range for each instrument/data-type pair.
Consumed by backfill scripts, feature services, and data pipeline services to know
which source to query for a given date.

── Why this file exists ──────────────────────────────────────────────────────
Several instruments have had their upstream data source change over time:
- Barchart provided VIX 15m CSV downloads; they are discontinuing this service.
- Yahoo Finance covers the last 60 days of 15m data via their history API.
- The transition creates a documented gap that no current source can fill.

Backfill scripts and downstream consumers MUST check this registry before
deciding which source to use for a given (instrument, data_type, date) tuple.

── Barchart note ─────────────────────────────────────────────────────────────
Barchart is a manual CSV download service, NOT a live API integration.
Files were downloaded and uploaded to GCS manually. Barchart is discontinuing
this offering — no new Barchart data will be available after BARCHART_VIX_LAST_DATE.
Do NOT build automated Barchart fetching; use Yahoo Finance or Databento instead.

!! KNOWN DATA GAP — VIX 15m — MANDATORY CONSUMER CONTRACT !!
─────────────────────────────────────────────────────────────
Dates from 2025-11-13 until approximately (today - 60 days) have NO 15-minute
VIX source anywhere. Neither Barchart nor Yahoo Finance covers this window:
  - Barchart ended:       2025-11-12 (service discontinued)
  - Yahoo Finance starts: today - 59 days (hard server-side rolling window)
  - FRED VIXCLS:          daily only — no intraday

get_vix_15m_source(date) returns "GAP_NO_SOURCE" for these dates.

ALL consumers MUST handle "GAP_NO_SOURCE" by returning:
  - empty DataFrame (pd.DataFrame())
  - NaN / None values
  - zero-length list

NEVER raise an exception for GAP_NO_SOURCE dates. This is expected, permanent,
and unrecoverable — the data simply does not exist at 15m granularity.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple, cast


class SourceWindow(NamedTuple):
    """A contiguous date window covered by a single data source."""

    source: str
    first_date: date
    last_date: date | None  # None = ongoing (no known end date)
    note: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# VIX 15-minute OHLCV (CBOE:INDEX:VIX-USD, data_type=ohlcv_15m)
# ──────────────────────────────────────────────────────────────────────────────

# Barchart CSV download — 12 files downloaded 2025-11-12, uploaded to dev GCS via
# market-tick-data-service/scripts/upload_vix_barchart_local.py.
# Local files: /vix/vix_intraday-15min_historical-data-*.csv (~77k bars)
BARCHART_VIX_FIRST_DATE: date = date(2020, 1, 2)
BARCHART_VIX_LAST_DATE: date = date(2025, 11, 12)
BARCHART_VIX_FILE_COUNT: int = 12  # source CSV files (each covers ~6 months)

# Yahoo Finance ^VIX — 15m interval, rolling 60-day window only.
# No fixed start date; always (today - 59 days) at earliest.
YAHOO_VIX_15M_WINDOW_DAYS: int = 60

# !! KNOWN GAP: 2025-11-13 → ~(today - 60d) — NO 15m VIX source exists !!
# This is the first date of the permanent gap. Last gap date is dynamic:
#   (today - YAHOO_VIX_15M_WINDOW_DAYS) - 1 day
# Use get_vix_15m_source(date) → "GAP_NO_SOURCE" to detect. Consumers MUST
# return empty DataFrame / NaN for gap dates. Do NOT raise.
VIX_15M_GAP_FIRST_DATE: date = date(2025, 11, 13)

VIX_15M_SOURCE_HISTORY: list[SourceWindow] = [
    SourceWindow(
        source="BARCHART_CSV",
        first_date=BARCHART_VIX_FIRST_DATE,
        last_date=BARCHART_VIX_LAST_DATE,
        note=(
            "12 Barchart CSV files (6-month chunks) downloaded 2025-11-12. "
            "Uploaded to dev GCS via scripts/upload_vix_barchart_local.py. "
            "Barchart is a manual CSV download service (not a live API) — discontinued. "
            "Time column is US/Eastern bar close time; converted to UTC nanoseconds. "
            "Schema: NautilusTrader parquet (ts_event/ts_init as int64 UTC ns)."
        ),
    ),
    SourceWindow(
        # !! KNOWN PERMANENT GAP — NO 15m VIX DATA EXISTS FOR THESE DATES !!
        # Gap duration: ~2 months as of 2026-03-20; shrinks by 1 day/day as
        # Yahoo Finance's rolling window advances. Will eventually close to 0.
        # FRED VIXCLS is daily-only — no 15m granularity available anywhere.
        # Consumers MUST return empty DataFrame / NaN. Do NOT raise.
        source="GAP_NO_SOURCE",
        first_date=VIX_15M_GAP_FIRST_DATE,  # 2025-11-13
        # last_date is dynamic: (today - YAHOO_VIX_15M_WINDOW_DAYS) - 1 day.
        # Cannot be a compile-time constant; compute at runtime via is_vix_15m_gap_date().
        last_date=None,
        note=(
            "PERMANENT GAP — NO 15m SOURCE EXISTS. "
            "Barchart ended 2025-11-12 (service discontinued). "
            "Yahoo Finance's 60-day rolling window starts ~today-59d. "
            "Only daily VIXCLS (FRED) is available for this range — no intraday. "
            "Consumers MUST return empty DataFrame / NaN, never raise."
        ),
    ),
    SourceWindow(
        source="YAHOO_FINANCE",
        # first_date is dynamic: today - 59 days. Cannot be a compile-time constant.
        # Use get_yahoo_vix_15m_start() at runtime.
        first_date=date(2026, 1, 18),  # approximate as of 2026-03-18 (today - 59d)
        last_date=None,  # ongoing
        note=(
            "Yahoo Finance ^VIX, 15m interval. Rolling 60-day window — data older "
            "than 60 days becomes unavailable. Fetch via yfinance Ticker.history(). "
            "Volume is always 0.0 (VIX is a calculated index, not traded). "
            "Timestamps are tz-aware (US/Eastern bar close time); converted to UTC "
            "nanoseconds to match Barchart ts_event/ts_init convention. "
            "Run backfill_vix_15m_yahoo.py (no --force) to append to GCS."
        ),
    ),
]


def get_vix_15m_source(query_date: date) -> str:
    """Return the canonical data source name for VIX 15m on a given date.

    Returns one of: "BARCHART_CSV", "YAHOO_FINANCE", "GAP_NO_SOURCE".

    !! MANDATORY CONSUMER CONTRACT for "GAP_NO_SOURCE" !!
    ─────────────────────────────────────────────────────
    When this function returns "GAP_NO_SOURCE", the queried date falls in the
    known permanent gap (2025-11-13 → ~today-60d) where NO 15m VIX data exists
    from ANY source.

    Callers MUST:
      - return an empty DataFrame (pd.DataFrame())
      - return NaN / None for scalar lookups
      - return [] for list-based APIs

    Callers MUST NOT:
      - raise an exception
      - retry with a different source
      - fall back to daily VIXCLS (different granularity)

    This gap is permanent and unrecoverable for 15m granularity. The only
    available data for this range is daily VIXCLS from FRED — a different
    data product not covered by this function.
    """
    today = datetime.now(UTC).date()
    yahoo_start = today - timedelta(days=YAHOO_VIX_15M_WINDOW_DAYS - 1)

    if query_date <= BARCHART_VIX_LAST_DATE:
        return "BARCHART_CSV"
    if query_date >= yahoo_start:
        return "YAHOO_FINANCE"
    return "GAP_NO_SOURCE"


def is_vix_15m_gap_date(query_date: date) -> bool:
    """Return True if query_date falls in the known VIX 15m data gap.

    The gap runs from 2025-11-13 (first date after Barchart ended) until
    approximately today - 60 days (where Yahoo Finance's rolling window begins).
    No 15m VIX data exists for gap dates from any source.

    Consumers that check this before querying can log a warning and return
    empty / NaN without needing to attempt a fetch.
    """
    return get_vix_15m_source(query_date) == "GAP_NO_SOURCE"


def get_yahoo_vix_15m_start() -> date:
    """Return the earliest date Yahoo Finance 15m data is available (today - 59 days)."""
    return datetime.now(UTC).date() - timedelta(days=YAHOO_VIX_15M_WINDOW_DAYS - 1)


# ──────────────────────────────────────────────────────────────────────────────
# DXY (US Dollar Index) — ICE/NYBOT, daily bars via Yahoo Finance (DX-Y.NYB)
# ──────────────────────────────────────────────────────────────────────────────

# Empirically confirmed: 1,864 daily bars 2019-01-03 → 2026-05-30 (2026-06-11).
# Yahoo's 1h data is capped to the last 730 days; daily is the full-history path.
DXY_DAILY_FIRST_DATE: date = date(2019, 1, 2)


def get_dxy_daily_source(query_date: date) -> str:
    """Return the source for ICE:INDEX:DXY-USD ohlcv_24h on *query_date*.

    DXY daily data is available from Yahoo Finance (DX-Y.NYB) back to 2019.
    Earlier dates and future unknown gaps are reported as GAP_NO_SOURCE.
    """
    if query_date < DXY_DAILY_FIRST_DATE:
        return "GAP_NO_SOURCE"
    return "YAHOO_FINANCE"


# ──────────────────────────────────────────────────────────────────────────────
# General-purpose temporal source resolution
# ──────────────────────────────────────────────────────────────────────────────

# Registry of instrument+data_type → resolver function.
# Each resolver takes a date and returns a source name string.
_SOURCE_RESOLVERS: dict[tuple[str, str], object] = {
    ("CBOE:INDEX:VIX-USD", "ohlcv_15m"): get_vix_15m_source,
    ("ICE:INDEX:DXY-USD", "ohlcv_24h"): get_dxy_daily_source,
}


def get_source_for_instrument(
    instrument_key: str,
    data_type: str,
    query_date: date,
) -> str | None:
    """Resolve data source for an instrument+data_type on a given date.

    Returns the source name (e.g. "BARCHART_CSV", "YAHOO_FINANCE"),
    "GAP_NO_SOURCE" for known gaps, or None if no temporal resolver is
    registered (caller should fall back to VENUE_TO_DATA_SOURCE).
    """
    resolver = _SOURCE_RESOLVERS.get((instrument_key, data_type))
    if resolver is None:
        return None
    assert callable(resolver)
    typed_resolver = cast(Callable[[date], str], resolver)
    return typed_resolver(query_date)


# ──────────────────────────────────────────────────────────────────────────────
# GCS bucket constants (referenced by backfill/migration scripts)
# ──────────────────────────────────────────────────────────────────────────────

VIX_PROD_BUCKET: str = "market-data-tick-tradfi-central-element-323112"
VIX_DEV_BUCKET: str = "market-data-tick-tradfi-test-central-element-323112"
VIX_INSTRUMENT_KEY: str = "CBOE:INDEX:VIX-USD"
VIX_DATA_TYPE: str = "ohlcv_15m"
VIX_TYPE_PREFIX: str = "indices"
