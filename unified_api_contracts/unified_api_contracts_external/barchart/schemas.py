"""Pydantic schemas for Barchart data. Migrated from BARCHART_OHLCV_15M_SCHEMA (market-tick-data-handler).

Source: Manual CSV dumps from Barchart subscription. Used for VIX index (CBOE) historical 15-minute data.
Example path: market-tick-data-handler/data/vix/vix_intraday-15min_historical-data-*.csv

VIX live research: Databento index in development; IBKR TWS can stream. See docs/VIX_LIVE_RESEARCH.md.
"""

__api_version__ = "v2"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field


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
