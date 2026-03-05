"""Kraken REST/WebSocket API schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class KrakenTradeDescr(BaseModel):
    """Kraken order description sub-object."""

    pair: str | None = None
    type: str | None = None  # buy or sell
    ordertype: str | None = None  # market, limit, etc.
    price: str | None = None
    price2: str | None = None
    leverage: str | None = None
    order: str | None = None
    close: str | None = None


class KrakenTrade(BaseModel):
    """Kraken public trade (REST: GET /0/public/Trades, WS: trade channel).

    REST array format: [price, volume, time, buy_sell, market_limit, misc, trade_id]
    """

    price: Decimal | str
    vol: Decimal | str
    time: Decimal | float  # Unix timestamp with decimal seconds
    buy_sell: str  # "b" = buy, "s" = sell
    market_limit: str  # "m" = market, "l" = limit
    misc: str | None = None
    trade_id: str | int | None = None

    @classmethod
    def from_list(cls, row: list[object]) -> KrakenTrade:
        """Create from Kraken REST array [price, vol, time, buy_sell, market_limit, misc, trade_id]."""
        return cls(
            price=str(row[0]) if len(row) > 0 else "0",
            vol=str(row[1]) if len(row) > 1 else "0",
            time=float(str(row[2])) if len(row) > 2 else 0.0,
            buy_sell=str(row[3]) if len(row) > 3 else "b",
            market_limit=str(row[4]) if len(row) > 4 else "m",
            misc=str(row[5]) if len(row) > 5 else None,
            trade_id=str(row[6]) if len(row) > 6 else None,
        )


class KrakenOrderBookLevel(BaseModel):
    """Single Kraken order book level: [price, volume, timestamp]."""

    price: str
    vol: str
    timestamp: float | None = None

    @classmethod
    def from_list(cls, row: list[object]) -> KrakenOrderBookLevel:
        """Create from Kraken order book array [price, vol, time]."""
        return cls(
            price=str(row[0]),
            vol=str(row[1]),
            timestamp=float(str(row[2])) if len(row) > 2 else None,
        )


class KrakenOrderBook(BaseModel):
    """Kraken order book (REST: GET /0/public/Depth, WS: book channel).

    bids/asks: [[price, vol, time], ...]
    """

    bids: list[list[str]] = []
    asks: list[list[str]] = []


class KrakenOrderBook_WS(BaseModel):  # noqa: N801
    """Kraken WebSocket order book snapshot/update (WS: book-10, book-25, etc.)."""

    as_: list[list[str]] = []  # asks snapshot (field name "as" is reserved)
    bs: list[list[str]] = []  # bids snapshot
    a: list[list[str]] = []  # asks update
    b: list[list[str]] = []  # bids update
    c: str | None = None  # checksum


class KrakenOrder(BaseModel):
    """Kraken private order (REST: GET /0/private/OpenOrders, ClosedOrders)."""

    refid: str | None = None
    userref: int | None = None
    status: str | None = None  # open, closed, canceled, pending, expired
    opentm: float | None = None
    starttm: float | None = None
    expiretm: float | None = None
    descr: KrakenTradeDescr | None = None
    vol: str | None = None
    vol_exec: str | None = None
    cost: str | None = None
    fee: str | None = None
    price: str | None = None  # avg price
    stopprice: str | None = None
    limitprice: str | None = None
    misc: str | None = None
    oflags: str | None = None
    order_id: str | None = None  # injected key from response dict


class KrakenTicker(BaseModel):
    """Kraken spot ticker (REST: GET /0/public/Ticker, WS: ticker channel).

    a: [ask, wholeLotVol, lotVol]
    b: [bid, wholeLotVol, lotVol]
    c: [lastTradeClosed, lotVol]
    v: [today, last24h]
    p: [vwap today, vwap last24h]
    t: [numTrades today, numTrades last24h]
    l: [low today, low last24h]
    h: [high today, high last24h]
    o: open price today
    """

    a: list[str] = []  # ask
    b: list[str] = []  # bid
    c: list[str] = []  # last trade closed
    v: list[str] = []  # volume
    p: list[str] = []  # vwap
    t: list[int] = []  # num trades
    l: list[str] = []  # low  # noqa: E741
    h: list[str] = []  # high
    o: str | None = None  # open


class KrakenFill(BaseModel):
    """Kraken private user trade/fill (REST: GET /0/private/TradesHistory)."""

    ordertxid: str | None = None
    postxid: str | None = None
    pair: str | None = None
    time: float | None = None
    type: str | None = None  # buy or sell
    ordertype: str | None = None  # market, limit
    price: str | None = None
    cost: str | None = None
    fee: str | None = None
    vol: str | None = None
    margin: str | None = None
    misc: str | None = None
    trade_id: str | None = None  # injected key


__all__ = [
    "KrakenFill",
    "KrakenOrder",
    "KrakenOrderBook",
    "KrakenOrderBookLevel",
    "KrakenOrderBook_WS",
    "KrakenTicker",
    "KrakenTrade",
    "KrakenTradeDescr",
]
