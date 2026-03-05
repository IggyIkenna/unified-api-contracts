"""Tardis.dev API contracts (historical market data, exchanges, instruments)."""

from pydantic import BaseModel


class TardisOptionQuote(BaseModel):
    """Tardis.dev normalized options quote (historical replay).

    Tardis normalizes options data across Deribit, OKX, Bybit, etc.
    Fields follow the Tardis normalized format for options quotes.
    """

    symbol: str  # e.g. BTC-28JUN24-50000-C (Deribit-style)
    exchange: str | None = None  # source exchange e.g. deribit, okex, bybit
    timestamp: int  # Unix ms
    local_timestamp: int | None = None  # Unix ms
    underlying_price: float | None = None
    strike_price: float | None = None
    option_type: str | None = None  # call or put
    expiration: int | None = None  # Unix ms
    bid_price: float | None = None
    ask_price: float | None = None
    bid_amount: float | None = None
    ask_amount: float | None = None
    mark_price: float | None = None
    mark_iv: float | None = None  # implied vol annualized (e.g. 0.80 = 80%)
    bid_iv: float | None = None
    ask_iv: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    open_interest: float | None = None
