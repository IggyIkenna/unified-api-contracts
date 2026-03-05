"""Smarkets API response schemas."""

from pydantic import BaseModel


class SmarketsPriceLevel(BaseModel):
    """Single back/lay level."""

    price: float | None = None
    size: float | None = None


class SmarketsOrderBook(BaseModel):
    """Smarkets order book schema."""

    market_id: str | None = None
    runner_id: str | None = None
    backs: list[SmarketsPriceLevel] | None = None
    lays: list[SmarketsPriceLevel] | None = None


class SmarketsMarket(BaseModel):
    """Smarkets market schema."""

    id: str | None = None
    name: str | None = None


class SmarketsEvent(BaseModel):
    """Smarkets event schema."""

    id: str | None = None
    name: str | None = None
