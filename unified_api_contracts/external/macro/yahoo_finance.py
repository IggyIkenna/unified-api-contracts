"""Pydantic schemas for Yahoo Finance macro data (DXY, yields, commodities).

Source: Yahoo Finance via yfinance library (https://github.com/ranaroussi/yfinance)
Free, no API key required. Rate limits: ~2000 requests/hour (unofficial).

Used by unified-market-interface for macro indicators: DXY (US Dollar Index), Treasury yields, gold, oil.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from datetime import datetime

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.errors import ErrorAction

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
