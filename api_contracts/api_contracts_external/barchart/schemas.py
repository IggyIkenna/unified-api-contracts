"""Pydantic schemas for Barchart data. CSV dumps + OnDemand REST API.

Sources:
- Manual CSV dumps: VIX index (CBOE) 15-minute historical. See docs/VIX_LIVE_RESEARCH.md.
- OnDemand REST: getHistory, getChart. Ref: https://docs.barchart.com/ondemand/
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


# --- CSV (legacy) ---
class BarchartOhlcv15m(BaseModel):
    """OHLCV 15-minute bar from Barchart CSV. VIX 15m historical. Timestamp in US Eastern Time."""

    Time: str = Field(..., description="Timestamp in US Eastern Time (format: YYYY-MM-DD HH:MM)")
    Open: float = Field(..., description="Opening price")
    High: float = Field(..., description="Highest price")
    Low: float = Field(..., description="Lowest price")
    Last: float = Field(..., description="Closing price (Barchart uses 'Last' for close)")
    Change: float | None = Field(None, description="Price change (absolute)")
    percent_change: str | None = Field(
        None,
        description="Price change (percentage)",
        validation_alias="%Change",
    )
    Volume: float | None = Field(None, description="Volume (typically 0 for VIX index)")


# --- OnDemand REST API ---
class BarchartHistoryBar(BaseModel):
    """Single OHLCV bar from Barchart getHistory REST API.

    Supports tick, minute, and end-of-day data for stocks, indexes, futures, FX, crypto.
    """

    timestamp: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    trade_count: int | None = Field(None, alias="tradeCount")

    model_config = {"populate_by_name": True}


class BarchartHistoryResponse(BaseModel):
    """Response from Barchart getHistory endpoint."""

    symbol: str | None = None
    session: str | None = None
    interval: str | None = None  # 1min | 5min | 15min | 1day | 1week
    bars: list[BarchartHistoryBar] | None = None
    status: dict | None = None


class BarchartChartResponse(BaseModel):
    """Response from Barchart getChart endpoint (chart image metadata)."""

    url: str | None = None
    symbol: str | None = None
    chart_type: str | None = Field(None, alias="chartType")
    period: str | None = None


class BarchartError(BaseModel):
    """Barchart API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Barchart error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD
