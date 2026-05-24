"""Scenario overlays and registry — main overlay model and registration system."""

from __future__ import annotations

from typing import Final, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._enums import _SCENARIO_ID_PATTERN, ScenarioCategory, ScenarioOverlayLayer
from ._mutations import ScenarioMutationSpec
from ._outcomes import ScenarioOutcomeAssertion


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
        data = cast(dict[str, object], yaml.safe_load(yaml_content))
        return cls.model_validate(data)


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
    "ScenarioApplicabilityFilter",
    "ScenarioOverlay",
    "register_scenario",
]
