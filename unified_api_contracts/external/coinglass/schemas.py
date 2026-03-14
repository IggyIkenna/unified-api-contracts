"""
Coinglass API schemas — liquidation heatmap endpoint.

API docs: https://docs.coinglass.com/reference/liquidation-heatmap
API key: coinglass-api-key (Secret Manager)
Rate limit: 10 requests/minute on free tier.
"""

from __future__ import annotations

__api_version__ = "v3"  # matches provider_api_versions.yaml


from pydantic import BaseModel, Field


class LiquidationLevel(BaseModel):
    """Single price level entry in a liquidation heatmap."""

    price: float = Field(description="Price level (USD)")
    long_liq_usd: float = Field(description="Estimated long liquidation volume at this price (USD)")
    short_liq_usd: float = Field(description="Estimated short liquidation volume at this price (USD)")


class LiquidationHeatmapResponse(BaseModel):
    """
    Response from Coinglass liquidation heatmap endpoint.

    Maps price levels to estimated liquidation volumes for both long and short positions.
    Used by liquidation_levels.py calculator to compute liq_gravity_ratio and
    next_liq_cluster_distance_pct features.
    """

    symbol: str = Field(description="Trading symbol, e.g. BTCUSDT")
    exchange: str = Field(description="Exchange name, e.g. Binance")
    current_price: float = Field(description="Current mark price (USD)")
    levels: list[LiquidationLevel] = Field(description="Liquidation levels sorted by price ascending")
    timestamp_ms: int = Field(description="Data timestamp in milliseconds since epoch")


class LiquidationHeatmapRequest(BaseModel):
    """Request parameters for Coinglass liquidation heatmap."""

    symbol: str = Field(description="Trading symbol, e.g. BTCUSDT")
    exchange: str = Field(default="Binance", description="Exchange name")
    range_pct: float = Field(
        default=10.0,
        description="Price range percentage above and below current price to fetch",
    )
    price_bucket_pct: float = Field(
        default=0.1,
        description="Price bucket size as percentage of current price",
    )
