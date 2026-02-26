"""Bybit adapter: markets, tickers, order book, trades, order/position, errors, WebSocket, FIX."""

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


class BybitMarket(BaseModel):
    """Bybit market/symbol."""

    symbol: str | None = None
    baseCoin: str | None = None
    quoteCoin: str | None = None
    info: dict | None = None


class BybitTicker(BaseModel):
    """Bybit ticker."""

    symbol: str | None = None
    lastPrice: str | None = None
    bid1Price: str | None = None
    ask1Price: str | None = None
    volume24h: str | None = None
    info: dict | None = None


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
