"""Hyblock API schemas — liquidation level and OI cluster endpoints.

API docs: https://docs.hyblock.co/reference
API key: hyblock-api-key (Secret Manager)
Rate limit: varies by plan; treat as 30 req/min for default tier.

Key distinction from CoinGlass:
  - Hyblock provides richer per-leverage-tier breakdowns and OI cluster data.
  - Liquidation levels are per-exchange with leverage-tier attribution.
  - OI clusters represent open-interest concentration bands, not just liq levels.
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from pydantic import BaseModel, Field


class HyblockLiquidationLevelEntry(BaseModel):
    """Single price level entry in a Hyblock liquidation level response."""

    price: float = Field(description="Price level (USD)")
    long_liq_usd: float = Field(description="Estimated long liquidation USD at this price")
    short_liq_usd: float = Field(description="Estimated short liquidation USD at this price")
    leverage_tier: str | None = Field(
        default=None,
        description="Leverage tier this level is attributed to, e.g. '10x', '25x', '50x'",
    )
    cluster_strength: float | None = Field(
        default=None,
        description="Normalised cluster intensity [0-1]; null if not provided by API",
    )


class HyblockLiquidationLevelResponse(BaseModel):
    """Response from Hyblock liquidation levels endpoint.

    Provides price-level breakdown of estimated forced liquidations with optional
    per-leverage-tier attribution. Richer than CoinGlass heatmap for perp analytics.
    """

    symbol: str = Field(description="Trading symbol, e.g. BTCUSDT")
    exchange: str = Field(description="Exchange name, e.g. binance")
    current_price: float = Field(description="Current mark price (USD)")
    levels: list[HyblockLiquidationLevelEntry] = Field(description="Liquidation price levels sorted by price ascending")
    timestamp_ms: int = Field(description="Data timestamp in milliseconds since epoch")


class HyblockOIClusterEntry(BaseModel):
    """Single open-interest concentration band in a Hyblock OI cluster response."""

    price_low: float = Field(description="Lower bound of this OI band (USD)")
    price_high: float = Field(description="Upper bound of this OI band (USD)")
    oi_usd: float = Field(description="Total open interest USD in this band")
    long_oi_usd: float | None = Field(default=None, description="Long OI component (USD)")
    short_oi_usd: float | None = Field(default=None, description="Short OI component (USD)")


class HyblockOIClusterResponse(BaseModel):
    """Response from Hyblock OI cluster endpoint.

    Provides open-interest concentration by price band — useful for identifying
    sticky OI zones that correlate with support/resistance behaviour.
    """

    symbol: str = Field(description="Trading symbol, e.g. BTCUSDT")
    exchange: str = Field(description="Exchange name")
    current_price: float = Field(description="Current mark price (USD)")
    clusters: list[HyblockOIClusterEntry] = Field(description="OI concentration bands sorted by price_low ascending")
    timestamp_ms: int = Field(description="Data timestamp in milliseconds since epoch")



# HyblockLiquidationLevelRequest and HyblockOIClusterRequest removed — no consumers.
