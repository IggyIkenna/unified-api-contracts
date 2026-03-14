"""MEXC Global REST/WebSocket API schemas."""

from __future__ import annotations

__api_version__ = "v3"  # matches provider_api_versions.yaml


from pydantic import BaseModel


class MexcTrade(BaseModel):
    """MEXC public trade (REST: GET /api/v3/trades, WS: spot@public.deals.v3.api@{symbol}).

    isBuyerMaker: true = seller is taker (sell trade), false = buyer is taker (buy trade).
    """

    id: str | None = None
    price: str | None = None
    qty: str | None = None
    quoteQty: str | None = None
    time: int | None = None  # ms
    isBuyerMaker: bool | None = None  # true=seller taker, false=buyer taker
    tradeType: str | None = None  # WS: ASK=sell, BID=buy


class MexcOrderBook(BaseModel):
    """MEXC order book (REST: GET /api/v3/depth, WS: spot@public.limit.depth.v3.api).

    asks/bids: [[price, qty], ...] strings.
    """

    lastUpdateId: int | None = None
    bids: list[list[str]] = []
    asks: list[list[str]] = []
    timestamp: int | None = None  # ms, WS only


class MexcOrder(BaseModel):
    """MEXC private order (REST: GET /api/v3/order).

    status: NEW, PARTIALLY_FILLED, FILLED, CANCELED, PENDING_CANCEL, REJECTED, EXPIRED.
    type: LIMIT, MARKET, LIMIT_MAKER, IMMEDIATE_OR_CANCEL, FILL_OR_KILL.
    """

    symbol: str | None = None
    orderId: str | None = None
    orderListId: int | None = None
    clientOrderId: str | None = None
    price: str | None = None
    origQty: str | None = None
    executedQty: str | None = None
    cummulativeQuoteQty: str | None = None
    status: str | None = None  # NEW, PARTIALLY_FILLED, FILLED, CANCELED, etc.
    timeInForce: str | None = None  # GTC, IOC, FOK, GTX
    type: str | None = None
    side: str | None = None  # BUY, SELL
    stopPrice: str | None = None
    icebergQty: str | None = None
    time: int | None = None  # creation ms
    updateTime: int | None = None  # ms
    isWorking: bool | None = None
    origQuoteOrderQty: str | None = None
    avgPrice: str | None = None


class MexcFill(BaseModel):
    """MEXC private trade/fill (REST: GET /api/v3/myTrades)."""

    symbol: str | None = None
    id: str | None = None
    orderId: str | None = None
    orderListId: int | None = None
    price: str | None = None
    qty: str | None = None
    quoteQty: str | None = None
    commission: str | None = None
    commissionAsset: str | None = None
    time: int | None = None  # ms
    isBuyer: bool | None = None
    isMaker: bool | None = None
    isBestMatch: bool | None = None
    tradeGroupId: int | None = None
    selfTradePrevention: str | None = None


class MexcTicker(BaseModel):
    """MEXC 24hr ticker (REST: GET /api/v3/ticker/24hr)."""

    symbol: str | None = None
    priceChange: str | None = None
    priceChangePercent: str | None = None
    prevClosePrice: str | None = None
    lastPrice: str | None = None
    bidPrice: str | None = None
    bidQty: str | None = None
    askPrice: str | None = None
    askQty: str | None = None
    openPrice: str | None = None
    highPrice: str | None = None
    lowPrice: str | None = None
    volume: str | None = None
    quoteVolume: str | None = None
    openTime: int | None = None
    closeTime: int | None = None
    count: int | None = None


__all__ = [
    "MexcFill",
    "MexcOrder",
    "MexcOrderBook",
    "MexcTicker",
    "MexcTrade",
]
