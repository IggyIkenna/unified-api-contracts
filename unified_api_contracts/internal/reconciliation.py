"""Reconciliation resolution schemas — cross-service contract.

Used by strategy-service/position and batch-live-reconciliation-service
to persist break resolutions and by the UI reporting API to submit operator
decisions.

Includes:
- Resolution workflow types (ReconciliationAction, ReconciliationResolution)
- Deviation lifecycle state machine (DeviationState, DeviationStatus, DeviationType)
- Balance reconciliation snapshots (BalanceReconciliationSnapshot, BalanceReconciliationStatus)
- PnL reconciliation snapshots (PnLReconciliationSnapshot)
- Auto-reconciliation reasons (AutoReconcileReason)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Resolution workflow
# ---------------------------------------------------------------------------


class ReconciliationAction(StrEnum):
    """Operator action on a reconciliation break."""

    ACCEPT = "accept"
    """Expected divergence (timing, rounding) — no correction needed."""

    REJECT = "reject"
    """Error requiring correction — triggers book-correction flow."""

    INVESTIGATE = "investigate"
    """Needs further analysis before resolution."""


class ReconciliationResolution(BaseModel):
    """Operator resolution of a reconciliation break.

    Persisted to the audit log for FCA compliance. When action is REJECT,
    the correcting_instruction_id links to the manual booking that corrects
    the break.
    """

    break_id: str
    action: ReconciliationAction
    note: str = Field(min_length=10)
    resolved_by: str
    correcting_instruction_id: str | None = None


# ---------------------------------------------------------------------------
# Auto-reconciliation reasons
# ---------------------------------------------------------------------------


class AutoReconcileReason(StrEnum):
    """Reason why a deviation was automatically reconciled without human action."""

    FEE_ROUNDING = "fee_rounding"
    """Exchange fee rounding difference below threshold."""

    MARGIN_INTEREST = "margin_interest"
    """Margin interest accrual difference below threshold."""

    EXCHANGE_FEE_ADJUSTMENT = "exchange_fee_adjustment"
    """Exchange-side fee adjustment (rebate, tier change)."""

    TIMING_DIFFERENCE = "timing_difference"
    """Transient timing difference that resolved itself."""

    STAKING_REWARD = "staking_reward"
    """Staking reward accrual not yet reflected locally."""

    FUNDING_RATE_ACCRUAL = "funding_rate_accrual"
    """Funding rate payment accrual difference."""


# ---------------------------------------------------------------------------
# Deviation lifecycle state machine
# ---------------------------------------------------------------------------


class DeviationType(StrEnum):
    """Type of reconciliation deviation."""

    POSITION = "position"
    BALANCE = "balance"
    PNL = "pnl"


class DeviationStatus(StrEnum):
    """Lifecycle status of a deviation.

    Flow: TRANSIENT → CONFIRMED → (AUTO_RECONCILED | ESCALATED) → RESOLVED
    """

    TRANSIENT = "transient"
    """Deviation just detected; waiting for confirmation threshold."""

    CONFIRMED = "confirmed"
    """Deviation persisted beyond confirmation threshold (e.g. 30s)."""

    AUTO_RECONCILED = "auto_reconciled"
    """Small deviation auto-accepted (fee rounding, interest, etc.)."""

    ESCALATED = "escalated"
    """Large deviation sent to human attention."""

    RESOLVED = "resolved"
    """Human operator resolved via accept/reject/investigate."""


class DeviationState(BaseModel):
    """State of a single reconciliation deviation through its lifecycle.

    Tracks a discrepancy between internal and exchange values from first
    detection through confirmation, auto-reconciliation or escalation,
    to final resolution.
    """

    deviation_id: str
    instrument: str
    venue: str
    deviation_type: DeviationType
    internal_value: Decimal
    exchange_value: Decimal
    discrepancy: Decimal
    discrepancy_pct: Decimal
    first_seen: datetime
    last_seen: datetime
    confirmed_at: datetime | None = None
    status: DeviationStatus = DeviationStatus.TRANSIENT
    resolution: ReconciliationAction | None = None
    resolution_note: str | None = None
    resolved_by: str | None = None
    auto_reconcile_reason: AutoReconcileReason | None = None


# ---------------------------------------------------------------------------
# Balance reconciliation
# ---------------------------------------------------------------------------


class BalanceReconciliationStatus(StrEnum):
    """Classification of a balance reconciliation result."""

    MATCH = "match"
    DISCREPANCY = "discrepancy"
    CRITICAL = "critical"


class BalanceReconciliationSnapshot(BaseModel):
    """Result of comparing internal vs exchange balance for a single currency."""

    venue: str
    currency: str
    timestamp: datetime
    internal_free: Decimal
    internal_locked: Decimal
    internal_total: Decimal
    exchange_free: Decimal
    exchange_locked: Decimal
    exchange_total: Decimal
    discrepancy_free: Decimal
    discrepancy_locked: Decimal
    discrepancy_total: Decimal
    discrepancy_pct: Decimal
    status: BalanceReconciliationStatus


# ---------------------------------------------------------------------------
# PnL reconciliation
# ---------------------------------------------------------------------------


class PnLReconciliationSnapshot(BaseModel):
    """Result of comparing attributed PnL components vs exchange-reported PnL.

    The goal is to minimize unexplained_pnl (= exchange_pnl - component_pnl).
    A non-zero residual indicates missing attribution factors.
    """

    venue: str
    instrument: str
    timestamp: datetime
    component_pnl: Decimal = Field(description="Sum of all attributed PnL components")
    exchange_pnl: Decimal = Field(description="PnL as reported by exchange (balance change)")
    unexplained_pnl: Decimal = Field(description="exchange_pnl - component_pnl")
    unexplained_pct: Decimal = Field(description="unexplained_pnl / abs(exchange_pnl) if nonzero")
    components: dict[str, Decimal] = Field(
        default_factory=dict,
        description=("Breakdown by dimension: greeks, funding, interest, fees, basis, spread, delta, etc."),
    )
    ad_hoc_items: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Non-standard items: staking rewards, airdrops, rebates, etc.",
    )
    status: BalanceReconciliationStatus = Field(
        description="MATCH if unexplained_pct < threshold, else DISCREPANCY or CRITICAL",
    )


# ---------------------------------------------------------------------------
# 12-dimension reconciliation taxonomy + age-tracking mixin (added 2026-05-23)
# ---------------------------------------------------------------------------
#
# Implementation plan: ``plans/active/reconciliation_age_tracking_and_escalation_2026_05_23.md``.
# Codex SSOT: planned ``codex/04-architecture/reconciliation-age-tracking.md`` (stub via plan).


class ReconciliationDimension(StrEnum):
    """Closed set of 12 dimensions the batch-live-reconciliation-service tracks
    independently. Every reconciliation delta MUST tag its dimension so the
    audit + alerting routing can apply per-dimension thresholds + escalation.
    """

    ORDERS = "ORDERS"
    FILLS = "FILLS"
    POSITIONS = "POSITIONS"
    BALANCES = "BALANCES"
    FUNDING_PAYMENTS = "FUNDING_PAYMENTS"
    FEES = "FEES"
    TRANSFERS = "TRANSFERS"
    BORROW_LENDING_BALANCES = "BORROW_LENDING_BALANCES"
    COLLATERAL_BALANCES = "COLLATERAL_BALANCES"
    MARGIN_MODE_AND_LEVERAGE = "MARGIN_MODE_AND_LEVERAGE"
    STRATEGY_LEVEL_ALLOCATION = "STRATEGY_LEVEL_ALLOCATION"
    ACCOUNT_LEVEL_AGGREGATE = "ACCOUNT_LEVEL_AGGREGATE"


class ReconciliationAgeFields(BaseModel):
    """Age-tracking mixin for reconciliation delta rows.

    Populate at row-write time (NEVER at query time — ages would drift). Use
    via composition or inheritance from existing delta models. The alerting
    rule ``evaluate_dependency_health`` reads ``unreconciled_age_seconds`` to
    decide WARN / SEV1 / SEV0 escalation per the 15-min / 30-min thresholds
    from ``disaster_recovery.md`` §7.

    All datetime fields are tz-aware UTC.
    """

    first_seen_at: datetime
    """When this specific reconciliation delta was first observed by the
    reconciliation engine."""

    last_seen_at: datetime
    """Most recent observation of this delta (re-observed if it persists
    across reconciliation cycles)."""

    event_time: datetime | None = None
    """The event time the delta is about (may be earlier than first_seen_at
    if the engine catches up after a delay)."""

    venue_trade_time: datetime | None = None
    """The venue-reported trade/event time, for delta scope linked to a
    specific venue event."""

    internal_trade_time: datetime | None = None
    """The internal-system trade/event time."""

    last_successful_reconciliation_at: datetime | None = None
    """The most recent timestamp at which this dimension fully reconciled
    (used to compute "time since last green")."""

    unreconciled_age_seconds: int
    """Computed at write time as ``int((last_seen_at - first_seen_at).total_seconds())``.
    NOT computed at query time to avoid drift."""

    oldest_unreconciled_trade_age_seconds: int | None = None
    """Among unreconciled trades in this dimension, the oldest's age."""

    oldest_unreconciled_order_age_seconds: int | None = None

    oldest_unreconciled_position_age_seconds: int | None = None


# ---------------------------------------------------------------------------
# Citadel paper ⟷ batch ⟷ live determinism spine (2026-06-19)
#
# SSOT: codex/09-strategy/operational/paper-batch-live-reconciliation.md
# Plan: plans/active/citadel_paper_batch_live_reconciliation_2026_06_19.md
#
# The three trading modes are the same program. paper(W) MUST equal
# batch-rerun(W) trade-for-trade (same code + same inputs + same fill model);
# the only intentional divergence is real venue fills at the LIVE boundary. So
# paper↔batch reconciliation is a DETERMINISM PROOF (ε=0), not a tolerance
# check, and live↔paper is the execution-quality measurement.
# ---------------------------------------------------------------------------


class TradingMode(StrEnum):
    """Which of the three operational modes produced a run."""

    PAPER = "PAPER"
    BATCH = "BATCH"
    LIVE = "LIVE"


class FillModel(StrEnum):
    """The two — and ONLY two — fill realities.

    ``BENCHMARK`` is the canonical simulation fill model used by BOTH batch and
    paper (so paper↔batch can be byte-identical). ``LIVE_VENUE`` is real venue
    fills, used by live only — the single intentional divergence. A third fill
    model on the batch/paper path is review-blocking (it re-creates the
    paper-vs-batch divergence the determinism spine eliminates).
    """

    BENCHMARK = "BENCHMARK"
    LIVE_VENUE = "LIVE_VENUE"


class RunManifest(BaseModel):
    """As-of snapshot pinning everything a deterministic rerun needs.

    A paper run writes this once. A batch rerun takes the paper run's manifest,
    asserts the ``code_shas``, replays ``captured_tick_stream`` (the exact
    market-state snapshots the paper run consumed) under the pinned
    ``feature_group_versions``, and writes its own ledger under a new ``run_id``
    with ``parent_run_id`` back-referencing the paper run. Given identical code +
    inputs + fill model, the emitted instructions AND simulated fills are a
    deterministic function of the snapshot — trade-for-trade identical.

    All datetime fields are tz-aware UTC. All GCS refs are immutable object
    prefixes (the point-in-time guarantee).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(description="Unique id for this run (paper/batch/live).")
    window_start: datetime = Field(description="Inclusive UTC window start.")
    window_end: datetime = Field(description="Exclusive UTC window end.")
    mode: TradingMode
    client_id: str = Field(description="Single client_id — never cross-client.")
    strategy_ids: tuple[str, ...] = Field(description="Strategies active in this run.")
    code_shas: dict[str, str] = Field(
        description="repo name -> git sha on the decision+fill path "
        "(strategy-service / execution-service / unified-api-contracts / "
        "unified-trading-library / features-service). A batch rerun asserts these.",
    )
    market_data_days: tuple[str, ...] = Field(
        description="Immutable GCS object refs / day partitions the run replayed.",
    )
    feature_group_versions: dict[str, int] = Field(
        description="feature_group -> pinned feature_group_version hive key.",
    )
    captured_tick_stream: str = Field(
        description="gs:// prefix of the exact MarketStateSnapshots consumed "
        "per tick (the as-of input snapshot a batch rerun replays).",
    )
    fill_model: FillModel
    ledger_root: str = Field(
        description="gs:// root of the four ledgers for this run (ledger_type=instruction/passive/position/pricing).",
    )
    parent_run_id: str | None = Field(
        default=None,
        description="A batch rerun back-references the paper run_id it reproduces.",
    )


def make_trade_key(
    instrument_key: str,
    strategy_instruction_id: str,
    tick_timestamp: datetime,
) -> str:
    """Deterministic per-trade identity — the reconciliation match key.

    The SAME ``(instrument_key, strategy_instruction_id, tick_timestamp)`` in
    paper and batch yields the SAME key, enabling trade-for-trade matching.
    Timestamp is normalised to UTC ISO-8601 microseconds so a tz-naive vs
    tz-aware mismatch can never split a key (a naive timestamp is assumed UTC —
    the workspace stores all timestamps in UTC).
    """

    ts = tick_timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    iso = ts.astimezone(UTC).isoformat(timespec="microseconds")
    return f"{instrument_key}|{strategy_instruction_id}|{iso}"


class TradeFillRecord(BaseModel):
    """A keyed per-trade fill — the unit the reconciliation matches on.

    Carried on the execution event AND mirrored to ``LedgerRow`` with
    ``event_type=TRADE`` (``trade_id`` = ``trade_key``). ``side`` maps to the
    ledger ``Direction`` enum value (kept as a string here to avoid coupling the
    reconciliation contract to the ledger module).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trade_key: str = Field(description="make_trade_key(...) — the match key.")
    instrument_key: str = Field(description="VENUE:INSTRUMENT_TYPE:SYMBOL.")
    strategy_instruction_id: str
    tick_timestamp: datetime
    venue: str
    side: str = Field(description="Ledger Direction value (BUY/SELL/LONG/SHORT/…).")
    qty: Decimal
    fill_price: Decimal
    fees_in_quote: Decimal
    fill_model: FillModel
    correlation_id: str | None = None
    client_order_id: str | None = None


class ReconVerdictType(StrEnum):
    """Which leg of the determinism decomposition a report covers."""

    DETERMINISM = "DETERMINISM"  # paper ↔ batch: expect ε = 0
    EXECUTION = "EXECUTION"  # live ↔ paper: execution alpha (expected non-zero)
    COMPOSITE = "COMPOSITE"  # live ↔ batch: = determinism(≈0) + execution


class DeterminismBugClass(StrEnum):
    """Classification of a non-zero paper↔batch diff (which is always a BUG)."""

    NONE = "NONE"
    NON_DETERMINISM = "NON_DETERMINISM"  # the decision path is not deterministic
    INPUT_CAPTURE_GAP = "INPUT_CAPTURE_GAP"  # the rerun saw different inputs
    FILL_MODEL_DRIFT = "FILL_MODEL_DRIFT"  # paper/batch used different fill code


class TradeDeviation(BaseModel):
    """Per-trade diff between two runs, keyed on ``trade_key``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trade_key: str
    instrument_key: str
    venue: str
    side_match: bool
    qty_delta: Decimal
    fill_price_delta_bps: Decimal
    fees_delta: Decimal
    timing_delta_ms: float
    present_in_a: bool
    present_in_b: bool


class WeeklyReconReport(BaseModel):
    """Trade-by-trade reconciliation over a window.

    For a ``DETERMINISM`` verdict (paper↔batch) ``is_deterministic`` is True iff
    every matched trade has ε=0 across (side, qty, fill_price, fees) AND there
    are no unmatched trades on either side; otherwise ``determinism_bug_class``
    names the failure mode. For an ``EXECUTION`` verdict (live↔paper) the
    fill-price-delta rollups carry the execution alpha.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict_type: ReconVerdictType
    run_a_id: str = Field(description="paper (DETERMINISM/EXECUTION) or live (COMPOSITE).")
    run_b_id: str = Field(description="batch (DETERMINISM/COMPOSITE) or paper (EXECUTION).")
    window_start: datetime
    window_end: datetime
    total_trades_a: int
    total_trades_b: int
    matched: int
    unmatched_a: int
    unmatched_b: int
    deviations: tuple[TradeDeviation, ...]
    is_deterministic: bool = Field(
        description="DETERMINISM verdict only: True iff ε=0 and no unmatched trades.",
    )
    determinism_bug_class: DeterminismBugClass = DeterminismBugClass.NONE
    mean_fill_price_delta_bps: Decimal = Decimal("0")
    p99_fill_price_delta_bps: Decimal = Decimal("0")


__all__ = [
    "AutoReconcileReason",
    "BalanceReconciliationSnapshot",
    "BalanceReconciliationStatus",
    "DeterminismBugClass",
    "DeviationState",
    "DeviationStatus",
    "DeviationType",
    "FillModel",
    "PnLReconciliationSnapshot",
    "ReconVerdictType",
    "ReconciliationAction",
    "ReconciliationAgeFields",
    "ReconciliationDimension",
    "ReconciliationResolution",
    "RunManifest",
    "TradeDeviation",
    "TradeFillRecord",
    "TradingMode",
    "WeeklyReconReport",
    "make_trade_key",
]
