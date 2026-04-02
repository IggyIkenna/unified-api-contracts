"""Tardis API: exchanges, instruments, trades, order book, errors, WebSocket.

Raw data types (CeFi): trades, book_snapshot_5, liquidations, derivative_ticker, options_chain.
Timestamp format: microseconds since epoch (μs). Side format: string ("buy" or "sell").
Ref: https://docs.tardis.dev/historical-data-details
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction

# =============================================================================
# Tardis data types (CeFi exchanges: Binance, Bybit, OKX, Deribit, etc.)
# =============================================================================
TARDIS_DATA_TYPES: tuple[str, ...] = (
    "trades",
    "book_snapshot_5",
    "book_snapshot_25",
    "incremental_book_L2",
    "quotes",
    "liquidations",
    "derivative_ticker",
    "options_chain",
)


class TardisExchange(BaseModel):
    """Exchange entry from Tardis exchanges list."""

    exchange: str | None = None
    name: str | None = None
    website: str | None = None
    info: dict[str, object] | None = None


class TardisInstrument(BaseModel):
    """Instrument from Tardis instruments API."""

    symbol: str | None = None
    exchange: str | None = None
    name: str | None = None
    info: dict[str, object] | None = None


class TardisInstrumentDetail(BaseModel):
    """Instrument from Tardis instruments metadata API.

    Returned by GET https://api.tardis.dev/v1/instruments/{exchange}
    or GET https://api.tardis.dev/v1/instruments/{exchange}/{symbol_id}.

    Also constructed from the simpler ``availableSymbols`` array of
    GET /v1/exchanges/{exchange} (fields beyond the basic set will be None).

    Ref: https://docs.tardis.dev/api/instruments-metadata-api
    """

    id: str
    type: str | None = None
    baseCurrency: str | None = None
    quoteCurrency: str | None = None
    availableSince: str | None = None
    availableTo: str | None = None
    expiry: str | None = None
    strikePrice: float | None = None
    optionType: str | None = None
    # Instrument specification fields (from /v1/instruments endpoint)
    priceIncrement: float | None = None
    amountIncrement: float | None = None
    minTradeAmount: float | None = None
    contractMultiplier: float | None = None
    inverse: bool | None = None
    contractType: str | None = None
    active: bool | None = None
    makerFee: float | None = None
    takerFee: float | None = None


class TardisAvailableSymbol(BaseModel):
    """Minimal symbol info from GET /v1/exchanges/:exchange availableSymbols array.

    Ref: https://docs.tardis.dev/api/http — /exchanges/:exchange response.
    """

    id: str = Field("", description="Symbol id e.g. btcusdt")
    type: str | None = Field(None, description="perpetual, spot, future, option")
    availableSince: str | None = Field(None, description="ISO datetime of first available data")
    availableTo: str | None = Field(None, description="ISO datetime of last available data; None if active")


class TardisExchangeDetail(BaseModel):
    """Exchange detail from Tardis exchange endpoint.

    Returned by GET https://api.tardis.dev/v1/exchanges/{exchange}.
    Ref: https://docs.tardis.dev/api/http — response has availableSymbols.
    """

    id: str = Field(..., description="Exchange identifier e.g. binance-futures")
    name: str = Field(..., description="Human-readable exchange name")
    enabled: bool | None = Field(None, description="Whether exchange is enabled")
    availableSince: str | None = Field(None, description="ISO datetime of earliest available data")
    availableSymbols: list[TardisAvailableSymbol] = Field(
        default_factory=list, description="Available symbols (id, type, availableSince)"
    )
    availableChannels: list[str] | None = Field(None, description="Available data channels")
    datasets: dict[str, object] | None = Field(None, description="CSV datasets info")
    incidentReports: list[dict[str, object]] | None = Field(None, description="Incident history")

    @property
    def instruments(self) -> list[TardisInstrumentDetail]:
        """Map availableSymbols response to TardisInstrumentDetail (current API field name).

        URDI and other consumers expect .instruments; API returns availableSymbols.
        """
        return [
            TardisInstrumentDetail(
                id=s.id,
                type=s.type,
                availableSince=s.availableSince,
                availableTo=s.availableTo,
            )
            for s in self.availableSymbols
        ]


class TardisTrade(BaseModel):
    """Trade record (CSV or JSON). Field names follow Tardis HTTP API / downloadable CSV."""

    timestamp: str | None = None
    exchange: str | None = None
    symbol: str | None = None
    price: float | None = None
    size: float | None = None
    side: str | None = None
    trade_id: str | None = None
    info: dict[str, object] | None = None


class TardisOrderBookLevel(BaseModel):
    """Single level in order book."""

    price: float | None = None
    size: float | None = None


class TardisOrderBook(BaseModel):
    """Order book snapshot."""

    timestamp: str | None = None
    exchange: str | None = None
    symbol: str | None = None
    bids: list[list[float]] | None = None
    asks: list[list[float]] | None = None


class TardisBookSnapshot5(BaseModel):
    """5-level order book snapshot (raw Tardis format)."""

    exchange: str = Field(..., description="Exchange identifier")
    symbol: str = Field(..., description="Symbol identifier")
    timestamp: int = Field(..., description="Exchange timestamp in microseconds since epoch")
    local_timestamp: int = Field(..., description="Local arrival timestamp in microseconds")
    ask_price_0: float = Field(..., description="Ask price at level 0")
    ask_volume_0: float = Field(..., description="Ask volume at level 0")
    bid_price_0: float = Field(..., description="Bid price at level 0")
    bid_volume_0: float = Field(..., description="Bid volume at level 0")
    ask_price_1: float | None = None
    ask_volume_1: float | None = None
    bid_price_1: float | None = None
    bid_volume_1: float | None = None
    ask_price_2: float | None = None
    ask_volume_2: float | None = None
    bid_price_2: float | None = None
    bid_volume_2: float | None = None
    ask_price_3: float | None = None
    ask_volume_3: float | None = None
    bid_price_3: float | None = None
    bid_volume_3: float | None = None
    ask_price_4: float | None = None
    ask_volume_4: float | None = None
    bid_price_4: float | None = None
    bid_volume_4: float | None = None


class TardisBookSnapshot25(BaseModel):
    """25-level order book snapshot (raw Tardis format).

    Ref: https://docs.tardis.dev/downloadable-csv-files#book_snapshot_25
    """

    exchange: str = Field(..., description="Exchange identifier")
    symbol: str = Field(..., description="Symbol identifier")
    timestamp: int = Field(..., description="Exchange timestamp in microseconds since epoch")
    local_timestamp: int = Field(..., description="Local arrival timestamp in microseconds")
    ask_price_0: float = Field(..., description="Ask price at level 0")
    ask_volume_0: float = Field(..., description="Ask volume at level 0")
    bid_price_0: float = Field(..., description="Bid price at level 0")
    bid_volume_0: float = Field(..., description="Bid volume at level 0")
    # Levels 1-24 (optional; empty if fewer levels available)
    ask_price_1: float | None = None
    ask_volume_1: float | None = None
    bid_price_1: float | None = None
    bid_volume_1: float | None = None
    ask_price_2: float | None = None
    ask_volume_2: float | None = None
    bid_price_2: float | None = None
    bid_volume_2: float | None = None
    ask_price_3: float | None = None
    ask_volume_3: float | None = None
    bid_price_3: float | None = None
    bid_volume_3: float | None = None
    ask_price_4: float | None = None
    ask_volume_4: float | None = None
    bid_price_4: float | None = None
    bid_volume_4: float | None = None
    ask_price_5: float | None = None
    ask_volume_5: float | None = None
    bid_price_5: float | None = None
    bid_volume_5: float | None = None
    ask_price_6: float | None = None
    ask_volume_6: float | None = None
    bid_price_6: float | None = None
    bid_volume_6: float | None = None
    ask_price_7: float | None = None
    ask_volume_7: float | None = None
    bid_price_7: float | None = None
    bid_volume_7: float | None = None
    ask_price_8: float | None = None
    ask_volume_8: float | None = None
    bid_price_8: float | None = None
    bid_volume_8: float | None = None
    ask_price_9: float | None = None
    ask_volume_9: float | None = None
    bid_price_9: float | None = None
    bid_volume_9: float | None = None
    ask_price_10: float | None = None
    ask_volume_10: float | None = None
    bid_price_10: float | None = None
    bid_volume_10: float | None = None
    ask_price_11: float | None = None
    ask_volume_11: float | None = None
    bid_price_11: float | None = None
    bid_volume_11: float | None = None
    ask_price_12: float | None = None
    ask_volume_12: float | None = None
    bid_price_12: float | None = None
    bid_volume_12: float | None = None
    ask_price_13: float | None = None
    ask_volume_13: float | None = None
    bid_price_13: float | None = None
    bid_volume_13: float | None = None
    ask_price_14: float | None = None
    ask_volume_14: float | None = None
    bid_price_14: float | None = None
    bid_volume_14: float | None = None
    ask_price_15: float | None = None
    ask_volume_15: float | None = None
    bid_price_15: float | None = None
    bid_volume_15: float | None = None
    ask_price_16: float | None = None
    ask_volume_16: float | None = None
    bid_price_16: float | None = None
    bid_volume_16: float | None = None
    ask_price_17: float | None = None
    ask_volume_17: float | None = None
    bid_price_17: float | None = None
    bid_volume_17: float | None = None
    ask_price_18: float | None = None
    ask_volume_18: float | None = None
    bid_price_18: float | None = None
    bid_volume_18: float | None = None
    ask_price_19: float | None = None
    ask_volume_19: float | None = None
    bid_price_19: float | None = None
    bid_volume_19: float | None = None
    ask_price_20: float | None = None
    ask_volume_20: float | None = None
    bid_price_20: float | None = None
    bid_volume_20: float | None = None
    ask_price_21: float | None = None
    ask_volume_21: float | None = None
    bid_price_21: float | None = None
    bid_volume_21: float | None = None
    ask_price_22: float | None = None
    ask_volume_22: float | None = None
    bid_price_22: float | None = None
    bid_volume_22: float | None = None
    ask_price_23: float | None = None
    ask_volume_23: float | None = None
    bid_price_23: float | None = None
    bid_volume_23: float | None = None
    ask_price_24: float | None = None
    ask_volume_24: float | None = None
    bid_price_24: float | None = None
    bid_volume_24: float | None = None


class TardisIncrementalBookL2(BaseModel):
    """Incremental L2 order book update (raw Tardis format).

    Ref: https://docs.tardis.dev/downloadable-csv-files#incremental_book_l2
    amount=0 indicates removal of price level. is_snapshot=true marks initial snapshot.
    """

    exchange: str = Field(..., description="Exchange identifier")
    symbol: str = Field(..., description="Symbol identifier")
    timestamp: int = Field(..., description="Exchange timestamp in microseconds since epoch")
    local_timestamp: int = Field(..., description="Local arrival timestamp in microseconds")
    is_snapshot: bool = Field(..., description="True if part of initial snapshot; else incremental update")
    side: str = Field(..., description="bid or ask")
    price: float = Field(..., description="Price level being updated")
    amount: float = Field(..., description="Updated amount at level; 0 = remove level")


class TardisQuotes(BaseModel):
    """Top-of-book quotes (raw Tardis format).

    Ref: https://docs.tardis.dev/downloadable-csv-files#quotes
    """

    exchange: str = Field(..., description="Exchange identifier")
    symbol: str = Field(..., description="Symbol identifier")
    timestamp: int = Field(..., description="Exchange timestamp in microseconds since epoch")
    local_timestamp: int = Field(..., description="Local arrival timestamp in microseconds")
    ask_price: float | None = Field(None, description="Best ask price; empty if no asks")
    ask_amount: float | None = Field(None, description="Best ask amount; empty if no asks")
    bid_price: float | None = Field(None, description="Best bid price; empty if no bids")
    bid_amount: float | None = Field(None, description="Best bid amount; empty if no bids")


class TardisLiquidations(BaseModel):
    """Liquidation event (raw Tardis format)."""

    exchange: str = Field(..., description="Exchange identifier")
    symbol: str = Field(..., description="Symbol identifier")
    timestamp: int = Field(..., description="Exchange timestamp in microseconds")
    local_timestamp: int = Field(..., description="Local arrival timestamp in microseconds")
    id: str | None = Field(None, description="Liquidation ID if available")
    side: str = Field(..., description="buy=short liquidated, sell=long liquidated")
    price: float = Field(..., description="Liquidation price")
    amount: float = Field(..., description="Liquidation amount")


class TardisDerivativeTicker(BaseModel):
    """Funding rates, open interest, mark prices (raw Tardis format)."""

    exchange: str = Field(..., description="Exchange identifier")
    symbol: str = Field(..., description="Symbol identifier")
    timestamp: int = Field(..., description="Exchange timestamp in microseconds")
    local_timestamp: int = Field(..., description="Local arrival timestamp in microseconds")
    funding_timestamp: int | None = None
    funding_rate: float | None = None
    predicted_funding_rate: float | None = None
    open_interest: float | None = None
    last_price: float | None = None
    index_price: float | None = None
    mark_price: float | None = None


class TardisOptionsChain(BaseModel):
    """Options pricing and greeks (raw Tardis format)."""

    exchange: str = Field(..., description="Exchange identifier")
    symbol: str = Field(..., description="Symbol identifier")
    timestamp: int = Field(..., description="Exchange timestamp in microseconds")
    local_timestamp: int = Field(..., description="Local arrival timestamp in microseconds")
    type: str = Field(..., description="Option type (put/call)")
    strike_price: float = Field(..., description="Strike price")
    expiration: int = Field(..., description="Expiration timestamp in microseconds")
    open_interest: float | None = None
    last_price: float | None = None
    bid_price: float | None = None
    bid_amount: float | None = None
    bid_iv: float | None = None
    ask_price: float | None = None
    ask_amount: float | None = None
    ask_iv: float | None = None
    mark_price: float | None = None
    mark_iv: float | None = None
    underlying_index: str | None = None
    underlying_price: float | None = None
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None
    rho: float | None = None


class TardisError(BaseModel):
    """Tardis API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Tardis error to retry action."""
        if code == 429 or (error and "rate" in error.lower()):
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL
        return ErrorAction.FAIL


# =============================================================================
# Raw column schemas (for DataFrame validation)
# =============================================================================

TARDIS_TRADES_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {"name": "id", "type": "string", "required": False, "description": "Trade ID (if available)"},
    {
        "name": "side",
        "type": "string",
        "required": True,
        "description": "Trade side ('buy' or 'sell')",
    },
    {"name": "price", "type": "float64", "required": True, "description": "Trade price"},
    {"name": "amount", "type": "float64", "required": True, "description": "Trade amount/quantity"},
]

TARDIS_BOOK_SNAPSHOT_5_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {
        "name": "ask_price_0",
        "type": "float64",
        "required": True,
        "description": "Ask price at level 0",
    },
    {
        "name": "ask_volume_0",
        "type": "float64",
        "required": True,
        "description": "Ask volume at level 0",
    },
    {
        "name": "bid_price_0",
        "type": "float64",
        "required": True,
        "description": "Bid price at level 0",
    },
    {
        "name": "bid_volume_0",
        "type": "float64",
        "required": True,
        "description": "Bid volume at level 0",
    },
]
for level in range(1, 5):
    TARDIS_BOOK_SNAPSHOT_5_SCHEMA.extend(
        [
            {
                "name": f"ask_price_{level}",
                "type": "float64",
                "required": False,
                "description": f"Ask price at level {level}",
            },
            {
                "name": f"ask_volume_{level}",
                "type": "float64",
                "required": False,
                "description": f"Ask volume at level {level}",
            },
            {
                "name": f"bid_price_{level}",
                "type": "float64",
                "required": False,
                "description": f"Bid price at level {level}",
            },
            {
                "name": f"bid_volume_{level}",
                "type": "float64",
                "required": False,
                "description": f"Bid volume at level {level}",
            },
        ]
    )

TARDIS_LIQUIDATIONS_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {
        "name": "id",
        "type": "string",
        "required": False,
        "description": "Liquidation ID (if available)",
    },
    {
        "name": "side",
        "type": "string",
        "required": True,
        "description": "Side: 'buy' = short liquidated, 'sell' = long liquidated",
    },
    {"name": "price", "type": "float64", "required": True, "description": "Liquidation price"},
    {"name": "amount", "type": "float64", "required": True, "description": "Liquidation amount"},
]

TARDIS_DERIVATIVE_TICKER_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {
        "name": "funding_timestamp",
        "type": "int64",
        "required": False,
        "description": "Funding timestamp (if provided)",
    },
    {
        "name": "funding_rate",
        "type": "float64",
        "required": False,
        "description": "Current funding rate",
    },
    {
        "name": "predicted_funding_rate",
        "type": "float64",
        "required": False,
        "description": "Predicted funding rate",
    },
    {
        "name": "open_interest",
        "type": "float64",
        "required": False,
        "description": "Open interest value",
    },
    {
        "name": "last_price",
        "type": "float64",
        "required": False,
        "description": "Last traded price",
    },
    {
        "name": "index_price",
        "type": "float64",
        "required": False,
        "description": "Underlying index price",
    },
    {"name": "mark_price", "type": "float64", "required": False, "description": "Mark price"},
]

TARDIS_OPTIONS_CHAIN_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {"name": "type", "type": "string", "required": True, "description": "Option type (put/call)"},
    {
        "name": "strike_price",
        "type": "float64",
        "required": True,
        "description": "Strike price of the option",
    },
    {
        "name": "expiration",
        "type": "int64",
        "required": True,
        "description": "Expiration timestamp in microseconds",
    },
    {
        "name": "open_interest",
        "type": "float64",
        "required": False,
        "description": "Open interest for the option",
    },
    {
        "name": "last_price",
        "type": "float64",
        "required": False,
        "description": "Last traded price",
    },
    {
        "name": "bid_price",
        "type": "float64",
        "required": False,
        "description": "Best bid price for the option",
    },
    {"name": "bid_amount", "type": "float64", "required": False, "description": "Best bid amount"},
    {
        "name": "bid_iv",
        "type": "float64",
        "required": False,
        "description": "Bid implied volatility",
    },
    {
        "name": "ask_price",
        "type": "float64",
        "required": False,
        "description": "Best ask price for the option",
    },
    {"name": "ask_amount", "type": "float64", "required": False, "description": "Best ask amount"},
    {
        "name": "ask_iv",
        "type": "float64",
        "required": False,
        "description": "Ask implied volatility",
    },
    {
        "name": "mark_price",
        "type": "float64",
        "required": False,
        "description": "Mark price of the option",
    },
    {
        "name": "mark_iv",
        "type": "float64",
        "required": False,
        "description": "Mark implied volatility",
    },
    {
        "name": "underlying_index",
        "type": "string",
        "required": False,
        "description": "Underlying instrument symbol",
    },
    {
        "name": "underlying_price",
        "type": "float64",
        "required": False,
        "description": "Underlying asset price",
    },
    {"name": "delta", "type": "float64", "required": False, "description": "Option delta"},
    {"name": "gamma", "type": "float64", "required": False, "description": "Option gamma"},
    {"name": "vega", "type": "float64", "required": False, "description": "Option vega"},
    {"name": "theta", "type": "float64", "required": False, "description": "Option theta"},
    {"name": "rho", "type": "float64", "required": False, "description": "Option rho"},
]

TARDIS_INCREMENTAL_BOOK_L2_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {
        "name": "is_snapshot",
        "type": "bool",
        "required": True,
        "description": "True if initial snapshot; else incremental",
    },
    {"name": "side", "type": "string", "required": True, "description": "bid or ask"},
    {
        "name": "price",
        "type": "float64",
        "required": True,
        "description": "Price level being updated",
    },
    {
        "name": "amount",
        "type": "float64",
        "required": True,
        "description": "Updated amount; 0 = remove level",
    },
]

TARDIS_QUOTES_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {"name": "ask_price", "type": "float64", "required": False, "description": "Best ask price"},
    {"name": "ask_amount", "type": "float64", "required": False, "description": "Best ask amount"},
    {"name": "bid_price", "type": "float64", "required": False, "description": "Best bid price"},
    {"name": "bid_amount", "type": "float64", "required": False, "description": "Best bid amount"},
]

TARDIS_BOOK_SNAPSHOT_25_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "exchange", "type": "string", "required": True, "description": "Exchange identifier"},
    {"name": "symbol", "type": "string", "required": True, "description": "Symbol identifier"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Exchange timestamp in microseconds",
    },
    {
        "name": "local_timestamp",
        "type": "int64",
        "required": True,
        "description": "Local arrival timestamp in microseconds",
    },
    {
        "name": "ask_price_0",
        "type": "float64",
        "required": True,
        "description": "Ask price at level 0",
    },
    {
        "name": "ask_volume_0",
        "type": "float64",
        "required": True,
        "description": "Ask volume at level 0",
    },
    {
        "name": "bid_price_0",
        "type": "float64",
        "required": True,
        "description": "Bid price at level 0",
    },
    {
        "name": "bid_volume_0",
        "type": "float64",
        "required": True,
        "description": "Bid volume at level 0",
    },
]
for level in range(1, 25):
    TARDIS_BOOK_SNAPSHOT_25_SCHEMA.extend(
        [
            {
                "name": f"ask_price_{level}",
                "type": "float64",
                "required": False,
                "description": f"Ask price at level {level}",
            },
            {
                "name": f"ask_volume_{level}",
                "type": "float64",
                "required": False,
                "description": f"Ask volume at level {level}",
            },
            {
                "name": f"bid_price_{level}",
                "type": "float64",
                "required": False,
                "description": f"Bid price at level {level}",
            },
            {
                "name": f"bid_volume_{level}",
                "type": "float64",
                "required": False,
                "description": f"Bid volume at level {level}",
            },
        ]
    )

TARDIS_SCHEMA_MAP: dict[str, list[dict[str, str | bool]]] = {
    "trades": TARDIS_TRADES_SCHEMA,
    "book_snapshot_5": TARDIS_BOOK_SNAPSHOT_5_SCHEMA,
    "book_snapshot_25": TARDIS_BOOK_SNAPSHOT_25_SCHEMA,
    "incremental_book_L2": TARDIS_INCREMENTAL_BOOK_L2_SCHEMA,
    "quotes": TARDIS_QUOTES_SCHEMA,
    "liquidations": TARDIS_LIQUIDATIONS_SCHEMA,
    "derivative_ticker": TARDIS_DERIVATIVE_TICKER_SCHEMA,
    "options_chain": TARDIS_OPTIONS_CHAIN_SCHEMA,
}


def get_tardis_schema(data_type: str) -> list[dict[str, str | bool]]:
    """Get Tardis raw schema for a specific data type."""
    return TARDIS_SCHEMA_MAP.get(data_type, [])


def get_tardis_required_columns(data_type: str) -> list[str]:
    """Get required column names for a Tardis data type."""
    schema = get_tardis_schema(data_type)
    return [str(col["name"]) for col in schema if col.get("required", False)]
