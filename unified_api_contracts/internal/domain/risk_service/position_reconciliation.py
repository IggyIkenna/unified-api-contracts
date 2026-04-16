"""Position reconciliation schemas — target vs actual drift monitoring.

Provides contracts for tracking the deviation between strategy target state
(target delta, target equity allocation) and actual state, per share class.

Live-mode only — reconciliation runs as a background process and emits
high-severity alerts when drift exceeds configured thresholds.

Used by:
- position-balance-monitor-service (produces snapshots via background loop)
- unified-trading-system-ui Observe tab (consumes snapshots for visualization)
- alert pipeline (consumes POSITION_DRIFT_DETECTED events)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class DriftSeverity(StrEnum):
    """Severity of position drift relative to configured thresholds."""

    NORMAL = "NORMAL"
    """Deviation within acceptable bounds (<2% equity, delta within limit)."""

    WARNING = "WARNING"
    """Deviation approaching limits (2-5% equity or delta nearing threshold)."""

    CRITICAL = "CRITICAL"
    """Deviation breaching limits (>5% equity or delta beyond threshold)."""


class DriftDimension(StrEnum):
    """Dimension in which drift is measured."""

    DELTA = "DELTA"
    """Net delta exposure deviation from target (in share class units)."""

    EQUITY_ALLOCATION = "EQUITY_ALLOCATION"
    """Equity allocation deviation from target (in USD)."""


class PositionDriftMetric(BaseModel, frozen=True):
    """Per-strategy target vs actual in one dimension and share class.

    One record per (strategy_id, share_class, dimension) triple.
    """

    strategy_id: str = Field(description="Strategy producing the drift")
    strategy_name: str = Field(description="Human-readable strategy name")
    share_class: str = Field(description="Share class: ETH, BTC, USDT, USD")
    dimension: DriftDimension = Field(description="What is drifting: delta or equity allocation")

    target_value: Decimal = Field(description="Target value (e.g. delta=0.0, allocation=25000.0)")
    actual_value: Decimal = Field(description="Actual observed value")
    deviation: Decimal = Field(description="actual - target (signed)")
    deviation_pct: Decimal = Field(
        description="Deviation as percentage of total equity: (actual - target) / total_equity * 100"
    )

    severity: DriftSeverity = Field(description="Threshold-based severity classification")
    updated_at: datetime = Field(description="When this metric was last computed")


class ShareClassSummary(BaseModel, frozen=True):
    """Aggregated target vs actual for one share class across all strategies."""

    share_class: str = Field(description="ETH, BTC, USDT, USD")

    target_delta: Decimal = Field(description="Sum of target deltas across strategies in this share class")
    actual_delta: Decimal = Field(description="Sum of actual deltas across strategies in this share class")
    delta_residual: Decimal = Field(description="actual_delta - target_delta (should be near zero)")

    target_equity: Decimal = Field(description="Sum of target equity allocations in USD")
    actual_equity: Decimal = Field(description="Sum of actual equity in USD")
    equity_deviation_pct: Decimal = Field(description="(actual_equity - target_equity) / target_equity * 100")


class PortfolioReconciliationSnapshot(BaseModel, frozen=True):
    """Full portfolio reconciliation state at a point in time.

    Produced by position-balance-monitor-service background reconciliation loop.
    Consumed by the Observe tab Position Reconciliation page.
    """

    # --- Portfolio totals ---
    total_equity_usd: Decimal = Field(description="Total portfolio equity in USD")
    allocated_equity_usd: Decimal = Field(description="Equity allocated to strategies")
    unallocated_equity_usd: Decimal = Field(description="Equity not allocated (cash, reserves)")
    allocation_deviation_pct: Decimal = Field(
        description="How far from fully allocated: (total - allocated) / total * 100"
    )

    # --- Per-strategy drift ---
    drift_metrics: list[PositionDriftMetric] = Field(
        default_factory=list,
        description="Per-strategy, per-share-class, per-dimension drift records",
    )

    # --- Per-share-class summary ---
    share_class_summary: dict[str, ShareClassSummary] = Field(
        default_factory=dict,
        description="Share class name -> aggregated summary",
    )

    # --- Worst drift for quick KPI ---
    worst_drift_pct: Decimal = Field(
        default=Decimal("0"),
        description="Largest absolute deviation_pct across all drift metrics",
    )
    worst_drift_strategy_id: str | None = Field(
        default=None,
        description="Strategy with the worst drift",
    )
    worst_drift_severity: DriftSeverity = Field(
        default=DriftSeverity.NORMAL,
        description="Severity of the worst drift",
    )

    # --- Metadata ---
    active_alerts_count: int = Field(default=0, description="Number of active POSITION_DRIFT_DETECTED alerts")
    snapshot_at: datetime = Field(description="When this snapshot was computed")


__all__ = [
    "DriftDimension",
    "DriftSeverity",
    "PortfolioReconciliationSnapshot",
    "PositionDriftMetric",
    "ShareClassSummary",
]
