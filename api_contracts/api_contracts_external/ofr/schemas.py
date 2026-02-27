"""Pydantic schemas for OFR (Office of Financial Research) API.

CDS spread indices — limited coverage. Mark fields as Optional.
Ref: https://www.financialresearch.gov/
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class OfrCdsSpreadIndex(BaseModel):
    """CDS spread index observation from OFR. Limited coverage — all Optional."""

    series_id: str | None = None
    date: str | None = None
    value: float | None = Field(None, description="Spread in bps")
    index_name: str | None = None
    tenor: str | None = None
    sector: str | None = None


class OfrCdsResponse(BaseModel):
    """OFR CDS data response."""

    data: list[OfrCdsSpreadIndex] | None = None
    metadata: dict | None = None


class OfrError(BaseModel):
    """OFR API error response."""

    error: str | None = None
    message: str | None = None
    status: int | None = None

    @classmethod
    def classify(cls, status: int | None = None, error: str | None = None) -> ErrorAction:
        """Map OFR error to retry action."""
        if status == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if status is not None and status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
