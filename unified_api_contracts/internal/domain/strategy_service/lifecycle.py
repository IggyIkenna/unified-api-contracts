"""Strategy lifecycle schemas — stages, transitions, paper trade comparison, maturity phasing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from unified_api_contracts.internal.execution import BatchExecutionMode
from unified_api_contracts.internal.modes import OperationalMode, RuntimeMode


class StrategyLifecycleStage(StrEnum):
    """Legacy lifecycle stages (pre-maturity-model). Retained for runtime consumers."""

    DRAFT = "DRAFT"
    BACKTEST = "BACKTEST"
    VALIDATED = "VALIDATED"
    PAPER = "PAPER"
    SHADOW = "SHADOW"
    LIVE = "LIVE"
    DEPRECATED = "DEPRECATED"


@dataclass
class StrategyLifecycleTransition:
    """Valid transition between lifecycle stages with gate requirements."""

    from_stage: StrategyLifecycleStage
    to_stage: StrategyLifecycleStage
    required_gates: list[str] = field(default_factory=list)
    human_approval_required: bool = False
    auto_trigger: bool = False


@dataclass
class PaperTradeComparison:
    """Result of comparing paper trading vs backtest performance."""

    strategy_id: str
    paper_sharpe: float
    backtest_sharpe: float
    sharpe_ratio_pct: float
    slippage_model_error: float = 0.0
    signal_decay_rate: float = 0.0


class StrategyMaturityPhase(StrEnum):
    """9-phase maturity model for strategy instances (2026-04-21 model).

    Ordering is strictly forward-only except for the terminal ``RETIRED`` sink —
    any phase may transition to ``RETIRED`` at any time. ``RETIRED`` is terminal.

    Phase semantics:
      - ``SMOKE``                pre-backtest smoke-test, mock data only
      - ``BACKTEST_MINIMAL``     < 1yr historical backtest, not viable yet
      - ``BACKTEST_1YR``         1-year backtest, minimum viability threshold
      - ``BACKTEST_MULTI_YEAR``  multi-year backtest, extended track
      - ``PAPER_1D``             first-day paper trading (odum-paper account)
      - ``PAPER_14D``            14-day paper trading
      - ``PAPER_STABLE``         extended paper, promotion-ready
      - ``LIVE_EARLY``           initial live, small capital (odum-live seed)
      - ``LIVE_STABLE``          mature live
      - ``RETIRED``              terminal, orthogonal to the forward ladder
    """

    SMOKE = "smoke"
    BACKTEST_MINIMAL = "backtest_minimal"
    BACKTEST_1YR = "backtest_1yr"
    BACKTEST_MULTI_YEAR = "backtest_multi_year"
    PAPER_1D = "paper_1d"
    PAPER_14D = "paper_14d"
    PAPER_STABLE = "paper_stable"
    LIVE_EARLY = "live_early"
    LIVE_STABLE = "live_stable"
    RETIRED = "retired"


# Forward-only phase ordering (index = rank in the ladder). RETIRED sits outside
# the ordered ladder — any phase can transition to it and it is terminal.
_PHASE_LADDER: tuple[StrategyMaturityPhase, ...] = (
    StrategyMaturityPhase.SMOKE,
    StrategyMaturityPhase.BACKTEST_MINIMAL,
    StrategyMaturityPhase.BACKTEST_1YR,
    StrategyMaturityPhase.BACKTEST_MULTI_YEAR,
    StrategyMaturityPhase.PAPER_1D,
    StrategyMaturityPhase.PAPER_14D,
    StrategyMaturityPhase.PAPER_STABLE,
    StrategyMaturityPhase.LIVE_EARLY,
    StrategyMaturityPhase.LIVE_STABLE,
)


def maturity_phase_rank(phase: StrategyMaturityPhase) -> int:
    """Return the ladder rank for a maturity phase. RETIRED returns -1 (orthogonal)."""
    if phase is StrategyMaturityPhase.RETIRED:
        return -1
    return _PHASE_LADDER.index(phase)


def is_valid_maturity_transition(
    from_phase: StrategyMaturityPhase,
    to_phase: StrategyMaturityPhase,
) -> bool:
    """Validate a maturity phase transition.

    Rules:
      - RETIRED is terminal — no transitions out of it.
      - Any phase may transition to RETIRED.
      - Forward-only moves up the ladder; skipping phases is allowed (e.g.
        BACKTEST_1YR → PAPER_1D skipping BACKTEST_MULTI_YEAR) because the
        multi-year tier is optional. Backward moves are rejected.
    """
    if from_phase is StrategyMaturityPhase.RETIRED:
        return False
    if to_phase is StrategyMaturityPhase.RETIRED:
        return True
    return maturity_phase_rank(to_phase) > maturity_phase_rank(from_phase)


def runtime_mode_for_phase(
    phase: StrategyMaturityPhase,
) -> tuple[RuntimeMode, BatchExecutionMode, OperationalMode]:
    """Return the canonical (RuntimeMode, BatchExecutionMode, OperationalMode) triple for a maturity phase.

    Design stub — wire-in deferred post-cutover (batch_live_symmetry_2026_05_10 Tab 2 J1).
    Signature locked here; full dispatch table ships in a follow-up plan phase.
    """
    raise NotImplementedError(
        f"runtime_mode_for_phase not yet wired — phase={phase!r} (batch_live_symmetry Tab 2 J1 follow-up)"
    )


class ProductRouting(StrEnum):
    """Which customer-facing product surfaces may see / subscribe to an instance.

    ``DART_ONLY`` and ``IM_ONLY`` gate visibility to DART (discretionary allocator
    routing terminal) and IM (investment management) respectively. ``BOTH`` makes
    the instance available on both product surfaces. ``INTERNAL_ONLY`` hides
    from all customer-facing surfaces — Odum-internal research / paper-only runs.
    """

    DART_ONLY = "dart_only"
    IM_ONLY = "im_only"
    BOTH = "both"
    INTERNAL_ONLY = "internal_only"


@dataclass(frozen=True)
class PhaseTransition:
    """One row in the phase-transition audit log for a strategy instance."""

    from_phase: StrategyMaturityPhase
    to_phase: StrategyMaturityPhase
    transitioned_at_utc: datetime
    transitioned_by: str
    rationale: str = ""


@dataclass(frozen=True)
class StrategyInstanceLifecycle:
    """Mutable lifecycle state for a single catalogue instance.

    The UAC catalogue itself is immutable (the set of possible 5-dim instances
    is fixed by the registries). This record holds the runtime-mutable state
    — maturity phase, product routing, series references, version lineage —
    owned by Firestore and hot-reloaded by services via ``LifecycleReloader``
    in ``unified-trading-library``.

    Series refs point to the odum-paper / odum-live account P&L streams keyed
    on ``(instance_id, account_type)``. Nullable when the phase has not yet
    produced a series (e.g. ``LIVE_SERIES_REF`` is ``None`` until the instance
    reaches ``LIVE_EARLY``).

    ``version_lineage`` carries ancestor version IDs for DART research-fork
    (Plan D) — empty tuple for v1 catalogue instances.
    """

    instance_id: str
    maturity_phase: StrategyMaturityPhase
    product_routing: ProductRouting
    available_since: datetime
    phased_at: datetime
    backtest_series_ref: str | None = None
    paper_series_ref: str | None = None
    live_series_ref: str | None = None
    phase_history: tuple[PhaseTransition, ...] = ()
    version_lineage: tuple[str, ...] = ()
