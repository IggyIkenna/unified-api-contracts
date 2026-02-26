"""Pydantic schemas for Yahoo Finance adapter responses. Full surface: market data, errors, edge cases."""

from pydantic import BaseModel


class YahooQuote(BaseModel):
    """Yahoo Finance quote (price data)."""

    symbol: str | None = None
    shortName: str | None = None
    regularMarketPrice: float | None = None
    regularMarketChange: float | None = None
    regularMarketVolume: int | None = None
    bid: float | None = None
    ask: float | None = None
    info: dict | None = None


class YahooChartResult(BaseModel):
    """Chart/quote result wrapper."""

    result: list | None = None
    error: dict | None = None


class YahooError(BaseModel):
    """Yahoo Finance error."""

    code: str | None = None
    description: str | None = None
