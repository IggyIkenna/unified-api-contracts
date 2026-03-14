"""Huobi / HTX REST/WebSocket API schemas.

Huobi rebranded to HTX in 2023. API endpoints remain under huobi.com/htx.
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from pydantic import BaseModel


class HuobiTrade(BaseModel):
    """Huobi/HTX public trade (REST: GET /market/history/trade, WS: market.{symbol}.trade.detail).

    direction: buy or sell.
    ts: timestamp ms.
    """

    id: int | str | None = None
    ts: int | None = None  # event timestamp ms
    tradeId: int | str | None = None
    amount: float | str | None = None
    price: float | str | None = None
    direction: str | None = None  # buy, sell
    trade_time: int | None = None  # inner trade timestamp ms


class HuobiOrderBook(BaseModel):
    """Huobi/HTX order book (REST: GET /market/depth, WS: market.{symbol}.depth.step0).

    bids/asks: [[price, amount], ...] floats.
    """

    ts: int | None = None
    version: int | None = None
    bids: list[list[float]] = []
    asks: list[list[float]] = []


class HuobiOrder(BaseModel):
    """Huobi/HTX private order (REST: GET /v1/order/orders/{order-id}).

    state: submitted, partial-filled, filled, partial-canceled, canceled, created.
    type: buy-market, sell-market, buy-limit, sell-limit, buy-ioc, sell-ioc, etc.
    """

    id: int | str | None = None
    client_order_id: str | None = None
    symbol: str | None = None
    account_id: int | None = None
    amount: str | None = None
    price: str | None = None
    created_at: int | None = None  # ms
    updated_at: int | None = None  # ms
    type: str | None = None  # buy-limit, sell-limit, buy-market, sell-market, etc.
    field_amount: str | None = None  # filled amount
    field_cash_amount: str | None = None
    field_fees: str | None = None  # filled fees
    finished_at: int | None = None
    user_id: int | None = None
    source: str | None = None
    state: str | None = None  # submitted, partial-filled, filled, canceled, etc.
    canceled_at: int | None = None
    exchange: str | None = None
    batch: str | None = None


class HuobiFill(BaseModel):
    """Huobi/HTX private trade/fill (REST: GET /v1/order/orders/{order-id}/matchresults)."""

    id: int | str | None = None
    order_id: int | str | None = None
    match_id: int | str | None = None
    symbol: str | None = None
    type: str | None = None  # buy-limit, sell-limit, etc.
    source: str | None = None  # api, spot-api, etc.
    price: str | None = None
    filled_amount: str | None = None
    filled_fees: str | None = None
    filled_points: str | None = None
    fee_deduct_currency: str | None = None
    fee_deduct_state: str | None = None
    role: str | None = None  # taker, maker
    created_at: int | None = None


class HuobiTicker(BaseModel):
    """Huobi/HTX merged ticker (REST: GET /market/detail/merged)."""

    id: int | None = None
    ts: int | None = None
    close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    amount: float | None = None
    count: int | None = None
    vol: float | None = None
    bid: list[float] | None = None  # [price, qty]
    ask: list[float] | None = None  # [price, qty]


__all__ = [
    "HuobiFill",
    "HuobiOrder",
    "HuobiOrderBook",
    "HuobiTicker",
    "HuobiTrade",
]
