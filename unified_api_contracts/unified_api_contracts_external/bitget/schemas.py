"""Bitget REST/WebSocket API schemas."""

from __future__ import annotations

__api_version__ = "v2"  # matches provider_api_versions.yaml


from pydantic import BaseModel


class BitgetTrade(BaseModel):
    """Bitget public trade (REST: GET /api/v2/spot/market/fills, WS: trade channel).

    side: buy or sell.
    ts: timestamp ms as string.
    """

    symbol: str | None = None
    tradeId: str | None = None
    side: str | None = None  # buy, sell
    fillPrice: str | None = None
    baseVolume: str | None = None
    quoteVolume: str | None = None
    ts: str | None = None  # timestamp ms


class BitgetOrderBook(BaseModel):
    """Bitget order book (REST: GET /api/v2/spot/market/orderbook, WS: books channel).

    asks/bids: [[price, size], ...] strings.
    ts: timestamp ms as string.
    """

    asks: list[list[str]] = []
    bids: list[list[str]] = []
    ts: str | None = None


class BitgetFeeDetail(BaseModel):
    """Bitget order fee detail sub-object."""

    feeCoin: str | None = None
    totalDeductionFee: str | None = None
    newFees: dict[str, str] | None = None


class BitgetOrder(BaseModel):
    """Bitget private order (REST: GET /api/v2/spot/trade/orderInfo).

    status: live, partially_fill, filled, cancelled, expired, none.
    orderType: limit, market.
    side: buy, sell.
    """

    userId: str | None = None
    symbol: str | None = None
    orderId: str | None = None
    clientOid: str | None = None
    priceAvg: str | None = None
    size: str | None = None
    orderType: str | None = None  # limit, market
    side: str | None = None  # buy, sell
    status: str | None = None  # live, partially_fill, filled, cancelled, expired
    baseVolume: str | None = None
    quoteVolume: str | None = None
    enterPointSource: str | None = None
    feeDetail: BitgetFeeDetail | None = None
    orderSource: str | None = None
    cTime: str | None = None  # creation timestamp ms
    uTime: str | None = None  # update timestamp ms
    price: str | None = None  # limit order price
    force: str | None = None  # time in force: normal, post_only, fok, ioc


class BitgetFill(BaseModel):
    """Bitget private fill/trade (REST: GET /api/v2/spot/trade/fills)."""

    userId: str | None = None
    symbol: str | None = None
    orderId: str | None = None
    tradeId: str | None = None
    orderType: str | None = None
    side: str | None = None
    priceAvg: str | None = None
    size: str | None = None
    amount: str | None = None  # quote amount
    feeDetail: BitgetFeeDetail | None = None
    tradeScope: str | None = None  # taker, maker
    cTime: str | None = None  # trade timestamp ms
    uTime: str | None = None


class BitgetTicker(BaseModel):
    """Bitget spot ticker (REST: GET /api/v2/spot/market/tickers)."""

    symbol: str | None = None
    high24h: str | None = None
    low24h: str | None = None
    close: str | None = None
    quoteVol: str | None = None
    baseVol: str | None = None
    usdtVol: str | None = None
    bidPr: str | None = None
    askPr: str | None = None
    bidSz: str | None = None
    askSz: str | None = None
    openUtc: str | None = None
    ts: str | None = None
    changeUtc24h: str | None = None
    change24h: str | None = None


__all__ = [
    "BitgetFeeDetail",
    "BitgetFill",
    "BitgetOrder",
    "BitgetOrderBook",
    "BitgetTicker",
    "BitgetTrade",
]
