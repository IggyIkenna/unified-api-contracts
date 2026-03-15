"""FRED normalizers — all normalize_fred_* functions.

Extracted from normalize_utils/tradfi.py.
Covers US Treasury yield observations from Federal Reserve Economic Data.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalYieldCurvePoint
from .schemas import FredObservation, FredSeriesObservationsResponse

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_decimal(val: float | str | int | None) -> Decimal | None:
    """Convert any numeric-ish value to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_date_to_utc(date_str: str | None) -> datetime:
    """Parse a YYYY-MM-DD date string to an aware UTC datetime (midnight UTC)."""
    if not date_str:
        return datetime.now(UTC)
    with contextlib.suppress(ValueError, TypeError):
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").replace(tzinfo=UTC)
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------


def normalize_fred_observation(
    raw: FredObservation,
    series_id: str = "",
    tenor: str | None = None,
    venue: str = "fred",
) -> CanonicalYieldCurvePoint | None:
    """Normalize a single FredObservation to CanonicalYieldCurvePoint.

    FRED uses "." to denote missing values; these are returned as None.

    Args:
        raw:       FredObservation from the observations list.
        series_id: FRED series ID (e.g. DGS10 for 10-year Treasury).
        tenor:     Human-readable tenor label (e.g. "10Y").
        venue:     Provider tag, defaults to "fred".

    Returns:
        CanonicalYieldCurvePoint or None if the observation is missing (value == ".").
    """
    value_str = raw.value or ""
    if value_str.strip() == "." or value_str.strip() == "":
        return None  # FRED missing value sentinel

    value = _to_decimal(value_str)
    if value is None:
        return None

    timestamp = _parse_date_to_utc(raw.date)

    return CanonicalYieldCurvePoint(
        timestamp=timestamp,
        venue=venue,
        series_id=series_id or raw.series_id or "",
        tenor=tenor,
        value=value,
        currency="USD",
    )


def normalize_fred_series_response(
    raw: FredSeriesObservationsResponse,
    series_id: str = "",
    tenor: str | None = None,
    venue: str = "fred",
) -> list[CanonicalYieldCurvePoint]:
    """Normalize all observations in a FredSeriesObservationsResponse.

    Skips missing-value observations (FRED "." sentinel).
    Returns a list sorted ascending by timestamp.

    Args:
        raw:       FredSeriesObservationsResponse from the FRED API.
        series_id: FRED series ID (e.g. DGS10).
        tenor:     Tenor label.
        venue:     Provider tag.
    """
    results: list[CanonicalYieldCurvePoint] = []
    for obs in raw.observations or []:
        point = normalize_fred_observation(obs, series_id=series_id, tenor=tenor, venue=venue)
        if point is not None:
            results.append(point)
    return results


__all__ = [
    "normalize_fred_observation",
    "normalize_fred_series_response",
]
