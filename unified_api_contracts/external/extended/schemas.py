"""Extended.exchange (StarkNet) REST API schemas (api.starknet.extended.exchange/api/v1/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtendedMarket(BaseModel):
    """Single perpetual market from GET /info/markets."""

    symbol: str = Field(..., description="Market symbol (e.g. BTC-USD)")
    base_asset: str = Field(..., description="Base asset ticker")
    quote_asset: str = Field(..., description="Quote asset ticker")
    status: str = Field(..., description="Market status (e.g. ACTIVE, INACTIVE)")
    tick_size: str = Field(..., description="Minimum price increment")
    step_size: str = Field(..., description="Minimum quantity increment")
    min_order_size: str | None = Field(None, description="Minimum order size")
    max_leverage: int | None = Field(None, description="Maximum allowed leverage")


class ExtendedMarketsResponse(BaseModel):
    """Response from GET /api/v1/info/markets."""

    markets: list[ExtendedMarket] = Field(default_factory=list)
