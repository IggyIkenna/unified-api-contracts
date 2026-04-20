"""Demo-universe derivation — formula #3 extracted from derivation.py.

Wave E closure (2026-04-20): part of the derivation.py split to keep
the main module under the 900-line QG ceiling. ``demo_universe`` +
its three private helpers + the commercial-path default profile
dict move out here. Public API stable — callers still import
``demo_universe`` via the ``unified_api_contracts.strategy`` facade
or ``unified_api_contracts.internal.architecture_v2``.

SSOT: ``codex/14-playbooks/infra-spec/stage-3c-derivation-engine.md`` §1.3.
"""

from __future__ import annotations

from collections.abc import Iterable

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeCapability,
)
from unified_api_contracts.internal.architecture_v2.derivation import (
    Combo,
    CommercialPath,
    DemoFlavour,
    DemoUniverse,
    Persona,
    RestrictionProfile,
    RouteDescriptor,
    SlotFilter,
    _all_supported_combos,
)
from unified_api_contracts.internal.architecture_v2.strategy_availability import (
    LockState,
    StrategyMaturity,
)

_DEFAULT_PROFILE_BY_COMMERCIAL_PATH: dict[CommercialPath, RestrictionProfile] = {
    CommercialPath.CLIENT_DOWNSTREAM: RestrictionProfile(
        profile_id="signals_only_downstream_default",
        visible_blocks=(
            "block_1_reporting_core",
            "block_4_strategy_service_entry",
            "block_5_instructions_integration",
            "block_7_execution_layer",
            "block_8_venue_packs",
            "block_9_chain_packs",
            "block_10_instrument_type_packs",
            "block_11_analytics_packs",
        ),
        locked_visible_blocks=("block_6_research_promote_pipeline",),
        hidden_blocks=(
            "block_2_regulatory_umbrella_reporting",
            "block_3_im_allocator_reporting",
            "block_12_exclusivity_premium",
            "block_13_custom_solution_premium",
        ),
        visible_routes=(
            RouteDescriptor(path="/services/strategy-catalogue/", label="Strategy Catalogue"),
            RouteDescriptor(path="/services/data", label="Data"),
        ),
    ),
    CommercialPath.CLIENT_FULL_PIPELINE: RestrictionProfile(
        profile_id="full_dart_default",
        visible_blocks=(
            "block_1_reporting_core",
            "block_4_strategy_service_entry",
            "block_5_instructions_integration",
            "block_6_research_promote_pipeline",
            "block_7_execution_layer",
            "block_8_venue_packs",
            "block_9_chain_packs",
            "block_10_instrument_type_packs",
            "block_11_analytics_packs",
        ),
        visible_routes=(
            RouteDescriptor(path="/services/strategy-catalogue/", label="Strategy Catalogue"),
            RouteDescriptor(path="/services/research", label="Research"),
        ),
    ),
    CommercialPath.IM_REPORTING_ONLY: RestrictionProfile(
        profile_id="im_reporting_only_default",
        visible_blocks=(
            "block_1_reporting_core",
            "block_3_im_allocator_reporting",
            "block_11_analytics_packs",
        ),
        hidden_blocks=("block_4_strategy_service_entry", "block_6_research_promote_pipeline"),
        visible_routes=(
            RouteDescriptor(
                path="/services/investment-management/catalog/",
                label="IM Catalogue",
            ),
            RouteDescriptor(path="/services/reports/overview", label="Reports"),
        ),
    ),
    CommercialPath.REG_UMBRELLA: RestrictionProfile(
        profile_id="reg_umbrella_default",
        visible_blocks=(
            "block_1_reporting_core",
            "block_2_regulatory_umbrella_reporting",
            "block_7_execution_layer",
            "block_8_venue_packs",
            "block_10_instrument_type_packs",
        ),
        hidden_blocks=("block_3_im_allocator_reporting", "block_6_research_promote_pipeline"),
        visible_routes=(
            RouteDescriptor(
                path="/services/reports/reconciliation",
                label="Reconciliation",
            ),
        ),
    ),
    CommercialPath.ODUM_INTERNAL: RestrictionProfile(
        profile_id="odum_internal_full",
        visible_blocks=tuple(f"block_{n}" for n in range(1, 14)),
        visible_routes=(RouteDescriptor(path="/*", label="Full universe"),),
    ),
}


def _flavour_overlay(
    base: RestrictionProfile,
    flavour: DemoFlavour,
) -> RestrictionProfile:
    """Overlay the demo flavour on a default profile.

    ``broader_platform`` widens the visible-route surface; ``turbo`` +
    ``deep_dive`` + ``sales_pitch`` narrow it. Today these are layout-
    only; real overlays ship with Stage-2 ``demo-restriction-profiles.md``.
    """

    _ = flavour  # referenced so signature stays stable for the full overlay suite
    return base


def demo_universe(
    persona: Persona,
    flavour: DemoFlavour,
    *,
    profile_registry: dict[str, RestrictionProfile] | None = None,
    capability_registry: Iterable[ArchetypeCapability] = ARCHETYPE_CAPABILITY_REGISTRY,
) -> DemoUniverse:
    """Return the visibility-sliced combo set a demo prospect sees.

    Stage-3C §1.3:
        demo_universe(persona, flavour) = combos INTERSECT demo_restriction_profile(persona, flavour)

    where:
        demo_restriction_profile(persona, flavour) =
              default_profile_for(persona.commercial_path)
            XOR flavour_overlay(flavour)
            XOR explicit_overrides(persona.assigned_profile)
    """

    # Short-circuit: ``admin`` persona sees full universe regardless of flavour.
    if persona.commercial_path == CommercialPath.ODUM_INTERNAL:
        all_supported = _all_supported_combos(capability_registry)
        return DemoUniverse(
            persona=persona,
            flavour=flavour,
            visible_combos=all_supported,
            visible_routes=(RouteDescriptor(path="/*", label="Full universe"),),
            slot_filter=SlotFilter(
                maturity_floor=StrategyMaturity.CODE_NOT_WRITTEN,
                lock_state_in=(
                    LockState.PUBLIC,
                    LockState.INVESTMENT_MANAGEMENT_RESERVED,
                    LockState.CLIENT_EXCLUSIVE,
                    LockState.RETIRED,
                ),
            ),
        )

    # G1.7 runtime delegation: `resolve_profile()` hydrates the YAML-
    # driven tile layer (per-persona padlock/hidden/unlocked map consumed
    # by `useTileLockState`). `_default_profile()` supplies the block-
    # level layer (visible_blocks / locked_visible_blocks / hidden_blocks
    # drive the cell filter below). Both layers compose on the single
    # RestrictionProfile envelope per the class docstring; neither is
    # redundant. `_default_profile()` is the no-YAML block-level fallback
    # — kept because rule-12 profile YAMLs carry tile state only.
    # Imported lazily because `restriction_profiles` imports `Persona` /
    # `RestrictionProfile` / `TileLockState` from this module.
    from unified_api_contracts.internal.architecture_v2.restriction_profiles import (
        resolve_profile,
    )

    block_profile = _default_profile(persona, profile_registry)
    tile_profile = resolve_profile(persona, flavour)
    profile = block_profile.model_copy(update={"tiles": dict(tile_profile.tiles)})
    overlaid = _flavour_overlay(profile, flavour)

    supported = _all_supported_combos(capability_registry)
    locked_visible: list[Combo] = []
    hidden: list[Combo] = []
    visible: list[Combo] = []

    for cell in supported:
        # Cell-to-block mapping is layout-only today; every cell lands in
        # ``visible`` when the profile has the block-4 entry, else hidden.
        if "block_4_strategy_service_entry" in overlaid.visible_blocks:
            visible.append(cell)
        elif "block_6_research_promote_pipeline" in overlaid.locked_visible_blocks:
            locked_visible.append(cell)
        else:
            hidden.append(cell)

    return DemoUniverse(
        persona=persona,
        flavour=flavour,
        visible_combos=tuple(visible),
        locked_visible_combos=tuple(locked_visible),
        hidden_combos=tuple(hidden),
        visible_routes=overlaid.visible_routes,
        locked_visible_routes=(),
        hidden_routes=(),
        slot_filter=overlaid.slot_filter,
    )


def _default_profile(
    persona: Persona,
    registry: dict[str, RestrictionProfile] | None,
) -> RestrictionProfile:
    """Look up the *block-level* restriction profile for ``persona``.

    Returns the commercial-path default block scaffolding (``visible_blocks``
    / ``locked_visible_blocks`` / ``hidden_blocks`` / ``visible_routes``) —
    the orthogonal companion to the G1.7 YAML-driven tile layer resolved by
    :func:`resolve_profile`.

    This helper is NOT redundant with ``resolve_profile``:

    * ``resolve_profile`` hydrates ``tiles`` from
      ``demo-ops/profiles/<persona>.yaml`` and returns a profile whose
      block-level fields are EMPTY (``visible_blocks = ()``, etc.).
    * ``_default_profile`` returns the commercial-path block scaffolding
      with EMPTY ``tiles``.

    ``demo_universe`` merges both layers so the returned :class:`RestrictionProfile`
    carries tile state AND block-level filtering. Deleting this helper
    would strand the block-level layer — YAML profiles do not yet declare
    block membership (rule-12 scope + rule-04 axes live elsewhere).

    Uses the injected ``registry`` when ``persona.assigned_profile`` points
    to a pre-constructed override (e.g. sales-assigned stage-2 profile);
    otherwise falls back to the module-level commercial-path defaults.
    """

    if persona.assigned_profile is not None and registry is not None:
        override = registry.get(persona.assigned_profile)
        if override is not None:
            return override
    return _DEFAULT_PROFILE_BY_COMMERCIAL_PATH[persona.commercial_path]


__all__ = ["demo_universe"]
