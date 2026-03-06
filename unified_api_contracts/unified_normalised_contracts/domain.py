"""Canonical domain schemas — self-contained (no internal imports).

Identifier convention
---------------------
``instrument_key``  — canonical cross-venue identifier in ``VENUE:TYPE:SYMBOL`` format
                      (e.g. ``"binance:PERPETUAL:BTCUSDT"``). Used in all market-data
                      canonical schemas (CanonicalTrade, CanonicalOrderBook, etc.) and
                      in instruments-service output. Stable and human-readable.

``instrument_id``   — venue-opaque identifier used only in *execution* schemas
                      (CanonicalOrder, CanonicalFill, ExecutionInstruction). May be a
                      venue-specific numeric/string ID. See execution.py for details.

Never mix the two: market-data consumers use ``instrument_key``; execution adapters
map venue-specific IDs via ``instrument_id`` defined in execution.py.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class InstrumentType(StrEnum):
    SPOT_PAIR = "SPOT_PAIR"
    PERPETUAL = "PERPETUAL"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    LST = "LST"
    A_TOKEN = "A_TOKEN"
    INDEX = "INDEX"


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class InstructionType(StrEnum):
    TRADE = "TRADE"
    SWAP = "SWAP"
    ZERO_ALPHA = "ZERO_ALPHA"


class MarketState(StrEnum):
    NORMAL = "normal"
    HALTED = "halted"
    AUCTION = "auction"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    CLOSED = "closed"


# ---------------------------------------------------------------------------
# Instrument — canonical row stored in GCS parquet by instruments-service
# ---------------------------------------------------------------------------


class InstrumentWarehouseRow(BaseModel):
    """Canonical instrument row stored in GCS parquet (subset of INSTRUMENTS_SCHEMA columns).

    Renamed from InstrumentRecord to avoid collision with UIC's InstrumentRecord
    (31-field, Decimal, normalized adapter contract). UAC owns this type as the
    output of instrument normalizers (normalize_databento_definition, etc.).
    """

    instrument_key: str = Field(description="VENUE:INSTRUMENT_TYPE:SYMBOL")
    venue: str
    instrument_type: InstrumentType
    symbol: str
    available_from_datetime: datetime
    timestamp: datetime

    instruction_type: InstructionType | None = None
    venue_type: str | None = None
    data_provider: str | None = None
    asset_class: str | None = None
    data_types: list[str] | None = None
    available_to_datetime: datetime | None = None
    base_asset: str | None = None
    quote_asset: str | None = None
    settle_asset: str | None = None
    exchange_raw_symbol: str | None = None
    databento_symbol: str | None = None
    tardis_exchange: str | None = None
    tardis_symbol: str | None = None
    ccxt_symbol: str | None = None
    ccxt_exchange: str | None = None
    inverse: bool | None = None
    tick_size: float | None = None
    min_size: float | None = None
    contract_size: float | None = None
    strike: float | None = None
    option_type: OptionType | None = None
    expiry: datetime | None = None
    underlying: str | None = None
    max_position_size: float | None = None
    max_leverage: float | None = None
    initial_margin_rate: float | None = None
    maintenance_margin_rate: float | None = None
    base_asset_contract_address: str | None = None
    quote_asset_contract_address: str | None = None
    pool_id: str | None = None
    pool_address: str | None = None
    pool_fee_tier: str | None = None
    flash_loan_providers: list[str] | None = None
    ltv: float | None = None
    liquidation_threshold: float | None = None
    trading_hours_open: str | None = None
    trading_hours_close: str | None = None
    trading_session: str | None = None
    is_trading_day: bool | None = None
    holiday_calendar: str | None = None
    regular_open_utc: str | None = None
    regular_close_utc: str | None = None
    auction_open_utc: str | None = None
    auction_close_utc: str | None = None
    early_close_utc: str | None = None
    session_date_tag: str | None = None


# ---------------------------------------------------------------------------
# Market tick schemas
# ---------------------------------------------------------------------------


class MarketTrade(BaseModel):
    """Raw trade tick (TRADES_SCHEMA)."""

    instrument_key: str
    price: float
    size: float
    aggressor_side: int = Field(description="1=buyer 2=seller")
    trade_id: str
    ts_event: int = Field(description="nanoseconds UTC")
    ts_init: int = Field(description="nanoseconds UTC")


class BookLevel(BaseModel):
    price: float
    size: float


class OrderBookSnapshot5(BaseModel):
    """Top-5 order book snapshot (BOOK_SNAPSHOT_5_SCHEMA)."""

    instrument_key: str
    ts_event: int
    ts_init: int
    bid_price_0: float | None = None
    bid_size_0: float | None = None
    bid_price_1: float | None = None
    bid_size_1: float | None = None
    bid_price_2: float | None = None
    bid_size_2: float | None = None
    bid_price_3: float | None = None
    bid_size_3: float | None = None
    bid_price_4: float | None = None
    bid_size_4: float | None = None
    ask_price_0: float | None = None
    ask_size_0: float | None = None
    ask_price_1: float | None = None
    ask_size_1: float | None = None
    ask_price_2: float | None = None
    ask_size_2: float | None = None
    ask_price_3: float | None = None
    ask_size_3: float | None = None
    ask_price_4: float | None = None
    ask_size_4: float | None = None


# ---------------------------------------------------------------------------
# Canonical normalized schemas (Decimal for price precision)
# ---------------------------------------------------------------------------


class CanonicalOrderBook(BaseModel):
    """Normalised order book (CanonicalOrderBook from unified-market-interface)."""

    venue: str
    symbol: str
    timestamp: datetime
    bids: list[tuple[Decimal, Decimal]] = Field(description="[(price, qty), ...]")
    asks: list[tuple[Decimal, Decimal]] = Field(description="[(price, qty), ...]")
    sequence_number: int | None = None
    instrument_key: str | None = Field(default=None, description="VENUE:TYPE:SYMBOL")
    levels: int | None = None
    schema_version: str = "1.0"


class CanonicalTrade(BaseModel):
    """Normalised trade (CanonicalTrade from unified-market-interface)."""

    venue: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    trade_id: str
    timestamp: AwareDatetime
    price: Decimal = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    side: str = Field(description="buy or sell")
    buyer_maker: bool | None = None
    venue_trade_id: str | None = None
    instrument_key: str | None = Field(default=None, description="VENUE:TYPE:SYMBOL")
    is_liquidation: bool | None = None
    schema_version: str = "1.0"


# ---------------------------------------------------------------------------
# Additional canonical types
# ---------------------------------------------------------------------------


class CanonicalTicker(BaseModel):
    """Normalised spot ticker — all venues."""

    instrument_key: str
    venue: str
    timestamp: datetime
    last_price: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    volume_24h: Decimal | None = None
    quote_volume_24h: Decimal | None = None
    price_change_24h: Decimal | None = None
    price_change_percent_24h: Decimal | None = None
    schema_version: str = "1.0"


class CanonicalLiquidation(BaseModel):
    """Normalised liquidation event — all CeFi venues."""

    instrument_key: str
    venue: str
    timestamp: datetime
    side: str = Field(description="buy or sell")
    price: Decimal
    size: Decimal
    order_id: str | None = None
    liquidated_account_value: Decimal | None = None
    liquidated_ntl_pos: Decimal | None = None
    liquidated_user: str | None = Field(default=None, json_schema_extra={"pii": True})
    schema_version: str = "1.0"


class CanonicalDerivativeTicker(BaseModel):
    """Normalised derivative ticker — perps/futures funding, OI, mark."""

    instrument_key: str
    venue: str
    timestamp: datetime
    mark_price: Decimal | None = None
    index_price: Decimal | None = None
    last_price: Decimal | None = None
    funding_rate: Decimal | None = None
    predicted_funding_rate: Decimal | None = None
    funding_timestamp: datetime | None = None
    next_funding_timestamp: datetime | None = None
    open_interest: Decimal | None = None
    open_interest_value: Decimal | None = None
    borrow_long_rate: Decimal | None = None
    borrow_short_rate: Decimal | None = None
    oracle_price: Decimal | None = None
    mid_price: Decimal | None = None
    day_ntl_volume: Decimal | None = None
    prev_day_price: Decimal | None = None
    basis: Decimal | None = None
    basis_rate: Decimal | None = None
    adl_rank: int | None = None
    schema_version: str = "1.0"


class CanonicalPosition(BaseModel):
    """Normalised position — all venues."""

    instrument_id: str
    side: str = Field(description="LONG or SHORT")
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    leverage: Decimal | None = None
    venue: str | None = None
    timestamp: datetime | None = None


class CanonicalBalance(BaseModel):
    """Normalised balance for a single currency."""

    currency: str
    free: Decimal
    locked: Decimal
    total: Decimal


class CanonicalFundingRate(BaseModel):
    """Normalised funding rate — perps/futures."""

    venue: str
    symbol: str
    rate: Decimal
    timestamp: datetime
    next_funding_timestamp: datetime | None = None
    predicted_rate: Decimal | None = None


class CanonicalOhlcvBar(BaseModel):
    """Normalised OHLCV bar — all venues."""

    timestamp: datetime
    venue: str
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal | None = None
    count: int | None = None
    vwap: Decimal | None = None


class CanonicalOptionsChainEntry(BaseModel):
    """Normalised options chain entry — strike, greeks, bid/ask."""

    timestamp: datetime
    venue: str
    symbol: str
    underlying: str
    strike: float
    option_type: str = Field(description="call or put")
    expiration: datetime | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    instrument_key: str | None = None


class CanonicalMarketInfo(BaseModel):
    """Normalised market/instrument metadata — all venues."""

    instrument_key: str
    venue: str
    symbol: str
    timestamp: datetime
    tick_size: float | None = None
    min_size: float | None = None
    contract_size: float | None = None
    base_asset: str | None = None
    quote_asset: str | None = None
    settle_asset: str | None = None


# CanonicalOraclePrice — owned by UIC (unified-internal-contracts/market_data/defi.py).
# No UAC normalizer produces this type; it is only used in internal pub-sub messaging.
# UIC re-exports it from unified_internal_contracts.market_data.

# CanonicalStakingRate — owned by UIC (unified-internal-contracts/market_data/defi.py).
# No UAC normalizer produces this type; it is only used in internal pub-sub messaging.
# UIC re-exports it from unified_internal_contracts.market_data.


class CanonicalWsMessage(BaseModel):
    """Normalised WebSocket message — minimal envelope."""

    channel: str
    timestamp: datetime
    venue: str
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class WebSocketEvent(StrEnum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ERROR = "error"
    RECONNECT = "reconnect"


class CanonicalWebSocketLifecycle(BaseModel):
    """Normalized WebSocket lifecycle event — connect, disconnect, ping/pong."""

    venue: str
    event: WebSocketEvent
    timestamp: datetime
    channel: str | None = None
    reason: str | None = None
    code: int | None = None  # WS close code
    latency_ms: float | None = None
    schema_version: str = "1.0"


class FeeType(StrEnum):
    """Canonical fee type (maker/taker/other)."""

    MAKER = "maker"
    TAKER = "taker"
    OTHER = "other"


class CanonicalFee(BaseModel):
    """Normalised fee — all venues (rate or amount)."""

    amount: Decimal = Field(description="Fee amount or rate (e.g. 0.001 for 0.1%)")
    currency: str = Field(description="Fee currency (e.g. USDT, BTC)")
    asset: str | None = Field(default=None, description="Asset symbol if different from currency")
    fee_type: FeeType = Field(default=FeeType.OTHER, description="maker, taker, or other")
    venue: str = Field(min_length=1)
    timestamp: datetime | None = Field(default=None, description="Optional timestamp")
    schema_version: str = "1.0"


# ---------------------------------------------------------------------------
# Processed candle schema from market-data-processing-service
# ---------------------------------------------------------------------------


class ProcessedCandle(BaseModel):
    """Output of market-data-processing-service (PROCESSED_CANDLE_SCHEMA)."""

    timestamp: datetime
    venue: str
    symbol: str
    instrument_id: str = Field(description="VENUE:TYPE:SYMBOL-QUOTE")
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    quote_volume: float | None = None
    count: int | None = None
    vwap: float | None = None
    market_state: MarketState | None = None
    is_halted: bool | None = None
    is_auction: bool | None = None
    expiration: datetime | None = None
    strike: float | None = None
    option_type: OptionType | None = None


# ---------------------------------------------------------------------------
# Sports and prediction market canonical schemas
# ---------------------------------------------------------------------------


class OddsFormat(StrEnum):
    DECIMAL = "decimal"
    AMERICAN = "american"
    FRACTIONAL = "fractional"


class CanonicalOdds(BaseModel):
    """Normalized odds from any bookmaker/exchange."""

    venue: str
    event_id: str
    market_id: str
    selection_id: str
    selection_name: str
    decimal_odds: Decimal  # Always stored as decimal
    timestamp: datetime
    is_back: bool = True  # True = back/buy, False = lay/sell
    available_size: Decimal | None = None
    runner_name: str | None = None
    event_name: str | None = None
    sport: str | None = None
    competition: str | None = None
    schema_version: str = "1.0"


class CanonicalBetMarket(BaseModel):
    """Normalized betting market metadata."""

    venue: str
    market_id: str
    event_id: str
    market_name: str
    event_name: str
    sport: str | None = None
    competition: str | None = None
    status: str | None = None  # open, suspended, closed, settled
    in_play: bool | None = None
    timestamp: datetime
    close_time: datetime | None = None
    schema_version: str = "1.0"


class CanonicalBetOrder(BaseModel):
    """Normalized bet order/placement."""

    venue: str
    order_id: str
    market_id: str
    selection_id: str
    side: str  # back or lay
    price: Decimal  # decimal odds
    size: Decimal  # stake
    status: str  # unmatched, matched, cancelled, settled
    timestamp: datetime
    matched_size: Decimal | None = None
    remaining_size: Decimal | None = None
    schema_version: str = "1.0"


__all__ = [
    "CanonicalBalance",
    "CanonicalBetMarket",
    "CanonicalBetOrder",
    "CanonicalDerivativeTicker",
    "CanonicalFee",
    "CanonicalFundingRate",
    "CanonicalLiquidation",
    "CanonicalMarketInfo",
    "CanonicalOdds",
    "CanonicalOhlcvBar",
    # CanonicalOptionsChainEntry — UAC owns (produced by UAC normalizers in normalize/options.py)
    "CanonicalOptionsChainEntry",
    # CanonicalOraclePrice — owned by UIC; not exported from UAC
    # CanonicalStakingRate — owned by UIC; not exported from UAC
    "CanonicalOrderBook",
    "CanonicalPosition",
    "CanonicalTicker",
    "CanonicalTrade",
    "CanonicalWebSocketLifecycle",
    "CanonicalWsMessage",
    "FeeType",
    "InstrumentType",
    # InstrumentWarehouseRow — renamed from InstrumentRecord to avoid collision with UIC's InstrumentRecord
    "InstrumentWarehouseRow",
    "MarketTrade",
    "OddsFormat",
    "OrderBookSnapshot5",
    "ProcessedCandle",
    "WebSocketEvent",
]
