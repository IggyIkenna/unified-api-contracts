"""Scenario outcome assertions and results — expected outcomes and actual results."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from ..alerting.codes import AlertCode
from ..circuit_breaker import BreakerAction, CircuitBreakerId
from ..kill_switch import KillSwitchId
from ..risk_rule import RiskRuleConsequence
from ._enums import OutcomeCategory


class ScenarioOutcomeAssertion(BaseModel):
    """Per-cell expected outcome — the 6-tuple-per-cell contract per handshake doc.

    Each archetype's expected outcome is a list of these (one per assertion
    the scenario expects). The `ScenarioOutcomeChecker` (UTL Phase 2.B)
    iterates these + emits a `ScenarioOutcomeResult` per assertion.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Carries optional :class:`RiskRuleConsequence` + :class:`CircuitBreakerId`
    + :class:`BreakerAction` + :class:`KillSwitchId` + :class:`AlertCode`
    references — the 5 canonical SSOTs the assertion checks against. Per
    handshake doc fragment 11 § "Per-axis registry handshake" + § "Outcome
    assertion → expected-state cross-product."
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype: str
    """Archetype identifier (e.g. ``"carry_staked_basis"`` /
    ``"ARBITRAGE_PRICE_DISPERSION"``). Free-form string (not enum) so the
    contract doesn't tightly couple to ``internal/architecture_v2/enums.py``
    StrategyArchetype — scenarios can target archetype-id values that
    aren't yet first-class enum members."""

    category: OutcomeCategory

    consequence: RiskRuleConsequence | None = Field(default=None)
    """For RISK_BREAKER_TRIPPED / ORDER_REJECTED / STRATEGY_SCALED_DOWN."""

    breaker_id: CircuitBreakerId | None = Field(default=None)
    """For RISK_BREAKER_TRIPPED — named breaker the assertion checks."""

    breaker_action: BreakerAction | None = Field(default=None)
    """For RISK_BREAKER_TRIPPED — what action the tripped breaker should emit."""

    kill_switch_id: KillSwitchId | None = Field(default=None)
    """For KILL_SWITCH_ARMED — named kill-switch the assertion checks."""

    alert_codes: frozenset[AlertCode] = Field(default_factory=frozenset)
    """For ALERT_FIRED — closed set of alerts that should fire with synthetic=true."""

    pnl_lower_bound_bps: Decimal | None = Field(default=None)
    """For PNL_BOUNDED_BY — lower bound in bps of pre-scenario NAV."""
    pnl_upper_bound_bps: Decimal | None = Field(default=None)
    """For PNL_BOUNDED_BY — upper bound in bps."""

    reconciler_id: str | None = Field(default=None)
    """For RECONCILIATION_FLAGGED — named reconciler (e.g. ``position`` / ``manifest`` / ``batch_live``)."""

    expected_within_seconds: int = Field(gt=0)
    """SLA from scenario injection time to observed state."""


class ScenarioOutcomeResult(BaseModel):
    """Per-assertion observed result. UTL `ScenarioOutcomeChecker` emits these."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    assertion: ScenarioOutcomeAssertion
    """The expected assertion."""

    passed: bool
    """True iff observed state matched assertion within expected_within_seconds."""

    observed_within_seconds: int | None = Field(default=None)
    """Actual time-to-observe; None if assertion timed out unobserved."""

    observed_summary: str = Field(default="")
    """Free-form one-liner describing what was observed (event id / breaker state / alert code)."""


class ScenarioReport(BaseModel):
    """Single-run report parquet shape.

    Written by UTL `ScenarioReportEmitter` (Phase 2.C — DEFERRED per
    compressed scope; pre-cutover harness uses in-memory + JSONL only).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    archetype: str
    run_id: str
    started_at_iso: str
    finished_at_iso: str
    outcome_results: tuple[ScenarioOutcomeResult, ...]
    synthetic: bool = True
    """Always True for scenario-runs; distinguishes from real-fire reports."""
    parquet_artifacts: frozenset[str] = Field(default_factory=frozenset)
    """Optional list of parquet paths the run wrote (per-stage snapshots)."""
    event_correlation_id: str = Field(default="")


__all__ = [
    "ScenarioOutcomeAssertion",
    "ScenarioOutcomeResult",
    "ScenarioReport",
]
