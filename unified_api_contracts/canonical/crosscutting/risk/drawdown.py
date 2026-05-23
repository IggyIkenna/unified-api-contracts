"""Per-strategy 7-threshold drawdown config + closed-set response policy.

Codifies ``disaster_recovery.md`` §8.2 + §8.3. Every live strategy MUST
declare all 7 DrawdownThresholdKind values (None = explicit-no-trigger) +
ExpectedDrawdownModel + ResponsePolicy.

Codex SSOT: planned ``codex/04-architecture/strategy-risk-config-schema.md``
(stub via implementation plan).
Implementation plan: ``plans/active/drawdown_liquidation_policy_and_strategy_risk_config_2026_05_23.md``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DrawdownThresholdKind(StrEnum):
    """Closed set of 7 drawdown threshold breakpoints.

    Order is the canonical "severity ladder" from least-action to most-action:
    WARNING < INVESTIGATION < HUMAN_ESCALATION < AUTO_PAUSE < AUTO_REDUCE <
    AUTO_CLOSE_ALL < LIQUIDATION_RISK.
    """

    WARNING = "WARNING"
    """Drawdown crossed a notice-level threshold. Slack only; no human wake-up."""

    INVESTIGATION = "INVESTIGATION"
    """Agent writes DrawdownInvestigationReport; audit event created."""

    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    """SEV1; operator must acknowledge active investigation."""

    AUTO_PAUSE = "AUTO_PAUSE"
    """Layer-0 ``pause_strategy.py`` fires automatically."""

    AUTO_REDUCE = "AUTO_REDUCE"
    """Strategy reduces position size by configured factor."""

    AUTO_CLOSE_ALL = "AUTO_CLOSE_ALL"
    """Strategy-specific close-all script fires."""

    LIQUIDATION_RISK = "LIQUIDATION_RISK"
    """SEV0 — liquidation imminent without immediate action."""


class ExpectedDrawdownModelBasis(StrEnum):
    """Closed set of 6 statistical bases for the strategy's expected-drawdown band."""

    HISTORICAL_BACKTEST = "HISTORICAL_BACKTEST"
    LIVE_VOLATILITY = "LIVE_VOLATILITY"
    VAR = "VAR"
    ES = "ES"
    MAX_ADVERSE_EXCURSION = "MAX_ADVERSE_EXCURSION"
    CUSTOM = "CUSTOM"


class ExpectedDrawdownModel(BaseModel):
    """Strategy-level model describing what drawdown the strategy is *expected*
    to produce. Used by ``DrawdownInvestigationReport`` to flag breaches that
    are outside the expected distribution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    basis: ExpectedDrawdownModelBasis
    confidence_level: Decimal | None = None
    """e.g. 0.95 for VaR / ES. None when basis doesn't use confidence."""
    lookback_window: timedelta | None = None
    """e.g. 30 days. None when basis doesn't use a lookback."""
    regime_adjustment: str | None = None
    """Free-form regime override description (e.g. 'crisis_2024Q1')."""


class ResponsePolicy(BaseModel):
    """5-flag explicit declaration of what auto-actions the strategy permits.

    NO defaults. Every strategy must declare all 5. None of the flags imply
    each other — e.g. allow_auto_pause=True + allow_auto_close_all=False is
    valid (strategy may pause but never auto-close).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    allow_agent_investigation: bool
    """Permit the agent to write DrawdownInvestigationReport without operator approval."""
    allow_auto_pause: bool
    """Permit Layer-0 ``pause_strategy.py`` at AUTO_PAUSE threshold."""
    allow_auto_reduce: bool
    """Permit position-reduce action at AUTO_REDUCE threshold."""
    allow_auto_close_all: bool
    """Permit strategy-specific close-all at AUTO_CLOSE_ALL threshold."""
    require_human_for_resume: bool
    """If True, operator must explicitly resume via Safety Ops tab after any
    auto-pause / auto-reduce / auto-close-all. Auto-resume blocked."""


class RiskThresholds(BaseModel):
    """Per-strategy 7-threshold dict. Every kind MUST be declared; None means
    'no trigger for this kind' (explicit opt-out)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pnl_drawdown: dict[DrawdownThresholdKind, Decimal | None] = Field(default_factory=dict)
    """Map of threshold kind → drawdown_pct. Negative numbers for losses
    (e.g. -0.02 = 2% drawdown). None opts out of that threshold for this strategy."""

    @model_validator(mode="after")
    def _all_kinds_declared(self) -> RiskThresholds:
        """Every DrawdownThresholdKind MUST appear as a key (value may be None)."""
        missing = {k for k in DrawdownThresholdKind} - self.pnl_drawdown.keys()
        if missing:
            raise ValueError(
                f"RiskThresholds.pnl_drawdown must declare every DrawdownThresholdKind; "
                f"missing: {sorted(k.value for k in missing)}"
            )
        return self

    @model_validator(mode="after")
    def _monotonic_severity(self) -> RiskThresholds:
        """Declared (non-None) thresholds must be monotonically decreasing
        along the severity ladder (more-negative = worse).

        i.e. WARNING <= INVESTIGATION <= HUMAN_ESCALATION <= AUTO_PAUSE
        <= AUTO_REDUCE <= AUTO_CLOSE_ALL <= LIQUIDATION_RISK
        (where "<=" is "less negative" → "more negative").
        """
        ladder = [
            DrawdownThresholdKind.WARNING,
            DrawdownThresholdKind.INVESTIGATION,
            DrawdownThresholdKind.HUMAN_ESCALATION,
            DrawdownThresholdKind.AUTO_PAUSE,
            DrawdownThresholdKind.AUTO_REDUCE,
            DrawdownThresholdKind.AUTO_CLOSE_ALL,
            DrawdownThresholdKind.LIQUIDATION_RISK,
        ]
        prev_val: Decimal | None = None
        prev_kind: DrawdownThresholdKind | None = None
        for kind in ladder:
            val = self.pnl_drawdown[kind]
            if val is None:
                continue
            if prev_val is not None and val > prev_val:
                raise ValueError(
                    f"RiskThresholds non-monotonic: {kind.value}={val} > {prev_kind.value if prev_kind else None}={prev_val}; "
                    f"thresholds must be more-negative further down the ladder"
                )
            prev_val, prev_kind = val, kind
        return self
