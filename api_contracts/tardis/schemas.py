"""Tardis API: exchanges, instruments, trades, order book, errors, WebSocket."""

from pydantic import BaseModel


class TardisExchange(BaseModel):
    """Exchange entry from Tardis exchanges list."""

    exchange: str | None = None
    name: str | None = None
    website: str | None = None
    info: dict | None = None


class TardisInstrument(BaseModel):
    """Instrument from Tardis instruments API."""

    symbol: str | None = None
    exchange: str | None = None
    name: str | None = None
    info: dict | None = None


class TardisTrade(BaseModel):
    """Trade record (CSV or JSON). Field names follow Tardis HTTP API / downloadable CSV."""

    timestamp: str | None = None
    exchange: str | None = None
    symbol: str | None = None
    price: float | None = None
    size: float | None = None
    side: str | None = None
    trade_id: str | None = None
    info: dict | None = None


class TardisOrderBookLevel(BaseModel):
    """Single level in order book."""

    price: float | None = None
    size: float | None = None


class TardisOrderBook(BaseModel):
    """Order book snapshot."""

    timestamp: str | None = None
    exchange: str | None = None
    symbol: str | None = None
    bids: list[list[float]] | None = None
    asks: list[list[float]] | None = None


class TardisError(BaseModel):
    """Tardis API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None
