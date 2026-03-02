"""Pydantic schemas for Aster adapter. Full surface: market data, order/position, errors, WebSocket.

Aster uses Binance Futures-compatible API. Field names follow Binance conventions.
"""

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction


class AsterAggTrade(BaseModel):
    """Aggregate trade. GET /fapi/v1/aggTrades (Binance Futures-compatible)."""

    a: int = 0  # aggregate tradeId
    p: str = ""  # price
    q: str = ""  # quantity
    f: int = 0  # first tradeId
    last_trade_id: int = Field(0, alias="l")  # last tradeId (l in API)
    T: int = 0  # timestamp ms
    m: bool = False  # was buyer maker


class AsterTrade(BaseModel):
    """Recent trade. GET /fapi/v1/trades (Binance Futures-compatible)."""

    id: int = 0
    price: str = ""
    qty: str = ""
    quoteQty: str = ""
    time: int = 0
    isBuyerMaker: bool = False
    isRPITrade: bool | None = None


class AsterKline(BaseModel):
    """Kline/candlestick. GET /fapi/v1/klines (Binance Futures-compatible).

    Array format: [openTime, open, high, low, close, volume, closeTime, ...]
    """

    openTime: int = 0
    open: str = ""
    high: str = ""
    low: str = ""
    close: str = ""
    volume: str = ""
    closeTime: int = 0
    quoteAssetVolume: str = ""
    numberOfTrades: int = 0
    takerBuyBaseAssetVolume: str = ""
    takerBuyQuoteAssetVolume: str = ""
    ignore: str = ""


class AsterMarkPrice(BaseModel):
    """Mark price / premium index. GET /fapi/v1/premiumIndex."""

    symbol: str = ""
    markPrice: str = ""
    indexPrice: str = ""
    estimatedSettlePrice: str = ""
    lastFundingRate: str = ""
    interestRate: str = ""
    nextFundingTime: int = 0
    time: int = 0


class AsterFundingRate(BaseModel):
    """Funding rate. GET /fapi/v1/fundingRate."""

    symbol: str = ""
    fundingRate: str = ""
    fundingTime: int = 0
    markPrice: str = ""


class AsterOpenInterest(BaseModel):
    """Open interest. GET /fapi/v1/openInterest."""

    openInterest: str = ""
    symbol: str = ""
    time: int = 0


class AsterOpenInterestHistory(BaseModel):
    """Open interest history. GET /futures/data/openInterestHist."""

    symbol: str = ""
    sumOpenInterest: str = ""
    sumOpenInterestValue: str = ""
    CMCCirculatingSupply: str = ""
    timestamp: str = ""


class AsterTicker24hr(BaseModel):
    """24hr ticker. GET /fapi/v1/ticker/24hr."""

    symbol: str = ""
    priceChange: str = ""
    priceChangePercent: str = ""
    weightedAvgPrice: str = ""
    lastPrice: str = ""
    lastQty: str = ""
    openPrice: str = ""
    highPrice: str = ""
    lowPrice: str = ""
    volume: str = ""
    quoteVolume: str = ""
    openTime: int = 0
    closeTime: int = 0
    firstId: int = 0
    lastId: int = 0
    count: int = 0


class AsterExchangeInfo(BaseModel):
    """Exchange info. GET /fapi/v1/exchangeInfo."""

    exchangeFilters: list[object] | None = None
    rateLimits: list[object] | None = None
    serverTime: int | None = None
    assets: list[object] | None = None
    symbols: list[object] | None = None
    timezone: str | None = None


class AsterAccountAsset(BaseModel):
    """Account asset balance."""

    asset: str = ""
    walletBalance: str = ""
    unrealizedProfit: str = ""
    marginBalance: str = ""
    maintMargin: str = ""
    initialMargin: str = ""
    positionInitialMargin: str = ""
    openOrderInitialMargin: str = ""
    crossWalletBalance: str = ""
    crossUnPnl: str = ""
    availableBalance: str = ""
    maxWithdrawAmount: str = ""
    marginAvailable: str = ""
    updateTime: int = 0


class AsterAccountPosition(BaseModel):
    """Account position."""

    symbol: str = ""
    initialMargin: str = ""
    maintMargin: str = ""
    unrealizedProfit: str = ""
    positionInitialMargin: str = ""
    openOrderInitialMargin: str = ""
    leverage: str = ""
    isolated: bool = False
    entryPrice: str = ""
    maxNotional: str = ""
    bidNotional: str = ""
    askNotional: str = ""
    positionSide: str = ""
    positionAmt: str = ""
    updateTime: int = 0


class AsterAccount(BaseModel):
    """Account. GET /fapi/v2/account (Binance Futures-compatible)."""

    feeTier: int = 0
    feeBurn: bool = False
    canTrade: bool = False
    canDeposit: bool = False
    canWithdraw: bool = False
    multiAssetsMargin: bool = False
    totalInitialMargin: str = ""
    totalMaintMargin: str = ""
    totalWalletBalance: str = ""
    totalUnrealizedProfit: str = ""
    totalMarginBalance: str = ""
    totalPositionInitialMargin: str = ""
    totalOpenOrderInitialMargin: str = ""
    totalCrossWalletBalance: str = ""
    totalCrossUnPnl: str = ""
    availableBalance: str = ""
    maxWithdrawAmount: str = ""
    assets: list[AsterAccountAsset] | None = None
    positions: list[AsterAccountPosition] | None = None


class AsterBalance(BaseModel):
    """Balance (from account assets)."""

    asset: str = ""
    walletBalance: str = ""
    unrealizedProfit: str = ""
    marginBalance: str = ""
    maintMargin: str = ""
    initialMargin: str = ""
    positionInitialMargin: str = ""
    openOrderInitialMargin: str = ""
    crossWalletBalance: str = ""
    crossUnPnl: str = ""
    availableBalance: str = ""
    maxWithdrawAmount: str = ""
    marginAvailable: str = ""
    updateTime: int = 0


class AsterIncome(BaseModel):
    """Income/funding PnL. GET /fapi/v1/income."""

    symbol: str = ""
    incomeType: str = ""
    income: str = ""
    asset: str = ""
    info: str = ""
    time: int = 0
    tranId: int = 0
    tradeId: str = ""


class AsterLeverageBracketItem(BaseModel):
    """Single bracket in leverage bracket."""

    bracket: int = 0
    initialLeverage: int = 0
    notionalCap: str = ""
    notionalFloor: str = ""
    maintMarginRatio: str = ""
    cum: str = ""


class AsterLeverageBracket(BaseModel):
    """Leverage bracket. GET /fapi/v1/leverageBracket."""

    symbol: str = ""
    notionalCoef: float = 0.0
    brackets: list[AsterLeverageBracketItem] | None = None


class AsterOrderTradeUpdate(BaseModel):
    """Order/trade update (WebSocket ORDER_TRADE_UPDATE)."""

    e: str = ""  # event type
    E: int = 0  # event time
    T: int = 0  # transaction time
    o: dict[str, object] | None = None  # order object


class AsterAccountUpdate(BaseModel):
    """Account update (WebSocket ACCOUNT_UPDATE)."""

    e: str = ""
    E: int = 0
    T: int = 0
    a: dict[str, object] | None = None  # update data (m, B, P)


class AsterLiquidationOrder(BaseModel):
    """Liquidation order (WebSocket @forceOrder)."""

    e: str = ""
    E: int = 0
    o: dict[str, object] | None = None  # order object


class AsterMarket(BaseModel):
    """Aster market / perps instrument."""

    market_id: str | None = None
    symbol: str | None = None
    base_asset: str | None = None
    quote_asset: str | None = None
    info: dict | None = None


class AsterOrderBook(BaseModel):
    """Order book snapshot."""

    market_id: str | None = None
    bids: list[list[str | float]] | None = None
    asks: list[list[str | float]] | None = None
    timestamp: int | None = None
    info: dict | None = None


class AsterOrder(BaseModel):
    """Order (submit / status)."""

    order_id: str | None = None
    market_id: str | None = None
    side: str | None = None
    size: str | None = None
    price: str | None = None
    status: str | None = None
    filled_size: str | None = None
    info: dict | None = None


class AsterPosition(BaseModel):
    """Position."""

    market_id: str | None = None
    side: str | None = None
    size: str | None = None
    entry_price: str | None = None
    unrealized_pnl: str | None = None
    info: dict | None = None


class AsterError(BaseModel):
    """Aster API/on-chain error."""

    code: int | str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int) -> ErrorAction:
        """Map Aster error code to retry action (Binance Futures-compatible API).

        Ref: https://github.com/asterdex/api-docs/blob/master/aster-finance-api.md#error-codes
        """
        # 429 = rate limit; 503 = request accepted but timeout (execution unknown — query REST)
        retry_codes = {-1000, -1001, -1003, -1006, -1007, -1008, 429, 503}
        reconnect_codes = {418}  # IP banned — use Retry-After
        if code in retry_codes:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code in reconnect_codes:
            return ErrorAction.RETRY_WITH_BACKOFF  # wait Retry-After
        return ErrorAction.FAIL_HARD


class AsterWebSocketSubscribe(BaseModel):
    """Aster WebSocket subscription request (Binance Futures-compatible format).

    WS: wss://fstream.asterdex.com
    Max 200 streams per connection. Max 10 messages/sec.
    """

    method: str  # "SUBSCRIBE" or "UNSUBSCRIBE" or "LIST_SUBSCRIPTIONS"
    params: list[str]  # e.g. ["btcusdt@aggTrade", "btcusdt@depth"]
    id: int  # request tracking id


class AsterListenKeyCreate(BaseModel):
    """Aster listen key response (POST /fapi/v1/listenKey for user data stream).

    Valid 60 minutes. Extend via PUT. Connection max 24 hours.
    """

    listenKey: str


class AsterWebSocketClose(BaseModel):
    """Aster WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy.
    """

    code: int
    reason: str | None = None
