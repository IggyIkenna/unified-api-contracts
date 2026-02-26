"""Binance REST/WebSocket: market data, order/position, errors, WebSocket payloads."""

from decimal import Decimal

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


class BinanceTicker(BaseModel):
    """Binance 24hr ticker statistics (REST or WebSocket)."""

    symbol: str
    priceChange: Decimal
    priceChangePercent: Decimal
    weightedAvgPrice: Decimal
    prevClosePrice: Decimal
    lastPrice: Decimal
    lastQty: Decimal
    bidPrice: Decimal
    bidQty: Decimal
    askPrice: Decimal
    askQty: Decimal
    openPrice: Decimal
    highPrice: Decimal
    lowPrice: Decimal
    volume: Decimal
    quoteVolume: Decimal
    openTime: int  # timestamp
    closeTime: int  # timestamp
    firstId: int
    lastId: int
    count: int


class BinanceOrderBook(BaseModel):
    """Binance order book (REST snapshot or WebSocket)."""

    lastUpdateId: int | None = None
    bids: list[list[str]] = []  # [[price, qty], ...]
    asks: list[list[str]] = []
    info: dict | None = None


class BinanceTrade(BaseModel):
    """Binance trade (REST or WebSocket)."""

    id: int
    price: Decimal
    qty: Decimal
    quoteQty: Decimal
    time: int  # timestamp
    isBuyerMaker: bool
    isBestMatch: bool


class BinanceOrder(BaseModel):
    """Binance order (REST or WebSocket)."""

    orderId: int | None = None
    clientOrderId: str | None = None
    symbol: str | None = None
    side: str | None = None
    type: str | None = None
    status: str | None = None
    price: str | None = None
    origQty: str | None = None
    executedQty: str | None = None
    cumQty: str | None = None
    timeInForce: str | None = None
    time: int | None = None
    updateTime: int | None = None
    info: dict | None = None


class BinancePosition(BaseModel):
    """Binance futures position (REST or WebSocket)."""

    symbol: str | None = None
    positionAmt: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    unRealizedProfit: str | None = None
    leverage: str | None = None
    info: dict | None = None


class BinanceKline(BaseModel):
    """Binance kline/candlestick data."""

    open_time: int  # timestamp
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: int  # timestamp
    quote_asset_volume: Decimal
    number_of_trades: int
    taker_buy_base_asset_volume: Decimal
    taker_buy_quote_asset_volume: Decimal
    ignore: str  # unused field

    @classmethod
    def from_list(
        cls,
        kline_data: list[int | str],
    ) -> "BinanceKline":
        """Create BinanceKline from list format returned by Binance API.

        Binance REST/WebSocket returns: [open_time, open, high, low, close,
        volume, close_time, quote_asset_volume, trades, taker_buy_base,
        taker_buy_quote, ignore]. Indices 0,6,8 are int; others are str.
        """
        return cls(
            open_time=int(kline_data[0]),
            open_price=Decimal(str(kline_data[1])),
            high_price=Decimal(str(kline_data[2])),
            low_price=Decimal(str(kline_data[3])),
            close_price=Decimal(str(kline_data[4])),
            volume=Decimal(str(kline_data[5])),
            close_time=int(kline_data[6]),
            quote_asset_volume=Decimal(str(kline_data[7])),
            number_of_trades=int(kline_data[8]),
            taker_buy_base_asset_volume=Decimal(str(kline_data[9])),
            taker_buy_quote_asset_volume=Decimal(str(kline_data[10])),
            ignore=str(kline_data[11]),
        )


class BinanceSymbol(BaseModel):
    """Binance symbol information from exchange info."""

    symbol: str
    status: str
    baseAsset: str
    baseAssetPrecision: int
    quoteAsset: str
    quotePrecision: int
    quoteAssetPrecision: int
    baseCommissionPrecision: int
    quoteCommissionPrecision: int
    orderTypes: list[str]
    icebergAllowed: bool
    ocoAllowed: bool
    quoteOrderQtyMarketAllowed: bool
    allowTrailingStop: bool
    cancelReplaceAllowed: bool
    isSpotTradingAllowed: bool
    isMarginTradingAllowed: bool


class BinanceExchangeInfo(BaseModel):
    """Binance exchange information."""

    timezone: str
    serverTime: int  # timestamp
    rateLimits: list[dict]
    exchangeFilters: list[dict]
    symbols: list[BinanceSymbol]


class BinanceError(BaseModel):
    """Binance API error payload."""

    code: int | None = None
    msg: str | None = None

    @classmethod
    def classify(cls, code: int) -> ErrorAction:
        """Map Binance error code to retry action.

        Ref: https://binance-docs.github.io/apidocs/futures/en/#error-codes
        """
        retry_codes = {-1000, -1001, -1003, -1006, -1007, -1008}
        reconnect_codes = {-1125}  # invalid listen key → regenerate and reconnect
        ip_ban_codes = {418}  # IP auto-banned: wait Retry-After
        if code in retry_codes:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code in reconnect_codes:
            return ErrorAction.RECONNECT
        if code in ip_ban_codes:
            return ErrorAction.RETRY_WITH_BACKOFF  # wait Retry-After header
        return ErrorAction.FAIL_HARD


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


class BinanceDeliveryPrice(BaseModel):
    """Binance futures delivery/settlement price (REST: GET /futures/data/delivery-price)."""

    pair: str
    deliveryTime: int  # timestamp (ms)
    deliveryPrice: Decimal


class BinanceWebSocketSubscribe(BaseModel):
    """Binance WebSocket subscription request."""

    method: str  # "SUBSCRIBE" or "UNSUBSCRIBE" or "LIST_SUBSCRIPTIONS"
    params: list[str]  # e.g. ["btcusdt@trade", "btcusdt@depth"]
    id: int  # request id for tracking responses


class BinanceOptionTicker(BaseModel):
    """Binance European options mark price ticker (EAPI @ticker stream).

    Stream: <symbol>@ticker (options WebSocket)
    """

    e: str  # event type = "ticker"
    E: int  # event time
    T: int  # transaction time
    s: str  # option symbol e.g. BTC-200730-9000-C
    o: Decimal  # open price
    h: Decimal  # highest price
    l: Decimal  # lowest price  # noqa: E741
    c: Decimal  # latest price
    V: Decimal  # trading volume (contracts)
    A: Decimal  # trading amount (USDT)
    P: Decimal  # price change percent
    p: Decimal  # price change
    Q: Decimal  # last trade volume
    F: int  # first trade id
    L: int  # last trade id
    n: int  # trade count
    b: Decimal  # best buy price
    a: Decimal  # best sell price
    d: Decimal  # delta
    t: Decimal  # theta
    g: Decimal  # gamma
    v: Decimal  # vega
    vo: Decimal  # implied volatility
    mp: Decimal  # mark price
    hl: Decimal  # buy max price
    ll: Decimal  # sell min price
    eep: Decimal  # estimated strike price


class BinanceOptionMarkPrice(BaseModel):
    """Binance European options mark price (EAPI @markPrice stream)."""

    e: str  # "markPrice"
    E: int  # event time
    s: str  # symbol
    mp: Decimal  # mark price
    r: Decimal  # interest rate (annualized)
    T: int  # delivery date (ms)


class BinanceWebSocketPing(BaseModel):
    """Binance WebSocket ping (server→client every 20s; client must respond with pong)."""

    # Binance sends a raw PING frame (no JSON body); this is a marker schema
    # Client sends a PONG frame back. If no pong within 60s, server disconnects.
    pass


class BinanceListenKeyCreate(BaseModel):
    """Binance listen key response (POST /fapi/v1/listenKey for futures user data stream).

    listenKey is valid for 60 minutes. Extend via PUT every 30 minutes.
    Max connection lifetime: 24 hours.
    """

    listenKey: str
