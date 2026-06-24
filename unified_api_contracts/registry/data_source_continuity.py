"""Data source continuity registry (SSOT).

Documents which data source covers which date range for each instrument/data-type pair.
Consumed by backfill scripts, feature services, and data pipeline services to know
which source to query for a given date. Also the SSOT for the GENERAL Yahoo Finance
granularity/lookback guardrail (every Yahoo fetch is bounded — see
``assert_yahoo_intraday_within_limit`` / ``assert_yahoo_request_width_ok``).

── Why this file exists ──────────────────────────────────────────────────────
Several instruments have had their upstream data source change over time, and
Yahoo's chart API bounds how far back / how wide each interval can be fetched.
Backfill scripts and downstream consumers MUST check this registry before
deciding which source to use for a given (instrument, data_type, date) tuple.

── VIX 15m (BARCHART RETIRED 2026-06-24) ─────────────────────────────────────
VIX 15m is now AGGREGATED from the VX FUTURES front contract captured via
Databento XCBF.PITCH (CFE). The CBOE cash-index was deleted (2026-06-23) and the
manual-CSV Barchart preload is removed (no shim) — VX futures track the index
with a small steady contango basis (corr 0.95-0.98). Yahoo's ^VIX rolling 60-day
window is a recent cross-check only. There is NO honest gap any more (VX futures
cover the full history), so ``is_vix_15m_gap_date`` always returns ``False`` and
``get_vix_15m_source`` returns "DATABENTO_VX_FUTURES" (historical) / "YAHOO_FINANCE"
(rolling). Do NOT build automated Barchart fetching — it is gone.
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
# VIX 15-minute OHLCV (data_type=ohlcv_15m)
# ──────────────────────────────────────────────────────────────────────────────
#
# BARCHART RETIRED 2026-06-24. The CBOE cash-index (CBOE:INDEX:VIX-USD) was DELETED
# (operator 2026-06-23) and VIX 15m is now AGGREGATED from the VX FUTURES front
# contract captured via Databento XCBF.PITCH (CFE) — the futures track the index
# with a small steady contango basis (sanity-checked: corr 0.95-0.98). Yahoo's
# ^VIX rolling window remains a recent-window cross-check source only. The Barchart
# CSV preload (BARCHART_VIX_FIRST/LAST_DATE/FILE_COUNT) is gone (no shim).

# Yahoo Finance ^VIX — 15m interval, rolling 60-day window only.
# No fixed start date; always (today - 59 days) at earliest.
YAHOO_VIX_15M_WINDOW_DAYS: int = 60

# ── Yahoo Finance granularity / lookback GUARDRAIL (SSOT, GENERAL) ──────────
# Yahoo's chart API bounds how far back EACH interval can reach AND how wide a
# single request may be. PROBED LIVE 2026-06-24 (tickers 005930.KS / 005380.KS /
# 000660.KS) — the MEASURED ladder (the HARD Yahoo error boundaries, not a target
# where Yahoo caps lower):
#   * 1d  : UNBOUNDED lookback (probed 2019-05 → today OK on KRX). Backfill FLOOR
#           is the operator target 2019-01-01 (:data:`YAHOO_DAILY_BACKFILL_FLOOR`)
#           — a 1d request before it is clamped (Yahoo would serve it; this is our
#           chosen TradFi history floor, enforced by the GENERAL guardrail).
#   * 1h  : 730 days. Probed: 365d OK; EXACTLY 730d back already FAILS ("must be
#           within the last 730 days") → serveable window is strictly < 730d.
#   * 15m : 60 days (NOT the 89 a prior note assumed). Probed on all 3 KRX tickers:
#           59d back OK; 60d+ → HTTP 422 "must be within the last 60 days".
#   * 1m  : 8 days PER REQUEST (Yahoo: "Only 8 days worth of 1m granularity data
#           are allowed to be fetched per request"). 7d OK; 28d EMPTY. Total 1m
#           history is ~30d but MUST be chunked in <=8d windows
#           (:data:`YAHOO_INTRADAY_MAX_REQUEST_DAYS`).
# A request OLDER/WIDER than the limit for its interval MUST be clamped/rejected
# (raise), never silently return empty — the durable guardrail consumed by
# ``YahooFinanceAdapter.download_daily``/``download_intraday`` (the non-bypassable
# fetch path) + the centralised venue/source/adapter parity gate.
# Value = max lookback (calendar days) from "today"; None = unbounded lookback.
YAHOO_INTRADAY_LOOKBACK_DAYS: dict[str, int | None] = {
    "1m": 30,  # ~30d total history; per-request cap 8d (chunked) — see MAX_REQUEST_DAYS
    "2m": 60,
    "5m": 60,
    "15m": 60,  # MEASURED 2026-06-24: 59d OK, 60d+ → 422 "within the last 60 days"
    "30m": 60,
    "60m": 60,
    "90m": 60,
    "1h": 730,  # MEASURED: <730d OK, exactly-730d FAILS → serveable strictly < 730d
    "1d": None,  # unbounded lookback (Yahoo); backfill floor = YAHOO_DAILY_BACKFILL_FLOOR
    "5d": None,
    "1wk": None,
    "1mo": None,
    "3mo": None,
}

# Operator backfill floor for unbounded (daily) Yahoo intervals — our chosen
# TradFi daily history floor (2019-01-01). A 1d request before this is clamped by
# the GENERAL guardrail (Yahoo would serve it, but we cap our history here).
YAHOO_DAILY_BACKFILL_FLOOR: date = date(2019, 1, 1)

# Per-REQUEST width cap (calendar days) for intraday intervals where Yahoo bounds
# a SINGLE request more tightly than the total lookback. MEASURED 2026-06-24: 1m
# is "8 days per request"; the fetch path MUST chunk 1m windows to <= this width.
# For intervals whose per-request cap equals the lookback (15m=60, 1h is wide),
# the value mirrors the lookback (a single request may span the whole window).
YAHOO_INTRADAY_MAX_REQUEST_DAYS: dict[str, int] = {
    "1m": 8,  # Yahoo: "Only 8 days worth of 1m granularity data ... per request"
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "60m": 60,
    "90m": 60,
}


class YahooLookbackExceededError(ValueError):
    """Raised when a Yahoo request reaches FURTHER BACK than the interval's
    lookback limit (:data:`YAHOO_INTRADAY_LOOKBACK_DAYS` /
    :data:`YAHOO_DAILY_BACKFILL_FLOOR`).

    Yahoo silently returns an empty/partial response (or HTTP 422) for an
    over-the-limit window, which a naive caller mis-reads as "no data". The
    guardrail fails LOUD instead so the caller clamps the window or routes to a
    deeper source (FRED/databento). The fetch path MUST consult
    :func:`assert_yahoo_intraday_within_limit` before hitting the API.
    """


class YahooRequestTooWideError(ValueError):
    """Raised when a SINGLE Yahoo intraday request spans more calendar days than
    the interval's per-request width cap (:data:`YAHOO_INTRADAY_MAX_REQUEST_DAYS`).

    Yahoo bounds 1m to "8 days per request" — a wider single request 422s. The
    fetch path MUST chunk the window before hitting the API; this guardrail
    fails loud if it didn't.
    """


def assert_yahoo_intraday_within_limit(interval: str, start_date: date, *, today: date | None = None) -> None:
    """Fail-closed GENERAL guardrail: raise if a Yahoo request for ``interval``
    would reach back before the interval's max lookback window.

    Handles BOTH intraday intervals (bounded lookback) AND the daily/unbounded
    intervals (clamped to :data:`YAHOO_DAILY_BACKFILL_FLOOR`) — so EVERY Yahoo
    fetch is bounded, not just intraday.

    Args:
        interval: Yahoo bar interval (``"1m"`` / ``"15m"`` / ``"1h"`` / ``"1d"`` / …).
        start_date: The earliest date the request asks for (UTC date).
        today: Reference "now" date (defaults to ``datetime.now(UTC).date()``).

    Raises:
        YahooLookbackExceededError: ``start_date`` is older than the interval's
            serveable floor (``today - YAHOO_INTRADAY_LOOKBACK_DAYS[interval]``
            for a bounded interval, or ``YAHOO_DAILY_BACKFILL_FLOOR`` for an
            unbounded daily+ interval).
        KeyError: ``interval`` is not a known Yahoo interval.
    """
    limit_days = YAHOO_INTRADAY_LOOKBACK_DAYS[interval]
    ref = today if today is not None else datetime.now(UTC).date()
    if limit_days is None:
        # Unbounded lookback (1d/5d/1wk/1mo/3mo): clamp to the operator floor so
        # even daily fetches are bounded (the GENERAL guardrail).
        if start_date < YAHOO_DAILY_BACKFILL_FLOOR:
            raise YahooLookbackExceededError(
                f"Yahoo {interval!r} cannot reach {start_date} — the TradFi daily "
                f"backfill floor is {YAHOO_DAILY_BACKFILL_FLOOR}. Clamp the window "
                f"to >= {YAHOO_DAILY_BACKFILL_FLOOR}."
            )
        return
    floor = ref - timedelta(days=limit_days)
    if start_date < floor:
        raise YahooLookbackExceededError(
            f"Yahoo intraday {interval!r} cannot reach {start_date} — the lookback "
            f"limit is {limit_days} days (earliest serveable: {floor}). Clamp the "
            f"window to >= {floor} or use a deeper source (FRED/databento)."
        )


def assert_yahoo_request_width_ok(interval: str, start_date: date, end_date: date) -> None:
    """Fail-closed guardrail: raise :class:`YahooRequestTooWideError` if a SINGLE
    Yahoo intraday request spans more calendar days than the interval's
    per-request width cap (:data:`YAHOO_INTRADAY_MAX_REQUEST_DAYS`).

    Intervals with no per-request width cap (daily+) never raise. The fetch path
    MUST chunk a wide intraday window (e.g. 1m → <=8d slices) before calling this.

    Args:
        interval: Yahoo bar interval.
        start_date: Request window start (UTC date).
        end_date: Request window end (UTC date, exclusive or inclusive — span is
            ``(end_date - start_date).days``).

    Raises:
        YahooRequestTooWideError: the request span exceeds the per-request cap.
    """
    cap = YAHOO_INTRADAY_MAX_REQUEST_DAYS.get(interval)
    if cap is None:
        return
    span_days = (end_date - start_date).days
    if span_days > cap:
        raise YahooRequestTooWideError(
            f"Yahoo {interval!r} single request spans {span_days}d "
            f"({start_date}→{end_date}) — the per-request cap is {cap}d. "
            f"Chunk the window into <= {cap}d slices before fetching."
        )


# VIX 15m source history. BARCHART RETIRED 2026-06-24 — the historical 15m series
# is now AGGREGATED from the VX FUTURES front contract captured via Databento
# XCBF.PITCH (CFE); Yahoo's ^VIX rolling 60-day window is a recent cross-check.
# The former Barchart preload window + the 2025-11-13→today-60d "permanent gap"
# (which only existed because Barchart ended + Yahoo's window is short) are GONE:
# VX futures via databento cover the full history → no honest gap remains.
DATABENTO_VX_FUTURES_FIRST_DATE: date = date(2020, 1, 2)  # our captured VX history floor

VIX_15M_SOURCE_HISTORY: list[SourceWindow] = [
    SourceWindow(
        source="DATABENTO_VX_FUTURES",
        first_date=DATABENTO_VX_FUTURES_FIRST_DATE,
        last_date=None,  # ongoing (live VX futures stream)
        note=(
            "VIX 15m AGGREGATED from the VX futures front contract captured via "
            "Databento XCBF.PITCH (CFE). The futures track the cash index with a "
            "small steady contango basis (sanity-checked corr 0.95-0.98). This "
            "supersedes the retired Barchart CSV preload + the CBOE cash-index "
            "(deleted 2026-06-23). No honest gap remains — VX futures cover the "
            "full history at 15m via downstream aggregation of ohlcv-1m."
        ),
    ),
    SourceWindow(
        source="YAHOO_FINANCE",
        # first_date is dynamic: today - 59 days. Cannot be a compile-time constant.
        # Use get_yahoo_vix_15m_start() at runtime.
        first_date=date(2026, 1, 18),  # approximate (today - 59d)
        last_date=None,  # ongoing
        note=(
            "Yahoo Finance ^VIX, 15m interval — a RECENT cross-check only (rolling "
            "60-day window). Volume is always 0.0 (VIX is a calculated index). The "
            "primary 15m source is now DATABENTO_VX_FUTURES (above)."
        ),
    ),
]


def get_vix_15m_source(query_date: date) -> str:
    """Return the canonical data source name for VIX 15m on a given date.

    Returns one of: "DATABENTO_VX_FUTURES", "YAHOO_FINANCE".

    BARCHART RETIRED 2026-06-24: VIX 15m is aggregated from VX futures (Databento
    XCBF.PITCH) for the full history; Yahoo's ^VIX rolling window is a recent
    cross-check. The former "GAP_NO_SOURCE" range no longer exists (VX futures
    cover it) — :func:`is_vix_15m_gap_date` always returns ``False`` now.
    """
    today = datetime.now(UTC).date()
    yahoo_start = today - timedelta(days=YAHOO_VIX_15M_WINDOW_DAYS - 1)
    if query_date >= yahoo_start:
        return "YAHOO_FINANCE"
    return "DATABENTO_VX_FUTURES"


def is_vix_15m_gap_date(query_date: date) -> bool:
    """Return True if query_date falls in a VIX 15m data gap.

    BARCHART RETIRED 2026-06-24: VX futures via Databento now cover the full
    history, so there is NO permanent gap — this always returns ``False``. The
    MTDS/MDPS callers that branch on it keep the same signature + semantics ("no
    data for this date"); the answer is simply now always "not a gap".
    """
    _ = query_date  # no date is a gap any more (VX futures cover the full history)
    return False


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


# Empirically confirmed: 6,642 daily bars 2000-01-03 → 2026-06-09 (2026-06-11)
# for each of ^IRX (3M), ^FVX (5Y), ^TNX (10Y), ^TYX (30Y). These are CBOE
# interest-rate indices whose daily "close" is the par yield in percent.
US_TREASURY_YIELD_DAILY_FIRST_DATE: date = date(2000, 1, 3)


def get_us_treasury_yield_daily_source(query_date: date) -> str:
    """Return the source for a CBOE US-treasury-yield index ohlcv_24h on *query_date*.

    Daily yield data is available from Yahoo Finance (^IRX / ^FVX / ^TNX / ^TYX)
    back to 2000-01-03. Earlier dates are reported as GAP_NO_SOURCE.
    """
    if query_date < US_TREASURY_YIELD_DAILY_FIRST_DATE:
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
    ("CBOE:INDEX:US3M-USD", "ohlcv_24h"): get_us_treasury_yield_daily_source,
    ("CBOE:INDEX:US5Y-USD", "ohlcv_24h"): get_us_treasury_yield_daily_source,
    ("CBOE:INDEX:US10Y-USD", "ohlcv_24h"): get_us_treasury_yield_daily_source,
    ("CBOE:INDEX:US30Y-USD", "ohlcv_24h"): get_us_treasury_yield_daily_source,
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


def data_types_for_instrument(instrument_key: str) -> list[str]:
    """Return the data_types with a registered temporal source resolver for *instrument_key*.

    Used by the expected-universe enumerator to derive an index instrument's
    capture data_type(s) (e.g. VIX → ``ohlcv_15m``, treasuries → ``ohlcv_24h``)
    from the single source-of-truth resolver registry, rather than duplicating
    the mapping. Returns an empty list when no resolver is registered.
    """
    return sorted(dt for key, dt in _SOURCE_RESOLVERS if key == instrument_key)


# ──────────────────────────────────────────────────────────────────────────────
# GCS bucket constants (referenced by backfill/migration scripts)
# ──────────────────────────────────────────────────────────────────────────────

VIX_PROD_BUCKET: str = "market-data-tick-tradfi-central-element-323112"
VIX_DEV_BUCKET: str = "market-data-tick-tradfi-test-central-element-323112"
VIX_INSTRUMENT_KEY: str = "CBOE:INDEX:VIX-USD"
VIX_DATA_TYPE: str = "ohlcv_15m"
VIX_TYPE_PREFIX: str = "indices"
