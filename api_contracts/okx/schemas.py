"""OKX adapter: markets, tickers, order book, trades, order/position, errors, WebSocket, FIX."""

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


class OKXMarket(BaseModel):
    """OKX market/instrument."""

    instId: str | None = None
    instType: str | None = None  # SPOT, MARGIN, SWAP, FUTURES, OPTION
    baseCcy: str | None = None
    quoteCcy: str | None = None
    info: dict | None = None


class OKXTicker(BaseModel):
    """OKX ticker."""

    instId: str | None = None
    last: str | None = None
    bidPx: str | None = None
    askPx: str | None = None
    vol24h: str | None = None
    info: dict | None = None


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
    info: dict | None = None


class OKXPosition(BaseModel):
    """OKX position."""

    instId: str | None = None
    posSide: str | None = None
    pos: str | None = None
    avgPx: str | None = None
    markPx: str | None = None
    upl: str | None = None  # unrealized PnL
    info: dict | None = None


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

    ts: str  # timestamp (ms) — bar open time
    o: str  # open
    h: str  # high
    l: str  # low  # noqa: E741
    c: str  # close
    vol: str  # volume (contracts)
    volCcy: str | None = None  # volume in currency
    volCcyQuote: str | None = None  # volume in quote currency
    confirm: str  # "0"=latest unclosed, "1"=closed bar


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
