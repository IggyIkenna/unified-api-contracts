"""Internal domain data schemas — instruments, market ticks, order books, OHLCV, derivatives."""

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


class AggressorSide(StrEnum):
    BUY = "1"
    SELL = "2"


# ---------------------------------------------------------------------------
# Instrument — canonical row stored in GCS parquet by instruments-service
# Format: instrument_key = VENUE:INSTRUMENT_TYPE:SYMBOL
# ---------------------------------------------------------------------------


class InstrumentRecord(BaseModel):
    """Canonical instrument row (subset of INSTRUMENTS_SCHEMA columns).

    Full schema has 50+ nullable columns; this model covers the required core
    and the most commonly used optional fields.
    """

    # Required
    instrument_key: str = Field(description="VENUE:INSTRUMENT_TYPE:SYMBOL")
    venue: str
    instrument_type: InstrumentType
    symbol: str
    available_from_datetime: datetime
    timestamp: datetime

    # Identity
    instruction_type: InstructionType | None = None
    venue_type: str | None = None
    data_provider: str | None = None
    asset_class: str | None = None
    data_types: list[str] | None = None

    # Lifecycle
    available_to_datetime: datetime | None = None

    # Asset pair
    base_asset: str | None = None
    quote_asset: str | None = None
    settle_asset: str | None = None

    # Cross-provider symbols
    exchange_raw_symbol: str | None = None
    databento_symbol: str | None = None
    tardis_exchange: str | None = None
    tardis_symbol: str | None = None
    ccxt_symbol: str | None = None
    ccxt_exchange: str | None = None

    # Contract specs
    inverse: bool | None = None
    tick_size: float | None = None
    min_size: float | None = None
    contract_size: float | None = None

    # Derivatives
    strike: float | None = None
    option_type: OptionType | None = None
    expiry: datetime | None = None
    underlying: str | None = None

    # Risk
    max_position_size: float | None = None
    max_leverage: float | None = None
    initial_margin_rate: float | None = None
    maintenance_margin_rate: float | None = None

    # DeFi
    base_asset_contract_address: str | None = None
    quote_asset_contract_address: str | None = None
    pool_id: str | None = None
    pool_address: str | None = None
    pool_fee_tier: str | None = None

    # Lending
    flash_loan_providers: list[str] | None = None
    ltv: float | None = None
    liquidation_threshold: float | None = None

    # TradFi session
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
# Market tick schemas — written to GCS parquet by market-tick-data-handler
# Timestamps are int64 nanoseconds UTC
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


class DerivativeTicker(BaseModel):
    """Derivative-specific rolling ticker (DERIVATIVE_TICKER_SCHEMA)."""

    instrument_key: str
    ts_event: int
    ts_init: int
    funding_rate: float | None = None
    index_price: float | None = None
    mark_price: float | None = None
    open_interest: float | None = None
    next_funding_time: int | None = None
    predicted_funding_rate: float | None = None


class LiquidationRecord(BaseModel):
    """Liquidation event tick (LIQUIDATIONS_SCHEMA)."""

    instrument_key: str
    price: float
    size: float
    aggressor_side: int = Field(description="1=buy 2=sell")
    ts_event: int
    ts_init: int


class OhlcvBar(BaseModel):
    """Processed OHLCV candle (OHLCV_1M_SCHEMA and aggregated timeframes)."""

    instrument_key: str
    ts_event: int = Field(description="end of period, nanoseconds UTC")
    ts_init: int
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None


class QuoteRecord(BaseModel):
    """L1 bid/ask quote (QUOTES_SCHEMA)."""

    instrument_key: str
    ts_event: int
    ts_init: int
    bid_price: float | None = None
    ask_price: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None


# ---------------------------------------------------------------------------
# Canonical normalized schemas from unified-market-interface
# Uses Decimal for price precision (in-memory, not stored to parquet)
# ---------------------------------------------------------------------------


class CanonicalOrderBook(BaseModel):
    """Normalised order book (CanonicalOrderBook dataclass from unified-market-interface)."""

    venue: str
    symbol: str
    timestamp: datetime
    bids: list[tuple[Decimal, Decimal]] = Field(description="[(price, qty), ...]")
    asks: list[tuple[Decimal, Decimal]] = Field(description="[(price, qty), ...]")
    sequence_number: int | None = None


class CanonicalTrade(BaseModel):
    """Normalised trade (CanonicalTrade dataclass from unified-market-interface)."""

    venue: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    trade_id: str
    timestamp: AwareDatetime
    price: Decimal = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    side: str = Field(description="buy or sell")
    buyer_maker: bool | None = None
    venue_trade_id: str | None = None


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
    # Derivatives
    expiration: datetime | None = None
    strike: float | None = None
    option_type: OptionType | None = None
