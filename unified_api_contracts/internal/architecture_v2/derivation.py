"""Derivation engine — five pure functions over the combo registry.

G1.6 of ``stage-3e-refactor-plan`` / ``uac-registry-gaps.md`` gap #11. Ships
the five derivation formulas specified in
``codex/14-playbooks/infra-spec/stage-3c-derivation-engine.md`` §1.1-§1.5 as
pure, side-effect-free functions that consume the G1.8 archetype capability
registry plus the Phase-10.5 strategy-availability registry.

Five formulas:

* ``combo(dimensions)`` (§1.1) — valid-combo membership wrapping the
  archetype capability lookup with blocker (BL-1..BL-22) filtering.
* ``cost(combo, tier, integration_depth=0.0)`` (§1.2) — shape-only pricing
  derivation. Numeric tables populate later once finance signs off; every
  ``QuoteLine`` carries ``todo_numeric=True`` today.
* ``demo_universe(persona, flavour)`` (§1.3) — visibility-sliced catalogue
  for demo prospects.
* ``prod_restrictions(client, package)`` (§1.4) — paying-client entitlement
  gate.
* ``access_control(user, route, item, phase)`` (§1.5) — phase-aware route
  gate composing the above four.

**Purity:** no I/O, no globals, no event emission. Event emission is the
caller's responsibility (store, watchdog, middleware).

**Citadel host pattern (Option X):** these pure functions live in UAC
alongside the other schemas they consume. Strategy-service imports them
via the ``unified_api_contracts.strategy`` public facade and wires them
into the allocator gate. Keeps the callers (pricing-engine, middleware,
non-strategy services) from pulling strategy-service as a dep.

**Future refactor:** stage-3c §5 recommends splitting into ``combo.py`` +
``pricing/`` sub-package + ``demo_universe.py`` + ``prod_restrictions.py``
+ ``access_control.py`` once the single-file surface stabilises. Tracked
as a follow-up in the G1.6 plan.

SSOT: ``codex/14-playbooks/infra-spec/stage-3c-derivation-engine.md``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeCapability,
    ArchetypeInstrumentType,
    CoverageStatus,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    StrategyArchetypeV2,
    VenueCategoryV2,
)
from unified_api_contracts.internal.architecture_v2.strategy_availability import (
    EXTERNAL_VISIBILITY_MIN_MATURITY,
    STRATEGY_AVAILABILITY_REGISTRY,
    LockState,
    StrategyAvailabilityEntry,
    StrategyMaturity,
    availability_for,
    maturity_rank,
)

# ---------------------------------------------------------------------------
# Phase + integration-depth literals (G1.1 thread-through + rule 10)
# ---------------------------------------------------------------------------

Phase = Literal["research", "paper", "live"]
"""Lifecycle phase per rule 03 §same-system principle. Matches the UI
binding threaded through ``lib/phase/use-phase-binding.ts`` (G1.1)."""

IntegrationDepth = Literal[
    "basic_instruction_integration",
    "richer_execution_constraints",
    "custom_allocator_handling",
]
"""Rule 10 integration-depth sub-dimension. Applies to blocks 5 + 7 only
per stage-3c §1.2 "Integration-depth extension" table."""

PricingTier = Literal["internal", "tier_a", "tier_b"]
"""Rule 08 pricing-tier enum. ``internal`` is codex-private — callers
without ``pricing.read_internal`` capability raise
``InternalCostLeakageError`` per stage-3c §1.2 Ex 4."""

DemoFlavour = Literal["broader_platform", "turbo", "deep_dive", "sales_pitch"]
"""Rule 06 demo-flavour enum. ``sales_pitch`` is the playbook-spec
Playwright default used by refactor-g1-6 reference spec."""

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InternalCostLeakageError(Exception):
    """Raised when a client-facing caller attempts ``cost(..., tier='internal')``.

    Per stage-3c §1.2 Ex 4 + rule 08 §"Internal cost column is codex-private".
    """


# ---------------------------------------------------------------------------
# Combo cell — output of formula #1
# ---------------------------------------------------------------------------


class Combo(BaseModel):
    """A fully-tagged dimension tuple plus the blockers it cleared.

    Output of ``combo(dimensions)`` (stage-3c §1.1). The input is the
    Cartesian dimension space; the output is the subset that both passes
    ``valid_cartesian`` AND isn't fired by any BL-1..BL-22 predicate.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype_id: StrategyArchetypeV2
    category: VenueCategoryV2
    instrument_type: ArchetypeInstrumentType
    venue_id: str | None = None
    chain: str | None = None
    slot_label: str | None = None
    cleared_blockers: tuple[str, ...] = ()
    advisory: str = ""


class DimensionQuery(BaseModel):
    """A single Cartesian tuple fed into ``combo(dimensions)``.

    Kept separate from :class:`Combo` because queries may be partially-
    specified (only ``archetype_id`` + pair), while outputs carry the
    full resolved tuple plus blocker metadata.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    archetype_id: StrategyArchetypeV2
    category: VenueCategoryV2
    instrument_type: ArchetypeInstrumentType
    venue_id: str | None = None
    chain: str | None = None
    slot_label: str | None = None


# ---------------------------------------------------------------------------
# Pricing types — formula #2
# ---------------------------------------------------------------------------


class QuoteLine(BaseModel):
    """One line item in a PriceQuote.

    ``todo_numeric=True`` marks shape-only rows per plan line 80-81 +
    stage-3c §1.2 "Owning service" note. Real numbers populate once
    Stage-2 ``commercial-model/pricing-building-blocks.md`` signs off.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    block_id: str
    tier: PricingTier
    integration_depth: IntegrationDepth | None = None
    upfront: str = "0"
    monthly_fixed: str = "0"
    monthly_variable: str = "0"
    todo_numeric: Literal[True] = True
    notes: str = ""


class Rule08Violation(BaseModel):
    """A pricing-quote violation of rule 08."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: Literal[
        "exclusivity_on_tier_a",
        "internal_cost_leakage",
        "mixed_tier_advisory",
        "raw_data_framing_on_tier_a",
    ]
    message: str


class PriceQuote(BaseModel):
    """Output of ``cost(combo, tier, integration_depth)``.

    Shape matches stage-3c §1.2 "Outputs" block. ``lines`` list is empty
    when a rule-08 violation prevents quote assembly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    combo: Combo
    tier: PricingTier
    integration_depth: IntegrationDepth | None = None
    lines: tuple[QuoteLine, ...] = ()
    premiums: tuple[QuoteLine, ...] = ()
    rule_08_violations: tuple[Rule08Violation, ...] = ()
    todo_numeric: Literal[True] = True


# ---------------------------------------------------------------------------
# Persona / demo-universe types — formula #3
# ---------------------------------------------------------------------------


class CommercialPath(StrEnum):
    """Rule 04 commercial-path axis mirror."""

    CLIENT_DOWNSTREAM = "client_downstream"
    CLIENT_FULL_PIPELINE = "client_full_pipeline"
    IM_REPORTING_ONLY = "im_reporting_only"
    REG_UMBRELLA = "reg_umbrella"
    ODUM_INTERNAL = "odum_internal"


class Persona(BaseModel):
    """Demo-universe input. Aligns with UI ``lib/auth/personas.ts``.

    ``assigned_profile`` lets sales override the default profile-per-
    commercial-path with an explicit Stage-2 profile id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    persona_id: str
    commercial_path: CommercialPath
    assigned_profile: str | None = None


class RouteDescriptor(BaseModel):
    """One navigable route in a demo/prod universe."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    label: str = ""
    visibility_mode: Literal["visible", "locked_visible", "hidden"] = "visible"


class SlotFilter(BaseModel):
    """Slot-level filter applied to catalogue queries in a demo universe."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maturity_floor: StrategyMaturity = EXTERNAL_VISIBILITY_MIN_MATURITY
    lock_state_in: tuple[LockState, ...] = (LockState.PUBLIC,)
    data_license_tier_max: str = "odum_proprietary"


class DemoUniverse(BaseModel):
    """Output of ``demo_universe(persona, flavour)``.

    Shape matches stage-3c §1.3 "Outputs" block.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    persona: Persona
    flavour: DemoFlavour
    visible_combos: tuple[Combo, ...] = ()
    locked_visible_combos: tuple[Combo, ...] = ()
    hidden_combos: tuple[Combo, ...] = ()
    visible_routes: tuple[RouteDescriptor, ...] = ()
    locked_visible_routes: tuple[RouteDescriptor, ...] = ()
    hidden_routes: tuple[RouteDescriptor, ...] = ()
    slot_filter: SlotFilter = SlotFilter()


# ---------------------------------------------------------------------------
# Production-restrictions types — formula #4
# ---------------------------------------------------------------------------


ClientAudience = Literal[
    "admin",
    "im_desk",
    "im_client",
    "trading_platform_subscriber",
    "reg_umbrella_client",
]


class ClientContext(BaseModel):
    """JWT-claims-shaped client context used by prod_restrictions + access_control."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    org_id: str
    client_id: str
    audience: ClientAudience
    business_unit: Literal["saas", "im_desk", "admin"] = "saas"
    fund_id: str | None = None
    reserving_business_unit_id: str | None = None


class ClientPackage(BaseModel):
    """Signed-contract state — which blocks are entitled at which tier.

    Shape-only today (contract-management layer is G1.7 scope). Populated
    from per-client fixture dicts until the dedicated service lands.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_id: str = "default"
    block_ids: tuple[str, ...] = ()
    tier: PricingTier = "tier_a"
    integration_depth: IntegrationDepth | None = None


class DenialReason(BaseModel):
    """Why a combo was denied from a client's entitled set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    slot_label: str = ""
    message: str = ""


class ProductionRestrictions(BaseModel):
    """Output of ``prod_restrictions(client, package)``.

    Shape matches stage-3c §1.4 "Outputs" block.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    client: ClientContext
    package: ClientPackage
    entitled_combos: tuple[Combo, ...] = ()
    entitled_routes: tuple[RouteDescriptor, ...] = ()
    denials: tuple[DenialReason, ...] = ()


# ---------------------------------------------------------------------------
# Access-control types — formula #5
# ---------------------------------------------------------------------------


class UserContext(BaseModel):
    """JWT-claims-shaped user context used by ``access_control``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    audience: ClientAudience
    entitlements: tuple[str, ...] = ()
    persona: Persona | None = None
    flavour: DemoFlavour = "sales_pitch"
    client: ClientContext | None = None
    package: ClientPackage | None = None


class ItemRef(BaseModel):
    """A reference to the item the route is rendering.

    ``None`` when the route is non-item-specific (landing, catalogue index).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slot_label: str | None = None
    combo: Combo | None = None


class AccessDecision(BaseModel):
    """Output of ``access_control(user, route, item, phase)``.

    Shape matches stage-3c §1.5 "Outputs" block. ``status`` is the
    four-value discriminator the caller routes on.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["allow", "locked_visible", "deny", "deny_phase"]
    reason: str = ""
    upgrade_hint: str = ""


# ---------------------------------------------------------------------------
# Restriction-profile type — shared shape used by demo_universe overlays
# ---------------------------------------------------------------------------


TileLockState = Literal["unlocked", "padlocked", "hidden"]
"""G1.3 three-state lock enum. Mirrors UI
``lib/visibility/tile-lock-state.ts`` TileLockState and
``demo-ops/profiles/*.yaml`` tile-level state values."""


class RestrictionProfile(BaseModel):
    """Stage-2 demo/prod restriction-profile shape.

    G1.7 extends the original stage-3c §1.4 block-level shape with a
    tile-level ``tiles`` field keyed by ``ServiceDefinition.key`` from
    ``unified-trading-system-ui/lib/config/services.ts``. The two layers
    compose: ``visible_blocks``/``hidden_blocks`` still drive block-level
    availability (pricing + demo universes); ``tiles`` drives the per-tile
    G1.3 lock-state on the services portal.

    Source of truth for ``tiles``:
    ``unified-trading-pm/codex/14-playbooks/demo-ops/profiles/<persona>.yaml``
    loaded by
    :func:`unified_api_contracts.internal.architecture_v2.restriction_profiles.resolve_profile`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    visible_blocks: tuple[str, ...] = ()
    locked_visible_blocks: tuple[str, ...] = ()
    hidden_blocks: tuple[str, ...] = ()
    visible_routes: tuple[RouteDescriptor, ...] = ()
    slot_filter: SlotFilter = SlotFilter()
    tiles: Mapping[str, TileLockState] = {}
    """Per-tile lock state. Keys match ``ServiceDefinition.key``; values are
    one of ``"unlocked"`` / ``"padlocked"`` / ``"hidden"``. Empty dict = the
    caller did not resolve from a YAML profile (legacy / test fixtures)."""


# ---------------------------------------------------------------------------
# Block list — BL-1..BL-22 predicate stubs
# ---------------------------------------------------------------------------

_BL_PREDICATES: tuple[tuple[str, str], ...] = (
    ("BL-1", "DeFi options — vol surface fidelity not yet wired"),
    ("BL-7", "DeFi perp market-making — venue latency > tick generator"),
    ("BL-8", "DeFi cross-sectional — basket gas-cost blowup"),
    ("BL-10", "Dated-future rolls — representative_future_service not deployed"),
    ("BL-11", "Signals-only package lacks block-6 research/promote"),
    ("BL-14", "CLIENT_EXCLUSIVE slot not in viewer org scope"),
    ("BL-15", "RETIRED lock_state — no new allocation"),
    ("BL-17", "LIVE_TINY maturity — notional cap applied"),
    ("BL-19", "Raw-data framing not allowed on Tier A quote"),
    ("BL-20", "Cross-chain bridge latency exceeds tick"),
    ("BL-22", "Org-scope mismatch on exclusive allocation"),
)


def _blocker_fires(
    query: DimensionQuery,
    capability: ArchetypeCapability,
    availability_registry: Iterable[StrategyAvailabilityEntry],
    today: str | None,
) -> tuple[str | None, str]:
    """Return the first BL-* id that fires for this query, or (None, '').

    Lightweight predicate implementation — sufficient for the five worked
    examples in stage-3c §1.1 and to gate the G1.6 unit tests. Full 22-
    blocker predicate suite lands in G1.7 when the combo-registry YAML
    ships. ``today`` is used by time-sensitive blockers (e.g. BL-10).
    """

    # BL-15: RETIRED slot
    if query.slot_label is not None:
        entry = availability_for(query.slot_label, registry=availability_registry)
        if entry.lock_state == LockState.RETIRED:
            return ("BL-15", "RETIRED lock_state — no new allocation")

    pair = (query.category, query.instrument_type)

    # BL-7: DeFi perp market-making
    if (
        capability.archetype_id == StrategyArchetypeV2.MARKET_MAKING_CONTINUOUS
        and query.category == VenueCategoryV2.DEFI
        and query.instrument_type == ArchetypeInstrumentType.PERP
    ):
        return ("BL-7", "DeFi perp market-making — venue latency > tick generator")

    # BL-1: DeFi options
    if query.category == VenueCategoryV2.DEFI and query.instrument_type == ArchetypeInstrumentType.OPTION:
        return ("BL-1", "DeFi options — vol surface fidelity not yet wired")

    # BL-10: dated-future rolls — slot_label carries the convention
    if (
        query.instrument_type == ArchetypeInstrumentType.DATED_FUTURE
        and query.slot_label is not None
        and "-dated-" in query.slot_label
        and capability.uses_rolling_futures
    ):
        return (
            "BL-10",
            "Dated-future rolls — representative_future_service not deployed",
        )

    # Fall-through: cell status is authoritative
    if pair in capability.blocked_pairs:
        return (
            "BL-MECH",
            f"mechanically unsupported: {query.category.value} x {query.instrument_type.value}",
        )

    _ = today  # referenced to keep signature stable; used by full suite
    return (None, "")


# ---------------------------------------------------------------------------
# Formula 1 — combo(dimensions)
# ---------------------------------------------------------------------------


def combo(
    dimensions: Iterable[DimensionQuery],
    *,
    today: str | None = None,
    capability_registry: Iterable[ArchetypeCapability] = ARCHETYPE_CAPABILITY_REGISTRY,
    availability_registry: Iterable[StrategyAvailabilityEntry] = STRATEGY_AVAILABILITY_REGISTRY,
) -> frozenset[Combo]:
    """Return the subset of ``dimensions`` that is valid AND unblocked.

    Stage-3C §1.1:
        combo(dimensions) = { d in dimensions :
              valid_cartesian(d)  AND
              NOT blocked(d)
        }

    ``valid_cartesian`` is satisfied when the archetype capability cell
    for ``(category, instrument_type)`` exists and its status is
    SUPPORTED or PARTIAL. ``blocked`` runs BL-1..BL-22 predicates via
    :func:`_blocker_fires`.

    Callers inject their own ``capability_registry`` /
    ``availability_registry`` for deterministic tests; defaults read the
    G1.8 + Phase-10.5 module-level tuples.
    """

    caps_by_archetype = {c.archetype_id: c for c in capability_registry}
    result: set[Combo] = set()

    for query in dimensions:
        capability = caps_by_archetype.get(query.archetype_id)
        if capability is None:
            continue  # archetype absent from registry — rejected silently

        pair = (query.category, query.instrument_type)
        # valid_cartesian: SUPPORTED or PARTIAL status
        if pair not in capability.supported_pairs and pair not in capability.partial_pairs:
            continue  # mechanical reject — no BL required

        blocker, advisory = _blocker_fires(
            query,
            capability,
            availability_registry=availability_registry,
            today=today,
        )
        if blocker is not None:
            continue  # blocked

        # Cleared-blockers list — empty today; G1.7 will populate when the
        # full BL-1..BL-22 predicate suite lands.
        cleared: tuple[str, ...] = ()

        result.add(
            Combo(
                archetype_id=query.archetype_id,
                category=query.category,
                instrument_type=query.instrument_type,
                venue_id=query.venue_id,
                chain=query.chain,
                slot_label=query.slot_label,
                cleared_blockers=cleared,
                advisory=advisory,
            )
        )

    return frozenset(result)


# ---------------------------------------------------------------------------
# Formula 2 — cost(combo, tier, integration_depth)
# ---------------------------------------------------------------------------
# Extracted to ``derivation_cost.py`` in Wave E closure (2026-04-20) to keep
# this module under the 900-line QG ceiling. Imported by
# ``architecture_v2/__init__.py``.


# ---------------------------------------------------------------------------
# Formula 3 — demo_universe(persona, flavour)
# ---------------------------------------------------------------------------
# Extracted to ``derivation_demo.py`` in Wave E closure (2026-04-20). The
# helper ``_all_supported_combos`` below stays here because
# ``prod_restrictions`` also consumes it.


def _all_supported_combos(
    capability_registry: Iterable[ArchetypeCapability],
) -> tuple[Combo, ...]:
    """Enumerate every SUPPORTED (archetype, category, instrument_type) cell."""

    out: list[Combo] = []
    for capability in capability_registry:
        for cell in capability.cells:
            if cell.status == CoverageStatus.SUPPORTED:
                out.append(
                    Combo(
                        archetype_id=capability.archetype_id,
                        category=cell.category,
                        instrument_type=cell.instrument_type,
                    )
                )
    return tuple(out)


# ---------------------------------------------------------------------------
# Formula 4 — prod_restrictions(client, package)
# ---------------------------------------------------------------------------


def prod_restrictions(
    client: ClientContext,
    package: ClientPackage,
    *,
    availability_registry: Iterable[StrategyAvailabilityEntry] = STRATEGY_AVAILABILITY_REGISTRY,
    capability_registry: Iterable[ArchetypeCapability] = ARCHETYPE_CAPABILITY_REGISTRY,
) -> ProductionRestrictions:
    """Return the production catalogue a paying client actually has access to.

    Stage-3C §1.4:
        prod_restrictions(client, package) =
              combos INTERSECT paid_entitlements(client, package)

    where paid_entitlements composes ``included_blocks(package)``,
    ``sub_scopes(package)``, ``tier(package)``, the rule-04 axis, CLIENT_
    EXCLUSIVE filtering (BL-14/BL-22), and the external-visibility
    maturity threshold.

    **G1.7 delegation note (runtime check):** the G1.7 plan line 431
    specifies that delegation to :func:`resolve_profile` applies to
    ``demo_universe()`` + ``prod_restrictions()`` "when caller provides a
    profile ID". ``prod_restrictions`` is scoped to a paying *client*
    (``ClientContext``) — not a demo *persona* — and derives entitlements
    from the ``availability_registry`` + per-audience lock-state rules,
    not from a YAML persona profile. There is no profile-ID arg on this
    signature today, so there is nothing to delegate. If a future client-
    scoped profile axis is added (e.g. per-client demo overlay), this
    function should call ``resolve_profile`` at that point — see
    ``refactor_g1_4_persona_combinatorial_expansion`` for the likely site.
    """

    all_cells = _all_supported_combos(capability_registry)
    denials: list[DenialReason] = []
    entitled: list[Combo] = []

    for cell in all_cells:
        slot_label = cell.slot_label or f"{cell.archetype_id.value}@{cell.category.value}-{cell.instrument_type.value}"
        entry = availability_for(slot_label, registry=availability_registry)

        # BL-15: retired
        if entry.lock_state == LockState.RETIRED:
            denials.append(
                DenialReason(
                    code="LOCK_STATE_RETIRED",
                    slot_label=slot_label,
                    message="RETIRED — existing positions wind down; no new capital flow",
                )
            )
            continue

        # External-visibility threshold — applies to every audience except admin + im_desk.
        if client.audience not in ("admin", "im_desk") and maturity_rank(entry.maturity) < maturity_rank(
            EXTERNAL_VISIBILITY_MIN_MATURITY
        ):
            continue  # silently not-entitled

        # Lock-state filtering per audience (matches
        # strategy_availability._visible semantics).
        if not _lock_state_permits(entry, client):
            continue

        entitled.append(cell)

    return ProductionRestrictions(
        client=client,
        package=package,
        entitled_combos=tuple(entitled),
        entitled_routes=(),
        denials=tuple(denials),
    )


def _lock_state_permits(
    entry: StrategyAvailabilityEntry,
    client: ClientContext,
) -> bool:
    if client.audience in ("admin", "im_desk"):
        return True
    if entry.lock_state == LockState.PUBLIC:
        return True
    if entry.lock_state == LockState.INVESTMENT_MANAGEMENT_RESERVED:
        return False
    if entry.lock_state == LockState.CLIENT_EXCLUSIVE:
        return entry.exclusive_client_id == client.client_id
    return False


# ---------------------------------------------------------------------------
# Formula 5 — access_control(user, route, item, phase)
# ---------------------------------------------------------------------------
# Extracted to ``derivation_access.py`` in Wave E closure (2026-04-20) to keep
# this module under the 900-line QG ceiling. Imported by
# ``architecture_v2/__init__.py``.


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    "AccessDecision",
    "ClientAudience",
    "ClientContext",
    "ClientPackage",
    "Combo",
    "CommercialPath",
    "DemoFlavour",
    "DemoUniverse",
    "DenialReason",
    "DimensionQuery",
    "IntegrationDepth",
    "InternalCostLeakageError",
    "ItemRef",
    "Persona",
    "Phase",
    "PriceQuote",
    "PricingTier",
    "ProductionRestrictions",
    "QuoteLine",
    "RestrictionProfile",
    "RouteDescriptor",
    "Rule08Violation",
    "SlotFilter",
    "UserContext",
    "combo",
    "prod_restrictions",
]
