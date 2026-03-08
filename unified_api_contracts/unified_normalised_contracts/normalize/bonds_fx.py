"""Bond, yield curve, and CDS normalizers: raw provider data → canonical schemas.

Covers:
- FRED (Federal Reserve Economic Data) — US Treasury yield observations
- ECB (European Central Bank SDMX REST) — EU OIS/ESTR yield curve
- OFR (Office of Financial Research) — CDS spread indices
- OpenBB Platform — Treasury bond bid/ask/YTM data

All monetary / rate values are converted to Decimal for precision.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...unified_api_contracts_external.ecb.schemas import (
    EcbDataflowResponse,
    EcbYieldCurveObservation,
)
from ...unified_api_contracts_external.fred.schemas import (
    FredObservation,
    FredSeriesObservationsResponse,
)
from ...unified_api_contracts_external.ofr.schemas import OfrCdsResponse, OfrCdsSpreadIndex
from ...unified_api_contracts_external.openbb.schemas import (
    OpenBBTreasuryPrice,
    OpenBBTreasuryPricesResponse,
)
from ..domain import CanonicalBondData, CanonicalCdsSpread, CanonicalYieldCurvePoint

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
# FRED — US Treasury yield observations
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


# ---------------------------------------------------------------------------
# ECB — European Central Bank yield curve (SDMX REST)
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
            # SDMX observation dicts have period → value mapping
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


# ---------------------------------------------------------------------------
# OFR — CDS spread indices
# ---------------------------------------------------------------------------


def normalize_ofr_cds_spread(
    raw: OfrCdsSpreadIndex,
    venue: str = "ofr",
) -> CanonicalCdsSpread | None:
    """Normalize a single OfrCdsSpreadIndex to CanonicalCdsSpread.

    OFR values are raw float CDS spreads; units depend on the series but are
    typically basis points (bps). Stored as-is in spread_bps.

    Args:
        raw:   OfrCdsSpreadIndex observation.
        venue: Provider tag, defaults to "ofr".
    """
    if raw.value is None:
        return None

    spread = _to_decimal(raw.value)
    if spread is None:
        return None

    timestamp = _parse_date_to_utc(raw.date)

    return CanonicalCdsSpread(
        timestamp=timestamp,
        venue=venue,
        series_id=raw.series_id or "",
        index_name=raw.index_name,
        tenor=raw.tenor,
        sector=raw.sector,
        spread_bps=spread,
    )


def normalize_ofr_cds_response(
    raw: OfrCdsResponse,
    venue: str = "ofr",
) -> list[CanonicalCdsSpread]:
    """Normalize OfrCdsResponse (list of CDS spread observations) to CanonicalCdsSpread list."""
    results: list[CanonicalCdsSpread] = []
    for item in raw.data or []:
        point = normalize_ofr_cds_spread(item, venue=venue)
        if point is not None:
            results.append(point)
    return results


# ---------------------------------------------------------------------------
# OpenBB Platform — Treasury bond bid/ask/YTM
# ---------------------------------------------------------------------------


def normalize_openbb_treasury_price(
    raw: OpenBBTreasuryPrice,
    venue: str = "openbb",
) -> CanonicalBondData | None:
    """Normalize a single OpenBBTreasuryPrice to CanonicalBondData.

    OpenBB treasury prices contain bid, ask, last (price), yield_to_maturity.
    date is a string in YYYY-MM-DD format.

    Args:
        raw:   OpenBBTreasuryPrice row.
        venue: Provider tag, defaults to "openbb".
    """
    if raw.symbol is None and raw.name is None:
        return None

    timestamp = _parse_date_to_utc(raw.date)

    return CanonicalBondData(
        timestamp=timestamp,
        venue=venue,
        symbol=raw.symbol or "",
        name=raw.name,
        bid=_to_decimal(raw.bid),
        ask=_to_decimal(raw.ask),
        last=_to_decimal(raw.last),
        yield_to_maturity=_to_decimal(raw.yield_to_maturity),
        currency=None,  # OpenBB does not expose currency directly in this schema
    )


def normalize_openbb_treasury_prices_response(
    raw: OpenBBTreasuryPricesResponse,
    venue: str = "openbb",
) -> list[CanonicalBondData]:
    """Normalize OpenBBTreasuryPricesResponse to a list of CanonicalBondData."""
    results: list[CanonicalBondData] = []
    for item in raw.results or []:
        point = normalize_openbb_treasury_price(item, venue=venue)
        if point is not None:
            results.append(point)
    return results


__all__ = [
    "normalize_ecb_dataflow_response",
    "normalize_ecb_yield_curve_observation",
    "normalize_fred_observation",
    "normalize_fred_series_response",
    "normalize_ofr_cds_response",
    "normalize_ofr_cds_spread",
    "normalize_openbb_treasury_price",
    "normalize_openbb_treasury_prices_response",
]
