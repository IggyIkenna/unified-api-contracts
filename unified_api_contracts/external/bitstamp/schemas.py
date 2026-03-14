"""Bitstamp REST/WebSocket API schemas."""

from __future__ import annotations

__api_version__ = "v2"  # matches provider_api_versions.yaml


from pydantic import BaseModel


class BitstampTrade(BaseModel):
    """Bitstamp public trade (REST: GET /api/v2/transactions/{currency_pair}/, WS: live_trades).

    type: 0=buy, 1=sell.
    """

    id: int | str | None = None
    timestamp: str | None = None  # Unix timestamp as string
    amount: str | float | None = None
    amount_str: str | None = None
    price: str | float | None = None
    price_str: str | None = None
    type: int | None = None  # 0=buy, 1=sell
    buy_order_id: int | None = None
    sell_order_id: int | None = None
    microtimestamp: str | None = None  # WS: microsecond timestamp


class BitstampOrderBook(BaseModel):
    """Bitstamp order book (REST: GET /api/v2/order_book/{pair}/, WS: order_book_{pair}).

    bids/asks: [[price, amount], ...] strings.
    timestamp: Unix timestamp as string.
    microtimestamp: WS microsecond timestamp.
    """

    timestamp: str | None = None
    microtimestamp: str | None = None
    bids: list[list[str]] = []
    asks: list[list[str]] = []


class BitstampOrder(BaseModel):
    """Bitstamp private order (REST: GET /api/v2/open_orders/{pair}/).

    type: 0=buy, 1=sell.
    status: Open, Finished, Canceled.
    """

    id: int | str | None = None
    datetime: str | None = None
    type: str | None = None  # "0"=buy, "1"=sell
    price: str | None = None
    amount: str | None = None
    currency_pair: str | None = None
    client_order_id: str | None = None
    status: str | None = None  # Open, Finished, Canceled, Expired
    amount_remaining: str | None = None


class BitstampFill(BaseModel):
    """Bitstamp private user trade (REST: GET /api/v2/user_transactions/).

    type: 2=trade.
    """

    id: int | str | None = None
    datetime: str | None = None
    type: str | None = None  # "0"=deposit, "1"=withdrawal, "2"=trade
    order_id: int | str | None = None
    fee: str | None = None
    usd: str | None = None
    btc: str | None = None
    eur: str | None = None
    btc_usd: str | None = None  # price
    # Generic: the pair currency amounts are named dynamically (e.g. eth, eth_usd)
    extra: dict[str, str | float | int | None] | None = None


class BitstampTicker(BaseModel):
    """Bitstamp ticker (REST: GET /api/v2/ticker/{pair}/)."""

    last: str | None = None
    bid: str | None = None
    ask: str | None = None
    high: str | None = None
    low: str | None = None
    vwap: str | None = None
    volume: str | None = None
    open: str | None = None
    open_24: str | None = None
    timestamp: str | None = None
    side: str | None = None  # "0"=buy, "1"=sell for last trade


__all__ = [
    "BitstampFill",
    "BitstampOrder",
    "BitstampOrderBook",
    "BitstampTicker",
    "BitstampTrade",
]
