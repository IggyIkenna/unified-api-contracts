"""Kalshi prediction exchange API: series, events, markets, orders, positions.

Kalshi is a regulated US prediction exchange. API hierarchy: Series → Event → Market.
Base URL: https://trading-api.kalshi.com/trade-api/v2

CRITICAL versioning notes:
- Integer cent fields (yes_bid, yes_ask, no_bid, no_ask, volume, open_interest) are
  deprecated effective March 5, 2026. All code must use string fixed-point fields:
  yes_bid_dollars ("0.4500"), volume_fp ("1234.00"), etc.
- Historical data window shrinks from ~1 year to ~3 months around March 6, 2026.
  Bulk-download /trade-api/v2/markets (historical), /trade-api/v2/fills before cutoff.
- Rate tiers: Basic 20/10 req/s read/write. Prime 400/400 req/s (requires 7.5% of
  exchange monthly volume).

Market lifecycle: initialized → inactive → active → closed → determined → disputed →
amended → finalized
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from unified_api_contracts.shared import ErrorAction


class KalshiPriceRange(BaseModel):
    """Price range for market tick structure. start/end/step in dollars."""

    start: str | None = None
    end: str | None = None
    step: str | None = None


class KalshiSeries(BaseModel):
    """Recurring market series template (KXCPI, KXFED, INXD, KXBTC, etc.).

    Endpoint: GET /trade-api/v2/series/{series_ticker}
    """

    ticker: str | None = None
    series_ticker: str | None = None
    title: str | None = None
    category: str | None = None  # Economics, Politics, Sports, Finance
    sub_category: str | None = None
    frequency: str | None = None  # daily, weekly, monthly, one-off
    tags: list[str] | None = None
    volume_fp: str | None = None  # "1234.00" total contracts across all events
    description: str | None = None
    settlement_sources: list[str] | None = None


class KalshiEvent(BaseModel):
    """Specific instance of a series (KXCPI-24DEC).

    Endpoint: GET /trade-api/v2/events/{event_ticker}
    """

    event_ticker: str | None = None
    series_ticker: str | None = None
    title: str | None = None
    sub_title: str | None = None
    status: str | None = None  # open, closed
    mutually_exclusive: bool | None = None  # True = neg-risk bucket arb possible
    expected_expiration_time: str | None = None
    floor_strike: float | None = None
    cap_strike: float | None = None
    markets: list[KalshiMarket] | None = None


class KalshiMarket(BaseModel):
    """Binary outcome market (KXCPI-24DEC-T3.2).

    Endpoint: GET /trade-api/v2/markets/{ticker}

    String fixed-point fields (yes_bid_dollars, yes_ask_dollars, no_bid_dollars,
    no_ask_dollars, volume_fp, open_interest_fp) use format "0.4500" representing
    $0.45 per contract. Integer cent fields are deprecated March 5, 2026.
    """

    ticker: str | None = None
    event_ticker: str | None = None
    market_type: str | None = None  # binary, scalar
    title: str | None = None
    subtitle: str | None = None
    yes_sub_title: str | None = None
    no_sub_title: str | None = None
    rules_primary: str | None = None
    rules_secondary: str | None = None
    # Status lifecycle
    status: (
        Literal[
            "initialized",
            "inactive",
            "active",
            "closed",
            "determined",
            "disputed",
            "amended",
            "finalized",
        ]
        | str
        | None
    ) = None
    result: Literal["yes", "no", "scalar", ""] | str | None = None
    # String fixed-point prices (use these — integer fields deprecated Mar 5 2026)
    yes_bid_dollars: str | None = None  # e.g. "0.4500"
    yes_ask_dollars: str | None = None
    no_bid_dollars: str | None = None
    no_ask_dollars: str | None = None
    last_price_dollars: str | None = None
    volume_fp: str | None = None  # e.g. "1234.00" total contracts traded
    open_interest_fp: str | None = None
    settlement_value_dollars: str | None = None
    # Price structure (replaces deprecated tick_size integer)
    price_level_structure: str | None = None
    price_ranges: list[KalshiPriceRange] | None = None
    # Strike (for range/scalar markets)
    strike_type: (
        Literal[
            "greater",
            "greater_or_equal",
            "less",
            "less_or_equal",
            "between",
            "functional",
            "custom",
            "structured",
        ]
        | str
        | None
    ) = None
    floor_strike: float | None = None
    cap_strike: float | None = None
    liquidity: str | None = None
    # Deprecated integer cent fields (zero after March 5, 2026)
    yes_bid: int | None = None
    yes_ask: int | None = None
    no_bid: int | None = None
    no_ask: int | None = None
    volume: int | None = None
    open_interest: int | None = None
    expiration_time: str | None = None
    open_time: str | None = None
    close_time: str | None = None
    resolution_source: str | None = None
    can_close_early: bool | None = None
    expected_expiration_time: str | None = None


class KalshiOrderBook(BaseModel):
    """Order book snapshot for a market.

    Endpoint: GET /trade-api/v2/markets/{ticker}/orderbook

    v2 format uses yes_dollars/no_dollars: [["0.45", "100.00"], ...] (price_str, size_str).
    yes/no (integer cents) deprecated March 5, 2026.
    """

    ticker: str | None = None
    yes_dollars: list[tuple[str, str]] | None = None  # [("0.45", "100.00"), ...]
    no_dollars: list[tuple[str, str]] | None = None
    yes: list[list[int]] | None = None  # [[price_cents, qty], ...] deprecated Mar 5 2026
    no: list[list[int]] | None = None


class KalshiTrade(BaseModel):
    """Public trade record.

    Endpoint: GET /trade-api/v2/markets/{ticker}/trades
    """

    trade_id: str | None = None
    ticker: str | None = None
    yes_price_dollars: str | None = None
    no_price_dollars: str | None = None
    count_fp: str | None = None  # number of contracts
    taker_side: Literal["yes", "no"] | str | None = None
    created_time: str | None = None
    # Deprecated
    count: int | None = None
    yes_price: int | None = None
    no_price: int | None = None


class KalshiOrder(BaseModel):
    """Resting order.

    Endpoint: GET /trade-api/v2/portfolio/orders/{order_id}
    """

    order_id: str | None = None
    ticker: str | None = None
    action: str | None = None  # "buy" | "sell"
    side: str | None = None  # "yes" | "no"
    type: str | None = None  # "limit" | "market"
    status: str | None = None  # resting, canceled, executed, pending
    yes_price: int | None = None
    no_price: int | None = None
    count: int | None = None
    remaining_count: int | None = None
    amend_count: int | None = None
    client_order_id: str | None = None
    created_time: str | None = None
    expiration_time: str | None = None


class KalshiFill(BaseModel):
    """Order fill record.

    Endpoint: GET /trade-api/v2/portfolio/fills
    """

    trade_id: str | None = None
    order_id: str | None = None
    ticker: str | None = None
    side: str | None = None  # "yes" | "no"
    action: str | None = None  # "buy" | "sell"
    count_fp: str | None = None
    yes_price_dollars: str | None = None
    fees_dollars: str | None = None
    is_taker: bool | None = None
    created_time: str | None = None
    # Deprecated
    count: int | None = None
    yes_price: int | None = None
    no_price: int | None = None


class KalshiPosition(BaseModel):
    """User position in a specific market.

    Endpoint: GET /trade-api/v2/portfolio/positions
    """

    ticker: str | None = None
    position: int | None = None  # deprecated; use position_fp
    position_fp: str | None = None  # net YES contracts (negative = net NO)
    market_exposure_dollars: str | None = None
    realized_pnl_dollars: str | None = None
    unrealized_pnl_dollars: str | None = None
    fees_paid_dollars: str | None = None
    resting_orders_count: int | None = None
    total_traded: int | None = None
    total_traded_dollars: str | None = None
    event_ticker: str | None = None
    series_ticker: str | None = None
    market_title: str | None = None
    last_price_dollars: str | None = None
    yes_bid_dollars: str | None = None
    yes_ask_dollars: str | None = None
    status: str | None = None
    settlement_value_dollars: str | None = None
    # Deprecated
    market_exposure_fp: str | None = None
    realized_pnl_fp: str | None = None


class KalshiBalance(BaseModel):
    """Account balance.

    Endpoint: GET /trade-api/v2/portfolio/balance
    """

    balance_dollars: str | None = None
    payout_dollars: str | None = None
    subaccount: str | None = None
    # Deprecated aliases
    balance_fp: str | None = None
    payout_fp: str | None = None


class KalshiCandlestick(BaseModel):
    """OHLCV candlestick for a market.

    Endpoint: GET /trade-api/v2/markets/{ticker}/candlesticks
    """

    end_period_ts: str | None = None
    ticker: str | None = None
    yes_bid_dollars: str | None = None
    yes_ask_dollars: str | None = None
    yes_open_dollars: str | None = None
    yes_close_dollars: str | None = None
    yes_high_dollars: str | None = None
    yes_low_dollars: str | None = None
    volume_fp: str | None = None
    open_interest_fp: str | None = None


class KalshiHistoricalCutoff(BaseModel):
    """Cutoff timestamps for historical data partition.

    Endpoint: GET /trade-api/v2/historical/cutoff
    """

    market_settled_ts: str | None = None
    trades_created_ts: str | None = None
    orders_updated_ts: str | None = None


class KalshiWebSocketTickerMsg(BaseModel):
    """WebSocket ticker channel message (public, no auth required).

    Subscribe: {"id": 1, "cmd": "subscribe", "params": {"channels": ["ticker"], "market_tickers": ["TICKER"]}}
    """

    type: str | None = None  # "ticker"
    seq: int | None = None
    market_ticker: str | None = None
    yes_bid: int | None = None  # cents
    yes_ask: int | None = None
    yes_price: int | None = None  # last traded price
    volume: int | None = None
    open_interest: int | None = None
    ts: int | None = None  # Unix ms


class KalshiWebSocketOrderbookDeltaMsg(BaseModel):
    """WebSocket orderbook_delta channel message.

    Sent on every orderbook change; reconstruct full book from deltas.
    """

    type: str | None = None  # "orderbook_delta"
    seq: int | None = None
    market_ticker: str | None = None
    price: int | None = None  # cents
    delta: int | None = None  # positive = add, negative = remove
    side: str | None = None  # "yes" | "no"
    ts: int | None = None


class KalshiWebSocketTradeMsg(BaseModel):
    """WebSocket trade channel message."""

    type: str | None = None  # "trade"
    seq: int | None = None
    trade_id: str | None = None
    market_ticker: str | None = None
    yes_price: int | None = None  # cents
    count: int | None = None
    taker_side: str | None = None  # "yes" | "no"
    ts: int | None = None


class KalshiWebSocketMarketLifecycleMsg(BaseModel):
    """WebSocket market_lifecycle_v2 channel: market open/close/settle events."""

    type: str | None = None  # "market_lifecycle_v2"
    market_ticker: str | None = None
    action: str | None = None  # "opened", "closed", "settled"
    status: str | None = None
    result: str | None = None  # "yes" | "no" | None
    ts: int | None = None


class KalshiError(BaseModel):
    """Kalshi API error response."""

    error: str | None = None
    code: str | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: str | None = None, http_status: int | None = None) -> ErrorAction:
        """Map Kalshi error to retry action."""
        if http_status == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        if http_status is not None and http_status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if http_status in (401, 403):
            return ErrorAction.FAIL_HARD
        if code == "rate_limit_exceeded":
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
