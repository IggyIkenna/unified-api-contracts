"""Bitfinex WebSocket/REST API schemas.

Bitfinex v2 API uses arrays rather than objects for efficiency.
AMOUNT: positive = buy side, negative = sell side.
COUNT in order book: 0 means remove price level, >0 is count at that price.
"""

from __future__ import annotations

from pydantic import BaseModel


class BitfinexTrade(BaseModel):
    """Bitfinex v2 public trade (WS: trades channel, te/tu events).

    REST: GET /v2/trades/{Symbol}/hist
    Array format: [ID, MTS, AMOUNT, PRICE]
    AMOUNT: positive = buy, negative = sell.
    """

    ID: int | None = None
    MTS: int | None = None  # timestamp ms
    AMOUNT: float | None = None  # positive=buy, negative=sell
    PRICE: float | None = None
    trade_type: str | None = None  # "te" = executed, "tu" = updated

    @classmethod
    def from_list(cls, row: list[object], trade_type: str = "te") -> BitfinexTrade:
        """Create from Bitfinex array [ID, MTS, AMOUNT, PRICE]."""
        return cls(
            ID=int(str(row[0])) if len(row) > 0 else None,
            MTS=int(str(row[1])) if len(row) > 1 else None,
            AMOUNT=float(str(row[2])) if len(row) > 2 else None,
            PRICE=float(str(row[3])) if len(row) > 3 else None,
            trade_type=trade_type,
        )


class BitfinexOrderBookLevel(BaseModel):
    """Bitfinex v2 order book level (WS: book channel).

    Array format: [PRICE, COUNT, AMOUNT]
    AMOUNT: positive = bid side, negative = ask side.
    COUNT = 0: remove this price level.
    """

    PRICE: float
    COUNT: int
    AMOUNT: float  # positive=bid, negative=ask

    @classmethod
    def from_list(cls, row: list[object]) -> BitfinexOrderBookLevel:
        """Create from Bitfinex array [PRICE, COUNT, AMOUNT]."""
        return cls(
            PRICE=float(str(row[0])),
            COUNT=int(str(row[1])),
            AMOUNT=float(str(row[2])),
        )


class BitfinexOrderBook(BaseModel):
    """Bitfinex v2 order book snapshot (WS: book channel P0/P1/P2/P3/R0 precision).

    Snapshot is a list of [PRICE, COUNT, AMOUNT] arrays.
    Use R0 precision for raw order books (per-order level).
    """

    bids: list[BitfinexOrderBookLevel] = []
    asks: list[BitfinexOrderBookLevel] = []
    symbol: str | None = None


class BitfinexOrder(BaseModel):
    """Bitfinex v2 private order (WS: order channel, REST: /v2/auth/r/orders).

    Array format (abbreviated): [ID, GID, CID, SYMBOL, MTS_CREATE, MTS_UPDATE,
    AMOUNT, AMOUNT_ORIG, TYPE, TYPE_PREV, ..., FLAGS, STATUS, ..., PRICE, ...]
    STATUS: ACTIVE, EXECUTED, PARTIALLY FILLED, CANCELED, RSN
    TYPE: LIMIT, EXCHANGE LIMIT, MARKET, EXCHANGE MARKET, STOP, STOP LIMIT, etc.
    """

    ID: int | None = None
    GID: int | None = None  # group id
    CID: int | None = None  # client order id
    SYMBOL: str | None = None  # e.g. tBTCUSD
    MTS_CREATE: int | None = None  # creation timestamp ms
    MTS_UPDATE: int | None = None  # last update timestamp ms
    AMOUNT: float | None = None  # positive=buy, negative=sell (remaining)
    AMOUNT_ORIG: float | None = None
    TYPE: str | None = None  # LIMIT, MARKET, STOP, etc.
    TYPE_PREV: str | None = None
    FLAGS: int | None = None
    STATUS: str | None = None  # ACTIVE, EXECUTED, PARTIALLY FILLED, CANCELED
    PRICE: float | None = None
    PRICE_AVG: float | None = None
    PRICE_TRAILING: float | None = None
    PRICE_AUX_LIMIT: float | None = None


class BitfinexFill(BaseModel):
    """Bitfinex v2 private trade/fill (REST: GET /v2/auth/r/trades/{symbol}/hist).

    Array: [ID, PAIR, MTS_CREATE, ORDER_ID, EXEC_AMOUNT, EXEC_PRICE,
    ORDER_TYPE, ORDER_PRICE, MAKER, FEE, FEE_CURRENCY, ...]
    EXEC_AMOUNT: positive=buy, negative=sell.
    MAKER: 1=maker, -1=taker.
    """

    ID: int | None = None
    PAIR: str | None = None
    MTS_CREATE: int | None = None  # ms
    ORDER_ID: int | None = None
    EXEC_AMOUNT: float | None = None  # positive=buy, negative=sell
    EXEC_PRICE: float | None = None
    ORDER_TYPE: str | None = None
    ORDER_PRICE: float | None = None
    MAKER: int | None = None  # 1=maker, -1=taker
    FEE: float | None = None
    FEE_CURRENCY: str | None = None


class BitfinexTicker(BaseModel):
    """Bitfinex v2 trading pair ticker (REST: GET /v2/ticker/{Symbol}).

    Array: [BID, BID_SIZE, ASK, ASK_SIZE, DAILY_CHANGE, DAILY_CHANGE_RELATIVE,
    LAST_PRICE, VOLUME, HIGH, LOW]
    """

    BID: float | None = None
    BID_SIZE: float | None = None
    ASK: float | None = None
    ASK_SIZE: float | None = None
    DAILY_CHANGE: float | None = None
    DAILY_CHANGE_RELATIVE: float | None = None
    LAST_PRICE: float | None = None
    VOLUME: float | None = None
    HIGH: float | None = None
    LOW: float | None = None
    symbol: str | None = None

    @classmethod
    def from_list(cls, row: list[object], symbol: str = "") -> BitfinexTicker:
        """Create from Bitfinex ticker array."""
        return cls(
            BID=float(str(row[0])) if len(row) > 0 else None,
            BID_SIZE=float(str(row[1])) if len(row) > 1 else None,
            ASK=float(str(row[2])) if len(row) > 2 else None,
            ASK_SIZE=float(str(row[3])) if len(row) > 3 else None,
            DAILY_CHANGE=float(str(row[4])) if len(row) > 4 else None,
            DAILY_CHANGE_RELATIVE=float(str(row[5])) if len(row) > 5 else None,
            LAST_PRICE=float(str(row[6])) if len(row) > 6 else None,
            VOLUME=float(str(row[7])) if len(row) > 7 else None,
            HIGH=float(str(row[8])) if len(row) > 8 else None,
            LOW=float(str(row[9])) if len(row) > 9 else None,
            symbol=symbol,
        )


__all__ = [
    "BitfinexFill",
    "BitfinexOrder",
    "BitfinexOrderBook",
    "BitfinexOrderBookLevel",
    "BitfinexTicker",
    "BitfinexTrade",
]
