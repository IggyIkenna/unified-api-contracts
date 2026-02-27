"""Pydantic schemas for FRED (Federal Reserve Economic Data) API.

US Treasury yield series (1m-30y), TIPS, yield curve observations.
Ref: https://fred.stlouisfed.org/docs/api/fred/
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class FredObservation(BaseModel):
    """Single observation from FRED series/observations endpoint."""

    date: str = Field(..., description="Observation date (YYYY-MM-DD)")
    value: str | None = Field(None, description="Value as string (. for missing)")


class FredSeriesObservationsResponse(BaseModel):
    """Response from FRED series/observations endpoint."""

    realtime_start: str | None = None
    realtime_end: str | None = None
    observation_start: str | None = None
    observation_end: str | None = None
    units: str | None = None
    output_type: int | None = None
    file_type: str | None = None
    order_by: str | None = None
    sort_order: str | None = None
    count: int | None = None
    offset: int | None = None
    limit: int | None = None
    observations: list[FredObservation] | None = None


class FredSeriesInfo(BaseModel):
    """Series metadata from FRED series endpoint."""

    id: str | None = None
    title: str | None = None
    observation_start: str | None = None
    observation_end: str | None = None
    frequency: str | None = None
    frequency_short: str | None = None
    units: str | None = None
    units_short: str | None = None
    seasonal_adjustment: str | None = None
    seasonal_adjustment_short: str | None = None
    last_updated: str | None = None
    popularity: int | None = None
    notes: str | None = None


class FredError(BaseModel):
    """FRED API error response."""

    error_code: int | None = None
    message: str | None = None

    @classmethod
    def classify(cls, error_code: int | None = None, http_status: int | None = None) -> ErrorAction:
        """Map FRED error to retry action."""
        if http_status == 429 or (error_code and error_code in (429, 503)):
            return ErrorAction.RETRY_WITH_BACKOFF
        if error_code == 400:
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
