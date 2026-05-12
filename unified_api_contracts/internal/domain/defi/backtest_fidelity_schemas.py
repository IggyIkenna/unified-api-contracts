"""Schemas for ``defi_simulation_realism_2026_05_10`` Phase 8 (backtest fidelity validation).

Phase 8A — ``BacktestFidelityReport`` (per-archetype 1-year replay; pre vs
post simulation-realism delta + per-leg attribution + max-drawdown delta).
Phase 8C — ``TenderlyReconciliationReport`` (live-vs-simulated reconciliation
across 1 day of paper-trade; per-tick |delta| < 10bps acceptance gate at the
95% coverage threshold; per-pool-shape failure-mode breakdown).
Phase 8D — ``SignOffReport`` (operator dashboard composite — aggregate signal
GREEN/YELLOW/RED + sign-off status persisted by ``pnl-attribution-service`` as
the May-23 cutover gate audit row).

Consumed by ``execution-service/tests/integration/backtest_fidelity/`` harness
scripts (Phase 8A/B carry + leveraged-funding-arb replays, Phase 8C Tenderly
reconciliation, Phase 8D ``compose_sign_off_report`` operator dashboard
composer) and rendered by ``deployment-ui`` as the Phase-8 dashboard tile.

SSOT: ``codex/04-architecture/amm-slippage-simulation.md`` § "Phase 8
validation framework".
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------
# Phase 8A/8B — Backtest fidelity report (per-archetype 1-year replay)
# ----------------------------------------------------------------------------


class PerLegAttribution(BaseModel):
    """Per-leg P&L attribution for a backtest archetype replay.

    Each archetype has multiple legs (e.g. ``carry_staked_basis`` has
    ``stake_long`` + ``perp_short`` legs; ``leveraged_funding_arb`` has
    ``perp_long`` + ``lending_borrow`` legs). The fidelity report breaks down
    the delta by leg so the operator can see which simulation primitive (per-
    shape AMM matcher / rate-impact / dynamic-hedge / yield-stream) is
    driving the bias-reduction.
    """

    leg_id: str  # archetype-specific leg identifier (e.g. "stake_long", "perp_short", "lending_borrow")
    leg_kind: str  # closed-set: "amm_swap" / "perp_position" / "lending_supply" / "lending_borrow" / "stake" / "restake"  # noqa: E501
    old_pnl_usdc: Decimal  # leg P&L under old (pre-2026-05-10) matching engine
    new_pnl_usdc: Decimal  # leg P&L under new (post Phase 2-7) matching engine
    delta_bps: Decimal  # signed bps delta vs old_pnl absolute value (negative = new is lower / more conservative)


class BacktestFidelityReport(BaseModel):
    """Per-archetype 1-year replay comparing pre-2026-05-10 vs post-Phase-2-7 matching engine.

    Phase 8A/8B output. ``run_carry_archetype_replay.py`` produces one row for
    ``carry_staked_basis``; ``run_leveraged_funding_arb_replay.py`` produces
    one for ``leveraged_funding_arb``. Both feed ``compose_sign_off_report.py``
    (Phase 8D) for the operator gate.

    Acceptance direction: ``delta_total_pnl_bps`` should be NEGATIVE
    (new engine reports lower P&L than old → expected because zero-impact + V2-
    only old engine over-estimated). A POSITIVE delta is a RED FLAG — surfaces
    a matcher correctness bug. The ``gate_pass`` property in ``SignOffReport``
    keys on this sign.

    Capture: harness writes a JSON snapshot at
    ``execution-service/tests/integration/backtest_fidelity/reports/{archetype}_{run_id}.json``
    """

    archetype: str  # "carry_staked_basis" / "leveraged_funding_arb"
    run_id: str  # ISO 8601 timestamp + harness git sha — keyed for replay
    generated_at: datetime
    lookback_days: int = Field(default=365, ge=30)  # ≥30 days required for meaningful stats
    n_trades: int  # number of historical trades replayed
    old_pnl_total_usdc: Decimal  # sum of P&L per-trade under old engine
    new_pnl_total_usdc: Decimal  # sum of P&L per-trade under new engine
    delta_total_pnl_bps: Decimal  # (new - old) / sum(|old|) * 10_000; NEGATIVE = expected direction
    old_pnl_std_usdc: Decimal  # stddev of per-trade P&L (old engine — more optimistic = lower realized variance)
    new_pnl_std_usdc: Decimal  # stddev of per-trade P&L (new engine — fuller fidelity, may be higher variance)
    bias_reduction_pct: Decimal  # (old_pnl_std - new_pnl_std) / old_pnl_std * 100
    max_drawdown_old_usdc: Decimal
    max_drawdown_new_usdc: Decimal
    max_drawdown_delta_pct: Decimal  # (new - old) / |old| * 100
    per_leg_breakdown: list[PerLegAttribution] = Field(default_factory=list)


# ----------------------------------------------------------------------------
# Phase 8C — Tenderly reconciliation report (live vs simulated)
# ----------------------------------------------------------------------------


class PerPoolShapeReconciliation(BaseModel):
    """Per-PoolShape breakdown of Tenderly-fork reconciliation drift.

    The Phase 8C harness records per-tick |delta_bps| keyed by ``pool_shape``
    so the operator can identify WHICH matcher (V3 / Curve / Solidly-fork /
    Solana CLMM / aggregator route / etc.) is drifting if the global gate
    fails. ``pool_shape`` is the string value of UAC's ``PoolShape`` StrEnum.
    """

    pool_shape: str  # UAC PoolShape value (e.g. "UNISWAP_V3", "CURVE_STABLE", "SOLIDLY_FORK")
    n_ticks: int
    within_tolerance_count: int  # ticks with |delta_bps| < tolerance_bps
    within_tolerance_pct: Decimal
    median_delta_bps: Decimal
    p95_delta_bps: Decimal
    max_delta_bps: Decimal  # surfaces the worst-case mismatch for triage


class TenderlyReconciliationReport(BaseModel):
    """Live-vs-simulated tick-by-tick reconciliation report from a Tenderly fork comparison.

    Phase 8C output. ``run_tenderly_live_reconciliation.py`` reads the
    paper-trade log over ``paper_trade_window_hours`` (default 24h) and
    re-simulates each fill via a Tenderly fork at the same block; the per-
    tick |delta_bps| is gated at ``tolerance_bps`` (10 bps default) with
    coverage ≥ ``coverage_threshold_pct`` (95% default) for ``pass_phase_8c_gate``.

    Tenderly fork budget: ~10c per fork x 5000 ticks/day = ~$500/day during
    Phase 8 validation runs; the harness deletes each fork immediately after
    the simulated fill is collected.

    Capture: harness writes a JSON snapshot at
    ``execution-service/tests/integration/backtest_fidelity/reports/tenderly_recon_{run_id}.json``.
    """

    run_id: str  # ISO 8601 timestamp + harness git sha
    generated_at: datetime
    paper_trade_window_hours: int = Field(default=24, ge=1)
    tolerance_bps: Decimal = Field(default=Decimal("10"))
    coverage_threshold_pct: Decimal = Field(default=Decimal("95"))
    n_ticks: int
    within_tolerance_count: int
    within_tolerance_pct: Decimal  # acceptance gate: >= coverage_threshold_pct
    median_delta_bps: Decimal
    p95_delta_bps: Decimal
    max_delta_bps: Decimal
    pass_phase_8c_gate: bool  # within_tolerance_pct >= coverage_threshold_pct
    per_pool_shape_breakdown: list[PerPoolShapeReconciliation] = Field(default_factory=list)


# ----------------------------------------------------------------------------
# Phase 8D — Sign-off report (operator dashboard composite)
# ----------------------------------------------------------------------------


class AggregateSignal(StrEnum):
    """Closed-set aggregate-pass signal for the May-23 cutover gate."""

    GREEN = "GREEN"  # all 3 of Phase 8A/B/C pass — sign-off recommended
    YELLOW = "YELLOW"  # 2/3 pass — operator review with risk-aware notes
    RED = "RED"  # ≤ 1/3 pass — sign-off blocked


class OperatorSignOffStatus(StrEnum):
    """Closed-set operator sign-off lifecycle."""

    PENDING = "PENDING"  # report generated; operator has not yet reviewed
    APPROVED = "APPROVED"  # operator clicked APPROVE in deployment-ui
    REJECTED = "REJECTED"  # operator clicked REJECT in deployment-ui


class SignOffReport(BaseModel):
    """Operator dashboard composite for the Phase 8D May-23 cutover gate.

    Phase 8D output. ``compose_sign_off_report.py`` composes Phase 8A
    (``carry_staked_basis`` replay) + Phase 8B (``leveraged_funding_arb``
    replay) + Phase 8C (Tenderly reconciliation) into a single audit row.

    The ``deployment-ui`` Phase-8 tile renders this report; the operator clicks
    APPROVE / REJECT + types notes. The completed report is persisted to
    ``pnl-attribution-service`` as a one-off audit row keyed by ``plan_version``.

    Gate semantics in ``gate_pass_summary``:

    - ``carry_replay_pass`` = Phase 8A delta_total_pnl_bps < 0 (new engine more conservative)
    - ``leveraged_replay_pass`` = Phase 8B delta_total_pnl_bps < 0
    - ``tenderly_reconciliation_pass`` = Phase 8C pass_phase_8c_gate

    Cross-reference: master plan Group F item 17 (paper-trade smoke) + item 18
    (batch-vs-live recon) reference this report for cutover sign-off.
    """

    plan_version: str  # plan-of-record version (e.g. "defi_simulation_realism_2026_05_10_v1.0")
    generated_at: datetime
    phase_8a_carry: BacktestFidelityReport
    phase_8b_leveraged: BacktestFidelityReport
    phase_8c_tenderly: TenderlyReconciliationReport
    aggregate_signal: AggregateSignal
    operator_sign_off_status: OperatorSignOffStatus = OperatorSignOffStatus.PENDING
    operator_sign_off_at: datetime | None = None
    operator_sign_off_notes: str = ""

    @property
    def gate_pass_summary(self) -> dict[str, bool]:
        """Per-phase gate pass map — drives ``aggregate_signal`` composition."""
        return {
            "carry_replay_pass": self.phase_8a_carry.delta_total_pnl_bps < Decimal("0"),
            "leveraged_replay_pass": self.phase_8b_leveraged.delta_total_pnl_bps < Decimal("0"),
            "tenderly_reconciliation_pass": self.phase_8c_tenderly.pass_phase_8c_gate,
        }


def compute_aggregate_signal(gate_pass_summary: dict[str, bool]) -> AggregateSignal:
    """Compose ``AggregateSignal`` from the 3-element gate-pass map.

    Rules (per codex § "Phase 8 validation framework"):

    - 3/3 pass → ``GREEN`` (sign-off recommended)
    - 2/3 pass → ``YELLOW`` (operator review with risk-aware notes)
    - ≤ 1/3 pass → ``RED`` (sign-off blocked; investigation required)
    """
    n_pass = sum(1 for v in gate_pass_summary.values() if v)
    if n_pass == 3:
        return AggregateSignal.GREEN
    if n_pass == 2:
        return AggregateSignal.YELLOW
    return AggregateSignal.RED
