"""Unwind preview schemas for cost-aware position close/reduce.

Provides request/response contracts for the execution-service preview endpoint
that estimates the cost of closing or reducing positions — gas, slippage,
exchange fees, bridge fees — without placing any orders.

Analogous to Uniswap's swap preview: shows expected costs before confirmation.

Live-mode only — these operations make no sense in batch/backtest.

Used by:
- execution-service ``/preview/unwind`` endpoint (produces responses)
- unified-trading-system-ui intervention controls (consumes responses)
- position-balance-monitor-service reconciliation page (consumes responses)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class UnwindAction(StrEnum):
    """Type of position unwind operation."""

    CLOSE = "CLOSE"
    """Close position entirely — set target to zero."""

    REDUCE = "REDUCE"
    """Reduce position by a percentage — partial unwind."""


class UnwindExecutionStyle(StrEnum):
    """How the unwind should be executed."""

    MARKET = "MARKET"
    """Immediate market orders — fastest, highest slippage."""

    TWAP = "TWAP"
    """Time-weighted average price over a window — balanced."""

    ATOMIC_DEFI = "ATOMIC_DEFI"
    """Single atomic DeFi transaction — flash loan or multicall."""


class UnwindConfidence(StrEnum):
    """Confidence level of the cost estimate."""

    HIGH = "HIGH"
    """Based on live market data and real-time quotes."""

    MEDIUM = "MEDIUM"
    """Based on cached data or recent historical estimates."""

    LOW = "LOW"
    """Based on static models or stale data."""


@dataclass(frozen=True)
class UnwindPreviewRequest:
    """Request to preview cost of closing or reducing positions.

    Live-mode only — disabled in batch/backtest.
    """

    action: UnwindAction
    """Whether to fully close or partially reduce."""

    execution_style: UnwindExecutionStyle = UnwindExecutionStyle.TWAP
    """How the unwind should be executed."""

    strategy_id: str | None = None
    """Target strategy. None = all strategies (firm-wide)."""

    reduce_pct: Decimal | None = None
    """Percentage to reduce (1-100). Required when action == REDUCE."""

    twap_duration_minutes: int = 15
    """TWAP window in minutes. Only used when execution_style == TWAP."""


@dataclass(frozen=True)
class UnwindStep:
    """One leg of the unwind execution plan.

    Each step represents a single atomic operation (market order, swap,
    repay, withdraw, etc.) needed to unwind a position.
    """

    instrument_id: str
    """Canonical instrument ID (VENUE:TYPE:PAYLOAD[@CHAIN])."""

    venue: str
    """Execution venue."""

    side: str
    """Direction to close: 'sell' for longs, 'buy' for shorts."""

    quantity: Decimal
    """Quantity to close."""

    estimated_price: Decimal
    """Expected execution price."""

    estimated_slippage_bps: Decimal
    """Expected slippage for this leg in basis points."""

    operation_type: str
    """Operation: market_order, swap, repay, withdraw, unstake, bridge."""

    chain: str = ""
    """Chain name for DeFi operations (empty for CeFi)."""

    gas_cost_usd: Decimal = Decimal("0")
    """Estimated gas cost for this specific step."""


@dataclass(frozen=True)
class UnwindPreviewResponse:
    """Full cost decomposition for a position close/reduce.

    Returned by execution-service ``/preview/unwind``.
    All monetary values in USD, all proportional values in basis points.
    """

    # --- Request echo ---
    action: UnwindAction
    strategy_id: str | None
    positions_affected: int

    # --- Cost breakdown ---
    estimated_slippage_usd: Decimal
    estimated_slippage_bps: Decimal
    estimated_gas_usd: Decimal
    estimated_exchange_fees_usd: Decimal
    estimated_bridge_fees_usd: Decimal
    total_estimated_cost_usd: Decimal
    total_estimated_cost_bps: Decimal
    """Total cost as fraction of notional being closed."""

    # --- Execution plan ---
    notional_to_close_usd: Decimal
    """Total notional value of positions being closed."""

    estimated_duration_minutes: Decimal
    """Estimated time to complete the unwind."""

    execution_steps: list[UnwindStep] = field(default_factory=list)
    """Ordered list of operations to execute."""

    # --- Risk ---
    market_impact_estimate_bps: Decimal = Decimal("0")
    """Estimated permanent market impact in basis points."""

    confidence: UnwindConfidence = UnwindConfidence.MEDIUM
    """How confident the cost estimate is."""

    timestamp: datetime | None = None
    """When this preview was generated."""

    notes: list[str] = field(default_factory=list)
    """Human-readable notes about the estimate."""


__all__ = [
    "UnwindAction",
    "UnwindConfidence",
    "UnwindExecutionStyle",
    "UnwindPreviewRequest",
    "UnwindPreviewResponse",
    "UnwindStep",
]
