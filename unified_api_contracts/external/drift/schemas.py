"""Pydantic schemas for Drift Protocol API (data.api.drift.trade/stats/markets)."""

from pydantic import BaseModel, Field


class DriftMarket(BaseModel):
    """A single Drift Protocol perpetual or spot market."""

    marketIndex: int = Field(description="Drift internal market index")
    symbol: str = Field(description="Market symbol (e.g. SOL-PERP, BTC-PERP)")
    marketType: str = Field(description="PERP or SPOT")
    currentOraclePrice: float = Field(description="Current oracle price (USD)")
    markPrice: float = Field(description="Current mark price (USD)")
    openInterestNotional: float = Field(description="Open interest in USD")
    volumeNotional24h: float = Field(description="24h volume in USD")
    fundingRate1h: float | None = Field(default=None, description="1-hour funding rate (basis points)")


class DriftMarketsResponse(BaseModel):
    """Response from GET /stats/markets."""

    markets: list[DriftMarket]
