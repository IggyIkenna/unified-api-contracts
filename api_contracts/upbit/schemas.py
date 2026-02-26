"""Upbit: market data, order/position feed, errors, WebSocket, FIX, corner cases."""

from pydantic import BaseModel


class UpbitMarket(BaseModel):
    """Upbit market."""

    market: str | None = None
    korean_name: str | None = None
    english_name: str | None = None
    info: dict | None = None


class UpbitTicker(BaseModel):
    """Upbit ticker."""

    market: str | None = None
    trade_price: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    acc_trade_volume_24h: float | None = None
    info: dict | None = None


class UpbitOrder(BaseModel):
    """Upbit order."""

    uuid: str | None = None
    side: str | None = None
    ord_type: str | None = None
    price: float | None = None
    state: str | None = None
    volume: str | None = None
    executed_volume: str | None = None
    info: dict | None = None


class UpbitBalance(BaseModel):
    """Upbit balance."""

    currency: str | None = None
    balance: float | None = None
    locked: float | None = None
    info: dict | None = None


class UpbitError(BaseModel):
    """Upbit API error."""

    error: dict | None = None
    message: str | None = None
