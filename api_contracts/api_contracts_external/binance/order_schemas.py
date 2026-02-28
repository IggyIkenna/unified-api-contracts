"""Binance order management schemas: orders, positions, executions."""

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


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


class BinanceAdlQuantile(BaseModel):
    """Binance ADL quantile per position (GET /fapi/v1/adlQuantile).

    ADL queue position 0-4 per symbol/positionSide.
    """

    symbol: str | None = None
    adlQuantile: dict[str, int] | None = None  # e.g. {"BOTH": 0} or {"LONG": 1, "SHORT": 2}


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
