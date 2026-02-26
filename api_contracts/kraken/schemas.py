"""Kraken API: market data, trading, errors."""

from decimal import Decimal

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class KrakenTickerData(BaseModel):
    """Kraken ticker data for a single pair."""

    a: list[str]  # ask [price, whole_lot_volume, lot_volume]
    b: list[str]  # bid [price, whole_lot_volume, lot_volume]
    c: list[str]  # last trade [price, lot_volume]
    v: list[str]  # volume [today, last_24h]
    p: list[str]  # volume weighted average price [today, last_24h]
    t: list[int]  # number of trades [today, last_24h]
    low: list[str] = Field(alias="l")  # low [today, last_24h] (Kraken API uses "l")
    h: list[str]  # high [today, last_24h]
    o: str  # today's opening price

    model_config = {"populate_by_name": True}


class KrakenTickerResponse(BaseModel):
    """Kraken ticker API response."""

    error: list[str]
    result: dict[str, KrakenTickerData]


class KrakenOrderBookLevel(BaseModel):
    """Kraken order book level."""

    price: Decimal
    volume: Decimal
    timestamp: int

    @classmethod
    def from_list(cls, level_data: list) -> "KrakenOrderBookLevel":
        """Create from [price, volume, timestamp] format."""
        return cls(
            price=level_data[0],
            volume=level_data[1],
            timestamp=level_data[2],
        )


class KrakenOrderBook(BaseModel):
    """Kraken order book response."""

    error: list[str]
    result: dict[str, dict]  # Complex nested structure


class KrakenTrade(BaseModel):
    """Kraken trade data."""

    price: Decimal
    volume: Decimal
    time: float  # timestamp
    buy_sell: str  # "b" or "s"
    market_limit: str  # "m" or "l"
    miscellaneous: str  # additional info

    @classmethod
    def from_list(cls, trade_data: list) -> "KrakenTrade":
        """Create from [price, volume, time, buy/sell, market/limit, misc] format."""
        return cls(
            price=trade_data[0],
            volume=trade_data[1],
            time=trade_data[2],
            buy_sell=trade_data[3],
            market_limit=trade_data[4],
            miscellaneous=trade_data[5],
        )


class KrakenOHLC(BaseModel):
    """Kraken OHLC data."""

    time: int  # timestamp
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    vwap: Decimal  # volume weighted average price
    volume: Decimal
    count: int  # number of trades

    @classmethod
    def from_list(cls, ohlc_data: list) -> "KrakenOHLC":
        """Create from [time, open, high, low, close, vwap, volume, count] format."""
        return cls(
            time=ohlc_data[0],
            open=ohlc_data[1],
            high=ohlc_data[2],
            low=ohlc_data[3],
            close=ohlc_data[4],
            vwap=ohlc_data[5],
            volume=ohlc_data[6],
            count=ohlc_data[7],
        )


class KrakenAssetPair(BaseModel):
    """Kraken asset pair information."""

    altname: str
    wsname: str | None = None
    aclass_base: str
    base: str
    aclass_quote: str
    quote: str
    lot: str
    pair_decimals: int
    lot_decimals: int
    lot_multiplier: int
    leverage_buy: list[int]
    leverage_sell: list[int]
    fees: list[list]
    fees_maker: list[list]
    fee_volume_currency: str
    margin_call: int
    margin_stop: int
    ordermin: str


class KrakenError(BaseModel):
    """Kraken API error response."""

    error: list[str]
    result: dict | None = None

    @classmethod
    def classify(cls, error_str: str) -> ErrorAction:
        """Map Kraken error string to retry action.

        Ref: https://docs.kraken.com/api/docs/guides/global-errors
        """
        retry_prefixes = (
            "EOrder:Rate limit",
            "EAuth:Rate limit",
            "EService:Unavailable",
            "EService:Deadline elapsed",
            "EService:No service",
        )
        for prefix in retry_prefixes:
            if error_str.startswith(prefix):
                return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


class KrakenWebSocketSubscribe(BaseModel):
    """Kraken WebSocket V2 subscription request.

    Public: wss://ws.kraken.com/v2
    Private: wss://ws-auth.kraken.com/v2 (auth via token)
    """

    method: str  # "subscribe" or "unsubscribe"
    params: dict[str, object]  # {"channel": "ticker", "symbol": ["BTC/USD", "ETH/USD"]}
    req_id: int | None = None  # optional request tracking id


class KrakenWebSocketPing(BaseModel):
    """Kraken WebSocket V2 ping."""

    method: str = "ping"
    req_id: int | None = None
