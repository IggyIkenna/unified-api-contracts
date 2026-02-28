"""Pydantic schemas for ECB (European Central Bank) SDMX 2.1 REST API data.

Source: https://data-api.ecb.europa.eu/service/data/IRS (ECB interest rates)
No auth required. SDMX 2.1 REST API.

Used by unified-market-interface ECBAdapter for EU sovereign yield curves (OIS, ESTR).
"""

from pydantic import BaseModel


class EcbYieldCurveObservation(BaseModel):
    """Single yield curve observation from ECB SDMX dataflow response."""
    
    period: str | None = None
    value: float | None = None


class EcbDataflowObservation(BaseModel):
    """Single observation within ECB dataflow response data."""
    
    observations: list[dict[str, str]] | None = None
    key: str | None = None
    attributes: list[str] | None = None


class EcbDataflowResponse(BaseModel):
    """ECB SDMX dataflow response containing yield curve observations."""
    
    data: list[EcbDataflowObservation] | None = None
    structure: dict[str, object] | None = None
    header: dict[str, object] | None = None