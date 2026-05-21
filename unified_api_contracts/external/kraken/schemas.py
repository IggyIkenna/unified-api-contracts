"""Kraken Spot REST API schemas (api.kraken.com/0/public/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KrakenTickerData(BaseModel):
    """Single ticker entry from GET /0/public/Ticker."""

    a: list[str] = Field(..., description="Ask [price, whole lot volume, lot volume]")
    b: list[str] = Field(..., description="Bid [price, whole lot volume, lot volume]")
    c: list[str] = Field(..., description="Last trade closed [price, lot volume]")
    v: list[str] = Field(..., description="Volume [today, last 24h]")
    p: list[str] = Field(..., description="Volume weighted average price [today, last 24h]")
    t: list[int] = Field(..., description="Number of trades [today, last 24h]")
    l: list[str] = Field(..., description="Low [today, last 24h]")
    h: list[str] = Field(..., description="High [today, last 24h]")
    o: str = Field(..., description="Today's opening price")


class KrakenTickerResponse(BaseModel):
    """Top-level Kraken Ticker response."""

    error: list[str] = Field(default_factory=list)
    result: dict[str, KrakenTickerData] = Field(default_factory=dict)
