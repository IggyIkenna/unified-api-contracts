"""CCXT responses: fetch_markets, fetch_ticker, order_book, order, my_trades, balance, positions,
funding_rate, open_interest, ohlcv, leverage_tiers, withdrawals, deposits, ledger, errors,
borrow_rate, borrow_interest, margin_adjustment, insurance_fund, liquidation, settlement_history,
subaccount, currency, option, fees."""

from typing import Literal

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction

# --- Order status (CCXT unified) ---
CcxtOrderStatus = Literal["open", "closed", "canceled", "cancelled", "expired", "rejected"]

# --- Simple enums ---
CcxtMarginMode = Literal["cross", "isolated"]
CcxtPositionMode = Literal["one-way", "hedge"]


# --- Fee (nested in trade) ---
class CcxtFee(BaseModel):
    """Fee object in CCXT trade."""

    cost: float | None = None
    currency: str | None = None


# --- Precision (nested in market) ---
class CcxtMarketPrecision(BaseModel):
    """Precision for amount, price, cost, base, quote (decimal or integer mode)."""

    amount: float | int | None = None
    price: float | int | None = None
    cost: float | int | None = None
    base: int | None = None
    quote: int | None = None


# --- Limits (nested in market) ---
class CcxtMarketLimits(BaseModel):
    """Min/max limits for amount, price, cost."""

    amount: dict[str, float] | None = None  # min, max
    price: dict[str, float] | None = None
    cost: dict[str, float] | None = None
    market: dict[str, float] | None = None


# --- Market fees (nested in market) ---
class CcxtMarketFees(BaseModel):
    """Taker/maker fee rates for market."""

    taker: float | None = None
    maker: float | None = None


# --- Order (fetch_order response) ---
class CcxtOrder(BaseModel):
    """CCXT unified order structure."""

    id: str = Field(..., description="Exchange order ID")
    clientOrderId: str | None = None
    timestamp: int | None = Field(None, description="Milliseconds since epoch")
    datetime: str | None = None
    symbol: str | None = None
    type: str | None = None  # market, limit, etc.
    side: str | None = None  # buy, sell
    price: float | None = None
    amount: float | None = None
    filled: float | None = None
    remaining: float | None = None
    average: float | None = None
    status: str | None = None  # open, closed, canceled, etc.
    timeInForce: str | None = None
    reduceOnly: bool | None = None
    stopPrice: float | None = None
    trades: list["CcxtTrade"] | None = Field(None, description="List of fills for this order")
    info: dict[str, object] | None = None


# --- Trade (fetch_my_trades item) ---
class CcxtTrade(BaseModel):
    """CCXT unified trade (fill) structure."""

    id: str | None = None
    order: str | None = Field(None, description="Order ID this fill belongs to")
    timestamp: int | None = None
    datetime: str | None = None
    symbol: str | None = None
    type: str | None = None  # market, limit
    side: str | None = None
    takerOrMaker: str | None = None  # taker, maker
    price: float | None = None
    amount: float | None = None
    cost: float | None = None
    fee: CcxtFee | dict[str, object] | None = None
    fees: list[CcxtFee | dict[str, object]] | None = Field(None, description="Array of fees (multi-leg)")
    info: dict[str, object] | None = None


# --- Balance (per-currency in fetch_balance) ---
class CcxtBalance(BaseModel):
    """Per-currency balance in CCXT fetch_balance."""

    free: float | None = None
    used: float | None = None
    total: float | None = None
    debt: float | None = None
    timestamp: int | None = None


# --- Balance response (fetch_balance) ---
# Top-level keys: info, free, used, total, plus one key per currency (e.g. USDT, BTC)
# We model the per-currency part as dict[str, CcxtBalance]; 'info' can be list or dict (e.g. Binance futures)
class CcxtBalanceResponse(BaseModel):
    """CCXT fetch_balance response. Extra currency keys allowed via model_config."""

    model_config = {"extra": "allow"}  # CCXT adds dynamic currency keys

    info: list[object] | dict[str, object] | None = None
    free: dict[str, object] | None = None
    used: dict[str, object] | None = None
    total: dict[str, object] | None = None


# --- Position (fetch_positions item) ---
class CcxtPosition(BaseModel):
    """CCXT unified position structure (futures)."""

    id: str | None = None
    symbol: str | None = None
    side: str | None = None  # long, short, both
    contracts: float | None = None
    contractSize: float | None = None
    entryPrice: float | None = None
    markPrice: float | None = None
    lastPrice: float | None = None
    unrealizedPnl: float | None = None
    leverage: float | int | None = None
    percentage: float | None = None
    collateral: float | None = None
    liquidationPrice: float | None = None
    realizedPnl: float | None = None
    marginMode: str | None = None  # cross, isolated
    positionMode: str | None = None  # one-way, hedge
    initialMargin: float | None = None
    maintenanceMargin: float | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Market (fetch_markets item) ---
class CcxtMarket(BaseModel):
    """CCXT market structure."""

    id: str | None = None
    symbol: str | None = None
    base: str | None = None
    quote: str | None = None
    active: bool | None = None
    type: str | None = None  # spot, futures, swap, margin
    spot: bool | None = None
    futures: bool | None = None
    swap: bool | None = None
    margin: bool | None = None
    contract: bool | None = None
    contractSize: float | None = None
    expiry: int | None = None
    expiryDatetime: str | None = None
    settle: str | None = None
    settleId: str | None = None
    linear: bool | None = None
    inverse: bool | None = None
    precision: CcxtMarketPrecision | dict[str, object] | None = None
    limits: CcxtMarketLimits | dict[str, object] | None = None
    percentage: bool | None = None
    fees: CcxtMarketFees | dict[str, object] | None = None
    info: dict[str, object] | None = None


# --- Ticker (fetch_ticker) ---
class CcxtTicker(BaseModel):
    """CCXT ticker structure."""

    symbol: str | None = None
    last: float | None = None
    bid: float | None = None
    ask: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    info: dict[str, object] | None = None


# --- Order book (fetch_order_book) ---
class CcxtOrderBook(BaseModel):
    """CCXT order book structure."""

    symbol: str | None = None
    bids: list[list[float]] = Field(default_factory=list)  # [[price, size], ...]
    asks: list[list[float]] = Field(default_factory=list)
    timestamp: int | None = None
    datetime: str | None = None
    nonce: int | None = None
    info: dict[str, object] | None = None


# --- Funding rate (fetch_funding_rate) ---
class CcxtFundingRate(BaseModel):
    """CCXT fetch_funding_rate response."""

    symbol: str | None = None
    fundingRate: float | None = None
    fundingTimestamp: int | None = None
    fundingDatetime: str | None = None
    info: dict[str, object] | None = None


# --- Funding rate history (fetch_funding_rate_history) ---
class CcxtFundingRateHistory(BaseModel):
    """CCXT fetch_funding_rate_history item."""

    symbol: str | None = None
    fundingRate: float | None = None
    fundingTimestamp: int | None = None
    fundingDatetime: str | None = None
    info: dict[str, object] | None = None


# --- Open interest (fetch_open_interest) ---
class CcxtOpenInterest(BaseModel):
    """CCXT fetch_open_interest response."""

    symbol: str | None = None
    openInterest: float | None = None
    openInterestValue: float | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Open interest history (fetch_open_interest_history) ---
class CcxtOpenInterestHistory(BaseModel):
    """CCXT fetch_open_interest_history item."""

    symbol: str | None = None
    openInterest: float | None = None
    openInterestValue: float | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- OHLCV (fetch_ohlcv item) ---
class CcxtOhlcv(BaseModel):
    """CCXT fetch_ohlcv candle: [timestamp, open, high, low, close, volume]."""

    timestamp: int | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    info: dict[str, object] | None = None


# --- Aggregate trade (fetch_trades / public trades) ---
class CcxtAggTrade(BaseModel):
    """CCXT fetch_trades (public) aggregate trade structure."""

    id: str | None = None
    symbol: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    side: str | None = None
    price: float | None = None
    amount: float | None = None
    info: dict[str, object] | None = None


# --- Leverage tier (nested in CcxtLeverageTiers) ---
class CcxtLeverageTier(BaseModel):
    """Single tier in fetch_leverage_tiers."""

    tier: int | None = None
    minNotional: float | None = None
    maxNotional: float | None = None
    maintenanceMarginRate: float | None = None
    maxLeverage: int | float | None = None
    info: dict[str, object] | None = None


# --- Leverage tiers (fetch_leverage_tiers) ---
class CcxtLeverageTiers(BaseModel):
    """CCXT fetch_leverage_tiers response (per-symbol tiers)."""

    symbol: str | None = None
    tiers: list[CcxtLeverageTier] | None = None
    info: dict[str, object] | None = None


# --- Long/short ratio (fetch_long_short_ratio) ---
class CcxtLongShortRatio(BaseModel):
    """CCXT fetch_long_short_ratio response."""

    symbol: str | None = None
    longShortRatio: float | None = None
    longAccount: float | None = None
    shortAccount: float | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Greeks (fetch_greeks / options) ---
class CcxtGreeks(BaseModel):
    """CCXT options greeks (delta, gamma, theta, vega)."""

    symbol: str | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    timestamp: int | None = None
    info: dict[str, object] | None = None


# --- Withdrawal (fetch_withdrawals / withdraw) ---
class CcxtWithdrawal(BaseModel):
    """CCXT withdrawal structure."""

    id: str | None = None
    txid: str | None = None
    currency: str | None = None
    amount: float | None = None
    address: str | None = None
    tag: str | None = None
    status: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    fee: CcxtFee | dict[str, object] | None = None
    info: dict[str, object] | None = None


# --- Deposit (fetch_deposits) ---
class CcxtDeposit(BaseModel):
    """CCXT deposit structure."""

    id: str | None = None
    txid: str | None = None
    currency: str | None = None
    amount: float | None = None
    address: str | None = None
    tag: str | None = None
    status: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    fee: CcxtFee | dict[str, object] | None = None
    info: dict[str, object] | None = None


# --- Deposit address (fetch_deposit_address) ---
class CcxtDepositAddress(BaseModel):
    """CCXT fetch_deposit_address response."""

    currency: str | None = None
    address: str | None = None
    tag: str | None = None
    network: str | None = None
    info: dict[str, object] | None = None


# --- Ledger (fetch_ledger / fetch_transactions) ---
class CcxtLedger(BaseModel):
    """CCXT ledger/transaction entry."""

    id: str | None = None
    type: str | None = None  # deposit, withdrawal, trade, fee, etc.
    currency: str | None = None
    amount: float | None = None
    balance: float | None = None
    fee: CcxtFee | dict[str, object] | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Transfer (transfer) ---
class CcxtTransfer(BaseModel):
    """CCXT internal transfer structure."""

    id: str | None = None
    currency: str | None = None
    amount: float | None = None
    fromAccount: str | None = None
    toAccount: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    status: str | None = None
    info: dict[str, object] | None = None


# --- Trading fee (fetch_trading_fee) ---
class CcxtTradingFee(BaseModel):
    """CCXT fetch_trading_fee response."""

    symbol: str | None = None
    maker: float | None = None
    taker: float | None = None
    percentage: bool | None = None
    tierBased: bool | None = None
    info: dict[str, object] | None = None


# --- Borrow rate (fetch_borrow_rate / fetch_borrow_rates) ---
class CcxtBorrowRate(BaseModel):
    """CCXT borrow rate structure (fetch_borrow_rates, fetch_cross_borrow_rate)."""

    currency: str | None = None
    rate: float | None = None
    period: int | None = None  # milliseconds
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Borrow interest (fetch_borrow_interest) ---
class CcxtBorrowInterest(BaseModel):
    """CCXT borrow interest structure."""

    currency: str | None = None
    interest: float | None = None
    symbol: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Margin adjustment (add/reduce/set margin, fetch_margin_adjustment_history) ---
class CcxtMarginAdjustment(BaseModel):
    """CCXT margin adjustment structure."""

    type: str | None = None  # add, reduce, set
    amount: float | None = None
    total: float | None = None
    code: str | None = None
    symbol: str | None = None
    status: str | None = None
    info: dict[str, object] | None = None


# --- Insurance fund (fetch_insurance_fund) ---
class CcxtInsuranceFund(BaseModel):
    """CCXT unified insurance fund structure (futures risk pool)."""

    symbol: str | None = None
    balance: float | None = None
    balanceInUsd: float | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Liquidation (fetch_liquidations) ---
class CcxtLiquidation(BaseModel):
    """CCXT unified liquidation structure."""

    symbol: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    price: float | None = None
    amount: float | None = None
    side: str | None = None  # long, short
    leverage: float | int | None = None
    contracts: float | None = None
    contractSize: float | None = None
    baseValue: float | None = None
    quoteValue: float | None = None
    info: dict[str, object] | None = None


# --- Settlement history (fetch_settlement_history) ---
class CcxtSettlementHistory(BaseModel):
    """CCXT settlement history item."""

    symbol: str | None = None
    price: float | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Subaccount / Account (fetch_accounts / fetch_subaccounts) ---
class CcxtSubaccount(BaseModel):
    """CCXT account/subaccount structure (fetch_accounts, fetch_subaccounts)."""

    id: str | None = None
    type: str | None = None  # main, margin, spot, subaccount
    name: str | None = None
    code: str | None = None
    info: dict[str, object] | None = None


# --- Currency network (nested in CcxtCurrency) ---
class CcxtCurrencyNetwork(BaseModel):
    """CCXT network structure per currency (ERC20, TRC20, BSC, etc)."""

    id: str | None = None
    network: str | None = None
    name: str | None = None
    active: bool | None = None
    fee: float | None = None
    precision: int | float | None = None
    deposit: bool | None = None
    withdraw: bool | None = None
    limits: dict[str, object] | None = None
    info: dict[str, object] | None = None


# --- Currency (fetch_currencies item) ---
class CcxtCurrency(BaseModel):
    """CCXT unified currency structure (fetch_currencies). Networks per asset."""

    id: str | None = None
    code: str | None = None
    name: str | None = None
    active: bool | None = None
    fee: float | None = None
    precision: int | float | None = None
    deposit: bool | None = None
    withdraw: bool | None = None
    limits: dict[str, object] | None = None
    networks: dict[str, CcxtCurrencyNetwork | dict[str, object]] | None = None
    info: dict[str, object] | None = None


# --- Option (fetch_option / fetch_option_chain) ---
class CcxtOption(BaseModel):
    """CCXT option chain structure."""

    symbol: str | None = None
    currency: str | None = None
    timestamp: int | None = None
    datetime: str | None = None
    impliedVolatility: float | None = None
    openInterest: float | None = None
    bidPrice: float | None = None
    askPrice: float | None = None
    midPrice: float | None = None
    markPrice: float | None = None
    lastPrice: float | None = None
    underlyingPrice: float | None = None
    change: float | None = None
    percentage: float | None = None
    baseVolume: float | None = None
    quoteVolume: float | None = None
    info: dict[str, object] | None = None


# --- Fees (fetch_fees - all fees) ---
class CcxtFees(BaseModel):
    """CCXT fetch_fees response (trading, funding, etc.)."""

    trading: dict[str, CcxtTradingFee | dict[str, object]] | None = None  # symbol -> fee
    funding: dict[str, object] | None = None
    info: dict[str, object] | None = None


# --- Volatility history (fetch_volatility_history, optional) ---
class CcxtVolatilityHistory(BaseModel):
    """CCXT volatility history item."""

    symbol: str | None = None
    volatility: float | None = None
    timestamp: int | None = None
    datetime: str | None = None
    info: dict[str, object] | None = None


# --- Leverage (set_leverage response) ---
class CcxtLeverage(BaseModel):
    """CCXT set_leverage response."""

    symbol: str | None = None
    leverage: float | int | None = None
    marginMode: str | None = None
    info: dict[str, object] | None = None


# --- Error (CCXT exception payload) ---
class CcxtErrorPayload(BaseModel):
    """Typical CCXT error response shape."""

    code: str | None = None
    message: str | None = None
    info: dict[str, object] | None = None

    @classmethod
    def classify(cls, code: str | None = None, message: str | None = None) -> ErrorAction:
        """Map CCXT error type to retry action.

        CCXT uses exchange-agnostic exception types.
        """
        retry_types = {"RateLimitExceeded", "ExchangeNotAvailable", "ExchangeError", "NetworkError", "RequestTimeout"}
        if code and code in retry_types:
            return ErrorAction.RETRY_WITH_BACKOFF
        if message and any(x in (message or "").lower() for x in ("rate", "limit", "timeout", "unavailable")):
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


CcxtOrder.model_rebuild()
