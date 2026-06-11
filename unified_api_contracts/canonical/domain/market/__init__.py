from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, Field

from ...crosscutting.market_session import MarketSession, SessionPhase
from .._base import CanonicalBase


class MarketState(StrEnum):
    NORMAL = "normal"
    HALTED = "halted"
    AUCTION = "auction"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    CLOSED = "closed"


class MarketTrade(CanonicalBase):
    """Raw trade tick (TRADES_SCHEMA)."""

    instrument_key: str
    price: float
    size: float
    aggressor_side: int = Field(description="1=buyer 2=seller")
    trade_id: str
    ts_event: int = Field(description="nanoseconds UTC")
    ts_init: int = Field(description="nanoseconds UTC")


class BookLevel(CanonicalBase):
    price: float
    size: float


class OrderBookSnapshot5(CanonicalBase):
    """Top-5 order book snapshot."""

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


class CanonicalOrderBook(CanonicalBase):
    """Normalised order book."""

    venue: str
    symbol: str
    timestamp: AwareDatetime
    bids: list[tuple[Decimal, Decimal]] = Field(description="[(price, qty), ...]")
    asks: list[tuple[Decimal, Decimal]] = Field(description="[(price, qty), ...]")
    sequence_number: int | None = None
    instrument_key: str | None = Field(default=None, description="VENUE:TYPE:SYMBOL")
    levels: int | None = None
    schema_version: str = "1.0"


class CanonicalTrade(CanonicalBase):
    """Normalised trade."""

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


class CanonicalTicker(CanonicalBase):
    """Normalised spot ticker."""

    instrument_key: str
    venue: str
    timestamp: AwareDatetime
    last_price: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    volume_24h: Decimal | None = None
    quote_volume_24h: Decimal | None = None
    price_change_24h: Decimal | None = None
    price_change_percent_24h: Decimal | None = None
    schema_version: str = "1.0"


class CanonicalOhlcvBar(CanonicalBase):
    """Normalised OHLCV bar."""

    timestamp: AwareDatetime
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
    session: MarketSession | None = None
    phase: SessionPhase | None = None


class OhlcvAggregation(StrEnum):
    """How a single OHLCV column aggregates when downsampling bars (finer → coarser timeframe)."""

    FIRST = "first"
    MAX = "max"
    MIN = "min"
    LAST = "last"
    SUM = "sum"
    VOLUME_WEIGHTED = "volume_weighted"
    RECOMPUTE_FROM_RAW = "recompute_from_raw"


# Canonical per-column aggregation semantics for resampling ``CanonicalOhlcvBar`` to a COARSER
# timeframe (e.g. 5m → 15m). The SSOT for "how does this candle column aggregate" — a candle
# resampler derives its recipe from this mapping rather than hardcoding ``{open:first, …}`` per
# service (UTL ``feature_calculator`` is the canonical consumer). Identity columns
# (``timestamp``/``venue``/``symbol``/``session``/``phase``) are NOT aggregated: ``timestamp`` is
# the bar-open boundary; venue/symbol are constant within a series; session/phase are derived. A
# column mapped to ``VOLUME_WEIGHTED`` (``vwap``) is ``Σ(price·volume) / Σ(volume)`` over the
# child bars — and ``RECOMPUTE_FROM_RAW`` when no volume is present (it cannot be naively averaged
# across child bars). Feature-layer indicators (RSI/MACD/…) are not OHLCV columns and are
# ``RECOMPUTE_FROM_RAW`` by definition (computed per-timeframe from the resampled candles).
OHLCV_AGGREGATION: dict[str, OhlcvAggregation] = {
    "open": OhlcvAggregation.FIRST,
    "high": OhlcvAggregation.MAX,
    "low": OhlcvAggregation.MIN,
    "close": OhlcvAggregation.LAST,
    "volume": OhlcvAggregation.SUM,
    "quote_volume": OhlcvAggregation.SUM,
    "count": OhlcvAggregation.SUM,
    "vwap": OhlcvAggregation.VOLUME_WEIGHTED,
}


class CanonicalMarketStateEvent(CanonicalBase):
    """Normalized market state transition event."""

    timestamp: AwareDatetime
    venue: str
    instrument_key: str = Field(description="VENUE:TYPE:SYMBOL")
    state: MarketState
    previous_state: MarketState | None = None
    reason: str | None = Field(default=None, description="Halt reason or auction trigger")
    scheduled_reopen: AwareDatetime | None = None
    schema_version: str = "1.0"
