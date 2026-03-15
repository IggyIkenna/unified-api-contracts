"""Polygon.io normalizers — all normalize_polygon_* functions.

Covers US equities/crypto OHLCV aggregates and reference tickers.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalInstrument, CanonicalOhlcvBar, InstrumentType
from .schemas import PolygonAggregate, PolygonAggregatesResponse, PolygonTicker


def _d(val: float | str | int | Decimal | None) -> Decimal:
    """Parse to Decimal; returns Decimal('0') for None."""
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _to_decimal(val: float | str | int | None) -> Decimal | None:
    """Convert to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _ts_ms_to_datetime(ts_ms: int | None) -> datetime:
    """Convert millisecond timestamp to UTC datetime."""
    if ts_ms is not None and ts_ms > 0:
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
    return datetime.now(UTC)


def normalize_polygon_aggregate(
    raw: PolygonAggregate,
    symbol: str = "",
    venue: str = "polygon",
) -> CanonicalOhlcvBar | None:
    """Convert a single PolygonAggregate to CanonicalOhlcvBar.

    Polygon aggregates use o/h/l/c/v (open/high/low/close/volume), t (timestamp ms).
    """
    if raw.c is None and raw.o is None:
        return None
    ts = _ts_ms_to_datetime(raw.t)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol or "",
        open=_d(raw.o),
        high=_d(raw.h),
        low=_d(raw.l),
        close=_d(raw.c),
        volume=_d(raw.v),
        quote_volume=None,
        count=raw.n,
        vwap=_to_decimal(raw.vw),
    )


def normalize_polygon_aggregates_response(
    raw: PolygonAggregatesResponse,
    symbol: str = "",
    venue: str = "polygon",
) -> list[CanonicalOhlcvBar]:
    """Normalize PolygonAggregatesResponse to list of CanonicalOhlcvBar."""
    sym = symbol or (raw.ticker or "")
    results: list[CanonicalOhlcvBar] = []
    for bar in raw.results or []:
        out = normalize_polygon_aggregate(bar, symbol=sym, venue=venue)
        if out is not None:
            results.append(out)
    return results


def normalize_polygon_ticker(
    raw: PolygonTicker,
    venue: str = "polygon",
) -> CanonicalInstrument:
    """Convert PolygonTicker (reference data) to CanonicalInstrument."""
    symbol = raw.ticker or ""
    instrument_key = f"{venue}:SPOT_PAIR:{symbol}"
    ts = datetime.now(UTC)
    if raw.last_updated_utc:
        with contextlib.suppress(ValueError, TypeError):
            parsed = datetime.fromisoformat(raw.last_updated_utc.replace("Z", "+00:00"))
            ts = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        instrument_type=InstrumentType.SPOT_PAIR,
        symbol=symbol,
        timestamp=ts,
        asset_class=raw.market,
        exchange_raw_symbol=raw.ticker,
    )


__all__ = [
    "normalize_polygon_aggregate",
    "normalize_polygon_aggregates_response",
    "normalize_polygon_ticker",
]
