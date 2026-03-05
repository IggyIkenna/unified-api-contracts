"""Smarkets Exchange API: errors, events, markets, prices, quotes, orders, balances.

Ref: https://smarkets.com/developer-api
"""

from __future__ import annotations

from pydantic import BaseModel


class SmarketsErrorResponse(BaseModel, frozen=True):
    """Smarkets API error response."""

    error: str = ""
    description: str = ""


class SmarketsEvent(BaseModel, frozen=True):
    id: str = ""
    name: str = ""


class SmarketsEventsResponse(BaseModel, frozen=True):
    events: list[SmarketsEvent] = []


class SmarketsMarket(BaseModel, frozen=True):
    id: str = ""
    name: str = ""
    type: str = ""


class SmarketsMarketsResponse(BaseModel, frozen=True):
    markets: list[SmarketsMarket] = []


class SmarketsBackPrice(BaseModel, frozen=True):
    price: int = 0


class SmarketsContract(BaseModel, frozen=True):
    id: str = ""
    name: str = ""


class SmarketsQuote(BaseModel, frozen=True):
    contract: SmarketsContract = SmarketsContract()
    back: list[SmarketsBackPrice] = []


class SmarketsQuotesResponse(BaseModel, frozen=True):
    quotes: list[SmarketsQuote] = []


class SmarketsOrderResponse(BaseModel, frozen=True):
    id: str = ""


class SmarketsPriceLevel(BaseModel, frozen=True):
    """Single back/lay price level."""

    price: float | None = None
    size: float | None = None


class SmarketsOrderBook(BaseModel, frozen=True):
    """Smarkets order book for a single runner."""

    market_id: str | None = None
    runner_id: str | None = None
    backs: list[SmarketsPriceLevel] | None = None
    lays: list[SmarketsPriceLevel] | None = None


class SmarketsBalanceInfo(BaseModel, frozen=True):
    available: str = "0"


class SmarketsAccountResponse(BaseModel, frozen=True):
    balance: SmarketsBalanceInfo = SmarketsBalanceInfo()
