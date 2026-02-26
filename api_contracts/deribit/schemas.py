"""Deribit REST/WebSocket: market data, order/position, errors."""

from decimal import Decimal

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


class DeribitInstrument(BaseModel):
    """Deribit instrument (options, futures, perps)."""

    instrument_name: str | None = None
    kind: str | None = None  # future, option
    base_currency: str | None = None
    quote_currency: str | None = None
    settlement_currency: str | None = None
    tick_size: Decimal | float | None = None
    min_trade_amount: Decimal | float | None = None
    info: dict | None = None


class DeribitTicker(BaseModel):
    """Deribit ticker (REST or WebSocket)."""

    instrument_name: str | None = None
    last_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    index_price: Decimal | float | None = None
    best_bid_price: Decimal | float | None = None
    best_ask_price: Decimal | float | None = None
    stats: dict | None = None
    info: dict | None = None


class DeribitOrderBook(BaseModel):
    """Deribit order book (REST or WebSocket)."""

    instrument_name: str | None = None
    bids: list[list[Decimal | float]] = []
    asks: list[list[Decimal | float]] = []
    change_id: int | None = None
    info: dict | None = None


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
    info: dict | None = None


class DeribitPosition(BaseModel):
    """Deribit position (options, futures, perps)."""

    instrument_name: str | None = None
    size: Decimal | float | None = None
    direction: str | None = None
    average_price: Decimal | float | None = None
    mark_price: Decimal | float | None = None
    total_profit_loss: Decimal | float | None = None
    info: dict | None = None


class DeribitError(BaseModel):
    """Deribit API error payload."""

    code: int | None = None
    message: str | None = None
    data: dict | None = None

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
