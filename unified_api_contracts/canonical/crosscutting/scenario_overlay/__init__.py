"""Scenario-overlay taxonomy — closed-set workspace SSOT for synthetic adversarial scenarios.

Phase 1.A-1.D of `simulation_scenarios_topology_price_shocks_2026_05_09.md`
(`unified-trading-pm/plans/active/`). Defines the canonical scenario taxonomy
that UTL `scenario/{applier,checker,runner}.py` consumes + that
strategy-service/risk + execution-service + alerting-service all observe
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

from ._enums import OutcomeCategory, ScenarioCategory, ScenarioOverlayLayer
from ._mutations import (
    BookSpoof,
    DropRows,
    EventDrop,
    EventDuplicate,
    GasSurge,
    LatencyInject,
    ManifestPhantom,
    OracleDeviate,
    PriceShift,
    RejectFills,
    ScenarioMutationSpec,
    StaleHold,
)
from ._outcomes import ScenarioOutcomeAssertion, ScenarioOutcomeResult, ScenarioReport
from ._overlays import (
    SCENARIO_REGISTRY,
    ScenarioApplicabilityFilter,
    ScenarioOverlay,
    register_scenario,
)

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
