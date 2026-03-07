"""Deribit REST/WebSocket: market data, order/position, errors."""

__api_version__ = "v2"  # matches provider_api_versions.yaml

from decimal import Decimal

from pydantic import BaseModel

from unified_api_contracts import ErrorAction


class DeribitInstrument(BaseModel):
    """Deribit instrument (options, futures, perps)."""

    instrument_name: str | None = None
    kind: str | None = None  # future, option
    base_currency: str | None = None
    quote_currency: str | None = None
    settlement_currency: str | None = None
    tick_size: Decimal | float | None = None
    min_trade_amount: Decimal | float | None = None
    info: dict[str, object] | None = None


class DeribitTicker(BaseModel):
    """Deribit ticker (REST or WebSocket)."""

    instrument_name: str | None = None
    last_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    index_price: Decimal | float | None = None
    best_bid_price: Decimal | float | None = None
    best_ask_price: Decimal | float | None = None
    stats: dict[str, object] | None = None
    info: dict[str, object] | None = None


class DeribitOrderBook(BaseModel):
    """Deribit order book (REST or WebSocket)."""

    instrument_name: str | None = None
    bids: list[list[Decimal | float]] = []
    asks: list[list[Decimal | float]] = []
    change_id: int | None = None
    info: dict[str, object] | None = None


class DeribitOrder(BaseModel):
    """Deribit order (REST or WebSocket)."""

    order_id: str | None = None
    order_state: str | None = None  # open, filled, cancelled
    instrument_name: str | None = None
    direction: str | None = None  # buy, sell
    amount: Decimal | float | None = None
    price: Decimal | float | None = None
    filled_amount: Decimal | float | None = None
    average_price: Decimal | float | None = None
    creation_timestamp: int | None = None
    info: dict[str, object] | None = None


class DeribitPosition(BaseModel):
    """Deribit position (options, futures, perps)."""

    instrument_name: str | None = None
    size: Decimal | float | None = None
    direction: str | None = None
    average_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    total_profit_loss: Decimal | float | None = None
    info: dict[str, object] | None = None


class DeribitTrade(BaseModel):
    """Deribit public trade (get_last_trades_by_instrument)."""

    trade_id: str | None = None
    instrument_name: str | None = None
    timestamp: int | None = None  # ms
    price: Decimal | float | None = None
    amount: Decimal | float | None = None
    direction: str | None = None  # buy or sell
    trade_seq: int | None = None


class DeribitError(BaseModel):
    """Deribit API error payload."""

    code: int | None = None
    message: str | None = None
    data: dict[str, object] | None = None

    @classmethod
    def classify(cls, code: int) -> ErrorAction:
        """Map Deribit error code to retry action.

        Ref: https://docs.deribit.com/articles/errors
        """
        retry_codes = {10028, 10040, 10041, 10047, 10066, 11051, 11094, 13028}
        reconnect_codes = {13009, 13010}  # invalid/revoked token → reauth + reconnect
        if code in retry_codes:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code in reconnect_codes:
            return ErrorAction.RECONNECT
        return ErrorAction.FAIL_HARD


class DeribitTickerFull(BaseModel):
    """Deribit WebSocket full ticker (channel: ticker.{instrument_name}.{interval}).

    Contains all fields including settlement, funding, and mark price.
    Interval: raw, 100ms, agg2
    """

    instrument_name: str
    state: str | None = None  # open, closed
    timestamp: int  # ms
    ask_price: Decimal | float | None = None
    bid_price: Decimal | float | None = None
    last_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    index_price: Decimal | float | None = None
    settlement_price: Decimal | float | None = None  # settlement/delivery price
    funding_8h: Decimal | float | None = None  # 8h funding rate (perpetuals)
    open_interest: Decimal | float | None = None
    best_bid_amount: Decimal | float | None = None
    best_ask_amount: Decimal | float | None = None
    high: Decimal | float | None = None
    low: Decimal | float | None = None
    stats: dict[str, object] | None = None  # volume, price_change, etc.


class DeribitPerpetualFunding(BaseModel):
    """Deribit WebSocket perpetual funding rate (channel: perpetual.{instrument_name}.{interval})."""

    instrument_name: str
    timestamp: int  # ms
    index_price: Decimal | float
    interest: Decimal | float  # current funding rate


class DeribitMarkPriceOption(BaseModel):
    """Deribit WebSocket options mark price (channel: markprice.options.{index_name}).

    Subscription: markprice.options.btc_usd, markprice.options.eth_usd, etc.
    """

    instrument_name: str
    mark_price: Decimal | float
    iv: Decimal | float | None = None  # implied volatility (0.01 = 1%)
    timestamp: int  # ms


class DeribitIndexPrice(BaseModel):
    """Deribit WebSocket index price (channel: deribit_price_index.{index_name})."""

    index_name: str  # e.g. btc_usd, eth_usd
    price: Decimal | float
    timestamp: int  # ms


class DeribitUserPortfolio(BaseModel):
    """Deribit WebSocket private user portfolio (channel: user.portfolio.{currency}).

    Subscription: user.portfolio.BTC or user.portfolio.ETH or user.portfolio.any
    Includes options portfolio greeks.
    """

    currency: str  # BTC, ETH, USDC, etc.
    equity: Decimal | float | None = None
    margin_balance: Decimal | float | None = None
    available_funds: Decimal | float | None = None
    initial_margin: Decimal | float | None = None
    maintenance_margin: Decimal | float | None = None
    delta_total: Decimal | float | None = None  # total delta exposure
    options_vega: Decimal | float | None = None
    options_theta: Decimal | float | None = None
    options_gamma: Decimal | float | None = None
    options_delta: Decimal | float | None = None
    futures_pl: Decimal | float | None = None
    futures_session_pl: Decimal | float | None = None
    total_pl: Decimal | float | None = None


class DeribitSettlementRecord(BaseModel):
    """Deribit settlement/delivery record (REST: private/get_settlement_history_by_currency).

    Settlement types:
    - settlement: regular perpetual funding settlement
    - delivery: futures/options delivery at expiry
    - bankruptcy: forced settlement due to bankruptcy
    """

    type: str  # settlement, delivery, bankruptcy
    timestamp: int  # ms
    instrument_name: str
    position: Decimal | float | None = None  # position size at settlement
    mark_price: Decimal | float | None = None
    index_price: Decimal | float | None = None
    funding: Decimal | float | None = None  # funding payment (settlement only)
    session_profit_loss: Decimal | float | None = None
    profit_loss: Decimal | float | None = None
    session_bankruptcy: Decimal | float | None = None  # bankruptcy only
    socialized: Decimal | float | None = None  # bankruptcy socialized loss


class DeribitOptionsGreeks(BaseModel):
    """Deribit per-instrument options greeks (from ticker channel or REST /public/get_order_book).

    Available in DeribitTickerFull.stats for options instruments,
    or via markprice.options channel (IV only there; full greeks from REST).
    """

    instrument_name: str
    mark_price: Decimal | float | None = None
    iv: Decimal | float | None = None  # implied volatility annualized (0.01 = 1%)
    delta: Decimal | float | None = None
    gamma: Decimal | float | None = None
    theta: Decimal | float | None = None
    vega: Decimal | float | None = None
    rho: Decimal | float | None = None
    timestamp: int | None = None


class DeribitWebSocketSubscribe(BaseModel):
    """Deribit WebSocket subscription request (JSON-RPC 2.0).

    Public channels: method = "public/subscribe"
    Private channels: method = "private/subscribe" (auth first via public/auth)
    """

    jsonrpc: str = "2.0"
    method: str  # "public/subscribe" or "private/subscribe"
    params: dict[str, object]  # {"channels": ["ticker.BTC-PERPETUAL.100ms", ...]}
    id: int  # request id for tracking response


class DeribitWebSocketAuth(BaseModel):
    """Deribit WebSocket authentication request (JSON-RPC 2.0).

    Must call before any private/subscribe.
    """

    jsonrpc: str = "2.0"
    method: str = "public/auth"
    params: dict[str, object]  # {"grant_type": "client_credentials", "client_id": ..., "client_secret": ...}
    id: int


class DeribitWebSocketHeartbeat(BaseModel):
    """Deribit WebSocket heartbeat (server sends test requests; client must respond)."""

    jsonrpc: str = "2.0"
    method: str  # "heartbeat" (server→client) or "public/test" (client→server response)
    params: dict[str, object] | None = None
    id: int | None = None


class DeribitWebSocketClose(BaseModel):
    """Deribit WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy.
    """

    code: int
    reason: str | None = None


class DeribitInstrumentInfoFull(BaseModel):
    """Deribit full instrument specification (REST: GET /public/get_instrument or /public/get_instruments).

    Covers futures, options, perpetuals for all currencies.
    """

    instrument_name: str
    kind: str | None = None  # future, option, spot, future_combo, option_combo
    instrument_type: str | None = None  # reversed_future, future, etc.
    base_currency: str | None = None  # BTC, ETH, SOL, USDC
    quote_currency: str | None = None  # USD, USDC
    settlement_currency: str | None = None
    creation_timestamp: int | None = None
    expiration_timestamp: int | None = None  # ms; 32503708800000 = no expiry (perp)
    strike: Decimal | float | None = None
    option_type: str | None = None  # call or put
    is_active: bool | None = None
    settlement_period: str | None = None  # day, week, month
    min_trade_amount: Decimal | float | None = None
    tick_size: Decimal | float | None = None
    contract_size: Decimal | float | None = None
    taker_commission: Decimal | float | None = None
    maker_commission: Decimal | float | None = None
    block_trade_commission: Decimal | float | None = None


class DeribitSettlementHistory(BaseModel):
    """Deribit settlement history record (REST: /private/get_settlement_history_by_currency)."""

    type: str  # settlement, delivery, bankruptcy
    timestamp: int  # ms
    instrument_name: str
    position: Decimal | float | None = None
    index_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    session_profit_loss: Decimal | float | None = None
    profit_loss: Decimal | float | None = None
    funding: Decimal | float | None = None  # settlement only
    session_bankruptcy: Decimal | float | None = None
    socialized: Decimal | float | None = None


# --- Institutional: Account, Portfolio Margin, Vol Index, Funding, Settlement, Risk ---


class DeribitAccountSummary(BaseModel):
    """Deribit full account snapshot (REST: private/get_account_summary).

    Includes fee tier (fee_group), balance, equity, margin, options greeks.
    Use extended=true for account ID, username, email, account type.
    """

    currency: str
    balance: Decimal | float | None = None
    equity: Decimal | float | None = None
    margin_balance: Decimal | float | None = None
    available_funds: Decimal | float | None = None
    available_withdrawal_funds: Decimal | float | None = None
    initial_margin: Decimal | float | None = None
    maintenance_margin: Decimal | float | None = None
    fee_group: str | None = None  # fee tier / volume-based discount level
    fee_balance: Decimal | float | None = None
    total_pl: Decimal | float | None = None
    session_rpl: Decimal | float | None = None
    session_upl: Decimal | float | None = None
    options_delta: Decimal | float | None = None
    options_gamma: Decimal | float | None = None
    options_theta: Decimal | float | None = None
    options_vega: Decimal | float | None = None
    options_pl: Decimal | float | None = None
    futures_pl: Decimal | float | None = None
    delta_total: Decimal | float | None = None
    projected_delta_total: Decimal | float | None = None
    deposit_address: str | None = None
    info: dict[str, object] | None = None


class DeribitPortfolioMarginSummary(BaseModel):
    """Deribit portfolio margin summary (WS: user.portfolio.{currency} or account summary).

    Aggregated delta/gamma/theta/vega across all options positions.
    """

    currency: str
    delta_total: Decimal | float | None = None
    projected_delta_total: Decimal | float | None = None
    options_delta: Decimal | float | None = None
    options_gamma: Decimal | float | None = None
    options_theta: Decimal | float | None = None
    options_vega: Decimal | float | None = None
    options_value: Decimal | float | None = None
    equity: Decimal | float | None = None
    initial_margin: Decimal | float | None = None
    maintenance_margin: Decimal | float | None = None
    available_funds: Decimal | float | None = None
    info: dict[str, object] | None = None


class DeribitVolatilityIndex(BaseModel):
    """Deribit volatility index (DVOL/BVOL).

    REST: public/get_volatility_index_data; WS: deribit_volatility_index.{index_name}.
    REST returns candles: [[timestamp_ms, open, high, low, close], ...].
    WS returns single index value updates.
    """

    index_name: str | None = None  # e.g. btc_usd, eth_usd
    currency: str | None = None  # BTC, ETH
    timestamp: int | None = None  # ms
    value: Decimal | float | None = None  # WS single value
    open: Decimal | float | None = None
    high: Decimal | float | None = None
    low: Decimal | float | None = None
    close: Decimal | float | None = None
    # REST candles: list[object] of [timestamp, open, high, low, close]
    data: list[list[Decimal | float]] | None = None
    continuation: int | None = None  # pagination
    info: dict[str, object] | None = None


class DeribitFundingRateHistory(BaseModel):
    """Deribit funding rate history (REST: public/get_funding_rate_history).

    Hourly funding rates for perpetual instruments.
    """

    instrument_name: str | None = None
    timestamp: int  # ms
    funding_rate: Decimal | float
    index_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    info: dict[str, object] | None = None


class DeribitSettlementCashFlows(BaseModel):
    """Deribit settlement cash flows (REST: private/get_settlement_history_by_instrument).

    Per-instrument settlement, delivery, and bankruptcy cash flows.
    """

    instrument_name: str
    type: str  # settlement, delivery, bankruptcy
    timestamp: int  # ms
    position: Decimal | float | None = None
    index_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    session_profit_loss: Decimal | float | None = None
    profit_loss: Decimal | float | None = None
    funding: Decimal | float | None = None
    session_bankruptcy: Decimal | float | None = None
    socialized: Decimal | float | None = None
    info: dict[str, object] | None = None


class DeribitRiskLimit(BaseModel):
    """Deribit risk limit (per instrument or account).

    Max notional, maintenance margin rate, initial margin rate.
    """

    instrument_name: str | None = None
    currency: str | None = None
    max_notional: Decimal | float | None = None
    maintenance_margin: Decimal | float | None = None
    initial_margin: Decimal | float | None = None
    max_order_size: Decimal | float | None = None
    info: dict[str, object] | None = None


class DeribitSessionBankruptcyDetails(BaseModel):
    """Deribit session bankruptcy event (socialized loss, forced settlement).

    Distinct from settlement record; captures bankruptcy-specific metadata.
    """

    instrument_name: str | None = None
    timestamp: int  # ms
    session_bankruptcy: Decimal | float | None = None  # bankruptcy amount
    socialized: Decimal | float | None = None  # socialized loss
    position: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    index_price: Decimal | float | None = None
    info: dict[str, object] | None = None


# ---------------------------------------------------------------------------
# Deribit combo instruments (future_combo, option_combo)
# ---------------------------------------------------------------------------


class DeribitComboLeg(BaseModel):
    """Single leg of a Deribit combo instrument."""

    instrument_name: str  # e.g. "BTC-29MAR24" or "BTC-29MAR24-50000-C"
    direction: str  # "buy" | "sell"
    ratio: int = 1  # typically 1 for most standard combos


class DeribitComboInstrument(BaseModel):
    """Deribit combo instrument definition.

    Endpoints:
    - GET /public/get_combo_details?combo_id={id}
    - GET /public/get_instruments?kind=combo (or future_combo, option_combo)

    Named combos include:
    - Calendar spreads: BTC-FS-29MAR24_28JUN24 (buy near, sell far)
    - Risk reversals: buy call + sell put (same expiry)
    - Straddles, strangles (option combos)
    - Custom OTC combos: block_trade_only=True

    Combo instruments were added to Deribit in Q3 2023.
    """

    combo_id: str | None = None  # Deribit-assigned combo ID
    instrument_name: str | None = None  # e.g. "BTC-FS-29MAR24_28JUN24"
    kind: str | None = None  # "future_combo" | "option_combo"
    state: str | None = None  # "active" | "inactive"
    block_trade_only: bool | None = None  # True = OTC block trade required
    legs: list[DeribitComboLeg] | None = None
    creation_timestamp: int | None = None  # Unix ms
    base_currency: str | None = None  # BTC, ETH
    quote_currency: str | None = None  # USD, USDC


class DeribitComboTicker(BaseModel):
    """Ticker/quote for a Deribit combo instrument.

    Sources:
    - REST: GET /public/get_order_book?instrument_name={combo_name}
    - WebSocket: ticker.{combo_instrument_name} subscription
    """

    instrument_name: str | None = None
    timestamp: int | None = None  # Unix ms
    mark_price: Decimal | float | None = None
    last_price: Decimal | float | None = None
    best_bid_price: Decimal | float | None = None
    best_ask_price: Decimal | float | None = None
    best_bid_amount: Decimal | float | None = None
    best_ask_amount: Decimal | float | None = None
    open_interest: Decimal | float | None = None


class DeribitBlockTradeRequest(BaseModel):
    """Block trade submission for custom multi-leg OTC trades.

    Endpoint: POST /private/execute_block_trade

    Each element in trades specifies one leg of the block trade.
    Role is "maker" (price provider) or "taker" (price taker).
    Nonce must be unique per request.
    """

    nonce: str
    role: str
    trades: list[dict[str, object]]


class DeribitLiquidationOrder(BaseModel):
    """Deribit liquidation order from user fills WebSocket channel."""

    instrument_name: str | None = None
    price: float | None = None
    amount: float | None = None
    side: str | None = None
    timestamp: int | None = None


# === Migrated from unified-market-interface adapters ===


class DeribitJsonRpcResponse(BaseModel, frozen=True):
    """Generic Deribit JSON-RPC response envelope."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: object | None = None
    error: DeribitError | None = None


class DeribitOrderInfo(BaseModel, frozen=True):
    """Order info returned in buy/sell result."""

    order_id: str = ""
    order_state: str = "open"
    instrument_name: str = ""
    direction: str = ""
    amount: float = 0.0
    price: float | None = None
    filled_amount: float = 0.0
    average_price: float = 0.0


class DeribitOrderResult(BaseModel, frozen=True):
    """Result payload for buy/sell endpoints."""

    order: DeribitOrderInfo = DeribitOrderInfo()
    trades: list["DeribitTradeFrozen"] = []


class DeribitTradeFrozen(BaseModel, frozen=True):
    """A single fill/trade returned by Deribit (frozen, API-boundary variant)."""

    trade_id: str = ""
    amount: float = 0.0
    price: float = 0.0
    fee: float = 0.0
    timestamp: int = 0


class DeribitOrderResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for buy/sell endpoints."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: DeribitOrderResult | None = None
    error: DeribitError | None = None


class DeribitCancelResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for cancel endpoint."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: DeribitOrderInfo | None = None
    error: DeribitError | None = None


class DeribitOrderStateResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for get_order_state endpoint."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: DeribitOrderInfo | None = None
    error: DeribitError | None = None


class DeribitPositionFrozen(BaseModel, frozen=True):
    """A single position returned by get_positions (frozen, API-boundary variant).

    Uses floating_profit_loss alias for unrealized_pnl per Deribit REST response.
    """

    instrument_name: str = ""
    size: float = 0.0
    average_price: float = 0.0
    unrealized_pnl: float = 0.0

    model_config = {"populate_by_name": True}


class DeribitPositionsResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for get_positions endpoint."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: list[DeribitPositionFrozen] = []
    error: DeribitError | None = None


class DeribitOpenOrdersResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for get_open_orders endpoint."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: list[DeribitOrderInfo] = []
    error: DeribitError | None = None


class DeribitInstrumentFrozen(BaseModel, frozen=True):
    """A single instrument returned by get_instruments (frozen, API-boundary variant)."""

    instrument_name: str = ""
    kind: str = ""
    base_currency: str = ""
    quote_currency: str = ""
    expiration_timestamp: int | None = None
    strike: float | None = None
    option_type: str | None = None
    tick_size: float | None = None
    contract_size: float | None = None
    min_trade_amount: float | None = None


class DeribitInstrumentsResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for get_instruments endpoint."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: list[DeribitInstrumentFrozen] = []
    error: DeribitError | None = None


class DeribitGetInstrumentsResponse(BaseModel):
    """Deribit JSON-RPC response for public/get_instruments (non-frozen variant).

    result is a list of DeribitInstrumentInfoFull objects.
    """

    jsonrpc: str | None = None
    id: int | None = None
    result: list[DeribitInstrumentInfoFull] = []
    error: DeribitError | None = None


class DeribitGetInstrumentResponse(BaseModel):
    """Deribit JSON-RPC response for public/get_instrument (single instrument)."""

    jsonrpc: str | None = None
    id: int | None = None
    result: DeribitInstrumentInfoFull | None = None
    error: DeribitError | None = None


class DeribitTickerResult(BaseModel, frozen=True):
    """Ticker data returned by Deribit REST ticker endpoint."""

    last_price: float | None = None
    best_bid_price: float | None = None
    best_ask_price: float | None = None
    mark_price: float | None = None
    index_price: float | None = None
    instrument_name: str = ""


class DeribitTickerResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for ticker endpoint."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: DeribitTickerResult | None = None
    error: DeribitError | None = None


class DeribitAccountSummaryFrozen(BaseModel, frozen=True):
    """Account summary data (frozen, API-boundary variant)."""

    equity: float | None = None
    available_funds: float | None = None
    margin_balance: float | None = None
    wallet_balance: float | None = None
    initial_margin: float | None = None
    maintenance_margin: float | None = None


class DeribitAccountSummaryResponse(BaseModel, frozen=True):
    """Full JSON-RPC response for get_account_summary endpoint."""

    jsonrpc: str = "2.0"
    id: int | None = None
    result: DeribitAccountSummaryFrozen | None = None
    error: DeribitError | None = None
