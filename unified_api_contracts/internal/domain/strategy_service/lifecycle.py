"""Strategy lifecycle schemas — stages, transitions, paper trade comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StrategyLifecycleStage(StrEnum):
    """Lifecycle stages a strategy progresses through."""

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
