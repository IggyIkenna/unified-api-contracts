"""ECB normalizers — all normalize_ecb_* functions.

Extracted from normalize_utils/tradfi.py.
Covers European Central Bank SDMX REST yield curve observations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.domain import CanonicalYieldCurvePoint
from .schemas import EcbDataflowResponse, EcbYieldCurveObservation

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


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------


def normalize_ecb_yield_curve_observation(
    raw: EcbYieldCurveObservation,
    series_id: str = "",
    tenor: str | None = None,
    venue: str = "ecb",
) -> CanonicalYieldCurvePoint | None:
    """Normalize a single EcbYieldCurveObservation to CanonicalYieldCurvePoint.

    ECB SDMX observations use `period` (YYYY-MM or YYYY-MM-DD) and `value` (float).

    Args:
        raw:       EcbYieldCurveObservation.
        series_id: Dataflow series key / maturity identifier.
        tenor:     Tenor label (e.g. "5Y").
        venue:     Provider tag, defaults to "ecb".
    """
    if raw.value is None:
        return None

    value = _to_decimal(raw.value)
    if value is None:
        return None

    # ECB uses YYYY-MM or YYYY-MM-DD period strings
    period = raw.period or ""
    ts: datetime = datetime.now(UTC)
    try:
        if len(period) == 10:
            ts = datetime.strptime(period, "%Y-%m-%d").replace(tzinfo=UTC)
        elif len(period) == 7:
            ts = datetime.strptime(period + "-01", "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        ts = datetime.now(UTC)

    return CanonicalYieldCurvePoint(
        timestamp=ts,
        venue=venue,
        series_id=series_id,
        tenor=tenor,
        value=value,
        currency="EUR",
    )


def normalize_ecb_dataflow_response(
    raw: EcbDataflowResponse,
    series_id: str = "",
    venue: str = "ecb",
) -> list[CanonicalYieldCurvePoint]:
    """Normalize ECB SDMX dataflow response to a list of CanonicalYieldCurvePoint.

    Each EcbDataflowObservation in raw.data may contain multiple per-period observations.
    The `key` field typically encodes the maturity / series identifier.
    """
    results: list[CanonicalYieldCurvePoint] = []
    for obs in raw.data or []:
        sid = obs.key or series_id
        for obs_dict in obs.observations or []:
            # SDMX observation dicts have period -> value mapping
            for period_key, raw_val in obs_dict.items():
                val = _to_decimal(raw_val)
                if val is None:
                    continue
                period_str = period_key.strip()
                ts: datetime
                try:
                    if len(period_str) == 10:
                        ts = datetime.strptime(period_str, "%Y-%m-%d").replace(tzinfo=UTC)
                    elif len(period_str) == 7:
                        ts = datetime.strptime(period_str + "-01", "%Y-%m-%d").replace(tzinfo=UTC)
                    else:
                        ts = datetime.now(UTC)
                except ValueError:
                    ts = datetime.now(UTC)
                results.append(
                    CanonicalYieldCurvePoint(
                        timestamp=ts,
                        venue=venue,
                        series_id=sid,
                        tenor=None,
                        value=val,
                        currency="EUR",
                    )
                )
    return results


__all__ = [
    "normalize_ecb_dataflow_response",
    "normalize_ecb_yield_curve_observation",
]
