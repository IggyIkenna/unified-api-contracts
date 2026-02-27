"""Pydantic schemas for ECB Data Portal API.

EU sovereign yield curves (OIS, ESTR). SDMX 2.1 REST.
Ref: https://data.ecb.europa.eu/help/api/
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class EcbObservation(BaseModel):
    """Single observation from ECB SDMX JSON data."""

    id: str | None = None
    name: str | None = None
    dimensions: dict[str, str] | None = None
    attributes: dict[str, str] | None = None
    observations: list[dict[str, str]] | None = Field(None, description="List of {0: period, 1: value} dicts")


class EcbDataflowResponse(BaseModel):
    """ECB SDMX 2.1 data response envelope (JSON format)."""

    structure: dict | None = None
    dataSets: list[dict] | None = Field(None, description="SDMX data sets")
    data: list[EcbObservation] | None = None


class EcbYieldCurveObservation(BaseModel):
    """Yield curve tenor observation (period, value in bps)."""

    period: str | None = Field(None, description="ISO period e.g. YYYY-MM-DD")
    value: float | None = Field(None, description="Yield in basis points")


class EcbError(BaseModel):
    """ECB API error response."""

    error: str | None = None
    message: str | None = None
    status: int | None = None

    @classmethod
    def classify(cls, status: int | None = None, error: str | None = None) -> ErrorAction:
        """Map ECB error to retry action."""
        if status == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if status is not None and status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
