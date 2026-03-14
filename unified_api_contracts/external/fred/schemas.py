"""Pydantic schemas for FRED (Federal Reserve Economic Data) API.

Source: https://fred.stlouisfed.org/docs/api/fred/
Free API key available at fred.stlouisfed.org. No subscription required.

Used by unified-market-interface FredAdapter for US Treasury yields, TIPS, and yield curve observations.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel


class FredObservation(BaseModel):
    """Single FRED observation from series observations response."""

    date: str | None = None
    value: str | None = None  # "." means missing data in FRED
    series_id: str | None = None


class FredSeriesObservationsResponse(BaseModel):
    """FRED series observations response containing yield curve/economic data."""

    observations: list[FredObservation] | None = None
    count: int | None = None
    offset: int | None = None
    limit: int | None = None
    order_by: str | None = None
    sort_order: str | None = None
    units: str | None = None
    output_type: int | None = None
    file_type: str | None = None
    realtime_start: str | None = None
    realtime_end: str | None = None
