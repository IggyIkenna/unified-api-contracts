"""Schemas for the recursive-loop orchestrator (Family 1 + Family 2 archetypes).

Consumed by ``execution-service.defi_execution.orchestrators.recursive_loop_orchestrator``
to open / unwind recursive supply-borrow positions atomically (flash mode) or iteratively
(persistent mode). Both Family 1 (``CARRY_RECURSIVE_BORROW_LENDING_ONLY``) and Family 2
(``CARRY_BASIS_PERP_INV``) consume these schemas; Family 2 attaches an
optional ``perp_leg_config`` per the delta-hedge topology.

Plan:
``unified-trading-pm/plans/active/defi_recursive_borrow_archetypes_2026_05_10.md``
Phase 5 — RecursiveLoopOrchestrator.

Schema provenance: schemas live here (UAC-internal) per CLAUDE.md "Schema provenance"
HARD RULE — execution-service consumes via import; no local re-declaration.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OpeningMode(StrEnum):
    """Whether to open the recursive loop iteratively or atomically."""

    PERSISTENT = "PERSISTENT"
    """N sequential supply→borrow→swap→supply iterations on-chain. No flash-loan
    premium; gas-bound; pre-iter HF gate aborts mid-loop on adverse moves. Default
    for ``base_capital < 5 ETH`` (gas crossover) or any chain where Aave flash-loan
    liquidity is thin."""

    FLASH = "FLASH"
    """Single tx via ``RecursiveLeverageReceiver.sol`` (Phase 4). Atomic; 5 bps
    Aave V3 flash-loan premium; no mid-iter HF risk. Default for
    ``base_capital >= 5 ETH`` on Ethereum / Base mainnet."""


class LendingProtocol(StrEnum):
    """Lending venue for the recursive loop's collateral + debt legs."""

    AAVE_V3 = "AAVE_V3"
    """Aave V3 — May-23 P0 across Ethereum / Base (Arbitrum if scope expands)."""

    SPARK = "SPARK"
    """SparkLend (Aave V3 fork) — Ethereum only; same ReserveParams shape."""

    MORPHO_BLUE = "MORPHO_BLUE"
    """Morpho Blue — per-market isolated; LLTV varies per (collateral, debt, oracle)."""

    COMPOUND_V3 = "COMPOUND_V3"
    """Compound V3 — per-(chain, market) base-asset model."""


class PerpVenueId(StrEnum):
    """Perp hedge venue for Family 2 cells (USDC-margined only)."""

    HYPERLIQUID = "HYPERLIQUID"
    """Hyperliquid L1 DEX perp — PRIMARY for May-23; 1h funding cadence; EIP-712 auth."""

    BYBIT = "BYBIT"
    """Bybit CeFi USDC-margin perp — SECONDARY for May-23; 8h funding cadence; HMAC auth;
    counterparty-cap <=50% of HYPERLIQUID for first 30d post-cutover (Feb-2025 hack)."""


class PerpLegConfig(BaseModel):
    """Family 2 perp leg config (None on Family 1 cells)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    perp_venue: PerpVenueId
    perp_pair: str = Field(..., description="e.g. 'ETH-PERP' on HL, 'ETHUSDT-PERP' on Bybit.")
    target_net_delta: Decimal = Field(
        ...,
        description=(
            "Net delta target in units of share-class coin. 0 = pure carry; +N = hold N "
            "long; -N = short N overlay. Family 2 sizes perp_short = max(0, E_actual - "
            "target_net_delta)."
        ),
    )
    usdc_margin_buffer_min_pct: Decimal = Field(
        Decimal("0.30"),
        description=(
            "Minimum USDC margin sitting at the venue as fraction of perp notional. "
            "Default 0.30 = 3x initial margin at 10x leverage; auto-topup trigger at "
            "available_margin/initial_margin < 1.5."
        ),
    )


class RecursiveLoopRequest(BaseModel):
    """Input to ``RecursiveLoopOrchestrator.open()`` or ``.unwind()``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: str = Field(
        ...,
        description=(
            "32-byte hex (bytes32-encodable) correlation_id; threaded into receiver "
            "contract `params` AND all Python-side LOOP_* events for end-to-end "
            "event-stream tracing per CLAUDE.md no-fire-and-forget rule."
        ),
    )
    start_amount: Decimal = Field(..., gt=0, description="Base capital, human-readable units.")
    share_class_coin: str = Field(..., description="'ETH' | 'WSTETH' | 'BTC' | 'WBTC' | 'SOL' | 'USDC'.")
    n_loops: int = Field(..., ge=1, le=15, description="Recursion depth.")
    ltv_per_loop: Decimal = Field(
        ...,
        gt=0,
        lt=1,
        description=(
            "Per-loop LTV. Must be < liquidation_threshold - safety_buffer "
            "(0.05 default) — orchestrator pre-iter HF gate enforces."
        ),
    )
    slippage_tolerance_bps: int = Field(
        50, ge=0, le=500, description="Per-swap slippage tolerance for cross-asset loops."
    )
    gas_buffer: Decimal = Field(
        Decimal("1.20"),
        description=(
            "Multiplier on per-iter gas estimate. Persistent driver halts mid-loop if "
            "cumulative gas exceeds gas_buffer x eth_balance_wei / current_gas_price."
        ),
    )
    opening_mode: OpeningMode
    chain: Literal["ETHEREUM", "ARBITRUM", "BASE", "OPTIMISM"]
    lending_protocol: LendingProtocol
    collateral_asset: str = Field(..., description="Asset symbol (e.g. 'WSTETH').")
    debt_asset: str = Field(..., description="Asset symbol (e.g. 'WETH').")
    perp_leg_config: PerpLegConfig | None = Field(
        None,
        description="Family 2 perp leg config; None for Family 1 (lending-only) cells.",
    )


class AavePositionState(BaseModel):
    """Snapshot of Aave position post-iter (from ``getUserAccountData``)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_collateral_eth: Decimal
    total_debt_eth: Decimal
    health_factor: Decimal = Field(..., description="HF = sum(coll_i x lt_i) / total_debt.")
    ltv: Decimal
    available_borrows_eth: Decimal


class LoopIterEvent(BaseModel):
    """Per-iter event for batch-vs-live reconciliation + replay."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    iter_idx: int
    mode: OpeningMode
    tx_hash: str | None = Field(None, description="None for failed-pre-tx aborts.")
    gas_used: int = 0
    a_token_balance_post: Decimal | None = None
    debt_post: Decimal | None = None
    hf_pre_iter: Decimal | None = None
    hf_post: Decimal | None = None
    slippage_observed_bps: int | None = None
    event_kind: Literal[
        "LOOP_ITER_STARTED",
        "LOOP_ITER_COMPLETED",
        "LOOP_ABORTED_HF_LOW",
    ]


class RecursiveLoopResult(BaseModel):
    """Output from ``RecursiveLoopOrchestrator.open()`` / ``.unwind()``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: str
    success: bool
    mode: OpeningMode
    direction: Literal["OPEN", "UNWIND"]
    tx_receipts_count: int = Field(..., description="N for persistent; 1 for flash. Receipts in event stream.")
    final_position: AavePositionState
    realised_supply_apy: Decimal
    realised_borrow_apy: Decimal
    total_gas_used: int
    total_gas_cost_usd: Decimal
    flash_premium_paid: Decimal = Field(
        Decimal("0"), description="0 for persistent; >=0 for flash (5 bps Aave V3 premium)."
    )
    per_iter_events: tuple[LoopIterEvent, ...] = Field(
        ..., description="Closed-set event taxonomy per CLAUDE.md no-fire-and-forget rule."
    )
    error_code: str | None = Field(
        None,
        description=(
            "DefiErrorCode StrEnum value if !success. Closed set: "
            "RECURSIVE_LOOP_ABORTED_HF / _GAS_BUDGET_EXCEEDED / _SLIPPAGE_REVERT / "
            "_FLASH_RECEIVER_NOT_FOUND / _FLASH_REPAYMENT_INSUFFICIENT / "
            "_FLASH_ACTION_FAILED_<idx> / _PARTIAL_OPEN_NO_UNWIND_FUNDS."
        ),
    )


__all__ = [
    "AavePositionState",
    "LendingProtocol",
    "LoopIterEvent",
    "OpeningMode",
    "PerpLegConfig",
    "PerpVenueId",
    "RecursiveLoopRequest",
    "RecursiveLoopResult",
]
