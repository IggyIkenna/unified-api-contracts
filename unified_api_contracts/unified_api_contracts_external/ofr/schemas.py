"""Pydantic schemas for OFR (Office of Financial Research) data.

Source: https://www.financialresearch.gov/
No auth required. Free open data from the US Treasury OFR.

Used by unified-market-interface OFRAdapter for CDS spread indices and financial stability data.
"""

from pydantic import BaseModel


class OfrCdsSpreadIndex(BaseModel):
    """Single CDS spread observation from OFR."""

    series_id: str | None = None
    date: str | None = None
    value: float | None = None
    index_name: str | None = None
    tenor: str | None = None
    sector: str | None = None


class OfrCdsResponse(BaseModel):
    """OFR CDS response containing spread indices and financial stability data."""

    data: list[OfrCdsSpreadIndex] | None = None
    metadata: dict[str, object] | None = None
    source: str | None = None
