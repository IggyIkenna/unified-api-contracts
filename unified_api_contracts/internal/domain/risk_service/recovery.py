"""Autonomous recovery schemas — reconciliation health, cascade state, deleverage.

Provides contracts for the autonomous recovery stack: tracking reconciliation
health before position closes, monitoring multi-venue circuit breaker cascades,
and requesting auto-deleverage operations.

Used by:
- execution-service (checks recon health before exit playbook)
- position-balance-monitor-service (detects dual failure, marks stale recon)
- unified-trading-system-ui Observe tab (recovery controls dashboard)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class ReconStatus(StrEnum):
    """Reconciliation health for a single venue."""

    HEALTHY = "HEALTHY"
    """Reconciled within last 60s, position counts match."""

    STALE = "STALE"
    """Last successful reconciliation >60s ago (may be circuit breaker related)."""

    FAILED = "FAILED"
    """Reconciliation attempt failed (venue unreachable or data mismatch)."""


class ExecStatus(StrEnum):
    """Execution connectivity for a single venue."""

    CONNECTED = "CONNECTED"
    """Circuit breaker CLOSED or HALF_OPEN — can submit orders."""

    DEGRADED = "DEGRADED"
    """Circuit breaker DEGRADED — some orders throttled."""

    DISCONNECTED = "DISCONNECTED"
    """Circuit breaker OPEN — cannot submit orders."""


class ReconHealthStatus(BaseModel, frozen=True):
    """Combined reconciliation + execution health for pre-close gating.

    The 2x2 matrix:
    - recon OK + exec OK = normal close
    - recon OK + exec down = can verify but can't act
    - recon down + exec OK = close with CAUTION, verify post-close
    - recon down + exec down = DUAL FAILURE, positions frozen
    """

    venue: str = Field(description="Venue being assessed")
    can_reconcile: bool = Field(description="True if reconciliation is healthy for this venue")
    can_execute: bool = Field(description="True if execution connectivity is available")
    recon_status: ReconStatus = Field(description="Detailed reconciliation status")
    exec_status: ExecStatus = Field(description="Detailed execution status")
    last_recon_at: datetime | None = Field(default=None, description="Last successful reconciliation timestamp")
    is_dual_failure: bool = Field(default=False, description="True when both recon and exec are down")
    assessed_at: datetime = Field(description="When this assessment was made")


class CascadeState(BaseModel, frozen=True):
    """Multi-venue circuit breaker cascade state.

    Tracks how many venues are in OPEN state simultaneously.
    Triggers escalation when threshold exceeded.
    """

    venues_open: list[str] = Field(default_factory=list, description="Venues with OPEN circuit breakers")
    venues_degraded: list[str] = Field(default_factory=list, description="Venues in DEGRADED state")
    venues_total: int = Field(description="Total active venues for the strategy/firm")
    cascade_pct: Decimal = Field(
        description="Percentage of venues that are OPEN: len(venues_open) / venues_total * 100"
    )
    is_cascade: bool = Field(default=False, description="True when cascade_pct > 50%")
    is_total_failure: bool = Field(default=False, description="True when all venues are OPEN")
    strategy_id: str | None = Field(default=None, description="Strategy affected (None = firm-wide)")
    assessed_at: datetime = Field(description="When this assessment was made")


class AutoDeleverageRequest(BaseModel, frozen=True):
    """Request to auto-deleverage a position to restore health factor."""

    strategy_id: str = Field(description="Strategy to deleverage")
    venue: str = Field(description="Venue where health factor is breached")
    current_health_factor: Decimal = Field(description="Current HF (below threshold)")
    target_health_factor: Decimal = Field(default=Decimal("2.0"), description="Target HF after deleverage")
    max_slippage_bps: int = Field(default=50, description="Maximum slippage tolerance")
    domain: str = Field(description="'defi' | 'cefi' | 'tradfi' — determines deleverage method")


class AutoDeleverageResponse(BaseModel, frozen=True):
    """Result of an auto-deleverage operation."""

    strategy_id: str
    venue: str
    success: bool
    previous_health_factor: Decimal
    new_health_factor: Decimal | None = Field(default=None, description="Post-deleverage HF (None if failed)")
    amount_deleveraged_usd: Decimal = Field(default=Decimal("0"))
    method: str = Field(
        default="", description="'flash_loan' (DeFi), 'market_close' (CeFi), 'reduce_position' (TradFi)"
    )
    error: str | None = None


class TriggerScenario(StrEnum):
    """Scenarios that trigger automatic recovery actions."""

    HF_CRITICAL = "HF_CRITICAL"
    """Health factor 1.0-1.2 — deleverage required."""

    HF_EMERGENCY = "HF_EMERGENCY"
    """Health factor < 1.0 — liquidation imminent."""

    VENUE_CASCADE = "VENUE_CASCADE"
    """>50% venues OPEN — cascade detected."""

    TOTAL_VENUE_FAILURE = "TOTAL_VENUE_FAILURE"
    """All venues OPEN — firm-wide halt."""

    DRIFT_CRITICAL = "DRIFT_CRITICAL"
    """Position drift > 5% — pause until investigated."""

    DUAL_FAILURE = "DUAL_FAILURE"
    """Recon + exec both down — positions frozen, human required."""

    TREASURY_LOW = "TREASURY_LOW"
    """Treasury below threshold."""

    UNHEDGED_POSITION = "UNHEDGED_POSITION"
    """Multi-leg partial fill — flatten delta on available venues."""


@dataclass(frozen=True)
class PlaybookTriggerMapping:
    """Maps a trigger scenario to an emergency exit playbook."""

    scenario: TriggerScenario
    exit_type: str  # EmergencyExitType value
    auto_deactivate_minutes: int = 60
    description: str = ""


# SSOT registry — maps each trigger scenario to the appropriate exit playbook.
PLAYBOOK_TRIGGER_MAP: dict[TriggerScenario, PlaybookTriggerMapping] = {
    TriggerScenario.HF_CRITICAL: PlaybookTriggerMapping(
        scenario=TriggerScenario.HF_CRITICAL,
        exit_type="deleverage_sequence",
        description="Reduce leverage via market orders (CeFi) or flash loan (DeFi)",
    ),
    TriggerScenario.HF_EMERGENCY: PlaybookTriggerMapping(
        scenario=TriggerScenario.HF_EMERGENCY,
        exit_type="fast_unwind",
        auto_deactivate_minutes=30,
        description="Emergency close all — liquidation imminent",
    ),
    TriggerScenario.VENUE_CASCADE: PlaybookTriggerMapping(
        scenario=TriggerScenario.VENUE_CASCADE,
        exit_type="stop_new_only",
        description="Block new orders, existing positions held",
    ),
    TriggerScenario.TOTAL_VENUE_FAILURE: PlaybookTriggerMapping(
        scenario=TriggerScenario.TOTAL_VENUE_FAILURE,
        exit_type="stop_new_only",
        auto_deactivate_minutes=120,
        description="All venues down — firm-wide halt",
    ),
    TriggerScenario.DRIFT_CRITICAL: PlaybookTriggerMapping(
        scenario=TriggerScenario.DRIFT_CRITICAL,
        exit_type="stop_new_only",
        description="Position drift >5% — pause until investigated",
    ),
    TriggerScenario.DUAL_FAILURE: PlaybookTriggerMapping(
        scenario=TriggerScenario.DUAL_FAILURE,
        exit_type="stop_new_only",
        auto_deactivate_minutes=15,
        description="Can't reconcile or execute — positions frozen, human required",
    ),
    TriggerScenario.TREASURY_LOW: PlaybookTriggerMapping(
        scenario=TriggerScenario.TREASURY_LOW,
        exit_type="stop_new_only",
        description="Treasury below threshold — block new allocations",
    ),
    TriggerScenario.UNHEDGED_POSITION: PlaybookTriggerMapping(
        scenario=TriggerScenario.UNHEDGED_POSITION,
        exit_type="delta_hedge",
        description="Multi-leg partial fill — flatten delta on available venues",
    ),
}


__all__ = [
    "PLAYBOOK_TRIGGER_MAP",
    "AutoDeleverageRequest",
    "AutoDeleverageResponse",
    "CascadeState",
    "ExecStatus",
    "PlaybookTriggerMapping",
    "ReconHealthStatus",
    "ReconStatus",
    "TriggerScenario",
]
