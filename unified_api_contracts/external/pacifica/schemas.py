"""Pacifica perp funding rate API schemas (api.pacifica.fi/api/v1/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PacificaFundingRateEntry(BaseModel):
    """Single historical funding rate record from Pacifica."""

    symbol: str = Field(..., description="Trading pair symbol (e.g. SOL-USDC)")
    funding_rate: float = Field(..., description="Funding rate for this interval")
    timestamp: int = Field(..., description="Unix timestamp (seconds)")
    mark_price: float | None = Field(None, description="Mark price at settlement")


class PacificaFundingRateResponse(BaseModel):
    """Response from GET /api/v1/funding_rate/history."""

    data: list[PacificaFundingRateEntry] = Field(default_factory=list)
    total: int | None = Field(None, description="Total record count")
