"""Pydantic schemas for Pyth Network WebSocket price feed data.

Source: Pyth Network WebSocket API
Used by unified-market-interface PythLiveAdapter for oracle price feeds.

Pyth uses fixed-point arithmetic: actual_price = price * 10^expo.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel


class PythPriceFeed(BaseModel):
    """Pyth price feed data structure."""

    id: str | None = None
    price: int | None = None  # Fixed-point mantissa
    conf: int | None = None  # Confidence interval mantissa
    expo: int | None = None  # Exponent for fixed-point conversion
    publish_time: int | None = None  # Unix timestamp in microseconds


class PythWsNotification(BaseModel):
    """Pyth WebSocket notification message."""

    method: str | None = None
    params: dict[str, object] | None = None
    id: str | None = None
    jsonrpc: str | None = None
