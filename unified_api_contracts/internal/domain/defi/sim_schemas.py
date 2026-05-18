"""Schemas for ``defi_simulation_realism_2026_05_10`` Phases 1C-1F.

Phase 1C — ``GovernanceProposal`` (capture adapter for Aave V3 / Compound V3 /
Spark / Lido governance proposals; consumed by Phase 4B
``GovernanceProposalSimulator``).
Phase 1D — ``StakingYieldDecomposition`` (per-LST/LRT forward yield breakdown
into native + restaking-AVS + LRT-protocol-fee + seasonal-points layers;
consumed by Phase 5E composite simulator).
Phase 1E — ``SlashingEvent`` (per-validator slashing capture; consumed by
Phase 7B ``SlashingTailRiskMC`` calibration).
Phase 1F — ``HedgeRatioSnapshot`` (carry-archetype hedge ratio state with
peg drift; consumed by Phase 6B dynamic hedge-ratio adjustment in
``staked_basis.py``).

SSOT: ``codex/04-architecture/amm-slippage-simulation.md``.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------
# Phase 1C — Governance proposal
# ----------------------------------------------------------------------------


class GovernanceProposalStatus(StrEnum):
    """Lifecycle states for a governance proposal (closed set)."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PASSED = "PASSED"
    FAILED = "FAILED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class GovernanceProposal(BaseModel):
    """Captured governance proposal across Aave V3 / Compound V3 / Spark / Lido.

    Capture path: MTDS ``governance_adapter`` (Phase 4A — NEW) reads on-chain
    Governor events via subgraph + Snapshot off-chain proposals API; writes to
    ``governance_proposals`` data_type. Simulator (Phase 4B) consumes this
    schema + a Tenderly fork to measure per-asset before/after parameter delta.
    """

    proposal_id: str  # 32-byte hex or numeric ID per protocol convention
    protocol: str  # AAVE_V3 / COMPOUND_V3 / SPARK / LIDO / UNISWAP
    chain: str  # ethereum / arbitrum / optimism / polygon / base / gnosis
    governor_address: str  # contract address of the Governor that owns this proposal
    proposer: str
    created_at: datetime
    voting_start: datetime
    voting_end: datetime
    executed_at: datetime | None = None
    status: GovernanceProposalStatus
    payload_targets: list[str] = Field(default_factory=list)  # contract addresses called
    payload_calldatas: list[str] = Field(default_factory=list)  # hex-encoded calldatas
    executor_address: str | None = None  # who/what calls execute(); usually timelock
    snapshot_proposal_id: str | None = None  # paired off-chain Snapshot proposal if any


# ----------------------------------------------------------------------------
# Phase 1D — Staking yield decomposition
# ----------------------------------------------------------------------------


class AVSRewardComponent(BaseModel):
    """Per-AVS reward component layered on top of native staking base."""

    avs_name: str  # EIGENLAYER / SYMBIOTIC / KARAK / JITO_RESTAKING / ...
    operator_allocation_share: Decimal  # 0..1 — fraction of LRT's stake routed through this AVS
    expected_apr: Decimal  # forward distribution mean
    apr_p5: Decimal  # 5th percentile
    apr_p95: Decimal  # 95th percentile


class StakingYieldDecomposition(BaseModel):
    """Forward-yield decomposition for an LST or LRT instrument.

    Phase 5E composite simulator produces this for ``carry_staked_basis`` PnL
    projection. The four layers convolve into a single ``ForwardYieldDistribution``
    that downstream consumers integrate over the trade horizon.

    Fields are forward-looking distributions (not point estimates). When
    ``risk_simulations_limits_alerting`` consumes this for scenario coverage it
    samples from these layers independently and convolves.
    """

    lst_or_lrt_symbol: str  # weETH / ezETH / jitoSOL / pufETH / rsETH / ...
    chain: str  # ethereum / solana
    horizon_epochs: int  # forward horizon in chain-native epochs
    as_of: datetime

    # Layer 1 — native staking (consensus + execution rewards)
    native_staking_apr: Decimal
    native_staking_apr_p5: Decimal
    native_staking_apr_p95: Decimal

    # Layer 1b — MEV / block-builder tips (ETH execution layer) or validator MEV (Solana)
    mev_apr: Decimal

    # Layer 2 — restaking AVS rewards (per AVS, optional)
    restaking_avs_components: list[AVSRewardComponent] = Field(default_factory=list)

    # Layer 3 — LRT protocol fee (negative — reduces realised yield)
    lrt_protocol_fee_bps: Decimal

    # Layer 4 — seasonal points (off-chain reward; nullable when protocol has no programme)
    seasonal_points_implied_apr: Decimal | None = None
    seasonal_points_discount_factor: Decimal | None = None  # operator-tuned, 0..1


# ----------------------------------------------------------------------------
# Phase 1E — Slashing event
# ----------------------------------------------------------------------------


class SlashingReason(StrEnum):
    """Closed set of slashing-reason codes across Ethereum + Solana."""

    # Ethereum beacon
    PROPOSER_SLASHING = "PROPOSER_SLASHING"
    ATTESTER_SLASHING = "ATTESTER_SLASHING"
    SURROUND_VOTE = "SURROUND_VOTE"
    DOUBLE_PROPOSE = "DOUBLE_PROPOSE"
    # Solana
    DOWNTIME = "DOWNTIME"
    DOUBLE_SIGN = "DOUBLE_SIGN"
    NETWORK_PARTITION = "NETWORK_PARTITION"
    # Generic
    OTHER = "OTHER"


class SlashingEvent(BaseModel):
    """One slashing event captured from on-chain history.

    Phase 1E schema. Captured by MTDS ``slashing_events_adapter`` per the
    capture table in codex § "Per-chain slashing event capture". Consumed by
    Phase 7A ``SlashingTailRiskMC.calibrate`` to fit per-chain slashing-rate
    distributions for the Monte Carlo simulator.
    """

    chain: str  # ethereum / solana
    validator_id: str  # 0x...pubkey on Ethereum; validator vote-account address on Solana
    slashed_at_epoch: int
    slashed_at_slot: int | None = None  # Ethereum-only (slot within epoch)
    slashed_amount_native: Decimal  # ETH or SOL units
    slashing_reason: SlashingReason
    slasher_validator_id: str | None = None  # Ethereum-only — who reported the slashing
    evidence_block_hash: str | None = None
    captured_at: datetime


# ----------------------------------------------------------------------------
# Phase 1F — Hedge ratio snapshot
# ----------------------------------------------------------------------------


class HedgeRatioSnapshot(BaseModel):
    """Carry-archetype hedge ratio state at a point in time.

    Phase 1F schema. Produced by Phase 6B ``_compute_dynamic_hedge_ratio`` in
    ``staked_basis.py``; persisted at every rebalance event for audit + later
    Phase 6C backtest comparison (dynamic vs static hedge realised P&L).
    Consumed by position-balance-monitor for delta-neutral verification.
    """

    archetype: str  # carry_staked_basis / leveraged_funding_arb
    instrument_long: str  # the LST/LRT leg (jitoSOL / weETH / ...)
    instrument_short: str  # the perp instrument hedging the long
    target_ratio: Decimal  # what the dynamic hedge calculator wants right now
    realized_ratio: Decimal  # what's actually deployed (may differ pre-rebalance)
    peg_drift_bps: Decimal  # current peg drift from last rebalance baseline
    peg_drift_threshold_bps: Decimal  # archetype-config rebalance trigger threshold
    last_adjustment_at: datetime | None = None  # null for initial entry
    rebalance_triggered: bool = False
    captured_at: datetime


class HedgeRatioSnapshotRecord(HedgeRatioSnapshot):
    """On-disk parquet shape for ``hedge_ratio_snapshot`` data_type.

    Extends :class:`HedgeRatioSnapshot` with the three standard parquet
    columns required by the manifest + availability-at SSOT:

    * ``partition_dt`` — date partition (``YYYY-MM-DD`` string; equals
      ``captured_at.date()`` at write time — drives GCS hive path
      ``dt={partition_dt}``).
    * ``available_at`` — per-row write-time stamp per the workspace
      ``fetch_completed_at`` semantic registered in
      ``availability_semantics.AVAILABILITY_AT_SEMANTICS``
      ``("defi", "hedge_ratio_snapshot")``.
    * ``correlation_id`` — propagated from the trade context for cross-service
      audit joins.

    Phase 0 design decision (hedge_ratio_snapshot_persistence_2026_05_13):
    * Bucket kind: ``strategy-store`` / ``defi`` asset_group (reuses existing
      bucket; no new bucket needed — cardinality / retention are identical).
    * Writer pattern: inline (Pattern A) for both batch + live; rebalance
      events are infrequent (~25 bps drift threshold) so I/O latency is not
      a concern and Pattern A is simpler with identical code path per
      batch=live SSOT.
    """

    partition_dt: str  # YYYY-MM-DD — hive partition key
    available_at: datetime  # write-time stamp (fetch_completed_at semantic)
    correlation_id: str | None = None  # trade-context correlation for audit joins


# ----------------------------------------------------------------------------
# Phase 5 — Strategy decision context (every tick, pre-decision inputs)
# ----------------------------------------------------------------------------


class StrategyDecisionContext(BaseModel):
    """Pre-decision input snapshot emitted on EVERY engine tick.

    Phase 5 schema. Produced by CarryStakedBasisEngine.on_tick before
    the rebalance gate — captures the APY/funding inputs and decision reason
    so non-rebalance ticks are auditable (distinguishes carry-unfavorable from
    config-bug from feature-stale).

    SSOT: ``hedge_ratio_snapshot_persistence_2026_05_13.md`` Phase 5.
    """

    archetype: str  # carry_staked_basis / leveraged_funding_arb
    instrument_long: str
    instrument_short: str
    stake_apy_bps: Decimal
    borrow_apy_bps: Decimal
    perp_funding_apy_bps: Decimal
    usdc_idle_apy_bps: Decimal
    computed_net_apr_bps: Decimal
    peg_drift_observed_bps: Decimal
    peg_drift_threshold_bps: Decimal
    # OPEN | HOLD_CARRY_UNFAVORABLE | HOLD_WITHIN_DRIFT | HOLD_FEATURE_STALE
    # | HOLD_POSITION_OPTIMAL | CLOSE_BASIS_INVERTED | REBALANCE
    decision_outcome: str
    decision_reason_detail: str | None = None
    position_state_long_units: Decimal = Decimal("0")
    position_state_short_units: Decimal = Decimal("0")
    captured_at: datetime


class StrategyDecisionContextRecord(StrategyDecisionContext):
    """On-disk parquet shape for ``strategy_decision_context`` data_type.

    Extends :class:`StrategyDecisionContext` with standard parquet columns
    (partition_dt / available_at / correlation_id). Mirrors
    :class:`HedgeRatioSnapshotRecord` pattern.

    Phase 5 design decision (hedge_ratio_snapshot_persistence_2026_05_13):
    * Bucket kind: ``strategy-store`` / ``defi`` asset_group.
    * Writer pattern: inline (Pattern A) on EVERY tick — 1-hour cadence
      makes per-row I/O cost acceptable.
    * Availability semantic: ``fetch_completed_at`` (write-time stamp; mirrors
      hedge_ratio_snapshot per AVAILABILITY_AT_SEMANTICS registry).
    """

    partition_dt: str  # YYYY-MM-DD — hive partition key
    available_at: datetime  # write-time stamp (fetch_completed_at semantic)
    correlation_id: str | None = None  # trade-context correlation for audit joins
