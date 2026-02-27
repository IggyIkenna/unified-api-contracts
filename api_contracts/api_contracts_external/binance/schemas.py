"""Binance REST/WebSocket: market data, order/position, errors, WebSocket payloads."""

from decimal import Decimal

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class BinanceTicker(BaseModel):
    """Binance 24hr ticker statistics (REST or WebSocket).

    Endpoints:
    - Spot: api.binance.com/api/v3/ticker/24hr (has prevClosePrice, bid/ask)
    - USD-M (futures + perps): fapi.binance.com/fapi/v1/ticker/24hr (no bid/ask; has funding)
    - Coin-M: dapi.binance.com/dapi/v1/ticker/24hr (no bid/ask; has pair)
    """

    symbol: str
    priceChange: Decimal
    priceChangePercent: Decimal
    weightedAvgPrice: Decimal
    lastPrice: Decimal
    lastQty: Decimal
    openPrice: Decimal
    highPrice: Decimal
    lowPrice: Decimal
    volume: Decimal
    quoteVolume: Decimal
    openTime: int  # timestamp ms
    closeTime: int  # timestamp ms
    firstId: int
    lastId: int
    count: int
    # Spot only (api); absent for USD-M/Coin-M (fapi/dapi)
    prevClosePrice: Decimal | None = None
    bidPrice: Decimal | None = None
    bidQty: Decimal | None = None
    askPrice: Decimal | None = None
    askQty: Decimal | None = None
    # USD-M futures/perps only (fapi); absent for Spot
    lastFundingRate: Decimal | None = None
    nextFundingTime: int | None = None  # timestamp ms
    time: int | None = None  # timestamp ms


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
    P: Decimal | None = None  # estimated settle price (only on last funding)
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


class BinanceInstrumentInfo(BaseModel):
    """Binance instrument/contract specification (REST: GET /fapi/v1/exchangeInfo or /eapi/v1/exchangeInfo)."""

    symbol: str
    status: str  # TRADING, BREAK, END_OF_DAY
    baseAsset: str | None = None
    quoteAsset: str | None = None
    contractType: str | None = None  # PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER
    deliveryDate: int | None = None  # timestamp ms; 4133404800000 = no expiry
    onboardDate: int | None = None  # timestamp ms
    contractSize: int | None = None  # 1 for standard
    marginAsset: str | None = None
    pricePrecision: int | None = None
    quantityPrecision: int | None = None
    baseAssetPrecision: int | None = None
    quotePrecision: int | None = None
    filters: list[dict] | None = None  # PRICE_FILTER, LOT_SIZE, etc.
    underlyingType: str | None = None  # COIN or TOKEN (futures)


class BinanceOptionInstrumentInfo(BaseModel):
    """Binance European options instrument (REST: GET /eapi/v1/exchangeInfo)."""

    id: int | None = None
    contractId: int | None = None
    underlying: str | None = None  # e.g. BTCUSDT
    quoteAsset: str | None = None  # USDT
    symbol: str | None = None  # e.g. BTC-200730-9000-C
    unit: int | None = None  # number of tokens per contract
    minQty: Decimal | None = None
    maxQty: Decimal | None = None
    priceScale: int | None = None
    quantityScale: int | None = None
    side: str | None = None  # CALL or PUT
    strikePrice: Decimal | None = None
    expiryDate: int | None = None  # timestamp ms


# --- CEX Order Submit / Ack / Cancel (per venue variant) ---


class BinanceSpotOrderSubmitRequest(BaseModel):
    """Binance Spot order submit request (POST /api/v3/order).

    Venue: binance-spot. No positionSide; no contractType.
    """

    symbol: str
    side: str  # BUY, SELL
    type: str  # LIMIT, MARKET, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, LIMIT_MAKER
    quantity: str | None = None
    quoteOrderQty: str | None = None  # for MARKET buy
    price: str | None = None
    timeInForce: str | None = None  # GTC, IOC, FOK
    newClientOrderId: str | None = None
    stopPrice: str | None = None
    icebergQty: str | None = None
    newOrderRespType: str | None = None  # ACK, RESULT, FULL


class BinanceSpotOrderSubmitResponse(BaseModel):
    """Binance Spot order submit response (ACK/RESULT/FULL per newOrderRespType)."""

    orderId: int | None = None
    clientOrderId: str | None = None
    symbol: str | None = None
    status: str | None = None
    transactTime: int | None = None
    price: str | None = None
    origQty: str | None = None
    executedQty: str | None = None
    cummulativeQuoteQty: str | None = None
    type: str | None = None
    side: str | None = None
    fills: list[dict[str, object]] | None = None


class BinanceUsdmOrderSubmitRequest(BaseModel):
    """Binance USD-M futures order submit request (POST /fapi/v1/order).

    Venue: binance-usdm. positionSide: BOTH (one-way) or LONG/SHORT (hedge).
    contractType: PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER (from symbol metadata).
    """

    symbol: str
    side: str  # BUY, SELL
    positionSide: str | None = None  # BOTH, LONG, SHORT
    type: str  # LIMIT, MARKET, STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET, etc.
    timeInForce: str | None = None
    quantity: str | None = None
    reduceOnly: str | None = None  # "true" | "false"
    price: str | None = None
    newClientOrderId: str | None = None
    stopPrice: str | None = None
    closePosition: str | None = None  # "true" for close-all
    newOrderRespType: str | None = None  # ACK, RESULT


class BinanceUsdmOrderSubmitResponse(BaseModel):
    """Binance USD-M futures order submit response."""

    orderId: int | None = None
    clientOrderId: str | None = None
    symbol: str | None = None
    status: str | None = None
    positionSide: str | None = None
    side: str | None = None
    type: str | None = None
    origQty: str | None = None
    executedQty: str | None = None
    cumQty: str | None = None
    price: str | None = None
    avgPrice: str | None = None
    reduceOnly: bool | None = None
    updateTime: int | None = None


class BinanceCoinmOrderSubmitRequest(BaseModel):
    """Binance Coin-M futures order submit request (POST /dapi/v1/order).

    Venue: binance-coinm. Uses pair (e.g. BTCUSD) not symbol. positionSide for hedge.
    contractType: PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER.
    """

    symbol: str  # e.g. BTCUSD_PERP
    side: str  # BUY, SELL
    positionSide: str | None = None  # BOTH, LONG, SHORT
    type: str
    timeInForce: str | None = None
    quantity: str | None = None
    reduceOnly: str | None = None
    price: str | None = None
    newClientOrderId: str | None = None
    stopPrice: str | None = None
    closePosition: str | None = None
    newOrderRespType: str | None = None


class BinanceCoinmOrderSubmitResponse(BaseModel):
    """Binance Coin-M futures order submit response."""

    orderId: int | None = None
    clientOrderId: str | None = None
    symbol: str | None = None
    status: str | None = None
    positionSide: str | None = None
    side: str | None = None
    type: str | None = None
    origQty: str | None = None
    executedQty: str | None = None
    cumQty: str | None = None
    price: str | None = None
    avgPrice: str | None = None
    updateTime: int | None = None


class BinanceOrderCancelRequest(BaseModel):
    """Binance order cancel request (DELETE /api/v3/order or /fapi/v1/order or /dapi/v1/order)."""

    symbol: str
    orderId: int | None = None
    origClientOrderId: str | None = None  # use orderId OR origClientOrderId


class BinanceOrderCancelResponse(BaseModel):
    """Binance order cancel response."""

    orderId: int | None = None
    clientOrderId: str | None = None
    symbol: str | None = None
    status: str | None = None  # CANCELED, EXPIRED, etc.


# --- Position, Margin, Realized PnL ---


class BinancePositionQueryResponse(BaseModel):
    """Binance position query response (GET /fapi/v2/positionRisk or /dapi/v2/positionRisk)."""

    symbol: str | None = None
    positionAmt: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    unRealizedProfit: str | None = None
    liquidationPrice: str | None = None
    leverage: str | None = None
    marginType: str | None = None  # isolated, cross
    positionSide: str | None = None  # BOTH, LONG, SHORT


class BinanceMarginBalanceResponse(BaseModel):
    """Binance futures margin/balance (GET /fapi/v2/balance or /dapi/v2/balance)."""

    asset: str | None = None
    balance: str | None = None
    availableBalance: str | None = None
    crossWalletBalance: str | None = None
    crossUnPnl: str | None = None
    availableWithdrawBalance: str | None = None


class BinanceRealizedPnlResponse(BaseModel):
    """Binance realized PnL from income history (GET /fapi/v1/income or /dapi/v1/income).

    incomeType: REALIZED_PNL, FUNDING_FEE, COMMISSION, etc.
    """

    symbol: str | None = None
    incomeType: str | None = None
    income: str | None = None
    asset: str | None = None
    info: str | None = None
    time: int | None = None
    tranId: str | None = None


# --- Withdrawal ---


class BinanceWithdrawalRequest(BaseModel):
    """Binance withdrawal request (POST /sapi/v1/capital/withdraw/apply)."""

    coin: str
    withdrawOrderId: str | None = None  # client id, optional
    network: str | None = None
    address: str
    amount: str
    transactionFeeFlag: bool | None = None
    name: str | None = None  # address tag name
    walletType: int | None = None  # 0=spot, 1=funding


class BinanceWithdrawalResponse(BaseModel):
    """Binance withdrawal response (returns id for tracking)."""

    id: str | None = None


# --- Institutional / Advanced Schemas ---


class BinanceAggTrade(BaseModel):
    """Binance aggregated trade (REST GET /api/v3/aggTrades or WebSocket @aggTrade).

    REST/WS use short keys (a,p,q,f,l,T,m,M); schema uses camelCase with aliases.
    """

    model_config = {"populate_by_name": True}

    aggTradeId: int = Field(alias="a")
    price: Decimal = Field(alias="p")
    qty: Decimal = Field(alias="q")
    firstTradeId: int = Field(alias="f")
    lastTradeId: int = Field(alias="l")
    isBuyerMaker: bool = Field(alias="m")
    isBestMatch: bool = Field(alias="M")
    time: int | None = Field(None, alias="T")  # timestamp ms (REST/WS)


class BinanceFundingRateHistory(BaseModel):
    """Binance funding rate history (GET /fapi/v1/fundingRate)."""

    symbol: str | None = None
    fundingTime: int  # timestamp ms
    fundingRate: Decimal
    markPrice: Decimal | None = None


class BinancePremiumIndex(BaseModel):
    """Binance premium index / mark price (GET /fapi/v1/premiumIndex)."""

    symbol: str | None = None
    markPrice: Decimal
    indexPrice: Decimal
    lastFundingRate: Decimal
    nextFundingTime: int  # timestamp ms
    interestRate: Decimal
    estimatedSettlePrice: Decimal | None = None
    time: int | None = None  # timestamp ms


class BinanceMarkPriceKline(BaseModel):
    """Binance mark price kline (REST: GET /fapi/v1/markPriceKlines, /dapi/v1/markPriceKlines).

    USD-M returns [timestamp, open, high, low, close, volume]. Coin-M returns full 12-field format.
    Use from_list() for array format.
    """

    open_time: int  # timestamp ms
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: int | None = None  # Coin-M only
    quote_asset_volume: Decimal | None = None  # Coin-M only
    number_of_trades: int | None = None  # Coin-M only
    taker_buy_base_asset_volume: Decimal | None = None  # Coin-M only
    taker_buy_quote_asset_volume: Decimal | None = None  # Coin-M only
    ignore: str | None = None  # Coin-M only

    @classmethod
    def from_list(
        cls,
        kline_data: list[int | str],
    ) -> "BinanceMarkPriceKline":
        """Create from array. USD-M: 6 fields; Coin-M: 12 fields."""
        if len(kline_data) >= 12:
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
        return cls(
            open_time=int(kline_data[0]),
            open_price=Decimal(str(kline_data[1])),
            high_price=Decimal(str(kline_data[2])),
            low_price=Decimal(str(kline_data[3])),
            close_price=Decimal(str(kline_data[4])),
            volume=Decimal(str(kline_data[5])),
        )


class BinanceIndexPriceKline(BaseModel):
    """Binance index price kline (REST: GET /fapi/v1/indexPriceKlines, /dapi/v1/indexPriceKlines).

    Same array format as mark price kline. Use from_list() for array format.
    """

    open_time: int  # timestamp ms
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: int | None = None
    quote_asset_volume: Decimal | None = None
    number_of_trades: int | None = None
    taker_buy_base_asset_volume: Decimal | None = None
    taker_buy_quote_asset_volume: Decimal | None = None
    ignore: str | None = None

    @classmethod
    def from_list(
        cls,
        kline_data: list[int | str],
    ) -> "BinanceIndexPriceKline":
        """Create from array. USD-M: 6 fields; Coin-M: 12 fields."""
        if len(kline_data) >= 12:
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
        return cls(
            open_time=int(kline_data[0]),
            open_price=Decimal(str(kline_data[1])),
            high_price=Decimal(str(kline_data[2])),
            low_price=Decimal(str(kline_data[3])),
            close_price=Decimal(str(kline_data[4])),
            volume=Decimal(str(kline_data[5])),
        )


class BinanceMyTrades(BaseModel):
    """Binance account trade list (REST: GET /fapi/v1/userTrades, /dapi/v1/userTrades).

    REST fills with fees. Spot: GET /api/v3/myTrades. USD-M/Coin-M: userTrades.
    """

    symbol: str
    id: int  # trade id
    orderId: int
    pair: str | None = None  # Coin-M only
    side: str  # BUY, SELL
    price: str
    qty: str
    realizedPnl: str | None = None
    marginAsset: str | None = None  # Coin-M
    baseQty: str | None = None  # Coin-M
    commission: str
    commissionAsset: str
    time: int  # timestamp ms
    positionSide: str | None = None  # BOTH, LONG, SHORT
    buyer: bool
    maker: bool
    quoteQty: str | None = None  # USD-M


class BinanceDeliveryHistory(BaseModel):
    """Binance delivery/settlement price history (GET /futures/data/delivery-price).

    With symbol: single object. With pair or no filter: array of {deliveryTime, deliveryPrice}.
    """

    pair: str | None = None  # Coin-M; symbol for USD-M
    symbol: str | None = None  # USD-M single-symbol response
    deliveryTime: int  # timestamp ms
    deliveryPrice: Decimal


class BinanceIncome(BaseModel):
    """Binance income history (GET /fapi/v1/income, /dapi/v1/income, /papi/v1/cm/income).

    PnL/funding history. Coin-M uses 'income'; USD-M uses 'amount'. Both have tradeId.
    """

    symbol: str | None = None
    incomeType: str  # TRANSFER, FUNDING_FEE, REALIZED_PNL, COMMISSION, etc.
    income: str | None = None  # Coin-M
    amount: str | None = None  # USD-M (some income types)
    asset: str
    info: str | None = None
    time: int  # timestamp ms
    tranId: str | None = None  # transaction id; API may return int or str
    tradeId: str | None = None


class BinanceDepositAddress(BaseModel):
    """Binance deposit address (GET /sapi/v1/capital/deposit/address)."""

    address: str
    coin: str | None = None
    tag: str | None = None  # address tag / memo
    url: str | None = None
    network: str | None = None


class BinanceDepositHistory(BaseModel):
    """Binance deposit history item (GET /sapi/v1/capital/deposit/hisrec)."""

    id: str | None = None
    amount: str | None = None
    coin: str | None = None
    network: str | None = None
    status: int | None = None
    address: str | None = None
    addressTag: str | None = None
    txId: str | None = None
    insertTime: int | None = None
    confirmTimes: str | None = None
    completeTime: int | None = None


class BinanceWithdrawalHistory(BaseModel):
    """Binance withdrawal history item (GET /sapi/v1/capital/withdraw/history)."""

    id: str | None = None
    amount: str | None = None
    transactionFee: str | None = None
    coin: str | None = None
    status: int | None = None
    address: str | None = None
    txId: str | None = None
    network: str | None = None
    applyTime: str | None = None
    completeTime: str | None = None


class BinanceFeeRate(BaseModel):
    """Binance trade fee rate (GET /sapi/v1/asset/tradeFee)."""

    symbol: str
    makerCommission: str
    takerCommission: str


class BinanceInternalTransfer(BaseModel):
    """Binance universal transfer request/response (POST /sapi/v1/asset/transfer)."""

    fromAccountType: str  # SPOT, USDT_FUTURE, COIN_FUTURE, etc.
    toAccountType: str
    asset: str
    amount: str
    txnId: str | None = None
    clientTranId: str | None = None


class BinanceSubAccount(BaseModel):
    """Binance sub-account (GET /sapi/v1/sub-account/list)."""

    email: str | None = None
    isFreeze: bool | None = None
    createTime: int | None = None


class BinanceSubAccountAssets(BaseModel):
    """Binance sub-account consolidated balances (GET /sapi/v1/sub-account/assets)."""

    balances: list[dict[str, object]] | None = None
    totalAssetOfBtc: str | None = None


class BinanceAdlQuantile(BaseModel):
    """Binance ADL quantile per position (GET /fapi/v1/adlQuantile).

    ADL queue position 0-4 per symbol/positionSide.
    """

    symbol: str | None = None
    adlQuantile: dict[str, int] | None = None  # e.g. {"BOTH": 0} or {"LONG": 1, "SHORT": 2}


class BinanceInsuranceFundAsset(BaseModel):
    """Single asset in Binance insurance fund snapshot."""

    asset: str
    marginBalance: str
    updateTime: int


class BinanceInsuranceFund(BaseModel):
    """Binance insurance fund snapshot (GET /fapi/v1/insuranceBalance).

    With symbol: single object with symbols + assets. Without: array of such objects.
    """

    symbols: list[str] | None = None
    assets: list[BinanceInsuranceFundAsset] | None = None


class BinancePositionRisk(BaseModel):
    """Binance full position risk (GET /fapi/v2/positionRisk).

    Full REST fields including margin and liquidation metrics.
    """

    symbol: str | None = None
    positionAmt: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    unRealizedProfit: str | None = None
    liquidationPrice: str | None = None
    leverage: str | None = None
    marginType: str | None = None
    positionSide: str | None = None
    maintMargin: str | None = None
    initialMargin: str | None = None
    marginRatio: str | None = None
    maxNotionalValue: str | None = None
    notional: str | None = None
    isolatedMargin: str | None = None
    isolatedWallet: str | None = None
    breakEvenPrice: str | None = None
    isAutoAddMargin: str | None = None
    updateTime: int | None = None


class BinancePapiAccount(BaseModel):
    """Binance portfolio margin account (GET /papi/v1/account)."""

    accountEquity: str | None = None
    actualEquity: str | None = None
    accountMaintMargin: str | None = None
    uniMMR: str | None = None
    accountStatus: str | None = None
    virtualMaxWithdrawAmount: str | None = None
    totalWalletBalance: str | None = None
    totalUnrealizedProfit: str | None = None
    totalMarginBalance: str | None = None
    totalPositionInitialMargin: str | None = None
    totalOpenOrderInitialMargin: str | None = None
    totalCrossWalletBalance: str | None = None
    totalCrossUnPnl: str | None = None


class BinancePapiBalance(BaseModel):
    """Binance portfolio margin balance (GET /papi/v1/balance)."""

    asset: str | None = None
    balance: str | None = None
    crossWalletBalance: str | None = None
    crossUnPnl: str | None = None
    availableBalance: str | None = None
    maxWithdrawAmount: str | None = None


class BinancePapiPosition(BaseModel):
    """Binance portfolio margin UM position (GET /papi/v1/um/positionRisk)."""

    symbol: str | None = None
    positionAmt: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    liquidationPrice: str | None = None
    unRealizedProfit: str | None = None
    leverage: str | None = None
    positionSide: str | None = None
    marginType: str | None = None
    notional: str | None = None
    isolatedMargin: str | None = None


class BinanceEapiOrderSubmitRequest(BaseModel):
    """POST https://eapi.binance.com/eapi/v1/order.

    EAPI is separate from FAPI/DAPI, requires separate options trading permission.
    Base URL: eapi.binance.com.
    """

    symbol: str  # e.g. BTC-200730-9000-C
    side: str  # BUY/SELL
    type: str  # LIMIT/MARKET
    quantity: str
    price: str | None = None
    timeInForce: str | None = None  # GTC/IOC/FOK
    reduceOnly: bool | None = None
    newOrderRespType: str | None = None  # ACK/RESULT/FULL
    isMmp: bool | None = None  # Market Maker Protection


class BinanceEapiOrderSubmitResponse(BaseModel):
    """Response from POST https://eapi.binance.com/eapi/v1/order."""

    orderId: int | None = None
    clientOrderId: str | None = None
    symbol: str | None = None
    side: str | None = None
    type: str | None = None
    price: str | None = None
    quantity: str | None = None
    status: str | None = None  # ACCEPTED/PARTIALLY_FILLED/FILLED/CANCELLED
    updateTime: int | None = None


class BinanceEapiPosition(BaseModel):
    """GET /eapi/v1/position.

    EAPI is separate from FAPI/DAPI, requires separate options trading permission.
    """

    symbol: str | None = None
    positionAmt: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    unrealizedProfit: str | None = None
    expiryDate: int | None = None
    strikePrice: str | None = None
    side: str | None = None  # CALL/PUT


class BinanceDualInvestmentProduct(BaseModel):
    """GET /sapi/v1/simple-earn/dualInvestment/product/list.

    Structured product: deposit + embedded short option auto-exercised at expiry.
    EAPI is separate from FAPI/DAPI; base URL eapi.binance.com.
    """

    id: str | None = None
    investCoin: str | None = None
    exercisedCoin: str | None = None
    subscribeStartTime: int | None = None
    subscribeEndTime: int | None = None
    deliveryDate: int | None = None
    strikePrice: str | None = None
    apy: str | None = None
    minAmount: str | None = None
    maxAmount: str | None = None
