"""Kaiko REST API schemas: CEX historical trade ticks, order book snapshots, OHLCV.

Ref: https://docs.kaiko.com/
     https://us.market-api.kaiko.io/v2/data/

Auth: X-Api-Key request header
Base URL: https://us.market-api.kaiko.io

Access tiers:
  Free:       1K calls/month, 2yr history
  Starter:    $99/mo, 5yr history, tick-level trades
  Growth:     $499/mo, full history, order book
  Enterprise: custom, all exchanges, all data types

Supported exchanges (subset): binance, coinbase, kraken, bitstamp,
  gemini, bitfinex, okex, huobi, bybit, kucoin
"""

__api_version__ = "v2"

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


class KaikoInstrument(BaseModel):
    """Trading pair on a specific exchange.

    From GET /v2/data/assets.instruments.v1/exchanges/{exchange}/instruments
    """

    exchange: str | None = None
    code: str | None = None  # e.g. "btc-usd"
    base_asset: str | None = Field(None, alias="base_asset")
    quote_asset: str | None = Field(None, alias="quote_asset")
    class_: str | None = Field(None, alias="class")  # "spot" | "futures" | "options"
    trade_start_time: str | None = Field(None, alias="trade_start_time")
    trade_end_time: str | None = Field(None, alias="trade_end_time")
    trade_count: int | None = Field(None, alias="trade_count")
    trade_compressed_size: int | None = Field(None, alias="trade_compressed_size")


class KaikoTrade(BaseModel):
    """Single historical trade tick.

    From GET /v2/data/trades.v1/exchanges/{exchange}/{class}/{instrument}/trades
    """

    timestamp: str | None = None  # ISO 8601
    id: str | None = None
    price: str | None = None  # string decimal for precision
    amount: str | None = None
    taker_side: str | None = Field(None, alias="taker_side")  # "buy" | "sell"


class KaikoOHLCV(BaseModel):
    """Single OHLCV candle.

    From GET /v2/data/trades.v1/exchanges/{exchange}/{class}/{instrument}/aggregations/ohlcv
    """

    timestamp: str | None = None
    open: str | None = None
    high: str | None = None
    low: str | None = None
    close: str | None = None
    volume: str | None = None
    count: int | None = None


class KaikoOrderBookEntry(BaseModel):
    """Single bid or ask level in order book snapshot."""

    price: str | None = None
    amount: str | None = None


class KaikoOrderBookSnapshot(BaseModel):
    """Order book snapshot at a point in time.

    From GET /v2/data/order_book_snapshots.v1/exchanges/{exchange}/{class}/{instrument}/ob_snapshots
    """

    timestamp: str | None = None
    bids: list[KaikoOrderBookEntry] | None = None
    asks: list[KaikoOrderBookEntry] | None = None


class KaikoPagination(BaseModel):
    """Kaiko pagination envelope."""

    data_version: str | None = None
    next_url: str | None = Field(None, alias="next_url")


class KaikoTradesResponse(BaseModel):
    """Paginated response from Kaiko trades endpoint."""

    query: dict[str, object] | None = None
    time: str | None = None
    timestamp: str | None = None
    data: list[KaikoTrade] | None = None
    next_url: str | None = Field(None, alias="next_url")
    continuation_token: str | None = Field(None, alias="continuation_token")
    result: str | None = None  # "ok" | "error"


class KaikoOHLCVResponse(BaseModel):
    """Paginated response from Kaiko OHLCV endpoint."""

    query: dict[str, object] | None = None
    time: str | None = None
    timestamp: str | None = None
    data: list[KaikoOHLCV] | None = None
    next_url: str | None = Field(None, alias="next_url")
    continuation_token: str | None = Field(None, alias="continuation_token")
    result: str | None = None


class KaikoInstrumentsResponse(BaseModel):
    """Response from Kaiko instruments listing endpoint."""

    query: dict[str, object] | None = None
    time: str | None = None
    timestamp: str | None = None
    data: list[KaikoInstrument] | None = None
    result: str | None = None


class KaikoError(BaseModel):
    """Kaiko API error response."""

    result: str | None = None  # "error"
    message: str | None = None
    status: int | None = None

    @classmethod
    def classify(cls, status: int | None = None, message: str | None = None) -> ErrorAction:
        """Map Kaiko error to retry action."""
        if status == 429 or (message and "rate" in (message or "").lower()):
            return ErrorAction.RETRY
        if status in (401, 403):
            return ErrorAction.FAIL
        if status is not None and status >= 500:
            return ErrorAction.RETRY
        return ErrorAction.FAIL
