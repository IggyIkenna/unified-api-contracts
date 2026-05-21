"""Kraken Futures REST API schemas (futures.kraken.com/derivatives/api/v3/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KrakenFuturesTicker(BaseModel):
    """Single ticker from GET /derivatives/api/v3/tickers."""

    symbol: str = Field(..., description="Instrument symbol (e.g. PI_XBTUSD)")
    bid: float | None = Field(None, description="Best bid price")
    bidSize: float | None = Field(None, description="Best bid quantity")
    ask: float | None = Field(None, description="Best ask price")
    askSize: float | None = Field(None, description="Best ask quantity")
    vol24h: float | None = Field(None, description="24-hour volume")
    last: float | None = Field(None, description="Last traded price")
    lastTime: str | None = Field(None, description="ISO8601 timestamp of last trade")
    markPrice: float | None = Field(None, description="Current mark price")
    indexPrice: float | None = Field(None, description="Index price (spot reference)")
    fundingRate: float | None = Field(None, description="Current funding rate")
    fundingRatePrediction: float | None = Field(None, description="Predicted next funding rate")
    openInterest: float | None = Field(None, description="Open interest in contracts")


class KrakenFuturesTickersResponse(BaseModel):
    """Top-level response from GET /derivatives/api/v3/tickers."""

    result: str = Field(..., description="'success' on OK")
    tickers: list[KrakenFuturesTicker] = Field(default_factory=list)
