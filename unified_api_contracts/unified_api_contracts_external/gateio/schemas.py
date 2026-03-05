"""Gate.io REST/WebSocket API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class GateioTrade(BaseModel):
    """Gate.io public trade (REST: GET /api/v4/spot/trades, WS: spot.trades).

    create_time_ms: Unix time in milliseconds (str).
    side: buy or sell.
    """

    id: str | None = None
    create_time: str | None = None  # Unix timestamp seconds (str)
    create_time_ms: str | None = None  # Unix timestamp ms (str)
    side: str | None = None  # buy, sell
    amount: str | None = None
    price: str | None = None
    currency_pair: str | None = None
    trade_seq: str | int | None = None


class GateioOrderBook(BaseModel):
    """Gate.io order book (REST: GET /api/v4/spot/order_book, WS: spot.order_book).

    asks/bids: [[price, size], ...] strings.
    """

    id: int | None = None
    current: int | None = None  # current timestamp ms
    update: int | None = None  # last update timestamp ms
    asks: list[list[str]] = []
    bids: list[list[str]] = []


class GateioOrder(BaseModel):
    """Gate.io private order (REST: GET /api/v4/spot/orders/{order_id}).

    status: open, closed, cancelled.
    type: limit, market.
    account: spot, margin, cross_margin.
    """

    id: str | None = None
    text: str | None = None  # client order id
    create_time: str | None = None
    update_time: str | None = None
    create_time_ms: int | None = None
    update_time_ms: int | None = None
    status: str | None = None  # open, closed, cancelled
    currency_pair: str | None = None
    type: str | None = None  # limit, market
    account: str | None = None  # spot, margin, cross_margin
    side: str | None = None  # buy, sell
    amount: str | None = None
    price: str | None = None
    time_in_force: str | None = None  # gtc, ioc, poc, fok
    iceberg: str | None = None
    auto_repay: bool | None = None
    left: str | None = None  # remaining amount
    filled_amount: str | None = None
    fill_price: str | None = None  # total fill price
    avg_deal_price: str | None = None  # average fill price
    fee: str | None = None
    fee_currency: str | None = None
    point_fee: str | None = None
    gt_fee: str | None = None
    gt_maker_fee: str | None = None
    gt_taker_fee: str | None = None
    rebated_fee: str | None = None
    rebated_fee_currency: str | None = None


class GateioFill(BaseModel):
    """Gate.io private trade/fill (REST: GET /api/v4/spot/my_trades)."""

    id: str | None = None
    user_id: int | None = None
    order_id: str | None = None
    currency_pair: str | None = None
    create_time: str | None = None
    create_time_ms: str | None = None
    side: str | None = None  # buy, sell
    role: str | None = None  # taker, maker
    amount: str | None = None
    price: str | None = None
    fee: str | None = None
    fee_currency: str | None = None
    point_fee: str | None = None
    gt_fee: str | None = None
    sequence_id: str | None = None


class GateioTicker(BaseModel):
    """Gate.io spot ticker (REST: GET /api/v4/spot/tickers)."""

    currency_pair: str | None = None
    last: str | None = None
    lowest_ask: str | None = None
    highest_bid: str | None = None
    change_percentage: str | None = None
    change_utc0: str | None = None
    change_utc8: str | None = None
    base_volume: str | None = None
    quote_volume: str | None = None
    high_24h: str | None = None
    low_24h: str | None = None


__all__ = [
    "GateioFill",
    "GateioOrder",
    "GateioOrderBook",
    "GateioTicker",
    "GateioTrade",
]
