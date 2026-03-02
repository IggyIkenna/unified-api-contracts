"""
CoinGecko API schemas — global cryptocurrency market data.

Endpoint: GET https://api.coingecko.com/api/v3/global
No API key required for the global endpoint (free tier, 10-30 req/min).
Used to compute btc_dominance_pct and alt_season_signal features.

Docs: https://docs.coingecko.com/reference/global
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GlobalMarketData(BaseModel):
    """
    Inner data payload from /api/v3/global.

    bitcoin_dominance_percentage is the primary feature source for
    btc_dominance_pct, btc_dominance_roc_1d, and alt_season_signal.
    """

    active_cryptocurrencies: int | None = None
    total_market_cap: dict[str, float] = Field(
        default_factory=dict,
        description="Total market cap per currency, e.g. {'usd': 2.5e12}",
    )
    total_volume: dict[str, float] = Field(
        default_factory=dict,
        description="24h total volume per currency",
    )
    market_cap_percentage: dict[str, float] = Field(
        default_factory=dict,
        description="Market cap percentage per coin, e.g. {'btc': 52.4, 'eth': 17.1}",
    )
    market_cap_change_percentage_24h_usd: float | None = Field(
        default=None,
        description="Total market cap % change over last 24h",
    )
    updated_at: int | None = Field(default=None, description="Unix timestamp of last update")

    @property
    def btc_dominance_pct(self) -> float | None:
        """BTC dominance as percentage of total crypto market cap."""
        return self.market_cap_percentage.get("btc")

    @property
    def eth_dominance_pct(self) -> float | None:
        """ETH dominance as percentage of total crypto market cap."""
        return self.market_cap_percentage.get("eth")

    @property
    def total_market_cap_usd(self) -> float | None:
        """Total crypto market cap in USD."""
        return self.total_market_cap.get("usd")


class GlobalMarketResponse(BaseModel):
    """Top-level response wrapper from /api/v3/global."""

    data: GlobalMarketData
