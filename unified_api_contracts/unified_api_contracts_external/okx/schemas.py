"""OKX adapter: markets, tickers, order book, trades, order/position, errors, WebSocket, FIX."""

__api_version__ = "v5"  # matches provider_api_versions.yaml

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts import ErrorAction


class OKXMarket(BaseModel):
    """OKX market/instrument."""

    instId: str | None = None
    instType: str | None = None  # SPOT, MARGIN, SWAP, FUTURES, OPTION
    baseCcy: str | None = None
    quoteCcy: str | None = None
    info: dict[str, object] | None = None


class OKXTrade(BaseModel):
    """OKX public trade (REST: GET /api/v5/market/trades)."""

    instId: str | None = None
    tradeId: str | None = None
    px: str | None = None
    sz: str | None = None
    side: str | None = None  # buy or sell
    ts: str | None = None  # timestamp (ms)


class OKXOrderBook(BaseModel):
    """OKX order book (REST: GET /api/v5/market/books).

    data[0] from response. asks/bids: [[price, qty, ...], ...].
    seqId supports snapshot/delta sequencing.
    """

    asks: list[list[str]] = []  # [[price, qty, ...], ...]
    bids: list[list[str]] = []
    ts: str | None = None  # timestamp (ms)
    seqId: int | None = None  # sequence ID for order book management


class OKXTicker(BaseModel):
    """OKX ticker."""

    instId: str | None = None
    last: str | None = None
    bidPx: str | None = None
    askPx: str | None = None
    vol24h: str | None = None
    info: dict[str, object] | None = None


class OKXOrder(BaseModel):
    """OKX order (REST or WebSocket)."""

    ordId: str | None = None
    clOrdId: str | None = None
    instId: str | None = None
    side: str | None = None
    ordType: str | None = None
    sz: str | None = None
    px: str | None = None
    state: str | None = None  # live, partially_filled, filled, canceled
    fillPx: str | None = None
    accFillSz: str | None = None
    info: dict[str, object] | None = None


class OKXPosition(BaseModel):
    """OKX position."""

    instId: str | None = None
    posSide: str | None = None
    pos: str | None = None
    avgPx: str | None = None
    markPx: str | None = None
    upl: str | None = None  # unrealized PnL
    info: dict[str, object] | None = None


class OKXError(BaseModel):
    """OKX API error."""

    code: str | None = None
    msg: str | None = None

    @classmethod
    def classify(cls, code: str | int) -> ErrorAction:
        """Map OKX error code to retry action.

        Ref: https://www.okx.com/docs-v5/en/#error-code
        """
        retry_str_codes = {"50011", "50026", "50061"}  # rate limit, system error, sub-account limit
        reconnect_str_codes = {"64008"}  # connection upgrading → reconnect
        str_code = str(code)
        if str_code in retry_str_codes:
            return ErrorAction.RETRY_WITH_BACKOFF
        if str_code in reconnect_str_codes:
            return ErrorAction.RECONNECT
        return ErrorAction.FAIL_HARD


class OKXFundingRate(BaseModel):
    """OKX WebSocket funding rate (channel: funding-rate).

    Subscription: {"channel": "funding-rate", "instId": "BTC-USD-SWAP"}
    """

    instType: str  # SWAP
    instId: str
    fundingRate: str
    fundingTime: str  # timestamp (ms)
    nextFundingRate: str | None = None
    nextFundingTime: str | None = None


class OKXLiquidationOrder(BaseModel):
    """OKX WebSocket liquidation order (channel: liquidation-orders).

    Subscription: {"channel": "liquidation-orders", "instType": "SWAP"}
    """

    instType: str  # SWAP, FUTURES, MARGIN, OPTION
    instId: str | None = None
    liqPx: str | None = None  # liquidation price
    sz: str | None = None  # liquidation size
    side: str | None = None  # buy or sell
    ts: str | None = None  # timestamp (ms)


class OKXMarkPrice(BaseModel):
    """OKX WebSocket mark price (channel: mark-price).

    Subscription: {"channel": "mark-price", "instId": "BTC-USDT-SWAP"}
    """

    instType: str
    instId: str
    markPx: str  # mark price
    ts: str  # timestamp (ms)


class OKXCandleWS(BaseModel):
    """OKX WebSocket candle/OHLCV (channel: candle1m, candle5m, etc.).

    IMPORTANT: Subscribe on wss://ws.okx.com:8443/ws/v5/business (NOT /public).
    """

    model_config = ConfigDict(populate_by_name=True)

    ts: str  # timestamp (ms) — bar open time
    o: str  # open
    h: str  # high
    low: str = Field(alias="l")  # low (alias matches OKX API field "l")
    c: str  # close
    vol: str  # volume (contracts)
    volCcy: str | None = None  # volume in currency
    volCcyQuote: str | None = None  # volume in quote currency
    confirm: str  # "0"=latest unclosed, "1"=closed bar


class OKXMarkPriceKline(BaseModel):
    """OKX mark price candlestick (REST: GET /api/v5/market/history-mark-price-candles).

    Also WS channel mark-price-candle1D, etc. Format: [ts, o, h, l, c, confirm].
    """

    model_config = ConfigDict(populate_by_name=True)

    ts: str  # timestamp (ms)
    o: str  # open
    h: str  # high
    low: str = Field(alias="l")  # low (alias matches OKX API field "l")
    c: str  # close
    confirm: str  # "0"=unclosed, "1"=closed

    @classmethod
    def from_list(cls, row: list[str]) -> "OKXMarkPriceKline":
        """Create from array [ts, o, h, l, c, confirm]."""
        return cls(
            ts=row[0],
            o=row[1],
            h=row[2],
            l=row[3],
            c=row[4],
            confirm=row[5] if len(row) > 5 else "0",
        )


class OKXIndexPriceKline(BaseModel):
    """OKX index price candlestick (REST: GET /api/v5/market/history-index-candles).

    Same format as mark price. WS channel index-candle30m, etc.
    """

    model_config = ConfigDict(populate_by_name=True)

    ts: str  # timestamp (ms)
    o: str  # open
    h: str  # high
    low: str = Field(alias="l")  # low (alias matches OKX API field "l")
    c: str  # close
    confirm: str  # "0"=unclosed, "1"=closed

    @classmethod
    def from_list(cls, row: list[str]) -> "OKXIndexPriceKline":
        """Create from array [ts, o, h, l, c, confirm]."""
        return cls(
            ts=row[0],
            o=row[1],
            h=row[2],
            l=row[3],
            c=row[4],
            confirm=row[5] if len(row) > 5 else "0",
        )


class OKXOptionSummary(BaseModel):
    """OKX options vol surface / Greeks (WS channel: opt-summary, REST: /api/v5/public/option-instrument).

    Per-instrument Greeks and implied vol. markVol, bidVol, askVol, volLv (ATM IV).
    """

    instType: str  # OPTION
    instId: str  # e.g. BTC-USD-241013-70000-P
    uly: str | None = None  # underlying e.g. BTC-USD
    delta: str | None = None
    gamma: str | None = None
    vega: str | None = None
    theta: str | None = None
    lever: str | None = None
    markVol: str | None = None  # mark volatility
    bidVol: str | None = None
    askVol: str | None = None
    realVol: str | None = None
    deltaBS: str | None = None
    gammaBS: str | None = None
    thetaBS: str | None = None
    vegaBS: str | None = None
    volLv: str | None = None  # ATM implied vol
    fwdPx: str | None = None  # forward price
    ts: str | None = None  # timestamp (ms)


class OKXOptionTicker(BaseModel):
    """OKX options ticker (REST: GET /api/v5/market/ticker, instType=OPTION).

    Last, bid, ask, volume for options. Distinct from OKXOptionMarketData (mark price only).
    """

    instType: str  # OPTION
    instId: str  # e.g. BTC-USD-231229-50000-C
    last: str | None = None
    bidPx: str | None = None
    askPx: str | None = None
    vol24h: str | None = None
    open24h: str | None = None
    high24h: str | None = None
    low24h: str | None = None
    ts: str | None = None  # timestamp (ms)


class OKXOrderUpdateWS(BaseModel):
    """OKX WebSocket private order update (channel: orders).

    Subscription: {"channel": "orders", "instType": "SPOT|FUTURES|SWAP|OPTION", "instId": "BTC-USDT"}
    State values: live, partially_filled, filled, canceled, mmp_canceled
    """

    instType: str  # SPOT, MARGIN, SWAP, FUTURES, OPTION
    instId: str
    ordId: str  # order id
    clOrdId: str | None = None  # client order id
    state: str  # live, partially_filled, filled, canceled, mmp_canceled
    fillSz: str | None = None  # last fill size
    accFillSz: str | None = None  # accumulated fill size
    fillPx: str | None = None  # last fill price
    avgPx: str | None = None  # average fill price
    sz: str | None = None  # order size
    px: str | None = None  # order price
    side: str | None = None  # buy or sell
    posSide: str | None = None  # long, short, net
    ordType: str | None = None  # market, limit, post_only, etc.
    tradeId: str | None = None  # fill trade id
    execType: str | None = None  # T=taker, M=maker
    cTime: str | None = None  # creation time (ms)
    uTime: str | None = None  # update time (ms)
    fillTime: str | None = None  # fill time (ms)
    code: str | None = None  # error code ("0"=success)
    msg: str | None = None  # error message


class OKXPositionUpdateWS(BaseModel):
    """OKX WebSocket private position update (channel: positions or balance-and-position)."""

    instType: str
    instId: str | None = None
    posId: str | None = None
    pos: str | None = None  # position size
    avgPx: str | None = None  # average entry price
    upl: str | None = None  # unrealized PnL
    liqPx: str | None = None  # liquidation price
    mgnMode: str | None = None  # cross or isolated
    lever: str | None = None  # leverage
    uTime: str | None = None  # update time (ms)


class OKXAccountGreeks(BaseModel):
    """OKX WebSocket private options greeks (channel: account-greeks).

    Subscription: {"channel": "account-greeks", "ccy": "BTC"}
    Portfolio-level greeks (not per-instrument).
    """

    ccy: str  # currency e.g. BTC
    deltaBS: str | None = None  # Black-Scholes delta
    deltaPA: str | None = None  # PA model delta
    gammaBS: str | None = None
    gammaPA: str | None = None
    thetaBS: str | None = None
    thetaPA: str | None = None
    vegaBS: str | None = None
    vegaPA: str | None = None
    ts: str | None = None  # timestamp (ms)


class OKXOptionMarketData(BaseModel):
    """OKX options mark price via mark-price channel (channel: mark-price for OPTIONS instType).

    Subscribe: {"channel": "mark-price", "instId": "BTC-USD-231229-50000-C"}
    For per-instrument IV, use the tickers channel.
    """

    instType: str  # OPTION
    instId: str  # e.g. BTC-USD-231229-50000-C
    markPx: str  # mark price
    ts: str  # timestamp (ms)


class OKXWebSocketSubscribe(BaseModel):
    """OKX WebSocket subscription request.

    Public: wss://ws.okx.com:8443/ws/v5/public
    Private: wss://ws.okx.com:8443/ws/v5/private  (requires login first)
    Business: wss://ws.okx.com:8443/ws/v5/business (candles, algo orders)
    """

    op: str  # "subscribe" or "unsubscribe"
    args: list[dict[str, object]]  # e.g. [{"channel": "tickers", "instId": "BTC-USDT"}]


class OKXWebSocketLogin(BaseModel):
    """OKX WebSocket login request (required before subscribing to private channels)."""

    op: str = "login"
    args: list[dict[str, object]]  # [{"apiKey": ..., "passphrase": ..., "timestamp": ..., "sign": ...}]


class OKXWebSocketPing(BaseModel):
    """OKX WebSocket ping (raw string 'ping', not JSON)."""

    # OKX sends/receives raw string "ping" — not a JSON message
    # Server sends "pong" response. No pong within 30s → disconnect.
    pass


class OKXWebSocketClose(BaseModel):
    """OKX WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy, 64008=connection upgrading.
    """

    code: int
    reason: str | None = None


class OKXInstrumentInfo(BaseModel):
    """OKX instrument specification (REST: GET /api/v5/public/instruments).

    instType: SPOT, MARGIN, SWAP, FUTURES, OPTION
    """

    instType: str
    instId: str
    uly: str | None = None  # underlying e.g. BTC-USD (SWAP/FUTURES/OPTION)
    instFamily: str | None = None  # instrument family e.g. BTC-USD
    category: str | None = None  # 1=standard, 2=standard, 3=non-standard
    baseCcy: str | None = None  # SPOT only
    quoteCcy: str | None = None  # SPOT only
    settleCcy: str | None = None  # settlement currency
    ctVal: str | None = None  # contract value in base currency
    ctMult: str | None = None  # contract multiplier
    ctValCcy: str | None = None  # currency of ctVal
    optType: str | None = None  # C=call, P=put (OPTION only)
    stk: str | None = None  # strike price (OPTION only)
    listTime: str | None = None
    expTime: str | None = None  # expiry time ms (FUTURES/OPTION)
    lever: str | None = None  # max leverage
    tickSz: str | None = None  # tick size
    lotSz: str | None = None  # lot size (min trade)
    minSz: str | None = None  # min order size
    ctType: str | None = None  # linear or inverse
    alias: str | None = None  # this_week, next_week, quarter, next_quarter
    state: str | None = None  # live, suspend, preopen, test, expired


class OKXInstrumentsResponse(BaseModel):
    """OKX instruments API response (GET /api/v5/public/instruments)."""

    code: str | None = None
    msg: str | None = None
    data: list[OKXInstrumentInfo] = []


# --- CEX Order Submit / Ack / Cancel ---


class OKXOrderSubmitRequest(BaseModel):
    """OKX order submit request (POST /api/v5/trade/order).

    instType: SPOT, MARGIN, SWAP, FUTURES, OPTION — determines order type rules.
    tdMode: cash (spot), isolated, cross, margin.
    """

    instId: str  # e.g. BTC-USDT, BTC-USDT-SWAP, BTC-USD-231229-50000-C
    tdMode: str  # cash, isolated, cross, margin
    side: str  # buy, sell
    ordType: str  # market, limit, post_only, fok, ioc
    sz: str  # size in base (spot) or contracts (derivatives)
    clOrdId: str | None = None
    px: str | None = None  # price for limit
    posSide: str | None = None  # long, short, net (hedge mode)
    reduceOnly: bool | None = None
    tag: str | None = None


class OKXOrderSubmitResponse(BaseModel):
    """OKX order submit response (data array item)."""

    ordId: str | None = None
    clOrdId: str | None = None
    tag: str | None = None
    sCode: str | None = None
    sMsg: str | None = None
    ts: str | None = None


class OKXOrderCancelRequest(BaseModel):
    """OKX order cancel request (POST /api/v5/trade/cancel-order)."""

    instId: str
    ordId: str | None = None
    clOrdId: str | None = None  # use ordId OR clOrdId


class OKXOrderCancelResponse(BaseModel):
    """OKX order cancel response."""

    ordId: str | None = None
    clOrdId: str | None = None
    sCode: str | None = None
    sMsg: str | None = None


# --- Position, Margin, Realized PnL ---


class OKXPositionQueryResponse(BaseModel):
    """OKX position query response (GET /api/v5/account/positions)."""

    instId: str | None = None
    instType: str | None = None  # SWAP, FUTURES, MARGIN, OPTION
    posSide: str | None = None  # long, short, net
    pos: str | None = None
    avgPx: str | None = None
    markPx: str | None = None
    upl: str | None = None  # unrealized PnL
    uplRatio: str | None = None
    liqPx: str | None = None
    lever: str | None = None
    mgnMode: str | None = None  # cross, isolated


class OKXMarginBalanceResponse(BaseModel):
    """OKX margin/balance (GET /api/v5/account/balance)."""

    ccy: str | None = None
    bal: str | None = None
    frozenBal: str | None = None
    availBal: str | None = None
    eq: str | None = None  # equity
    availEq: str | None = None  # available equity
    upl: str | None = None  # unrealized PnL
    uplLiq: str | None = None


class OKXRealizedPnlResponse(BaseModel):
    """OKX realized PnL from fills (GET /api/v5/trade/fills) or pnl (GET /api/v5/account/bills)."""

    instId: str | None = None
    instType: str | None = None
    pnl: str | None = None
    posSide: str | None = None
    fillPx: str | None = None
    fillSz: str | None = None
    fee: str | None = None
    ts: str | None = None


# --- Withdrawal ---


class OKXWithdrawalRequest(BaseModel):
    """OKX withdrawal request (POST /api/v5/asset/withdrawal)."""

    ccy: str
    amt: str
    dest: str  # 3=internal, 4=on-chain
    toAddr: str
    fee: str | None = None  # network fee; if omitted, uses min
    chain: str | None = None  # e.g. BTC-Bitcoin
    clientId: str | None = None
    pwd: str | None = None  # trade password
    tag: str | None = None  # memo/destination tag


class OKXWithdrawalResponse(BaseModel):
    """OKX withdrawal response."""

    wdId: str | None = None
    ccy: str | None = None
    chain: str | None = None
    amt: str | None = None
    clientId: str | None = None
    state: str | None = None  # -2=failed, -1=canceled, 0=pending, 1=success, 2=waiting


# --- Institutional: Fee, Funding, Deposits, Transfers, OI, Risk, Portfolio, Delivery ---


class OKXFeeRate(BaseModel):
    """OKX fee rate (GET /api/v5/account/trade-fee)."""

    maker: str | None = None
    taker: str | None = None
    tier: str | None = None
    category: str | None = None


class OKXFundingRateHistory(BaseModel):
    """OKX funding rate history item (GET /api/v5/public/funding-rate-history)."""

    fundingTime: str | None = None
    fundingRate: str | None = None


class OKXDepositAddress(BaseModel):
    """OKX deposit address (GET /api/v5/asset/deposit-address)."""

    ccy: str | None = None
    chain: str | None = None
    addr: str | None = None
    to: str | None = None  # deposit address
    tag: str | None = None  # memo/destination tag


class OKXDepositHistory(BaseModel):
    """OKX deposit history item (GET /api/v5/asset/deposit-history)."""

    ccy: str | None = None
    chain: str | None = None
    amt: str | None = None
    txId: str | None = None
    fromAddr: str | None = None
    to: str | None = None
    ts: str | None = None
    state: str | None = None  # 0=pending, 1=success, 2=crediting


class OKXWithdrawalHistory(BaseModel):
    """OKX withdrawal history item (GET /api/v5/asset/withdrawal-history)."""

    wdId: str | None = None
    ccy: str | None = None
    chain: str | None = None
    amt: str | None = None
    txId: str | None = None
    to: str | None = None
    ts: str | None = None
    state: str | None = None  # -2=failed, -1=canceled, 0=pending, 1=success, 2=waiting


class OKXFundTransfer(BaseModel):
    """OKX internal fund transfer (POST /api/v5/asset/transfer)."""

    transId: str | None = None
    ccy: str | None = None
    amt: str | None = None
    fromAccount: str | None = None  # 6=funding, 18=trading
    toAccount: str | None = None
    subAcct: str | None = None  # sub-account name (if applicable)
    ts: str | None = None
    state: str | None = None  # success, pending, failed


class OKXLongShortRatio(BaseModel):
    """OKX long/short ratio (GET /api/v5/rubik/stat/contracts/long-short-account-ratio)."""

    longShortRatio: str | None = None
    longAccount: str | None = None
    shortAccount: str | None = None
    ts: str | None = None


class OKXOpenInterest(BaseModel):
    """OKX open interest (GET /api/v5/public/open-interest)."""

    instId: str | None = None
    instType: str | None = None
    oi: str | None = None
    oiCcy: str | None = None
    ts: str | None = None


class OKXOpenInterestHistory(BaseModel):
    """OKX open interest history (GET /api/v5/public/open-interest-history)."""

    instId: str | None = None
    instType: str | None = None
    oi: str | None = None
    oiCcy: str | None = None
    ts: str | None = None


class OKXRiskLimit(BaseModel):
    """OKX risk limit tier (GET /api/v5/public/risk-limit)."""

    tier: str | None = None
    maxLeverage: str | None = None
    maintenanceMarginRate: str | None = None
    maxLoan: str | None = None


class OKXPortfolioMarginAccount(BaseModel):
    """OKX portfolio margin account (GET /api/v5/account/portfolio-account)."""

    adjEq: str | None = None  # adjusted equity
    imr: str | None = None  # initial margin requirement
    mmr: str | None = None  # maintenance margin requirement
    mgnRatio: str | None = None
    ts: str | None = None


class OKXDeliveryExerciseHistory(BaseModel):
    """OKX delivery/exercise history (GET /api/v5/account/delivery-exercise-history)."""

    instId: str | None = None
    instType: str | None = None
    ts: str | None = None
    type: str | None = None  # delivery, exercise
    pnl: str | None = None
    fee: str | None = None


class OKXOptionTickerGreeks(BaseModel):
    """Per-instrument options greeks from GET /api/v5/market/ticker for OPTION instType.

    OKX has no native combo instrument type; multi-leg options are done via RFQ system.
    """

    instType: str | None = None
    instId: str | None = None
    last: str | None = None
    bidPx: str | None = None
    askPx: str | None = None
    markPx: str | None = None
    delta: str | None = None
    gamma: str | None = None
    vega: str | None = None
    theta: str | None = None
    lever: str | None = None
    markVol: str | None = None
    bidVol: str | None = None
    askVol: str | None = None
    realVol: str | None = None
    volLv: str | None = None
    oi: str | None = None
    ts: str | None = None


class OKXRfqLeg(BaseModel):
    """Single leg in OKX RFQ multi-leg block trade.

    OKX has no native combo instrument type; multi-leg is done via RFQ system.
    """

    instId: str | None = None
    sz: str | None = None
    side: str | None = None
    posSide: str | None = None


class OKXRfqCreateRequest(BaseModel):
    """POST /api/v5/otc/rfq/create-rfq for multi-leg block trades.

    OKX has no native combo instrument type; multi-leg is done via RFQ system.
    """

    anonymous: bool | None = None
    clRfqId: str | None = None
    counterparties: list[str] | None = None
    legs: list[OKXRfqLeg] = []
    tag: str | None = None


class OKXRfqResponse(BaseModel):
    """Response from OKX RFQ create or status.

    State: active, canceled, pending_fill, filled, expired, traded_away.
    """

    rfqId: str | None = None
    clRfqId: str | None = None
    state: str | None = None
    legs: list[OKXRfqLeg] | None = None
    cTime: str | None = None
    uTime: str | None = None


class OKXQuoteLeg(BaseModel):
    """Single leg in OKX quote response."""

    instId: str | None = None
    sz: str | None = None
    side: str | None = None
    px: str | None = None


class OKXQuoteResponse(BaseModel):
    """Response from OKX quote request."""

    quoteId: str | None = None
    rfqId: str | None = None
    clQuoteId: str | None = None
    state: str | None = None
    legs: list[OKXQuoteLeg] | None = None
    validUntil: str | None = None
    cTime: str | None = None
    uTime: str | None = None
