"""Schemas for the perp hedge sizer (Family 2 archetype delta-hedge controller).

Consumed by ``execution-service.defi_execution.helpers.perp_hedge_sizer`` to compute
rebalance instructions + USDC margin top-up triggers for Family 2 cells.

Plan:
``unified-trading-pm/plans/active/defi_recursive_borrow_archetypes_2026_05_10.md``
Phase 7 — PerpHedgeSizer + USDC margin top-up automation.

Schema provenance: schemas live here (UAC-internal) per CLAUDE.md "Schema provenance"
HARD RULE — execution-service consumes via import; no local re-declaration.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.recursive_loop_orchestrator import (
    PerpVenueId,
)


class RebalanceAction(StrEnum):
    """Closed set of PerpHedgeSizer decisions."""

    SHORT = "SHORT"
    """Increase perp short to track target_net_delta."""

    COVER = "COVER"
    """Reduce perp short (buy-back) to track target_net_delta."""

    NOOP = "NOOP"
    """Drift within band; no rebalance needed."""


class RebalanceReason(StrEnum):
    """Why a rebalance fired (drives downstream attribution + alerting)."""

    DRIFT_BAND_BREACH = "DRIFT_BAND_BREACH"
    """|perp_short_size - E_actual| > rebalance_band_pct x E_actual."""

    ORACLE_RATE_MOVE = "ORACLE_RATE_MOVE"
    """cbETH/ETH or wstETH/ETH oracle rate moved > 1% intra-day."""

    FUNDING_REGIME_SHIFT = "FUNDING_REGIME_SHIFT"
    """Phase 7.5 adaptive sizing: 30d-avg funding crossed threshold."""

    TARGET_DELTA_CHANGE = "TARGET_DELTA_CHANGE"
    """Operator changed target_net_delta via config."""


class TopupSource(StrEnum):
    """Where USDC margin top-up draws from."""

    TREASURY_HOT = "TREASURY_HOT"
    """Pre-funded treasury hot wallet (testnet + early-mainnet)."""

    COPPER_MPC = "COPPER_MPC"
    """Copper MPC custody bridge (mainnet; gated on Group F item 19)."""

    CEFFU_MPC = "CEFFU_MPC"
    """CEFFU MPC custody bridge (mainnet; alternative to Copper)."""


class HedgeSizerConfig(BaseModel):
    """Per-cell PerpHedgeSizer config."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_net_delta_eth: Decimal = Field(
        ..., description="Net delta target in ETH units (0 for pure carry; +N long; -N short)."
    )
    usdc_margin_buffer_min: Decimal = Field(
        Decimal("1.5"),
        description=(
            "Minimum (available_margin / initial_margin) ratio before top-up fires. "
            "Default 1.5 = ~30% price-move headroom at 10x leverage."
        ),
    )
    auto_topup_threshold: Decimal = Field(
        Decimal("1.5"),
        description=(
            "Target ratio post-top-up. Top-up amount = "
            "(auto_topup_threshold x initial_margin) - available_margin."
        ),
    )
    rebalance_band_pct: Decimal = Field(
        Decimal("0.05"),
        description=(
            "Drift band as fraction of E_actual. Rebalance fires when "
            "|perp_short_size - target_perp_size| > rebalance_band_pct x E_actual."
        ),
    )
    initial_margin_fraction: Decimal = Field(
        Decimal("0.10"),
        description=(
            "Initial margin as fraction of perp notional. 0.10 = 10x leverage default "
            "on Hyperliquid + Bybit (tighter than 50x max for safety buffer)."
        ),
    )


class RebalanceInstruction(BaseModel):
    """Output from ``PerpHedgeSizer.compute_rebalance()``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    perp_venue: PerpVenueId
    perp_pair: str
    action: RebalanceAction
    reason: RebalanceReason
    size_delta_eth: Decimal = Field(
        ..., description="Absolute size delta in ETH (always positive; sign from `action`)."
    )
    target_perp_size: Decimal
    current_perp_size: Decimal
    e_actual: Decimal = Field(
        ..., description="Live net ETH-equivalent exposure read from Aave getUserAccountData x er."
    )
    target_net_delta: Decimal
    correlation_id: str


class MarginTopupInstruction(BaseModel):
    """Output from ``PerpHedgeSizer.compute_margin_topup()`` (or None if within buffer)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    perp_venue: PerpVenueId
    amount_usdc: Decimal
    source: TopupSource
    bridge_eta_seconds: int = Field(
        ...,
        description=(
            "Expected bridge latency: HL Arbitrum-bridge ~10s; Bybit USDC deposit "
            "1-5min depending on source chain (prefer Arbitrum-route for cost+speed)."
        ),
    )
    pending_until_ts: int | None = Field(
        None,
        description=(
            "For withdrawals only: 5-min dispute window on Hyperliquid. None for deposits."
        ),
    )
    correlation_id: str


__all__ = [
    "HedgeSizerConfig",
    "MarginTopupInstruction",
    "RebalanceAction",
    "RebalanceInstruction",
    "RebalanceReason",
    "TopupSource",
]
