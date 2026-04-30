"""Generic leveraged-leg portfolio primitives.

Strategy-agnostic, asset_group-agnostic schema for the LeveragedLegController:
every archetype that holds N legs with target_leverage and target_net_delta
publishes its desired state via these types and consumes the controller's
emitted rebalance instructions.

Replaces hand-rolled `_build_legs` + bespoke rebalance loops scattered across
strategy-service archetype engines, position-balance-monitor sports_arb_engine,
and execution-service tracers — each was solving the same shape of problem
with strategy-specific code. See
``unified-trading-pm/plans/active/leveraged_leg_controller_2026_05_01.plan.md``.

The wire-format primitive here is consumed by:
  - ``execution_service.algo_library.leveraged_leg_controller`` — drift +
    rebalance emission.
  - ``risk-and-exposure-service`` — LEVERAGE_BREACH alerts on drift.
  - ``position-balance-monitor-service`` — per-leg current_leverage on snapshot.

Time-varying ``target_leverage``: strategies publish ``target_leverage_now``
per tick (e.g. ML_DIRECTIONAL scales with conviction_pct, VOL_TRADING with
realized-vol regime). The controller treats it as input and adjusts position
to track. Venue capability declarations from instruments-service clamp
``target_leverage`` to ``venue.max_leverage``; SPORTS venues declare
max_leverage=1.0 and the controller silently caps without strategy code knowing.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class CashSweepPolicy(StrEnum):
    """When to move PnL between legs to restore per-leg target leverage."""

    ALWAYS_SWEEP_TO_LOSER = "ALWAYS_SWEEP_TO_LOSER"
    """On every rebalance trigger, move surplus equity from the leg with
    leverage-below-target to the leg with leverage-above-target. Highest
    leverage stability; highest tx cost."""

    PERIODIC = "PERIODIC"
    """Sweep on a fixed cadence (``sweep_cadence_seconds``) regardless of
    drift size. Predictable cost; tolerates drift between cadences."""

    THRESHOLD = "THRESHOLD"
    """Sweep only when any leg's drift exceeds ``rebalance_trigger_bps``.
    Default; balances cost vs leverage stability."""


class LegSizingStrategy(StrEnum):
    """How to size legs at allocation time given a venue universe."""

    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    PROPORTIONAL_TO_DEV_FROM_MEAN = "PROPORTIONAL_TO_DEV_FROM_MEAN"
    """Cross-venue funding allocator: SHORT on highest-funding venue, LONG
    across cheaper venues with weights proportional to |dev_from_mean|. Net delta = 0
    within coin."""

    HEDGE_UNDERLYING = "HEDGE_UNDERLYING"
    """Long primary instrument + short hedge, sized so net delta on the
    underlying = target_net_delta (typically 0). Used by CARRY_STAKED_BASIS,
    MEAN_REVERSION, MARKET_MAKING inventory hedge."""

    LEVERAGE_LOOP = "LEVERAGE_LOOP"
    """Recursive collateral-borrow loop: stake → pledge → borrow → restake.
    N supply legs + N-1 borrow legs sized via geometric series at fixed LTV."""

    BORROW_RICH_LEND_CHEAP = "BORROW_RICH_LEND_CHEAP"
    """Cross-chain interest-rate arb: borrow on the lowest-rate chain, lend
    on the highest-rate chain. Net delta on the asset = 0."""

    KELLY_OVERROUND = "KELLY_OVERROUND"
    """Sports value-betting: stake per outcome proportional to (kelly_fraction x bankroll
    x edge / odds). Venue-capability clamps target_leverage to 1.0 since
    SPORTS venues declare ``supports_margin=false``."""

    CONVICTION_WEIGHTED = "CONVICTION_WEIGHTED"
    """ML/RULES directional: single leg, target_leverage scales with
    conviction_pct or rule_strength. target_net_delta = ±target_leverage."""

    REGIME_WEIGHTED = "REGIME_WEIGHTED"
    """VOL_TRADING / REGIME-AWARE: target_leverage scales with realized-vol
    regime multiplier (lower in high-vol regimes)."""


class LeveragedLeg(BaseModel):
    """One leg of a leveraged multi-leg portfolio.

    A strategy declares per-leg ``(side, target_leverage, venue, instrument)``.
    target_leverage is time-varying: strategies publish a fresh value on
    every tick (e.g. ML_DIRECTIONAL scales with conviction_pct). The
    controller diffs current position vs (equity x target_leverage x side)
    and emits the rebalance instruction.
    """

    leg_id: str = Field(description="Stable identifier for cross-tick continuity")
    side: Literal["LONG", "SHORT"]
    venue: str
    instrument: str
    target_leverage: Decimal = Field(
        description=(
            "Per-leg leverage target. May be time-varying — strategies update "
            "per tick. Controller clamps to venue.max_leverage from "
            "instruments-service capability declarations."
        ),
    )
    target_leverage_source: str = Field(
        default="constant",
        description=(
            "Provenance of target_leverage for observability. One of: "
            "``constant``, ``conviction``, ``regime``, ``carry_quality``, "
            "``proximity_to_event``, ``manual_override``."
        ),
    )
    rebalance_trigger_bps: int = Field(
        default=50,
        description=(
            "Trigger rebalance when actual_leverage drifts from target by "
            "more than this many basis points (50 = 0.50x drift on a "
            "denominator-normalised scale)."
        ),
    )
    min_leg_notional: Decimal | None = Field(
        default=None,
        description="Filter out leg adjustments below this notional (dust threshold).",
    )


class LegPortfolioState(BaseModel):
    """The full leveraged multi-leg portfolio state for one strategy instance.

    Passed to ``LeveragedLegController.update(state, current_positions,
    current_equity)`` per tick. The controller produces the AtomicInstruction
    list that brings the portfolio back to (target_leverage_per_leg,
    target_net_delta).
    """

    strategy_instance_id: str
    legs: list[LeveragedLeg]
    target_net_delta: Decimal = Field(
        default=Decimal("0"),
        description=(
            "Aggregate net delta target across legs. 0 = market-neutral; "
            "1 = full long; L-1 = recursive-leverage exposure (delta-positive). "
            "Controller satisfies this constraint while simultaneously "
            "respecting per-leg target_leverage."
        ),
    )
    cash_sweep_policy: CashSweepPolicy = CashSweepPolicy.THRESHOLD
    sweep_cadence_seconds: int = Field(
        default=3600,
        description="Used only when cash_sweep_policy = PERIODIC.",
    )
    sizing_strategy: LegSizingStrategy = LegSizingStrategy.EQUAL_WEIGHT
    """How legs are sized at INITIAL allocation. Once initialised, drift
    detection drives subsequent rebalance — sizing_strategy is referenced
    only on first allocation or after full close."""


class LegDrift(BaseModel):
    """Computed per-leg drift between current state and target.

    Output of ``LeveragedLegController.compute_drift``. One per leg in the
    LegPortfolioState. The controller consumes this list to decide whether
    a rebalance is warranted (drift > rebalance_trigger_bps) and to size the
    rebalance instructions.
    """

    leg_id: str
    actual_leverage: Decimal
    target_leverage: Decimal
    leverage_drift_bps: int = Field(
        description="Signed: positive = actual > target (over-leveraged); negative = under-leveraged"
    )
    actual_position_units: Decimal
    target_position_units: Decimal
    position_delta_units: Decimal = Field(
        description="target_position_units - actual_position_units; positive = need to add, negative = need to trim"
    )
    actual_equity: Decimal
    """Per-leg equity (notional value at risk on this leg). For futures =
    margin posted; for spot+borrow = collateral net of debt; for sports =
    stake. Sourced from PBM per-leg snapshot."""
    requires_cash_sweep: bool = Field(
        description=(
            "True if this leg's actual_leverage drifted by > rebalance_trigger_bps. "
            "Controller will emit a TRANSFER+TRADE instruction set covering this leg."
        ),
    )


__all__ = [
    "CashSweepPolicy",
    "LegDrift",
    "LegPortfolioState",
    "LegSizingStrategy",
    "LeveragedLeg",
]
