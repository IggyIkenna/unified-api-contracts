"""Coinbase Advanced Trade API: market data, trading, errors."""

from decimal import Decimal

from pydantic import BaseModel

from unified_api_contracts.shared import ErrorAction


class CoinbaseTicker(BaseModel):
    """Coinbase ticker data."""

    ask: Decimal
    bid: Decimal
    volume: Decimal
    trade_id: int
    price: Decimal
    size: Decimal
    time: str  # ISO timestamp
    rfq_volume: Decimal


class CoinbaseOrderBook(BaseModel):
    """Coinbase order book level 2 data."""

    sequence: int
    bids: list[list[str]]  # [[price, size], ...]
    asks: list[list[str]]


class CoinbaseTrade(BaseModel):
    """Coinbase trade from recent trades."""

    time: str  # ISO timestamp
    trade_id: int
    price: Decimal
    size: Decimal
    side: str  # "buy" or "sell"


class CoinbaseCandle(BaseModel):
    """Coinbase OHLCV candle data."""

    # Coinbase returns: [timestamp, low, high, open, close, volume]
    timestamp: int
    low: Decimal
    high: Decimal
    open: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_list(cls, candle_data: list[int | float | Decimal]) -> "CoinbaseCandle":
        """Create CoinbaseCandle from list format returned by API."""
        return cls(
            timestamp=int(candle_data[0]),
            low=Decimal(str(candle_data[1])),
            high=Decimal(str(candle_data[2])),
            open=Decimal(str(candle_data[3])),
            close=Decimal(str(candle_data[4])),
            volume=Decimal(str(candle_data[5])),
        )


class CoinbaseProduct(BaseModel):
    """Coinbase product information."""

    id: str
    base_currency: str
    quote_currency: str
    base_min_size: Decimal
    base_max_size: Decimal
    quote_increment: Decimal
    base_increment: Decimal
    display_name: str
    min_market_funds: Decimal
    max_market_funds: Decimal
    margin_enabled: bool
    post_only: bool
    limit_only: bool
    cancel_only: bool
    trading_disabled: bool
    status: str
    status_message: str


class CoinbaseError(BaseModel):
    """Coinbase API error response."""

    message: str
    type: str | None = None

    @classmethod
    def classify(cls, error_type: str, http_status: int | None = None) -> ErrorAction:
        """Map Coinbase error type to retry action.

        Ref: https://docs.cdp.coinbase.com/advanced-trade/docs/rest-api-errors
        """
        if http_status is not None and http_status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        retry_types = {"INTERNAL_SERVICE_ERROR", "TEMPORARILY_UNAVAILABLE"}
        if error_type in retry_types:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


class CoinbaseWebSocketSubscribe(BaseModel):
    """Coinbase Advanced Trade WebSocket subscription request.

    IMPORTANT: Always include 'heartbeats' channel to prevent auto-close
    after 60-90s of no updates on other channels.
    """

    type: str  # "subscribe" or "unsubscribe"
    product_ids: list[str]  # e.g. ["BTC-USD", "ETH-USD"]
    channel: str  # heartbeats, ticker, level2, market_trades, candles, user, futures_balance_summary
    jwt: str | None = None  # JWT token (required for private channels: user, futures_balance_summary)


class CoinbaseWebSocketHeartbeat(BaseModel):
    """Coinbase WebSocket heartbeat event (channel: heartbeats).

    Subscribe to this channel to keep all other subscriptions alive.
    """

    channel: str = "heartbeats"
    client_id: str | None = None
    timestamp: str | None = None  # ISO8601
    sequence_num: int | None = None
    current_time: str | None = None
    heartbeat_counter: int | None = None


class CoinbaseWebSocketClose(BaseModel):
    """Coinbase WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy.
    """

    code: int
    reason: str | None = None


class CoinbaseProductInfo(BaseModel):
    """Coinbase Advanced Trade product specification (REST: GET /api/v3/brokerage/products/{product_id})."""

    product_id: str  # e.g. BTC-USD, ETH-USD
    price: str | None = None
    price_percentage_change_24h: str | None = None
    volume_24h: str | None = None
    volume_percentage_change_24h: str | None = None
    base_increment: str | None = None  # minimum order size
    quote_increment: str | None = None  # tick size
    quote_min_size: str | None = None
    quote_max_size: str | None = None
    base_min_size: str | None = None
    base_max_size: str | None = None
    base_name: str | None = None
    quote_name: str | None = None
    watched: bool | None = None
    is_disabled: bool | None = None
    new: bool | None = None
    status: str | None = None
    cancel_only: bool | None = None
    limit_only: bool | None = None
    post_only: bool | None = None
    trading_disabled: bool | None = None
    auction_mode: bool | None = None
    product_type: str | None = None  # SPOT, FUTURE
    quote_currency_id: str | None = None
    base_currency_id: str | None = None
    fcm_trading_session_details: dict[str, object] | None = None
    mid_market_price: str | None = None
    alias: str | None = None
    alias_to: list[str] | None = None
    base_display_symbol: str | None = None
    quote_display_symbol: str | None = None
    view_only: bool | None = None
    price_increment: str | None = None
    display_name: str | None = None
    product_venue: str | None = None  # CBE, INTX
    approximate_quote_24h_volume: str | None = None


# --- CEX Order Submit / Ack / Cancel ---


class CoinbaseOrderSubmitRequest(BaseModel):
    """Coinbase Advanced Trade order submit request (POST /api/v3/brokerage/orders).

    product_type: SPOT, FUTURE. client_order_id required for idempotency.
    """

    client_order_id: str
    product_id: str  # e.g. BTC-USD
    side: str  # BUY, SELL
    order_configuration: dict[str, object]  # limit_limit_gtc, market_market_ioc, etc.
    leverage: str | None = None  # futures only
    leverage_strategy: str | None = None  # cross, isolated
    retail_portfolio_id: str | None = None
    self_trade_prevention_id: str | None = None


class CoinbaseOrderSubmitResponse(BaseModel):
    """Coinbase Advanced Trade order submit response."""

    success: bool | None = None
    failure_reason: str | None = None
    order_id: str | None = None
    success_response: dict[str, object] | None = None  # order_details
    error_response: dict[str, object] | None = None


class CoinbaseOrderCancelRequest(BaseModel):
    """Coinbase order cancel request (POST /api/v3/brokerage/orders/batch_cancel)."""

    order_ids: list[str] | None = None  # batch cancel by ids


class CoinbaseOrderCancelResponse(BaseModel):
    """Coinbase order cancel response."""

    results: list[dict[str, object]] | None = None  # per-order success/failure


# --- Position, Margin (Coinbase Advanced Trade: spot + futures) ---


class CoinbasePositionQueryResponse(BaseModel):
    """Coinbase futures position (GET /api/v3/brokerage/orders/historical/fills or positions)."""

    product_id: str | None = None
    side: str | None = None
    size: str | None = None
    entry_price: str | None = None
    mark_price: str | None = None
    unrealized_pnl: str | None = None
    leverage: str | None = None


class CoinbaseMarginBalanceResponse(BaseModel):
    """Coinbase balance (GET /api/v3/brokerage/accounts)."""

    uuid: str | None = None
    currency: str | None = None
    available_balance: dict[str, str] | None = None  # value, currency
    hold: dict[str, str] | None = None
    name: str | None = None


# --- Withdrawal ---


class CoinbaseWithdrawalRequest(BaseModel):
    """Coinbase withdrawal request.

    Note: Advanced Trade API has limited withdrawal support. Full withdrawal via
    Prime API or Exchange API. Schema covers common fields for crypto withdrawal.
    """

    profile_id: str | None = None
    amount: str
    currency: str
    crypto_address: str
    network: str | None = None
    no_destination_tag: bool | None = None
    destination_tag: str | None = None  # memo
    two_factor_code: str | None = None


class CoinbaseWithdrawalResponse(BaseModel):
    """Coinbase withdrawal response."""

    id: str | None = None
    amount: dict[str, str] | None = None
    fee: dict[str, str] | None = None
    subtotal: dict[str, str] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    resource: str | None = None  # withdraw


# --- Institutional: Fee Schedule, Order, Fill ---


class CoinbaseFeeSchedule(BaseModel):
    """Coinbase fee schedule (GET /api/v3/brokerage/transaction_summary).

    Fee tier, maker/taker rates, volume breakdown.
    """

    total_fees: Decimal | float | None = None  # USD
    total_volume: Decimal | float | None = None  # USD
    fee_tier: dict[str, object] | None = None  # pricing_tier, taker_fee_rate, maker_fee_rate
    pricing_tier: str | None = None
    taker_fee_rate: str | None = None
    maker_fee_rate: str | None = None
    advanced_trade_only_volume: Decimal | float | None = None
    advanced_trade_only_fees: Decimal | float | None = None
    volume_breakdown: list[dict[str, object]] | None = None
    margin_rate: Decimal | float | None = None  # futures only
    info: dict[str, object] | None = None


class CoinbaseOrder(BaseModel):
    """Coinbase order (GET /api/v3/brokerage/orders/historical/batch or single order)."""

    order_id: str | None = None
    product_id: str | None = None
    side: str | None = None  # BUY, SELL
    client_order_id: str | None = None
    status: str | None = None  # OPEN, FILLED, CANCELLED
    time_in_force: str | None = None
    created_time: str | None = None
    completion_percentage: str | None = None
    filled_size: str | None = None
    average_filled_price: str | None = None
    fee: str | None = None
    total_value_after_fees: str | None = None
    order_configuration: dict[str, object] | None = None
    info: dict[str, object] | None = None


class CoinbaseFill(BaseModel):
    """Coinbase fill (GET /api/v3/brokerage/orders/historical/fills). Fills with fees."""

    order_id: str | None = None
    trade_id: str | None = None
    product_id: str | None = None
    price: str | None = None
    size: str | None = None
    fee: str | None = None
    created_time: str | None = None
    liquidity: str | None = None  # maker, taker
    side: str | None = None
    info: dict[str, object] | None = None
