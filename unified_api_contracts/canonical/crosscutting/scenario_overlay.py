"""Scenario-overlay taxonomy — closed-set workspace SSOT for synthetic adversarial scenarios.

Phase 1.A-1.D of `simulation_scenarios_topology_price_shocks_2026_05_09.md`
(`unified-trading-pm/plans/active/`). Defines the canonical scenario taxonomy
that UTL `scenario/{applier,checker,runner}.py` consumes + that
risk-and-exposure-service + execution-service + alerting-service all observe
when scenarios fire `synthetic=true` events.

Five orthogonal axes per scenario:

1. :class:`ScenarioId` — closed-set identifier (regex `[a-z][a-z0-9_]+`).
2. :class:`ScenarioCategory` — high-level shape (TOPOLOGY_GAP / STALENESS /
   PRICE_SHOCK / VENUE_OUTAGE / DATA_CORRUPTION / CROSS_ASSET / OPERATIONAL).
3. :class:`ScenarioOverlayLayer` — pipeline tap point (RAW_TICK / FEATURE /
   SIGNAL / ORDER / EVENT / MANIFEST).
4. :class:`ScenarioMutationSpec` — discriminated union over the 11 typed
   mutations (PriceShift / StaleHold / LatencyInject / BookSpoof /
   RejectFills / OracleDeviate / GasSurge / DropRows / EventDrop /
   EventDuplicate / ManifestPhantom).
5. :class:`ScenarioOutcomeAssertion` — declared expected outcome at run-time
   (RiskRuleConsequence / CircuitBreakerId trip / KillSwitchId arm /
   AlertCode fire / PnL-bounded / reconciliation-flagged).

Per CLAUDE.md "Live = batch" rule: scenarios ride the SAME prod codepaths as
live + batch — only the overlay mutation differs. `synthetic=true` metadata
on every emitted event distinguishes scenario-fire from real-fire so
alerting-service suppresses paging.

§ 7 SSOT reconciliation seam
----------------------------

Every Pydantic class docstring below includes a "§ 7 SSOT reconciliation"
subsection per the seam mandate in
[`risk_simulations_limits_alerting_2026_05_10.md:44-87`](../../../../unified-trading-pm/plans/active/risk_simulations_limits_alerting_2026_05_10.md).
The seam:

- :class:`ScenarioOutcomeAssertion` carries optional
  :class:`RiskRuleConsequence` + :class:`CircuitBreakerId` +
  :class:`BreakerAction` + :class:`KillSwitchId` + :class:`AlertCode`
  references. These COMPOSE with the 4-layer risk-gates model:
  Layer 2 (rule decision) → Layer 3 (breaker) → Layer 4 (venue error).
- :class:`ScenarioOverlayLayer` is a NEW axis distinct from
  :class:`BreakerScope` (per-venue / per-archetype / etc.) — overlay layer
  is the PIPELINE TAP, scope is the RULE-APPLICABILITY axis. A scenario at
  `RAW_TICK` layer may fire breakers at `PER_VENUE` scope; orthogonal.
- :class:`ScenarioCategory` orthogonal to
  ``honest_coverage.EmptyConfirmedReason`` — category is operator-facing
  scenario taxonomy, EmptyConfirmedReason is on-disk manifest provenance.
  Where both apply, the scenario emits both.

Adding a new scenario
---------------------

1. Append the identifier to :class:`ScenarioId` regex (if needed) + add a
   :class:`ScenarioOverlay` entry to the per-asset_group registry under
   ``unified_api_contracts/registry/scenarios/<asset_group>.py``.
2. If the scenario tests a NEW mutation shape not in the 11-member union,
   first extend :class:`ScenarioMutationSpec` here (per Citadel-Grade
   pre-audit — workspace-grep every existing applier consumer).
3. Update the codex doc per
   ``simulation_scenarios_topology_price_shocks_2026_05_09.md`` Phase 8.

Compressed-scope status (2026-05-12)
------------------------------------

Per the plan body's "compressed-scope" banner (lines 51-103), the
pre-cutover ship includes:

- 11 mutation types (this module): used across the 10 Day-1 scenarios; the
  compressed-scope plan said "5 mutations" but the Day-1 design fragments
  surfaced needs for all 11 — shipping all to avoid a second pass.
- 9 outcome assertion categories: covers every declared expected outcome
  across the 10 scenarios. Closed set; reviewers reject scenario seeds that
  declare outcomes outside this enum.
- 10 :class:`ScenarioOverlay` registry instances: 6 topology + 4 price-shock
  per CONTINUE-prompt scope.

Deferred to successor `simulation_scenarios_post_cutover_2026_06_01.md`:

- First-class :class:`LendingFeatureSpike` / :class:`VenueOutage` /
  :class:`MempoolCongestion` mutation members (Day-1 fragments composed
  them via primitives — see fragments 03 / 01 / 06 in
  ``plans/active/scratch_scenarios_day1/``).
- Phase 4 broader scenario library (≥34 scenarios).
- Phase 6-9 (CLI / UI / cron / nightly-VM cadence).
"""

from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .alerting.codes import AlertCode
from .circuit_breaker import BreakerAction, CircuitBreakerId
from .kill_switch import KillSwitchId
from .risk_rule import RiskRuleConsequence

# ---------------------------------------------------------------------------
# Closed-set enums (Phase 1.A)
# ---------------------------------------------------------------------------


_SCENARIO_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]+$")


class ScenarioCategory(StrEnum):
    """High-level scenario taxonomy.

    Closed-set 7. A scenario may declare ONE primary category; secondary
    categories are captured in the per-scenario design fragment but not
    surfaced on the :class:`ScenarioOverlay` Pydantic instance (one-of-N
    keeps consumer dispatchers narrow).

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Orthogonal to :class:`EmptyConfirmedReason` (manifest-side honest-absence
    vocabulary). Where both apply, the scenario emits both:
    `ScenarioCategory.TOPOLOGY_GAP` + manifest `record_empty(reason=...)`
    with the appropriate reason. Categories DO NOT shadow reasons.
    """

    TOPOLOGY_GAP = "TOPOLOGY_GAP"
    """Pipeline-topology rows missing (data gap, not a price move)."""
    STALENESS = "STALENESS"
    """Last-tick / heartbeat age exceeds threshold."""
    PRICE_SHOCK = "PRICE_SHOCK"
    """Mid-price / funding / basis / peg moves >= N sigma."""
    VENUE_OUTAGE = "VENUE_OUTAGE"
    """Venue / chain / protocol stops responding (REST + WS both down)."""
    DATA_CORRUPTION = "DATA_CORRUPTION"
    """Row content invalid (wild-print oracle, sandwich-attack signature, ...)."""
    CROSS_ASSET = "CROSS_ASSET"
    """Multi-instrument / multi-asset_group correlated event."""
    OPERATIONAL = "OPERATIONAL"
    """Operational dynamics (gas spike / mempool congestion / tx-inclusion delay)."""


class ScenarioOverlayLayer(StrEnum):
    """Pipeline-tap injection point for the mutation.

    Closed-set 6. A scenario may declare ONE primary layer; multi-layer
    mutations decompose into N scenarios composing via :attr:`ScenarioOverlay.composes_with`.

    Reuse-prod-codepath principle: every layer here corresponds to a real
    boundary in the unified pipeline (MTDS → MDPS → features-* → strategy →
    execution → matching engine; manifest writer + event stream are
    cross-cutting). No standalone backtest engine.
    """

    RAW_TICK = "RAW_TICK"
    """MTDS adapter `_post_fetch` hook — tick + book + funding rows."""
    FEATURE = "FEATURE"
    """features-service `_compute_*` exit OR mdps feature-layer hook."""
    SIGNAL = "SIGNAL"
    """strategy-service `signal_generator` emit boundary."""
    ORDER = "ORDER"
    """execution-service order submit + matching-engine adversarial mode."""
    EVENT = "EVENT"
    """Cross-cutting event stream injection (chain-slot / venue-halt / tx-status)."""
    MANIFEST = "MANIFEST"
    """ManifestWriter `record_*` hook — phantom-row or honest-empty injection."""


class ScenarioApplicabilityFilter(BaseModel):
    """Per-scenario filter narrowing which (venue, data_type, instrument, day, archetype) cells the overlay applies to.

    Sparse — every field is optional; an empty filter matches everything in
    the scenario's declared `asset_groups`. Operator-runtime override:
    matrix-runner can layer additional filters atop the registry default.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with :class:`unified_api_contracts.canonical.crosscutting.risk_rule.RiskRuleScope` —
    a filter at ``per_venue`` granularity tests rules at
    :attr:`RiskRuleScope.PER_VENUE`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venues: frozenset[str] | None = Field(default=None)
    """Optional venue allow-list (lowercase short-names per CLAUDE.md vocab)."""
    chains: frozenset[str] | None = Field(default=None)
    """Optional chain allow-list (lowercase: `ethereum` / `arbitrum` / `solana` / ...)."""
    instruments: frozenset[str] | None = Field(default=None)
    """Optional per-instrument allow-list (e.g. `BTCUSDT`)."""
    data_types: frozenset[str] | None = Field(default=None)
    """Optional data-type allow-list (e.g. `trades` / `orderbook` / `funding_rate`)."""
    archetypes: frozenset[str] | None = Field(default=None)
    """Optional archetype-id allow-list (e.g. `carry_staked_basis`)."""
    protocols: frozenset[str] | None = Field(default=None)
    """Optional protocol allow-list (e.g. `aave_v3` / `marinade`)."""


# ---------------------------------------------------------------------------
# Mutation discriminated-union (Phase 1.B)
# ---------------------------------------------------------------------------


class _MutationBase(BaseModel):
    """Common base — frozen + extra-forbid + discriminator literal in each subclass."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PriceShift(_MutationBase):
    """Shift a price-like value by a target delta. Funding-rate / mid-price / peg-price all use this."""

    mutation_type: Literal["PriceShift"] = "PriceShift"
    target_value_bps: Decimal
    """Absolute target value in bps (e.g. 100 = 0.1%/period for funding)."""
    baseline_bps: Decimal | None = Field(default=None)
    """Optional baseline for delta-mode; ``None`` = absolute-target mode."""
    duration_seconds: int = Field(gt=0)
    recovery_curve: Literal["step", "linear", "exponential_decay", "ramp"] = "step"


class StaleHold(_MutationBase):
    """Freeze last value emitted — emulates feed staleness past heartbeat."""

    mutation_type: Literal["StaleHold"] = "StaleHold"
    stale_duration_seconds: int = Field(gt=0)
    heartbeat_count: int | None = Field(default=None, gt=0)
    """If set: number of heartbeats to skip (preferred over absolute seconds for feeds with non-uniform heartbeat)."""


class LatencyInject(_MutationBase):
    """Add fixed/variable latency on a pipeline edge."""

    mutation_type: Literal["LatencyInject"] = "LatencyInject"
    added_latency_seconds: Decimal = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    recovery_curve: Literal["step", "linear", "exponential_decay"] = "step"


class BookSpoof(_MutationBase):
    """Inject synthetic book imbalance / liquidity withdrawal."""

    mutation_type: Literal["BookSpoof"] = "BookSpoof"
    book_depth_scale: Decimal = Field(gt=0, le=1)
    """0..1 multiplier on book depth (e.g. 0.3 = withdraw 70% of LP liquidity)."""
    duration_seconds: int = Field(gt=0)
    imbalance_target: Decimal | None = Field(default=None, ge=-1, le=1)
    """Optional book-imbalance target in [-1, 1]."""


class RejectFills(_MutationBase):
    """Force matching-engine to reject fills with a typed reason."""

    mutation_type: Literal["RejectFills"] = "RejectFills"
    reject_rate: Decimal = Field(ge=0, le=1)
    """0..1 fraction of fills to reject."""
    duration_seconds: int = Field(gt=0)
    reject_reason: str
    """Typed reject reason (e.g. ``"BorrowCapExceeded"`` / ``"PoolPaused"`` / ``"VenueHalted"``)."""


class OracleDeviate(_MutationBase):
    """Wild-print or sustained-deviation oracle mutation. Distinct from StaleHold."""

    mutation_type: Literal["OracleDeviate"] = "OracleDeviate"
    deviation_sigma: Decimal
    """30sigma for the canonical worst case; sign indicates direction."""
    deviation_duration_heartbeats: int = Field(gt=0)
    oracle_id: str
    """Oracle-feed identifier (e.g. `pyth_solana_usdc`, Chainlink aggregator address)."""


class GasSurge(_MutationBase):
    """Spike gas / priority-fee on a chain."""

    mutation_type: Literal["GasSurge"] = "GasSurge"
    surge_multiplier: Decimal = Field(gt=1)
    """Multiplier over baseline (e.g. 50 = 50x spike)."""
    baseline_gwei: Decimal = Field(gt=0)
    surge_duration_seconds: int = Field(gt=0)
    recovery_curve: Literal["step", "linear", "exponential_decay"] = "linear"


class DropRows(_MutationBase):
    """Drop rows entirely from raw-tick or feature output."""

    mutation_type: Literal["DropRows"] = "DropRows"
    drop_rate: Decimal = Field(ge=0, le=1)
    duration_seconds: int = Field(gt=0)


class EventDrop(_MutationBase):
    """Drop named events from the event stream."""

    mutation_type: Literal["EventDrop"] = "EventDrop"
    event_types: frozenset[str]
    duration_seconds: int = Field(gt=0)


class EventDuplicate(_MutationBase):
    """Duplicate a synthetic event payload onto the stream."""

    mutation_type: Literal["EventDuplicate"] = "EventDuplicate"
    event_type: str
    payload_template: str
    """Operator-readable payload template for the synthetic event (parsed at apply-time by UTL applier)."""


class ManifestPhantom(_MutationBase):
    """Inject a synthetic manifest row at a target (asset_group, venue, data_type, day, ...)."""

    mutation_type: Literal["ManifestPhantom"] = "ManifestPhantom"
    target_capture_status: Literal["captured", "empty_confirmed", "attempted_failed", "expected_unattempted"]
    target_value: Decimal | None = Field(default=None)
    """Optional manifest-row value (e.g. utilization=0.99 for lending-indices phantoms)."""


ScenarioMutationSpec = Annotated[
    PriceShift
    | StaleHold
    | LatencyInject
    | BookSpoof
    | RejectFills
    | OracleDeviate
    | GasSurge
    | DropRows
    | EventDrop
    | EventDuplicate
    | ManifestPhantom,
    Field(discriminator="mutation_type"),
]
"""Discriminated union over the 11 mutation types.

Per `simulation_scenarios_topology_price_shocks_2026_05_09.md` Phase 1.B
compressed-scope: 5 mutations shipped pre-cutover. Day-1 scenario design
surfaced needs for all 11 — shipping all in one pass.

Adding new mutation types: append a new ``_MutationBase`` subclass + a new
discriminator literal + extend the union. UTL applier per Phase 2.A MUST
add a corresponding ``apply_<mutation>()`` method in the same logical unit
(per Citadel-Grade Pre-Audit).
"""


# ---------------------------------------------------------------------------
# Outcome assertion (Phase 1.C)
# ---------------------------------------------------------------------------


class OutcomeCategory(StrEnum):
    """Closed-set assertion category — what the scenario expects to observe.

    9 members covering the cross-product of `RiskRuleConsequence` x
    `CircuitBreakerId` x `KillSwitchId` x `AlertCode` plus P&L bounds +
    reconciliation hooks. Per the handshake doc fragment 11 § "Outcome
    assertion → expected-state cross-product."
    """

    STRATEGY_HALTED = "STRATEGY_HALTED"
    """No new signals emitted on (archetype, instrument) within SLA."""
    STRATEGY_SCALED_DOWN = "STRATEGY_SCALED_DOWN"
    """Signal size <= baseline * scale_factor within SLA."""
    RISK_BREAKER_TRIPPED = "RISK_BREAKER_TRIPPED"
    """Named :class:`CircuitBreakerId` transitions OPEN or DEGRADED."""
    ORDER_REJECTED = "ORDER_REJECTED"
    """execution-service refuses order at pre-flight."""
    ORDER_CANCELLED_ON_STALE = "ORDER_CANCELLED_ON_STALE"
    """Cancellation tx submitted within SLA after staleness signal."""
    KILL_SWITCH_ARMED = "KILL_SWITCH_ARMED"
    """Named :class:`KillSwitchId` armed by named provenance."""
    ALERT_FIRED = "ALERT_FIRED"
    """Named :class:`AlertCode` rule evaluates true with synthetic=true."""
    PNL_BOUNDED_BY = "PNL_BOUNDED_BY"
    """Per-archetype P&L stays within [lower, upper] bound post-scenario."""
    RECONCILIATION_FLAGGED = "RECONCILIATION_FLAGGED"
    """Named reconciler emits ``RECONCILIATION_DRIFT_DETECTED`` event."""


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


# ---------------------------------------------------------------------------
# ScenarioOverlay + registry (Phase 1.D)
# ---------------------------------------------------------------------------


class ScenarioOverlay(BaseModel):
    """A full synthetic-scenario declaration.

    Each entry in the per-asset_group registry seed (under
    ``unified_api_contracts/registry/scenarios/<asset_group>.py``) is a
    :class:`ScenarioOverlay` instance. Reviewers cross-check that every
    :class:`ScenarioId` listed for an asset_group has at least one
    :class:`ScenarioOutcomeAssertion` per declared targets-archetype.

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Composes with the cross-plan seam declared in handshake-integration
    fragment 11 (``plans/active/scratch_scenarios_day1/11_handshake_integration.md``):
    `ScenarioOverlay` produces `ScenarioOutcomeAssertion` cells; UTL
    `ScenarioOutcomeChecker` consumes them; risk + DR plan registries
    provide the consequence / breaker / kill-switch / alert vocabulary.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    """Snake-case identifier; must match :data:`_SCENARIO_ID_PATTERN`."""

    category: ScenarioCategory
    layer: ScenarioOverlayLayer
    asset_groups: frozenset[str]
    """Asset-group keys (lowercase per CLAUDE.md vocab rule —
    `cefi` / `defi` / `tradfi` / `sports` / `prediction`)."""

    applies_to: ScenarioApplicabilityFilter = Field(
        default_factory=ScenarioApplicabilityFilter,
    )

    mutation_spec: ScenarioMutationSpec
    """The typed mutation the applier injects."""

    expected_outcomes: tuple[ScenarioOutcomeAssertion, ...]
    """Closed list of assertions per archetype; minimum 1 entry."""

    description: str = Field(default="")
    """One-line operator-readable description."""

    real_world_referent: str = Field(default="")
    """Real-world incident(s) this scenario models (date + venue + root cause)."""

    composes_with: frozenset[str] = Field(default_factory=frozenset)
    """Scenario ids this scenario commonly co-fires with (Phase 5 matrix uses for composite cells)."""

    @field_validator("scenario_id")
    @classmethod
    def _validate_id_format(cls, v: str) -> str:
        if not _SCENARIO_ID_PATTERN.match(v):
            raise ValueError(f"scenario_id {v!r} must match regex ^[a-z][a-z0-9_]+$ (snake_case ASCII identifier)")
        return v

    @field_validator("expected_outcomes")
    @classmethod
    def _validate_outcomes_nonempty(
        cls,
        v: tuple[ScenarioOutcomeAssertion, ...],
    ) -> tuple[ScenarioOutcomeAssertion, ...]:
        if len(v) < 1:
            raise ValueError(
                "expected_outcomes must declare at least 1 ScenarioOutcomeAssertion "
                "(scenario with no outcomes is unverifiable)"
            )
        return v

    @classmethod
    def model_validate_yaml(cls, yaml_content: str) -> ScenarioOverlay:
        """Parse a YAML string into a ScenarioOverlay.

        Phase 6.C facade used by the backtest CLI ``--scenario-overlay-yaml`` path.
        Importable as ``unified_api_contracts.scenario_overlay.ScenarioOverlay.model_validate_yaml``.
        """
        import yaml

        data = yaml.safe_load(yaml_content)
        return cls.model_validate(data)


# ---------------------------------------------------------------------------
# Run-time report types (Phase 1.E from full-scope plan; ships pre-cutover for matrix harness)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Module-level registry index (populated at module-load by registry/scenarios)
# ---------------------------------------------------------------------------


SCENARIO_REGISTRY: Final[dict[str, ScenarioOverlay]] = {}
"""Global registry — populated at import time by ``registry/scenarios/__init__.py``.

Lookup: ``SCENARIO_REGISTRY[scenario_id]``. Reviewers reject any scenario
declared in a `registry/scenarios/<asset_group>.py` module that doesn't
register itself here via the module's ``_register()`` helper.
"""


def register_scenario(scenario: ScenarioOverlay) -> None:
    """Register a scenario in the global :data:`SCENARIO_REGISTRY`.

    Idempotent — raises :class:`ValueError` on duplicate `scenario_id`.
    Called by per-asset_group registry modules at module-load time.
    """
    if scenario.scenario_id in SCENARIO_REGISTRY:
        existing = SCENARIO_REGISTRY[scenario.scenario_id]
        if existing == scenario:
            return  # idempotent re-registration
        raise ValueError(
            f"duplicate scenario_id {scenario.scenario_id!r}; "
            f"existing={existing.description!r} vs new={scenario.description!r}",
        )
    SCENARIO_REGISTRY[scenario.scenario_id] = scenario


__all__ = [
    "SCENARIO_REGISTRY",
    "BookSpoof",
    "DropRows",
    "EventDrop",
    "EventDuplicate",
    "GasSurge",
    "LatencyInject",
    "ManifestPhantom",
    "OracleDeviate",
    "OutcomeCategory",
    "PriceShift",
    "RejectFills",
    "ScenarioApplicabilityFilter",
    "ScenarioCategory",
    "ScenarioMutationSpec",
    "ScenarioOutcomeAssertion",
    "ScenarioOutcomeResult",
    "ScenarioOverlay",
    "ScenarioOverlayLayer",
    "ScenarioReport",
    "StaleHold",
    "register_scenario",
]
