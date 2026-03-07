"""Binance WebSocket schemas: private streams, order/account updates."""

__api_version__ = "v3"  # matches provider_api_versions.yaml

from decimal import Decimal

from pydantic import BaseModel


class BinanceMarkPriceUpdate(BaseModel):
    """Binance WebSocket mark price update (futures @markPrice stream).

    Stream: {symbol}@markPrice or {symbol}@markPrice@1s
    """

    e: str  # event type = "markPriceUpdate"
    E: int  # event time (ms)
    s: str  # symbol
    p: Decimal  # mark price
    i: Decimal  # index price
    P: Decimal  # estimated settle price (only on last funding)
    r: Decimal  # funding rate
    T: int  # next funding time (ms)


class BinanceLiquidationOrder(BaseModel):
    """Binance WebSocket liquidation order (futures !forceOrder@arr or {sym}@forceOrder)."""

    e: str  # event type = "forceOrder"
    E: int  # event time
    o: dict[str, object]  # order fields: s=symbol, S=side, o=type, q=qty, p=price, ap=avgPrice,
    # X=orderStatus, l=lastFilledQty, z=cumFilledQty, T=tradeTime


class BinanceOrderTradeUpdate(BaseModel):
    """Binance WebSocket private order/trade update (futures ORDER_TRADE_UPDATE).

    Stream: wss://fstream.binance.com/ws/<listenKey>
    Covers: NEW, PARTIALLY_FILLED, FILLED, CANCELED, EXPIRED, AMENDMENT
    """

    e: str  # "ORDER_TRADE_UPDATE"
    E: int  # event time (ms)
    T: int  # transaction time (ms)
    # order object fields (prefixed o. in raw message, flattened here)
    o_s: str  # symbol (from o.s)
    o_c: str  # client order id (o.c); "autoclose-XXX"=liquidation, "adl_autoclose"=ADL
    o_S: str  # side: BUY or SELL
    o_o: str  # order type: LIMIT, MARKET, STOP_MARKET, LIQUIDATION, etc.
    o_x: str  # execution type: NEW, CANCELED, TRADE, EXPIRED, CALCULATED, AMENDMENT
    o_X: str  # order status: NEW, PARTIALLY_FILLED, FILLED, CANCELED, EXPIRED, EXPIRED_IN_MATCH
    o_i: int  # order id
    o_l: Decimal  # last filled qty
    o_z: Decimal  # cumulative filled qty
    o_L: Decimal  # last filled price
    o_t: int  # trade id (-1 if no fill)
    o_n: Decimal | None = None  # commission amount
    o_N: str | None = None  # commission asset
    o_rp: Decimal | None = None  # realized PnL
    o_ps: str | None = None  # position side: LONG, SHORT, BOTH
    o_m: bool | None = None  # is maker
    o_R: bool | None = None  # reduce only
    o_er: str | None = None  # expiry reason (0-9)


class BinanceAccountUpdate(BaseModel):
    """Binance WebSocket private account/position update (futures ACCOUNT_UPDATE).

    Stream: wss://fstream.binance.com/ws/<listenKey>
    """

    e: str  # "ACCOUNT_UPDATE"
    E: int  # event time (ms)
    T: int  # transaction time (ms)
    a_m: str  # reason: ORDER, DEPOSIT, WITHDRAW, FUNDING_FEE, MARGIN_TRANSFER, etc.
    a_B: list[dict[str, object]]  # balance updates
    a_P: list[dict[str, object]]  # position updates


class BinanceWebSocketSubscribe(BaseModel):
    """Binance WebSocket subscription request."""

    method: str  # "SUBSCRIBE" or "UNSUBSCRIBE" or "LIST_SUBSCRIPTIONS"
    params: list[str]  # e.g. ["btcusdt@trade", "btcusdt@depth"]
    id: int  # request id for tracking responses


class BinanceWebSocketPing(BaseModel):
    """Binance WebSocket ping (server→client every 20s; client must respond with pong)."""

    # Binance sends a raw PING frame (no JSON body); this is a marker schema
    # Client sends a PONG frame back. If no pong within 60s, server disconnects.
    pass


class BinanceWebSocketClose(BaseModel):
    """Binance WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal/EOF, 1008=policy violation.
    """

    code: int
    reason: str | None = None


class BinanceListenKeyCreate(BaseModel):
    """Binance listen key response (POST /fapi/v1/listenKey for futures user data stream).

    listenKey is valid for 60 minutes. Extend via PUT every 30 minutes.
    Max connection lifetime: 24 hours.
    """

    listenKey: str
