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
"""

from __future__ import annotations

from datetime import date
from typing import NamedTuple


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
        source="GAP_NO_SOURCE",
        first_date=date(2025, 11, 13),
        # last_date is dynamic: (today - YAHOO_VIX_15M_WINDOW_DAYS) - 1 day.
        # Cannot be a compile-time constant; compute at runtime.
        last_date=None,
        note=(
            "Small gap (~2 months) between Barchart end (2025-11-12) and Yahoo "
            "Finance 15m window start (~today - 59 days). Only daily VIXCLS from "
            "FRED is available for this range."
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
    """
    from datetime import UTC, datetime, timedelta  # noqa: qg-inside-import (runtime only)

    today = datetime.now(UTC).date()
    yahoo_start = today - timedelta(days=YAHOO_VIX_15M_WINDOW_DAYS - 1)

    if query_date <= BARCHART_VIX_LAST_DATE:
        return "BARCHART_CSV"
    if query_date >= yahoo_start:
        return "YAHOO_FINANCE"
    return "GAP_NO_SOURCE"


def get_yahoo_vix_15m_start() -> date:
    """Return the earliest date Yahoo Finance 15m data is available (today - 59 days)."""
    from datetime import UTC, datetime, timedelta  # noqa: qg-inside-import (runtime only)

    return datetime.now(UTC).date() - timedelta(days=YAHOO_VIX_15M_WINDOW_DAYS - 1)


# ──────────────────────────────────────────────────────────────────────────────
# GCS bucket constants (referenced by backfill/migration scripts)
# ──────────────────────────────────────────────────────────────────────────────

VIX_PROD_BUCKET: str = "market-data-tick-tradfi-central-element-323112"
VIX_DEV_BUCKET: str = "market-data-tick-tradfi-test-central-element-323112"
VIX_INSTRUMENT_KEY: str = "CBOE:INDEX:VIX-USD"
VIX_DATA_TYPE: str = "ohlcv_15m"
VIX_TYPE_PREFIX: str = "indices"
