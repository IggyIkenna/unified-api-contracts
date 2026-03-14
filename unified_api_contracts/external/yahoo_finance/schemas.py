"""Pydantic schemas for Yahoo Finance adapter responses. Full surface: market data, errors, edge cases."""

__api_version__ = "v8"  # matches provider_api_versions.yaml

from datetime import datetime

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


class YahooOhlcv24h(BaseModel):
    """Daily OHLCV bar from Yahoo Finance (yfinance history / yf.download)."""

    Date: str | None = None
    Open: float | None = None
    High: float | None = None
    Low: float | None = None
    Close: float | None = None
    Adj_Close: float | None = None
    Volume: float | None = None


class YahooSplits(BaseModel):
    """Stock split record from Yahoo Finance (yfinance ticker.splits / actions)."""

    ticker: str | None = None
    effective_date: str | None = None
    ratio: float | None = None
    split_from: int | None = None
    split_to: int | None = None
    is_reverse_split: bool | None = None
    adjustment_factor: float | None = None
    source: str | None = None


class YahooDividends(BaseModel):
    """Dividend record from Yahoo Finance (yfinance ticker.dividends / actions)."""

    ticker: str | None = None
    ex_date: str | None = None
    pay_date: str | None = None
    record_date: str | None = None
    declaration_date: str | None = None
    amount: float | None = None
    dividend_type: str | None = None
    currency: str | None = None
    source: str | None = None


class YahooQuote(BaseModel):
    """Yahoo Finance quote (price data)."""

    symbol: str | None = None
    shortName: str | None = None
    regularMarketPrice: float | None = None
    regularMarketChange: float | None = None
    regularMarketVolume: int | None = None
    bid: float | None = None
    ask: float | None = None
    info: dict[str, object] | None = None


class YahooChartResult(BaseModel):
    """Chart/quote result wrapper."""

    result: list[object] | None = None
    error: dict[str, object] | None = None


class YahooError(BaseModel):
    """Yahoo Finance error."""

    code: str | None = None
    description: str | None = None

    @classmethod
    def classify(cls, code: str | None = None, http_status: int | None = None) -> ErrorAction:
        """Map Yahoo Finance error to retry action."""
        if http_status == 429:
            return ErrorAction.RETRY
        if code and "RATE_LIMIT" in (code or "").upper():
            return ErrorAction.RETRY
        return ErrorAction.FAIL


class YahooEarningsEvent(BaseModel):
    """Source: ticker.calendar, ticker.earnings_dates."""

    ticker: str | None = None
    earnings_date: str | None = None
    eps_estimate: float | None = None
    eps_actual: float | None = None
    eps_surprise_pct: float | None = None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None
    period: str | None = None
    source: str | None = None


class YahooKeyStatistics(BaseModel):
    """Source: ticker.info."""

    ticker: str | None = None
    beta: float | None = None
    pe_ratio_ttm: float | None = None
    forward_pe: float | None = None
    eps_ttm: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    price_to_book: float | None = None
    price_to_sales_ttm: float | None = None
    profit_margins: float | None = None
    short_ratio: float | None = None
    short_percent_of_float: float | None = None
    shares_outstanding: float | None = None
    float_shares: float | None = None
    book_value_per_share: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    source: str | None = None


class YahooAnalystRating(BaseModel):
    """Source: ticker.recommendations."""

    ticker: str | None = None
    date: str | None = None
    firm: str | None = None
    to_grade: str | None = None
    from_grade: str | None = None
    action: str | None = None
    source: str | None = None


class YahooPriceTarget(BaseModel):
    """Source: ticker.info."""

    ticker: str | None = None
    mean_price_target: float | None = None
    high_price_target: float | None = None
    low_price_target: float | None = None
    number_of_analyst_opinions: int | None = None
    recommendation_key: str | None = None
    recommendation_mean: float | None = None
    source: str | None = None


class YahooOptionContract(BaseModel):
    """Single option contract from ticker.options chain."""

    ticker: str | None = None
    expiration: str | None = None
    option_type: str | None = None  # call/put
    strike: float | None = None
    last_price: float | None = None
    bid: float | None = None
    ask: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    in_the_money: bool | None = None
    contract_symbol: str | None = None
    last_trade_date: str | None = None
    source: str | None = None


class YahooOptionsChain(BaseModel):
    """Source: ticker.option_chain()."""

    ticker: str | None = None
    expiration: str | None = None
    calls: list[YahooOptionContract] | None = None
    puts: list[YahooOptionContract] | None = None
    underlying_price: float | None = None
    source: str | None = None


class YahooInstitutionalHolder(BaseModel):
    """Source: ticker.institutional_holders."""

    ticker: str | None = None
    holder: str | None = None
    shares: int | None = None
    date_reported: str | None = None
    percent_out: float | None = None
    value: float | None = None
    source: str | None = None


class YahooInsiderTransaction(BaseModel):
    """Source: ticker.insider_transactions."""

    ticker: str | None = None
    insider: str | None = None
    relation: str | None = None
    transaction_date: str | None = None
    transaction_type: str | None = None
    shares: int | None = None
    value: float | None = None
    source: str | None = None


class YahooMajorHolder(BaseModel):
    """Source: ticker.info major holders fields."""

    ticker: str | None = None
    pct_shares_held_by_insiders: float | None = None
    pct_shares_held_by_institutions: float | None = None
    pct_float_held_by_institutions: float | None = None
    number_of_institutions_holding: int | None = None
    source: str | None = None


# =============================================================================
# Macro schemas (merged from external/macro/yahoo_finance.py)
# =============================================================================

# API Constants
YAHOO_FINANCE_BASE_URL = "https://query1.finance.yahoo.com/v8/finance"
YAHOO_FINANCE_RATE_LIMIT_UNOFFICIAL = 2000  # requests per hour (estimated)

# Macro ticker symbols
TICKER_DXY = "DX-Y.NYB"  # US Dollar Index
TICKER_US_10Y = "^TNX"  # 10-Year Treasury Yield
TICKER_US_2Y = "^IRX"  # 2-Year Treasury Yield
TICKER_US_30Y = "^TYX"  # 30-Year Treasury Yield
TICKER_GOLD = "GC=F"  # Gold Futures
TICKER_OIL_WTI = "CL=F"  # Crude Oil WTI Futures
TICKER_OIL_BRENT = "BZ=F"  # Crude Oil Brent Futures
TICKER_VIX = "^VIX"  # CBOE Volatility Index


class YahooFinanceMacroOhlcv(BaseModel):
    """OHLCV bar for macro instruments (DXY, yields, commodities)."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Bar timestamp (UTC)")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    ticker: str = Field(..., description="Yahoo Finance ticker symbol")
    open: float | None = Field(None, description="Opening price")
    high: float | None = Field(None, description="High price")
    low: float | None = Field(None, description="Low price")
    close: float = Field(..., description="Closing price")
    adj_close: float | None = Field(None, description="Adjusted close (for dividends/splits)")
    volume: int | None = Field(None, description="Trading volume")


class YahooFinanceMacroOhlcvResponse(BaseModel):
    """Response from yfinance history() for macro data."""

    ticker: str = Field(..., description="Ticker symbol")
    data: list[YahooFinanceMacroOhlcv] = Field(..., description="Historical OHLCV bars")
    interval: str = Field(default="1d", description="Data interval: 1d, 1h, 1m, etc.")
    start: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end: str | None = Field(None, description="End date (YYYY-MM-DD)")


class YahooFinanceDXYSnapshot(BaseModel):
    """Current DXY (US Dollar Index) snapshot."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Snapshot timestamp (UTC)")
    ticker: str = Field(default=TICKER_DXY, description="DXY ticker symbol")
    price: float = Field(..., description="Current DXY value")
    change: float | None = Field(None, description="Absolute price change")
    change_percent: float | None = Field(None, description="Percentage change")
    open: float | None = Field(None, description="Session open price")
    high: float | None = Field(None, description="Session high price")
    low: float | None = Field(None, description="Session low price")
    previous_close: float | None = Field(None, description="Previous session close")


class YahooFinanceYieldSnapshot(BaseModel):
    """Current Treasury yield snapshot."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Snapshot timestamp (UTC)")
    ticker: str = Field(..., description="Yield ticker symbol (^TNX, ^IRX, ^TYX)")
    yield_value: float = Field(..., description="Yield value (e.g., 4.25 for 4.25%)")
    change: float | None = Field(None, description="Absolute yield change")
    change_percent: float | None = Field(None, description="Percentage change")
    maturity: str = Field(..., description="Maturity: 2Y, 10Y, 30Y")


class YahooFinanceYieldCurve(BaseModel):
    """Treasury yield curve snapshot (2Y, 10Y, 30Y)."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Snapshot timestamp (UTC)")
    yield_2y: float = Field(..., description="2-Year Treasury yield (%)")
    yield_10y: float = Field(..., description="10-Year Treasury yield (%)")
    yield_30y: float = Field(..., description="30-Year Treasury yield (%)")
    spread_10y_2y: float = Field(..., description="10Y-2Y spread (basis points)")
    spread_30y_10y: float = Field(..., description="30Y-10Y spread (basis points)")
    is_inverted: bool = Field(..., description="Whether 10Y-2Y spread is negative (inverted curve)")


class YahooFinanceCommoditySnapshot(BaseModel):
    """Current commodity price snapshot (gold, oil)."""

    timestamp_utc: datetime = Field(..., alias="datetime", description="Snapshot timestamp (UTC)")
    ticker: str = Field(..., description="Commodity ticker (GC=F, CL=F, BZ=F)")
    commodity: str = Field(..., description="Commodity name: gold, oil_wti, oil_brent")
    price: float = Field(..., description="Current price")
    change: float | None = Field(None, description="Absolute price change")
    change_percent: float | None = Field(None, description="Percentage change")
    open: float | None = Field(None, description="Session open price")
    high: float | None = Field(None, description="Session high price")
    low: float | None = Field(None, description="Session low price")
    volume: int | None = Field(None, description="Trading volume")


class YahooFinanceError(BaseModel):
    """Yahoo Finance API error."""

    message: str | None = Field(None, description="Error message")
    status_code: int | None = Field(None, description="HTTP status code")

    @classmethod
    def classify(cls, status_code: int | None = None) -> ErrorAction:
        """Map Yahoo Finance error to retry action."""
        if status_code == 429:
            return ErrorAction.RETRY
        if status_code is not None and status_code >= 500:
            return ErrorAction.RETRY
        if status_code == 404:
            return ErrorAction.FAIL  # Invalid ticker
        return ErrorAction.FAIL


class YahooFinanceRequestParams(BaseModel):
    """Request parameters for yfinance API."""

    ticker: str = Field(..., description="Yahoo Finance ticker symbol")
    period: str | None = Field(None, description="Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max")
    interval: str = Field(
        default="1d",
        description="Interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo",
    )
    start: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end: str | None = Field(None, description="End date (YYYY-MM-DD)")
    prepost: bool = Field(default=False, description="Include pre/post market data")
    auto_adjust: bool = Field(default=True, description="Adjust all OHLC automatically")
    back_adjust: bool = Field(default=False, description="Back-adjust data for splits")


# Macro indicator thresholds
DXY_STRONG_DOLLAR = 105.0  # DXY > 105 = strong dollar (bearish for crypto)
DXY_WEAK_DOLLAR = 95.0  # DXY < 95 = weak dollar (bullish for crypto)
YIELD_CURVE_INVERSION_THRESHOLD = 0.0  # 10Y-2Y < 0 = inverted (recession signal)
YIELD_10Y_HIGH = 5.0  # 10Y yield > 5% = high rates (bearish for risk assets)
YIELD_10Y_LOW = 2.0  # 10Y yield < 2% = low rates (bullish for risk assets)
GOLD_SAFE_HAVEN_THRESHOLD = 2000.0  # Gold > $2000 = risk-off sentiment
VIX_HIGH_VOLATILITY = 30.0  # VIX > 30 = high market fear
VIX_LOW_VOLATILITY = 15.0  # VIX < 15 = low market fear (complacency)
