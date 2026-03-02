"""Bybit adapter: markets, tickers, order book, trades, order/position, errors, WebSocket, FIX."""

from pydantic import BaseModel

from unified_api_contracts.shared import ErrorAction


class BybitMarket(BaseModel):
    """Bybit market/symbol."""

    symbol: str | None = None
    baseCoin: str | None = None
    quoteCoin: str | None = None
    info: dict | None = None


class BybitOrderBook(BaseModel):
    """Bybit order book (REST: GET /v5/market/orderbook, WS: orderbook.{depth}.{symbol}).

    result from REST; data from WS snapshot. a=asks, b=bids: [[price, size], ...].
    """

    s: str | None = None  # symbol
    a: list[list[str]] = []  # asks [[price, size], ...]
    b: list[list[str]] = []  # bids [[price, size], ...]
    ts: int | None = None  # timestamp (ms)
    u: int | None = None  # update ID
    seq: int | None = None  # cross sequence
    cts: int | None = None  # matching engine timestamp (ms)


class BybitTicker(BaseModel):
    """Bybit ticker."""

    symbol: str | None = None
    lastPrice: str | None = None
    bid1Price: str | None = None
    ask1Price: str | None = None
    volume24h: str | None = None
    info: dict | None = None


class BybitMarkPriceKline(BaseModel):
    """Bybit mark price kline (REST: GET /v5/market/mark-price-kline).

    Each candle: [startTime, openPrice, highPrice, lowPrice, closePrice]. Sorted reverse by startTime.
    """

    startTime: str  # timestamp ms
    openPrice: str
    highPrice: str
    lowPrice: str
    closePrice: str

    @classmethod
    def from_list(cls, row: list[str]) -> "BybitMarkPriceKline":
        """Create from array [startTime, openPrice, highPrice, lowPrice, closePrice]."""
        return cls(
            startTime=row[0],
            openPrice=row[1],
            highPrice=row[2],
            lowPrice=row[3],
            closePrice=row[4],
        )


class BybitIndexPriceKline(BaseModel):
    """Bybit index price kline (REST: GET /v5/market/index-price-kline).

    Same format as mark price kline: [startTime, openPrice, highPrice, lowPrice, closePrice].
    """

    startTime: str  # timestamp ms
    openPrice: str
    highPrice: str
    lowPrice: str
    closePrice: str

    @classmethod
    def from_list(cls, row: list[str]) -> "BybitIndexPriceKline":
        """Create from array [startTime, openPrice, highPrice, lowPrice, closePrice]."""
        return cls(
            startTime=row[0],
            openPrice=row[1],
            highPrice=row[2],
            lowPrice=row[3],
            closePrice=row[4],
        )


class BybitOrder(BaseModel):
    """Bybit order."""

    orderId: str | None = None
    orderLinkId: str | None = None
    symbol: str | None = None
    side: str | None = None
    orderType: str | None = None
    qty: str | None = None
    price: str | None = None
    orderStatus: str | None = None
    avgPrice: str | None = None
    cumExecQty: str | None = None
    info: dict | None = None


class BybitPosition(BaseModel):
    """Bybit position."""

    symbol: str | None = None
    side: str | None = None
    size: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    unrealisedPnl: str | None = None
    info: dict | None = None


class BybitError(BaseModel):
    """Bybit API error."""

    retCode: int | None = None
    retMsg: str | None = None

    @classmethod
    def classify(cls, code: int) -> ErrorAction:
        """Map Bybit error code (retCode) to retry action.

        Ref: https://bybit-exchange.github.io/docs/v5/error
        """
        retry_codes = {10000, 10016, 20003, 10429, 429}
        reconnect_codes = {10019}  # WS trade service restarting → new connection
        if code in retry_codes:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code in reconnect_codes:
            return ErrorAction.RECONNECT
        return ErrorAction.FAIL_HARD


class BybitOrderUpdateWS(BaseModel):
    """Bybit WebSocket private order update (topic: order or order.{category}).

    Covers all order state changes: New, PartiallyFilled, Filled, Cancelled, Rejected
    """

    orderId: str
    orderLinkId: str | None = None
    symbol: str
    side: str  # Buy or Sell
    orderType: str  # Limit, Market, etc.
    price: str | None = None
    qty: str | None = None
    orderStatus: str  # New, PartiallyFilled, Filled, Cancelled, Rejected
    cancelType: str | None = None  # cancel reason
    rejectReason: str | None = None  # e.g. EC_NoError, EC_PerCancelRequest
    avgPrice: str | None = None
    leavesQty: str | None = None
    cumExecQty: str | None = None
    cumExecValue: str | None = None
    cumExecFee: str | None = None
    closedPnl: str | None = None
    category: str | None = None  # spot, linear, inverse, option
    updatedTime: int | None = None  # timestamp (ms)


class BybitExecutionWS(BaseModel):
    """Bybit WebSocket private execution (fill) event (topic: execution or execution.{category}).

    Pushed on every fill (partial or complete).
    """

    execId: str
    symbol: str
    side: str  # Buy or Sell
    orderType: str
    execPrice: str
    execQty: str
    execType: str  # Trade, AdlTrade, BustTrade, Delivery, BlockTrade
    execValue: str | None = None
    execTime: int  # timestamp (ms)
    execFee: str | None = None
    execPnl: str | None = None
    closedSize: str | None = None
    isMaker: bool | None = None
    orderId: str | None = None
    orderLinkId: str | None = None
    seq: int | None = None  # cross-sequence number


class BybitPositionWS(BaseModel):
    """Bybit WebSocket private position update (topic: position or position.{category}).

    Note: no initial snapshot on subscribe — query REST /v5/position/list first.
    """

    symbol: str
    side: str  # Buy or Sell or None
    size: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    unrealisedPnl: str | None = None
    curRealisedPnl: str | None = None
    cumRealisedPnl: str | None = None
    liqPrice: str | None = None
    leverage: str | None = None
    positionStatus: str | None = None  # Normal, Liq, Adl
    positionIdx: int | None = None  # 0=one-way, 1=long, 2=short
    seq: int | None = None
    category: str | None = None


class BybitWalletWS(BaseModel):
    """Bybit WebSocket private wallet/balance update (topic: wallet).

    Note: no initial snapshot on subscribe — query REST /v5/account/wallet-balance first.
    Provides UNIFIED account balance summary.
    """

    accountType: str  # UNIFIED, CONTRACT, etc.
    totalEquity: str | None = None
    totalWalletBalance: str | None = None
    totalMarginBalance: str | None = None
    totalAvailableBalance: str | None = None
    totalPerpUPL: str | None = None
    totalInitialMargin: str | None = None
    totalMaintenanceMargin: str | None = None
    coin: list[dict[str, object]] | None = None  # per-coin balance details


class BybitWebSocketSubscribe(BaseModel):
    """Bybit WebSocket subscription request (V5 API)."""

    op: str  # "subscribe" or "unsubscribe"
    args: list[str]  # e.g. ["publicTrade.BTCUSDT", "orderbook.1.BTCUSDT"]
    req_id: str | None = None  # optional request tracking id


class BybitWebSocketPing(BaseModel):
    """Bybit WebSocket ping (keep-alive).

    Send every 20s to prevent 10-min inactivity disconnect.
    """

    op: str = "ping"
    req_id: str | None = None


class BybitWebSocketPong(BaseModel):
    """Bybit WebSocket pong response."""

    success: bool
    ret_msg: str  # "pong"
    conn_id: str | None = None
    op: str = "pong"
    req_id: str | None = None


class BybitWebSocketClose(BaseModel):
    """Bybit WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy.
    """

    code: int
    reason: str | None = None


class BybitInstrumentInfo(BaseModel):
    """Bybit instrument specification (REST: GET /v5/market/instruments-info).

    Works for category=spot, linear (USDT perp/futures), inverse, option.
    """

    symbol: str
    contractType: str | None = None  # LinearPerpetual, LinearFutures, InversePerpetual, etc.
    status: str | None = None  # Trading, Settling, Expired
    baseCoin: str | None = None
    quoteCoin: str | None = None
    launchTime: str | None = None
    deliveryTime: str | None = None  # ISO timestamp; perps have no delivery
    deliveryFeeRate: str | None = None
    priceScale: str | None = None
    leverageFilter: dict | None = None
    priceFilter: dict | None = None  # tickSize
    lotSizeFilter: dict | None = None  # qtyStep, minOrderQty, maxOrderQty
    unifiedMarginTrade: bool | None = None
    fundingInterval: int | None = None  # minutes
    settleCoin: str | None = None
    optionsType: str | None = None  # Call or Put (for options)
    strikePrice: str | None = None


# --- CEX Order Submit / Ack / Cancel ---


class BybitOrderSubmitRequest(BaseModel):
    """Bybit order submit request (POST /v5/order/create).

    category: spot, linear (USDT perp/futures), inverse, option.
    positionIdx: 0=one-way, 1=long, 2=short (hedge).
    """

    category: str  # spot, linear, inverse, option
    symbol: str
    side: str  # Buy, Sell
    orderType: str  # Limit, Market, etc.
    qty: str
    price: str | None = None
    timeInForce: str | None = None  # GTC, IOC, FOK, PostOnly
    orderLinkId: str | None = None
    positionIdx: int | None = None  # 0=one-way, 1=long, 2=short
    reduceOnly: bool | None = None
    takeProfit: str | None = None
    stopLoss: str | None = None
    tpOrderType: str | None = None
    slOrderType: str | None = None


class BybitOrderSubmitResponse(BaseModel):
    """Bybit order submit response."""

    orderId: str | None = None
    orderLinkId: str | None = None


class BybitOrderCancelRequest(BaseModel):
    """Bybit order cancel request (POST /v5/order/cancel)."""

    category: str  # spot, linear, inverse, option
    symbol: str
    orderId: str | None = None
    orderLinkId: str | None = None  # use orderId OR orderLinkId


class BybitOrderCancelResponse(BaseModel):
    """Bybit order cancel response."""

    orderId: str | None = None
    orderLinkId: str | None = None


# --- Position, Margin, Realized PnL ---


class BybitPositionQueryResponse(BaseModel):
    """Bybit position query response (GET /v5/position/list)."""

    symbol: str | None = None
    side: str | None = None  # Buy, Sell
    size: str | None = None
    entryPrice: str | None = None
    markPrice: str | None = None
    unrealisedPnl: str | None = None
    cumRealisedPnl: str | None = None
    liqPrice: str | None = None
    leverage: str | None = None
    positionIdx: int | None = None
    category: str | None = None


class BybitMarginBalanceResponse(BaseModel):
    """Bybit margin/balance (GET /v5/account/wallet-balance)."""

    totalEquity: str | None = None
    totalWalletBalance: str | None = None
    totalMarginBalance: str | None = None
    totalAvailableBalance: str | None = None
    totalPerpUPL: str | None = None
    totalInitialMargin: str | None = None
    totalMaintenanceMargin: str | None = None
    coin: list[dict[str, object]] | None = None  # per-coin details


class BybitRealizedPnlResponse(BaseModel):
    """Bybit realized PnL from execution (GET /v5/execution/list) or closed PnL."""

    symbol: str | None = None
    side: str | None = None
    closedPnl: str | None = None
    execPrice: str | None = None
    execQty: str | None = None
    execTime: str | None = None
    execType: str | None = None  # Trade, Funding, AdlTrade, BustTrade, Delivery


# --- Withdrawal ---


class BybitWithdrawalRequest(BaseModel):
    """Bybit withdrawal request (POST /v5/asset/withdraw/create)."""

    coin: str
    chain: str
    address: str
    tag: str | None = None  # memo/destination tag
    amount: str
    forceChain: int | None = None  # 0=auto, 1=force
    accountType: str | None = None  # UNIFIED, CONTRACT, etc.
    feeType: int | None = None  # 0=pay on chain, 1=deduct from amount


class BybitWithdrawalResponse(BaseModel):
    """Bybit withdrawal response."""

    withdrawId: str | None = None
    success: bool | None = None


# --- Institutional: Fee, Funding, Deposits, Transfers, Risk, Insurance, Delivery ---


class BybitFeeRate(BaseModel):
    """Bybit fee rate (GET /v5/account/fee-rate)."""

    baseFeeRate: str | None = None
    discountFeeRate: str | None = None
    takerFeeRate: str | None = None
    makerFeeRate: str | None = None
    symbol: str | None = None
    baseCoin: str | None = None


class BybitFundingRateHistory(BaseModel):
    """Bybit funding rate history item (GET /v5/market/funding/history)."""

    symbol: str | None = None
    fundingRate: str | None = None
    fundingRateTimestamp: str | None = None


class BybitDepositAddress(BaseModel):
    """Bybit deposit address (GET /v5/asset/deposit/query-address)."""

    coin: str | None = None
    chain: str | None = None
    address: str | None = None
    tag: str | None = None  # memo/destination tag


class BybitDepositRecords(BaseModel):
    """Bybit deposit record item (GET /v5/asset/deposit/query-record)."""

    coin: str | None = None
    chain: str | None = None
    amount: str | None = None
    txID: str | None = None
    toAddress: str | None = None
    successAt: str | None = None
    depositStatus: str | None = None  # 0=pending, 1=success, 2=crediting


class BybitWithdrawals(BaseModel):
    """Bybit withdrawal record item (GET /v5/asset/withdraw/query-record)."""

    withdrawId: str | None = None
    coin: str | None = None
    chain: str | None = None
    amount: str | None = None
    txID: str | None = None
    toAddress: str | None = None
    withdrawFee: str | None = None
    successAt: str | None = None
    withdrawStatus: str | None = None  # SecurityCheck, Pending, success, CancelByUser, Reject, Fail


class BybitAccountTransfer(BaseModel):
    """Bybit account transfer (POST /v5/asset/transfer/inter-transfer)."""

    transferId: str | None = None
    coin: str | None = None
    amount: str | None = None
    fromAccountType: str | None = None  # UNIFIED, CONTRACT, SPOT
    toAccountType: str | None = None
    ts: str | None = None
    status: str | None = None  # success, pending, failed


class BybitLongShortRatio(BaseModel):
    """Bybit long/short ratio (GET /v5/market/account-ratio)."""

    symbol: str | None = None
    buyRatio: str | None = None
    sellRatio: str | None = None
    timestamp: str | None = None


class BybitRiskLimit(BaseModel):
    """Bybit risk limit tier (GET /v5/market/risk-limit)."""

    tier: int | None = None
    maxLeverage: str | None = None
    maintenanceMarginRate: str | None = None
    maxOrderQty: str | None = None
    symbol: str | None = None


class BybitInsuranceFund(BaseModel):
    """Bybit insurance fund (GET /v5/insurance/insurance-record)."""

    coin: str | None = None
    balance: str | None = None
    value: str | None = None
    updatedTime: str | None = None


class BybitDeliveryRecord(BaseModel):
    """Bybit delivery record (GET /v5/asset/delivery-record)."""

    symbol: str | None = None
    deliveryPrice: str | None = None
    deliveryTime: str | None = None
    side: str | None = None
    size: str | None = None
    deliveryFee: str | None = None
    deliveryType: str | None = None  # delivery, adl


class BybitLiquidationOrder(BaseModel):
    """Bybit liquidation order (topic: allLiquidation WS stream)."""

    s: str | None = None
    S: str | None = None
    v: str | None = None
    p: str | None = None
    T: int | None = None
