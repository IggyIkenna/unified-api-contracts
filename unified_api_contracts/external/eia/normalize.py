"""EIA (U.S. Energy Information Administration) normalizers.

Energy inventory and price data -> CanonicalOnChainMetric, CanonicalOhlcvBar.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalOhlcvBar, CanonicalOnChainMetric
from .schemas import (
    EIASeriesObservation,
    EIAStorageReport,
    EIAWeeklyCrudeStorageReport,
)


def _to_decimal(val: float | str | int | Decimal | None) -> Decimal | None:
    """Convert numeric-ish value to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_period_to_utc(period: str | None) -> datetime:
    """Parse EIA period (YYYY-MM-DD) to UTC datetime."""
    if not period:
        return datetime.now(UTC)
    with contextlib.suppress(ValueError, TypeError):
        return datetime.strptime(str(period).strip()[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    return datetime.now(UTC)


def normalize_eia_storage_report(
    raw: EIAStorageReport,
    venue: str = "eia",
) -> CanonicalOnChainMetric:
    """Normalize EIAStorageReport (Natural Gas) to CanonicalOnChainMetric.

    metric_type="natural_gas_storage_bcf", value=value_bcf.
    """
    ts = raw.retrieved_at if raw.retrieved_at.tzinfo else raw.retrieved_at.replace(tzinfo=UTC)
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="natural_gas_storage_bcf",
        asset="NG",
        value=Decimal(str(raw.value_bcf)),
        secondary_value=_to_decimal(raw.deviation_bcf),
        raw={
            "value_bcf": float(raw.value_bcf),
            "year_ago_bcf": float(raw.year_ago_bcf) if raw.year_ago_bcf else None,
            "five_year_avg_bcf": float(raw.five_year_avg_bcf) if raw.five_year_avg_bcf else None,
            "deviation_bcf": float(raw.deviation_bcf) if raw.deviation_bcf else None,
            "deviation_pct": raw.deviation_pct,
        },
    )


def normalize_eia_crude_storage_report(
    raw: EIAWeeklyCrudeStorageReport,
    venue: str = "eia",
) -> CanonicalOnChainMetric:
    """Normalize EIAWeeklyCrudeStorageReport to CanonicalOnChainMetric.

    metric_type="crude_storage_mb", value=value_mb.
    """
    ts = raw.retrieved_at if raw.retrieved_at.tzinfo else raw.retrieved_at.replace(tzinfo=UTC)
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="crude_storage_mb",
        asset="WTI",
        value=Decimal(str(raw.value_mb)),
        secondary_value=_to_decimal(raw.deviation_mb),
        raw={
            "value_mb": float(raw.value_mb),
            "year_ago_mb": float(raw.year_ago_mb) if raw.year_ago_mb else None,
            "five_year_avg_mb": float(raw.five_year_avg_mb) if raw.five_year_avg_mb else None,
            "deviation_mb": float(raw.deviation_mb) if raw.deviation_mb else None,
            "deviation_pct": raw.deviation_pct,
        },
    )


def normalize_eia_series_observation(
    raw: EIASeriesObservation,
    metric_type: str | None = None,
    venue: str = "eia",
) -> CanonicalOnChainMetric | None:
    """Normalize EIASeriesObservation to CanonicalOnChainMetric.

    Skips None/missing values. metric_type defaults to series_id.
    """
    if raw.value is None or str(raw.value).strip() == "":
        return None
    val = _to_decimal(raw.value)
    if val is None:
        return None
    ts = _parse_period_to_utc(raw.period)
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type=metric_type or raw.series_id or "eia_series",
        asset=raw.series_id or "",
        value=val,
        raw={"period": raw.period, "value": raw.value, "units": raw.units},
    )


def normalize_eia_series_observation_to_ohlcv(
    raw: EIASeriesObservation,
    symbol: str = "EIA",
    venue: str = "eia",
) -> CanonicalOhlcvBar | None:
    """Normalize EIASeriesObservation (price series) to CanonicalOhlcvBar.

    Single observation -> o=h=l=c=value, volume=0. Use for EIA price series.
    """
    if raw.value is None or str(raw.value).strip() == "":
        return None
    val = _to_decimal(raw.value)
    if val is None:
        return None
    ts = _parse_period_to_utc(raw.period)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol or raw.series_id or "EIA",
        open=val,
        high=val,
        low=val,
        close=val,
        volume=Decimal("0"),
        quote_volume=None,
        count=None,
        vwap=None,
    )


__all__ = [
    "normalize_eia_crude_storage_report",
    "normalize_eia_series_observation",
    "normalize_eia_series_observation_to_ohlcv",
    "normalize_eia_storage_report",
]
