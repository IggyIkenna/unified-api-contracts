"""Pydantic schemas for TWS/ib_insync. Full surface: market data, order, position, account, errors, callbacks."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


# --- Market data (bars, ticker, order book) ---
class IBKRBar(BaseModel):
    """Historical bar from reqHistoricalData / reqBarChartData."""

    date: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    barCount: int | None = None
    average: float | None = None


class IBKRReqHistoricalDataParams(BaseModel):
    """Params for reqHistoricalData (TWS)."""

    contract: dict[str, Any] | None = None
    endDateTime: str | None = None
    durationStr: str | None = None
    barSizeSetting: str | None = None
    whatToShow: str | None = None
    useRTH: int | None = None
    formatDate: int | None = None


class IBKRBondMarketData(BaseModel):
    """Bond market data from TWS (bid/ask, YTW, duration, convexity, DV01)."""

    bid_price: float | None = None
    ask_price: float | None = None
    bid_yield: float | None = None
    ask_yield: float | None = None
    ytm: float | None = None
    ytw: float | None = None
    duration: float | None = None
    convexity: float | None = None
    dv01: float | None = None


class IBKRTicker(BaseModel):
    """Live ticker (bid, ask, last, etc.)."""

    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    bidSize: float | None = None
    askSize: float | None = None
    lastSize: float | None = None
    volume: float | None = None
    high: float | None = None
    low: float | None = None
    open: float | None = None
    close: float | None = None


# --- Order ---
class IBKROrder(BaseModel):
    """Order submission / status. Align with ib_insync order attributes."""

    orderId: int | None = None
    clientId: int | None = None
    permId: int | None = None
    action: str | None = None  # BUY, SELL
    orderType: str | None = None  # MKT, LMT, etc.
    totalQuantity: float | None = None
    lmtPrice: float | None = None
    auxPrice: float | None = None
    status: str | None = None  # PendingSubmit, Submitted, Filled, Cancelled, etc.
    filledQuantity: float | None = None
    avgFillPrice: float | None = None
    info: dict[str, Any] | None = None


# --- Position ---
class IBKRPosition(BaseModel):
    """Position from reqPositions / position update."""

    account: str | None = None
    contract: dict | None = None  # conId, symbol, secType, exchange, etc.
    position: float | None = None
    avgCost: float | None = None
    marketPrice: float | None = None
    marketValue: float | None = None
    unrealizedPNL: float | None = None
    realizedPNL: float | None = None
    info: dict[str, Any] | None = None


# --- Account summary / balance ---
class IBKRAccountValue(BaseModel):
    """Single account value (NetLiquidation, TotalCashValue, etc.)."""

    tag: str | None = None
    value: str | None = None
    currency: str | None = None
    account: str | None = None


class IBKRAccountUpdateMulti(BaseModel):
    """IBKR multi-account update (reqAccountUpdatesMulti / updateAccountValue).

    Same structure as IBKRAccountValue; used when subscribed to multiple accounts.
    Each callback delivers one account's key/value pair.
    """

    tag: str | None = None
    value: str | None = None
    currency: str | None = None
    account: str | None = None


class IBKRPortfolioItem(BaseModel):
    """Portfolio item (holding)."""

    account: str | None = None
    contract: dict | None = None
    position: float | None = None
    marketPrice: float | None = None
    marketValue: float | None = None
    avgCost: float | None = None
    unrealizedPNL: float | None = None
    realizedPNL: float | None = None


# --- PnL ---
class IBKRPnL(BaseModel):
    """Daily PnL (reqPnL)."""

    dailyPnL: float | None = None
    unrealizedPnL: float | None = None


# --- Error / status ---
class IBKRWebSocketClose(BaseModel):
    """IBKR/TWS WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy.
    """

    code: int
    reason: str | None = None


class IBKRError(BaseModel):
    """TWS error message."""

    reqId: int | None = None
    errorCode: int | None = None
    errorString: str | None = None
    advancedOrderRejectJson: str | None = None

    @classmethod
    def classify(cls, error_code: int | None = None) -> ErrorAction:
        """Map IBKR/TWS error code to retry action.

        Ref: https://interactivebrokers.github.io/tws-api/message_codes.html
        """
        if error_code in (100, 2103, 2104, 2106):
            return ErrorAction.RETRY_WITH_BACKOFF
        if error_code == 1100:
            return ErrorAction.RECONNECT
        if error_code and 1300 <= error_code < 1400:  # order rejections
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD


class IBKRContractDetails(BaseModel):
    """IBKR contract details (TWS API: reqContractDetails).

    Note: IBKR uses TWS API (not REST). These schemas represent the
    normalized response for reference data purposes.
    """

    conid: int | None = None  # contract ID
    symbol: str | None = None
    secType: str | None = None  # STK, OPT, FUT, CASH, CFD
    lastTradeDateOrContractMonth: str | None = None
    strike: Decimal | float | None = None
    right: str | None = None  # C=call, P=put
    multiplier: str | None = None  # contract multiplier
    exchange: str | None = None
    currency: str | None = None
    localSymbol: str | None = None
    tradingClass: str | None = None
    minTick: Decimal | float | None = None
    longName: str | None = None
    industry: str | None = None
    category: str | None = None
    subcategory: str | None = None
    timeZoneId: str | None = None
    underConid: int | None = None  # underlying contract id
    evRule: str | None = None


class IBKRCorporateAction(BaseModel):
    """IBKR corporate action event (from IBKR statement/flex query)."""

    conid: int | None = None
    symbol: str
    description: str | None = None
    reportDate: str | None = None  # YYYY-MM-DD
    currency: str | None = None
    type: str | None = None  # Dividends, Splits, Mergers, BonusRights
    amount: Decimal | None = None
    actionDescription: str | None = None


# --- Scanner (reqScannerSubscription / scannerData) ---
class IBKRScannerSubscription(BaseModel):
    """Scanner subscription parameters (TWS reqScannerSubscription)."""

    numberOfRows: int | None = None
    instrument: str | None = None  # STK, FUT, etc.
    locationCode: str | None = None
    scanCode: str | None = None
    abovePrice: float | None = None
    belowPrice: float | None = None
    aboveVolume: int | None = None
    marketCapAbove: float | None = None
    marketCapBelow: float | None = None
    moodyRatingAbove: str | None = None
    moodyRatingBelow: str | None = None
    spyOptionExpirationAbove: str | None = None
    spyOptionExpirationBelow: str | None = None
    averageOptionVolumeAbove: int | None = None
    scannerSettingPairs: str | None = None
    stockTypeFilter: str | None = None


class IBKRScannerData(BaseModel):
    """Scanner result row (TWS scannerData callback)."""

    rank: int | None = None
    contractDetails: dict | None = None
    distance: str | None = None
    benchmark: str | None = None
    projection: str | None = None
    legsStr: str | None = None


# --- Execution / Commission ---
class IBKRExecution(BaseModel):
    """Execution (fill) from execDetails callback."""

    execId: str | None = None
    time: str | None = None
    account: str | None = None
    exchange: str | None = None
    side: str | None = None
    shares: float | None = None
    price: float | None = None
    permId: int | None = None
    clientId: int | None = None
    orderId: int | None = None
    liquidation: int | None = None
    cumQty: float | None = None
    avgPrice: float | None = None
    orderRef: str | None = None
    evRule: str | None = None
    evMultiplier: float | None = None
    modelCode: str | None = None
    lastLiquidity: int | None = None


class IBKRCommissionReport(BaseModel):
    """Commission report (TWS commissionReport callback)."""

    execId: str | None = None
    commission: float | None = None
    currency: str | None = None
    realizedPNL: float | None = None
    yield_: float | None = None
    yieldRedemptionDate: int | None = None


# --- PnL (single position / history) ---
class IBKRPnLSingle(BaseModel):
    """Single-position PnL (reqPnLSingle)."""

    reqId: int | None = None
    posId: int | None = None
    dailyPnL: float | None = None
    unrealizedPnL: float | None = None
    realizedPnL: float | None = None
    value: float | None = None


class IBKRPnLHistory(BaseModel):
    """PnL history (reqPnL)."""

    reqId: int | None = None
    dailyPnL: float | None = None
    unrealizedPnL: float | None = None
    realizedPnL: float | None = None


# --- Market depth (L2) ---
class IBKRMarketDepth(BaseModel):
    """Level 2 market depth (reqMktDepth / mktDepthData)."""

    reqId: int | None = None
    position: int | None = None
    operation: int | None = None  # 0=insert, 1=update, 2=delete
    side: int | None = None  # 0=ask, 1=bid
    price: float | None = None
    size: float | None = None
    isSmartDepth: bool | None = None


# --- Historical ticks ---
class IBKRHistoricalTick(BaseModel):
    """Historical tick (reqHistoricalTicks, tickType=TRADES)."""

    time: int | None = None
    price: float | None = None
    size: float | None = None


class IBKRHistoricalTickBidAsk(BaseModel):
    """Historical bid/ask tick (reqHistoricalTicks, tickType=BID_ASK)."""

    time: int | None = None
    priceBid: float | None = None
    priceAsk: float | None = None
    sizeBid: float | None = None
    sizeAsk: float | None = None


class IBKRHistoricalTickLast(BaseModel):
    """Historical last tick (reqHistoricalTicks, tickType=LAST)."""

    time: int | None = None
    price: float | None = None
    size: float | None = None
    exchange: str | None = None
    specialConditions: str | None = None


# --- Options (sec def, greeks, volatility) ---
class IBKRSecDefOptParams(BaseModel):
    """Security definition option params (reqSecDefOptParams)."""

    reqId: int | None = None
    underlyingSymbol: str | None = None
    tradingClass: str | None = None
    multiplier: str | None = None
    expirations: list[str] | None = None
    strikes: list[float] | None = None


class IBKROptionGreeks(BaseModel):
    """Option greeks (reqCalculateOptionPrice / reqCalculateImpliedVolatility)."""

    modelPrice: float | None = None
    impliedVol: float | None = None
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None


class IBKRHistoricalVolatility(BaseModel):
    """Historical volatility (reqHistoricalData with HLV)."""

    date: str | None = None
    volatility: float | None = None


# --- Real-time bars (5s) ---
class IBKRRealTimeBar(BaseModel):
    """5-second real-time bar (reqRealTimeBars)."""

    time: int | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    wap: float | None = None
    count: int | None = None


# ---------------------------------------------------------------------------
# IBKR combo (BAG) contracts — spread and multi-leg instruments
# ---------------------------------------------------------------------------


class IBKRComboLeg(BaseModel):
    """Single leg of an IBKR combination (BAG) contract.

    All fields map to TWS API ComboLeg object. Conid (contract ID) identifies
    the specific instrument — use reqContractDetails to look up conids.
    """

    conid: int  # Contract ID of the leg instrument
    ratio: int = 1  # Quantity ratio (e.g. 1 for equal legs, 2 for 2:1 ratio)
    action: str  # "BUY" | "SELL"
    exchange: str | None = None  # Leg-specific exchange; "SMART" for auto-routing
    open_close: int | None = None  # 0=same as parent, 1=open, 2=close, 3=unknown
    short_sale_slot: int | None = None
    designated_location: str | None = None
    exempt_code: int = -1  # -1 = default


class IBKRComboContract(BaseModel):
    """IBKR combination/spread contract (secType='BAG' in TWS API).

    Covers all multi-leg strategies:
    - Straddle: buy call + buy put (same strike/expiry)
    - Strangle: buy OTM call + buy OTM put
    - Bull call spread: buy lower strike call + sell higher strike call
    - Bear put spread: buy higher strike put + sell lower strike put
    - Butterfly: buy 1 + sell 2 + buy 1
    - Condor: 4-leg spread
    - Calendar spread (time spread): buy near + sell far same instrument type
    - EFP: futures vs ETF/basket (separate IBKREfpContract below)

    Workflow: build IBKRComboContract → reqContractDetails to validate → reqMktData
    for combo quote → placeOrder with IBKRComboOrderRequest.
    """

    symbol: str  # Underlying symbol (e.g. "AAPL", "SPX", "BTC")
    sec_type: str = "BAG"  # Always "BAG" for combinations
    exchange: str | None = None  # e.g. "SMART", "CBOE"
    currency: str | None = None  # e.g. "USD"
    combo_legs_descrip: str | None = None  # Human-readable e.g. "BUY 1 CALL + SELL 1 CALL"
    combo_legs: list[IBKRComboLeg] | None = None


class IBKRComboOrderRequest(BaseModel):
    """Order for an IBKR combination contract.

    For delta-neutral combos: set delta_neutral_order_type and
    delta_neutral_aux_price — TWS automatically adds a hedge leg.

    smart_combo_routing_params controls net-debit/credit/even fill logic:
    [{"tag": "NonGuaranteed", "val": "1"}, {"tag": "PriceCondConid", "val": "0"}]
    """

    contract: IBKRComboContract
    action: str  # "BUY" (enter) | "SELL" (exit)
    total_quantity: float
    order_type: str  # "LMT", "MKT", "REL" (relative/pegged)
    lmt_price: float | None = None
    smart_combo_routing_params: list[dict] | None = None  # [{tag, val}] pairs
    # Delta-neutral hedging (auto-creates a hedge leg)
    delta_neutral_order_type: str | None = None  # "MKT" | "LMT"
    delta_neutral_aux_price: float | None = None


class IBKREfpContract(BaseModel):
    """IBKR Exchange for Physical (EFP) contract.

    An EFP exchanges a futures position for the underlying physical basket
    (typically an ETF or equity). Represented as a BAG with one futures leg
    and one basket/ETF leg.

    Common use: rolling a futures position to spot by swapping futures for ETF.
    """

    fut_conid: int  # Futures contract conid
    basket_conid: int | None = None  # ETF or basket conid (can be None for single stock)
    ratio: int = 1
    futures_symbol: str | None = None  # For documentation
    basket_symbol: str | None = None
