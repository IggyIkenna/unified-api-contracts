"""Binance market data schemas: tickers, order books, trades, klines."""

from __future__ import annotations

__api_version__ = "v3"  # matches provider_api_versions.yaml

from decimal import Decimal

from pydantic import BaseModel, Field


class BinanceTicker(BaseModel):
    """Binance 24hr ticker statistics (REST or WebSocket).

    Endpoints:
    - Spot: api.binance.com/api/v3/ticker/24hr (has prevClosePrice, bid/ask)
    - USD-M (futures + perps): fapi.binance.com/fapi/v1/ticker/24hr (no bid/ask; has funding)
    - Coin-M: dapi.binance.com/dapi/v1/ticker/24hr (no bid/ask; has pair)
    """

    symbol: str
    priceChange: Decimal
    priceChangePercent: Decimal
    weightedAvgPrice: Decimal
    lastPrice: Decimal
    lastQty: Decimal
    openPrice: Decimal
    highPrice: Decimal
    lowPrice: Decimal
    volume: Decimal
    quoteVolume: Decimal
    openTime: int  # timestamp ms
    closeTime: int  # timestamp ms
    firstId: int
    lastId: int
    count: int
    # Spot only (api); absent for USD-M/Coin-M (fapi/dapi)
    prevClosePrice: Decimal | None = None
    bidPrice: Decimal | None = None
    bidQty: Decimal | None = None
    askPrice: Decimal | None = None
    askQty: Decimal | None = None
    # USD-M futures/perps only (fapi); absent for Spot
    lastFundingRate: Decimal | None = None
    nextFundingTime: int | None = None  # timestamp ms
    time: int | None = None  # timestamp ms


class BinanceOrderBook(BaseModel):
    """Binance order book (REST snapshot or WebSocket)."""

    lastUpdateId: int | None = None
    bids: list[list[str]] = []  # [[price, qty], ...]
    asks: list[list[str]] = []
    info: dict[str, object] | None = None


class BinanceTrade(BaseModel):
    """Binance trade (REST or WebSocket)."""

    id: int
    price: Decimal
    qty: Decimal
    quoteQty: Decimal
    time: int  # timestamp
    isBuyerMaker: bool
    isBestMatch: bool


class BinanceKline(BaseModel):
    """Binance kline/candlestick data."""

    open_time: int  # timestamp
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: int  # timestamp
    quote_asset_volume: Decimal
    number_of_trades: int
    taker_buy_base_asset_volume: Decimal
    taker_buy_quote_asset_volume: Decimal
    ignore: str  # unused field

    @classmethod
    def from_list(
        cls,
        kline_data: list[int | str],
    ) -> BinanceKline:
        """Create BinanceKline from list format returned by Binance API.

        Binance REST/WebSocket returns: [open_time, open, high, low, close,
        volume, close_time, quote_asset_volume, trades, taker_buy_base,
        taker_buy_quote, ignore]. Indices 0,6,8 are int; others are str.
        """
        return cls(
            open_time=int(kline_data[0]),
            open_price=Decimal(str(kline_data[1])),
            high_price=Decimal(str(kline_data[2])),
            low_price=Decimal(str(kline_data[3])),
            close_price=Decimal(str(kline_data[4])),
            volume=Decimal(str(kline_data[5])),
            close_time=int(kline_data[6]),
            quote_asset_volume=Decimal(str(kline_data[7])),
            number_of_trades=int(kline_data[8]),
            taker_buy_base_asset_volume=Decimal(str(kline_data[9])),
            taker_buy_quote_asset_volume=Decimal(str(kline_data[10])),
            ignore=str(kline_data[11]),
        )


class BinanceSymbol(BaseModel):
    """Binance symbol information from exchange info."""

    symbol: str
    status: str
    baseAsset: str
    baseAssetPrecision: int
    quoteAsset: str
    quotePrecision: int
    quoteAssetPrecision: int
    baseCommissionPrecision: int
    quoteCommissionPrecision: int
    orderTypes: list[str]
    icebergAllowed: bool
    ocoAllowed: bool
    quoteOrderQtyMarketAllowed: bool
    allowTrailingStop: bool
    cancelReplaceAllowed: bool
    isSpotTradingAllowed: bool
    isMarginTradingAllowed: bool


class BinanceExchangeInfo(BaseModel):
    """Binance exchange information."""

    timezone: str
    serverTime: int  # timestamp
    rateLimits: list[dict[str, object]]
    exchangeFilters: list[dict[str, object]]
    symbols: list[BinanceSymbol]


class BinanceFuturesExchangeInfo(BaseModel):
    """Binance futures/options exchange info (REST: GET /fapi/v1/exchangeInfo or /eapi/v1/exchangeInfo).

    Futures endpoint returns BinanceInstrumentInfo objects (with contractType, deliveryDate, filters, etc.).
    Options endpoint returns optionSymbols (BinanceOptionInstrumentInfo objects).
    """

    timezone: str | None = None
    serverTime: int | None = None
    symbols: list[BinanceInstrumentInfo] | None = None
    optionSymbols: list[BinanceOptionInstrumentInfo] | None = None


class BinanceAggTrade(BaseModel):
    """Binance aggregated trade (REST GET /api/v3/aggTrades or WebSocket @aggTrade).

    REST/WS use short keys (a,p,q,f,l,T,m,M); schema uses camelCase with aliases.
    """

    model_config = {"populate_by_name": True}

    aggTradeId: int = Field(alias="a")
    price: Decimal = Field(alias="p")
    qty: Decimal = Field(alias="q")
    firstTradeId: int = Field(alias="f")
    lastTradeId: int = Field(alias="l")
    isBuyerMaker: bool = Field(alias="m")
    isBestMatch: bool = Field(alias="M")
    time: int | None = Field(None, alias="T")  # timestamp ms (REST/WS)


class BinanceFundingRateHistory(BaseModel):
    """Binance funding rate history (GET /fapi/v1/fundingRate)."""

    symbol: str | None = None
    fundingTime: int  # timestamp ms
    fundingRate: Decimal
    markPrice: Decimal | None = None


class BinancePremiumIndex(BaseModel):
    """Binance premium index / mark price (GET /fapi/v1/premiumIndex)."""

    symbol: str | None = None
    markPrice: Decimal
    indexPrice: Decimal
    lastFundingRate: Decimal
    nextFundingTime: int  # timestamp ms
    interestRate: Decimal
    estimatedSettlePrice: Decimal | None = None
    time: int | None = None  # timestamp ms


class BinanceMarkPriceKline(BaseModel):
    """Binance mark price kline (REST: GET /fapi/v1/markPriceKlines, /dapi/v1/markPriceKlines).

    USD-M returns [timestamp, open, high, low, close, volume]. Coin-M returns full 12-field format.
    Use from_list() for array format.
    """

    open_time: int  # timestamp ms
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: int | None = None  # Coin-M only
    quote_asset_volume: Decimal | None = None  # Coin-M only
    number_of_trades: int | None = None  # Coin-M only
    taker_buy_base_asset_volume: Decimal | None = None  # Coin-M only
    taker_buy_quote_asset_volume: Decimal | None = None  # Coin-M only
    ignore: str | None = None  # Coin-M only

    @classmethod
    def from_list(
        cls,
        kline_data: list[int | str],
    ) -> BinanceMarkPriceKline:
        """Create from array. USD-M: 6 fields; Coin-M: 12 fields."""
        if len(kline_data) >= 12:
            return cls(
                open_time=int(kline_data[0]),
                open_price=Decimal(str(kline_data[1])),
                high_price=Decimal(str(kline_data[2])),
                low_price=Decimal(str(kline_data[3])),
                close_price=Decimal(str(kline_data[4])),
                volume=Decimal(str(kline_data[5])),
                close_time=int(kline_data[6]),
                quote_asset_volume=Decimal(str(kline_data[7])),
                number_of_trades=int(kline_data[8]),
                taker_buy_base_asset_volume=Decimal(str(kline_data[9])),
                taker_buy_quote_asset_volume=Decimal(str(kline_data[10])),
                ignore=str(kline_data[11]),
            )
        return cls(
            open_time=int(kline_data[0]),
            open_price=Decimal(str(kline_data[1])),
            high_price=Decimal(str(kline_data[2])),
            low_price=Decimal(str(kline_data[3])),
            close_price=Decimal(str(kline_data[4])),
            volume=Decimal(str(kline_data[5])),
        )


class BinanceIndexPriceKline(BaseModel):
    """Binance index price kline (REST: GET /fapi/v1/indexPriceKlines, /dapi/v1/indexPriceKlines).

    Same array format as mark price kline. Use from_list() for array format.
    """

    open_time: int  # timestamp ms
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time: int | None = None
    quote_asset_volume: Decimal | None = None
    number_of_trades: int | None = None
    taker_buy_base_asset_volume: Decimal | None = None
    taker_buy_quote_asset_volume: Decimal | None = None
    ignore: str | None = None

    @classmethod
    def from_list(
        cls,
        kline_data: list[int | str],
    ) -> BinanceIndexPriceKline:
        """Create from array. USD-M: 6 fields; Coin-M: 12 fields."""
        if len(kline_data) >= 12:
            return cls(
                open_time=int(kline_data[0]),
                open_price=Decimal(str(kline_data[1])),
                high_price=Decimal(str(kline_data[2])),
                low_price=Decimal(str(kline_data[3])),
                close_price=Decimal(str(kline_data[4])),
                volume=Decimal(str(kline_data[5])),
                close_time=int(kline_data[6]),
                quote_asset_volume=Decimal(str(kline_data[7])),
                number_of_trades=int(kline_data[8]),
                taker_buy_base_asset_volume=Decimal(str(kline_data[9])),
                taker_buy_quote_asset_volume=Decimal(str(kline_data[10])),
                ignore=str(kline_data[11]),
            )
        return cls(
            open_time=int(kline_data[0]),
            open_price=Decimal(str(kline_data[1])),
            high_price=Decimal(str(kline_data[2])),
            low_price=Decimal(str(kline_data[3])),
            close_price=Decimal(str(kline_data[4])),
            volume=Decimal(str(kline_data[5])),
        )


class BinanceDeliveryPrice(BaseModel):
    """Binance futures delivery/settlement price (REST: GET /futures/data/delivery-price)."""

    pair: str
    deliveryTime: int  # timestamp (ms)
    deliveryPrice: Decimal


class BinanceDeliveryHistory(BaseModel):
    """Binance delivery/settlement price history (GET /futures/data/delivery-price).

    With symbol: single object. With pair or no filter: array of {deliveryTime, deliveryPrice}.
    """

    pair: str | None = None  # Coin-M; symbol for USD-M
    symbol: str | None = None  # USD-M single-symbol response
    deliveryTime: int  # timestamp ms
    deliveryPrice: Decimal


class BinanceInstrumentInfo(BaseModel):
    """Binance instrument/contract specification (REST: GET /fapi/v1/exchangeInfo or /eapi/v1/exchangeInfo)."""

    symbol: str
    status: str  # TRADING, BREAK, END_OF_DAY
    baseAsset: str | None = None
    quoteAsset: str | None = None
    contractType: str | None = None  # PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER
    deliveryDate: int | None = None  # timestamp ms; 4133404800000 = no expiry
    onboardDate: int | None = None  # timestamp ms
    contractSize: int | None = None  # 1 for standard
    marginAsset: str | None = None
    pricePrecision: int | None = None
    quantityPrecision: int | None = None
    baseAssetPrecision: int | None = None
    quotePrecision: int | None = None
    filters: list[dict[str, object]] | None = None  # PRICE_FILTER, LOT_SIZE, etc.
    underlyingType: str | None = None  # COIN or TOKEN (futures)


class BinanceOptionInstrumentInfo(BaseModel):
    """Binance European options instrument (REST: GET /eapi/v1/exchangeInfo)."""

    id: int | None = None
    contractId: int | None = None
    underlying: str | None = None  # e.g. BTCUSDT
    quoteAsset: str | None = None  # USDT
    symbol: str | None = None  # e.g. BTC-200730-9000-C
    unit: int | None = None  # number of tokens per contract
    minQty: Decimal | None = None
    maxQty: Decimal | None = None
    priceScale: int | None = None
    quantityScale: int | None = None
    side: str | None = None  # CALL or PUT
    strikePrice: Decimal | None = None
    expiryDate: int | None = None  # timestamp ms


class BinanceOptionTicker(BaseModel):
    """Binance European options mark price ticker (EAPI @ticker stream).

    Stream: <symbol>@ticker (options WebSocket)
    """

    e: str  # event type = "ticker"
    E: int  # event time
    T: int  # transaction time
    s: str  # option symbol e.g. BTC-200730-9000-C
    o: Decimal  # open price
    h: Decimal  # highest price
    l: Decimal  # lowest price  # noqa: E741
    c: Decimal  # latest price
    V: Decimal  # trading volume (contracts)
    A: Decimal  # trading amount (USDT)
    P: Decimal  # price change percent
    p: Decimal  # price change
    Q: Decimal  # last trade volume
    F: int  # first trade id
    L: int  # last trade id
    n: int  # trade count
    b: Decimal  # best buy price
    a: Decimal  # best sell price
    d: Decimal  # delta
    t: Decimal  # theta
    g: Decimal  # gamma
    v: Decimal  # vega
    vo: Decimal  # implied volatility
    mp: Decimal  # mark price
    hl: Decimal  # buy max price
    ll: Decimal  # sell min price
    eep: Decimal  # estimated strike price


class BinanceOptionMarkPrice(BaseModel):
    """Binance European options mark price (EAPI @markPrice stream)."""

    e: str  # "markPrice"
    E: int  # event time
    s: str  # symbol
    mp: Decimal  # mark price
    r: Decimal  # interest rate (annualized)
    T: int  # delivery date (ms)


class BinanceInsuranceFundAsset(BaseModel):
    """Single asset in Binance insurance fund snapshot."""

    asset: str
    marginBalance: str
    updateTime: int


class BinanceInsuranceFund(BaseModel):
    """Binance insurance fund snapshot (GET /fapi/v1/insuranceBalance).

    With symbol: single object with symbols + assets. Without: array of such objects.
    """

    symbols: list[str] | None = None
    assets: list[BinanceInsuranceFundAsset] | None = None


# Rebuild models that reference forward-declared classes.
# Required because from __future__ import annotations defers evaluation and
# Pydantic v2 cannot automatically resolve forward references without model_rebuild().
BinanceFuturesExchangeInfo.model_rebuild()
