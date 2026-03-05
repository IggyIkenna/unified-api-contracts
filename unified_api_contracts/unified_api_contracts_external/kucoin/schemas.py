"""KuCoin REST/WebSocket API schemas."""

from __future__ import annotations

from pydantic import BaseModel


class KucoinTrade(BaseModel):
    """KuCoin public trade (REST: GET /api/v1/market/histories, WS: /market/match).

    WS also delivers: sequence, side, size, price, bestBidSize, bestBidPrice,
    bestAskSize, bestAskPrice, type, time, tradeId.
    """

    sequence: str | None = None
    side: str | None = None  # buy or sell
    size: str | None = None
    price: str | None = None
    bestBidSize: str | None = None
    bestBidPrice: str | None = None
    bestAskSize: str | None = None
    bestAskPrice: str | None = None
    type: str | None = None  # match, open, done
    time: str | int | None = None  # nanoseconds timestamp (str for large int precision)
    tradeId: str | None = None


class KucoinOrderBook(BaseModel):
    """KuCoin order book (REST: GET /api/v1/market/orderbook/level2_100).

    sequence: sequence number for delta updates.
    bids/asks: [[price, size], ...] strings.
    """

    sequence: str | None = None
    bids: list[list[str]] = []
    asks: list[list[str]] = []
    time: str | int | None = None


class KucoinOrder(BaseModel):
    """KuCoin private order (REST: GET /api/v1/orders/{orderId}).

    status: active, done.
    type: limit, market.
    side: buy, sell.
    """

    id: str | None = None
    symbol: str | None = None
    type: str | None = None  # limit, market
    side: str | None = None  # buy, sell
    price: str | None = None
    size: str | None = None
    funds: str | None = None
    dealFunds: str | None = None
    dealSize: str | None = None
    fee: str | None = None
    feeCurrency: str | None = None
    stp: str | None = None  # self-trade prevention
    timeInForce: str | None = None  # GTC, GTT, IOC, FOK
    timeInForceExt: str | None = None
    postOnly: bool | None = None
    isActive: bool | None = None
    status: str | None = None  # active, done
    cancelExist: bool | None = None
    createdAt: int | None = None  # ms
    updatedAt: int | None = None  # ms
    tradeType: str | None = None  # TRADE, MARGIN_TRADE


class KucoinFill(BaseModel):
    """KuCoin private fill/trade (REST: GET /api/v1/fills)."""

    symbol: str | None = None
    tradeId: str | None = None
    orderId: str | None = None
    counterOrderId: str | None = None
    side: str | None = None
    liquidity: str | None = None  # taker, maker
    forceTaker: bool | None = None
    price: str | None = None
    size: str | None = None
    funds: str | None = None
    fee: str | None = None
    feeRate: str | None = None
    feeCurrency: str | None = None
    stop: str | None = None
    type: str | None = None
    createdAt: int | None = None
    tradeType: str | None = None


class KucoinTicker(BaseModel):
    """KuCoin ticker (REST: GET /api/v1/market/stats, WS: /market/snapshot)."""

    symbol: str | None = None
    symbolName: str | None = None
    buy: str | None = None
    sell: str | None = None
    changeRate: str | None = None
    changePrice: str | None = None
    high: str | None = None
    low: str | None = None
    vol: str | None = None
    volValue: str | None = None
    last: str | None = None
    averagePrice: str | None = None
    takerFeeRate: str | None = None
    makerFeeRate: str | None = None
    takerCoefficient: str | None = None
    makerCoefficient: str | None = None


__all__ = [
    "KucoinFill",
    "KucoinOrder",
    "KucoinOrderBook",
    "KucoinTicker",
    "KucoinTrade",
]
