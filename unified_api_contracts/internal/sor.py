"""Smart Order Routing (SOR) internal contract schemas.

The SOR exists in execution-services (defi_router.py, algorithms/sor.py, algorithms/sor_twap.py).
These schemas type the routing decisions, child orders, and execution summaries produced by the SOR.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SorVenueScore(BaseModel):
    """Score assigned to a candidate venue during route selection."""

    venue: str
    fee_score: float = Field(description="0-1, higher = lower fees")
    liquidity_score: float = Field(description="0-1, higher = deeper book")
    latency_score: float = Field(description="0-1, higher = lower latency")
    composite_score: float = Field(description="weighted sum of component scores")
    available_liquidity: Decimal | None = Field(default=None, description="estimated available qty at target price")
    estimated_market_impact_bps: float | None = None
    notes: str | None = None


class SorRouteDecision(BaseModel):
    """Routing decision output — which venue was selected and why."""

    instruction_id: str
    timestamp: datetime
    selected_venue: str
    routing_reason: str = Field(description="e.g. best_composite_score, stablecoin_curve_preference")
    all_scores: list[SorVenueScore] = Field(default_factory=list)
    fallback_venues: list[str] = Field(default_factory=list, description="ordered fallback if selected venue rejects")
    split_required: bool = Field(default=False, description="True if qty exceeds single-venue depth")


class SorChildOrder(BaseModel):
    """Single child order produced by the SOR for a parent instruction."""

    child_order_id: str
    parent_instruction_id: str
    venue: str
    instrument_id: str
    side: str
    quantity: Decimal
    price: Decimal | None = None
    order_type: str = "LIMIT"
    slice_number: int | None = Field(default=None, description="TWAP slice index (1-based)")
    scheduled_time: datetime | None = Field(default=None, description="TWAP: when this slice should be submitted")
    submitted_at: datetime | None = None
    status: str = "pending"


class SorTwapSlice(BaseModel):
    """One TWAP time slice — groups child orders within a time window."""

    slice_id: str
    parent_instruction_id: str
    slice_number: int
    start_time: datetime
    end_time: datetime
    target_qty: Decimal
    submitted_qty: Decimal = Decimal("0")
    filled_qty: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    child_order_ids: list[str] = Field(default_factory=list)
    status: str = "pending"


class SorExecutionSummary(BaseModel):
    """Aggregate result of a fully executed SOR instruction."""

    instruction_id: str
    completed_at: datetime
    total_quantity: Decimal
    total_filled: Decimal
    avg_price: Decimal | None = None
    venues_used: list[str] = Field(default_factory=list)
    total_slippage_bps: float | None = None
    total_fees: Decimal | None = None
    market_impact_bps: float | None = None
    child_order_count: int = 0
    slice_count: int = 0
    route_decision: SorRouteDecision | None = None
    notes: str | None = None


class SorVenueCapacity(BaseModel):
    """Real-time venue capacity estimate used by the DeFi router."""

    venue: str
    pair: str = Field(description="e.g. ETH-USDC")
    available_liquidity: Decimal
    price_impact_1pct: float | None = None
    fee_tier: float | None = Field(default=None, description="e.g. 0.003 for 0.3%")
    pool_address: str | None = None
    last_updated: datetime | None = None
