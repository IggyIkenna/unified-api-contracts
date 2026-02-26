"""Coinbase Advanced Trade API: market data, trading, errors."""

from decimal import Decimal

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


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
    def from_list(cls, candle_data: list) -> "CoinbaseCandle":
        """Create CoinbaseCandle from list format returned by API."""
        return cls(
            timestamp=candle_data[0],
            low=candle_data[1],
            high=candle_data[2],
            open=candle_data[3],
            close=candle_data[4],
            volume=candle_data[5],
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
    fcm_trading_session_details: dict | None = None
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
