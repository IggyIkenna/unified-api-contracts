"""Access-control derivation — formula #5 extracted from derivation.py.

Wave E closure (2026-04-20): derivation.py grew past the 900-line QG
ceiling. ``access_control`` + ``_allowed_phases`` + the two module-
private block-6 / paper-surface entitlement constants move out here.
Public API stable — callers still import ``access_control`` via the
``unified_api_contracts.strategy`` facade or
``unified_api_contracts.internal.architecture_v2``.

SSOT: ``codex/16-strategy-playbooks/infra-spec/stage-3c-derivation-engine.md`` §1.5.
"""

from __future__ import annotations

from collections.abc import Iterable

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeCapability,
)
from unified_api_contracts.internal.architecture_v2.derivation import (
    AccessDecision,
    ItemRef,
    Phase,
    UserContext,
)
from unified_api_contracts.internal.architecture_v2.derivation_demo import (
    demo_universe,
)
from unified_api_contracts.internal.architecture_v2.strategy_availability import (
    STRATEGY_AVAILABILITY_REGISTRY,
    LockState,
    StrategyAvailabilityEntry,
    availability_for,
)

_BLOCK_6_ENTITLEMENT = "block_6_research_promote_pipeline"
_PAPER_SURFACE_ENTITLEMENT = "paper_surface"


def access_control(
    user: UserContext,
    route: str,
    item: ItemRef | None,
    phase: Phase,
    *,
    availability_registry: Iterable[StrategyAvailabilityEntry] = STRATEGY_AVAILABILITY_REGISTRY,
    capability_registry: Iterable[ArchetypeCapability] = ARCHETYPE_CAPABILITY_REGISTRY,
) -> AccessDecision:
    """Phase-aware per-request gate composing the above four formulas.

    Stage-3C §1.5:
        access_control(user, route, item, phase) =
              visible(user, combo(item))
            AND phase in allowed_phases(user.entitlements)
            AND NOT rule_06_explicit_hide(user, route, item)

    Returns an :class:`AccessDecision` envelope with ``status`` in
    {allow, locked_visible, deny, deny_phase}.
    """

    # Admin short-circuit: every phase, every item.
    if user.audience == "admin":
        return AccessDecision(status="allow", reason="admin audience — unrestricted")

    # G1.11 pre-check (rule 12): service-family scope. Denial short-circuits
    # before any other gate. Imported lazily to avoid module-load coupling.
    from unified_api_contracts.internal.architecture_v2.service_family_scope import (
        check_service_family_scope,
    )

    scope_decision = check_service_family_scope(user, route)
    if scope_decision.status == "deny":
        return AccessDecision(
            status="deny",
            reason=scope_decision.reason,
            upgrade_hint=scope_decision.upgrade_hint,
        )

    # Phase-entitlement gate first — `deny_phase` distinct from `deny`.
    allowed = _allowed_phases(user.entitlements)
    if phase not in allowed:
        return AccessDecision(
            status="deny_phase",
            reason=f"phase={phase} not in allowed_phases={sorted(allowed)}",
            upgrade_hint=(
                f"{phase!r} phase requires block_6_research_promote_pipeline "
                if phase == "research"
                else f"{phase!r} phase requires paper_surface entitlement "
            )
            + "(stage-3c §1.5 allowed_phases).",
        )

    # Visibility gate over the item (if any).
    if item is not None and item.slot_label is not None:
        entry = availability_for(item.slot_label, registry=availability_registry)

        # CLIENT_EXCLUSIVE mismatch: HIDDEN-ENTIRELY per stage-3c §1.5 Ex 4.
        if entry.lock_state == LockState.CLIENT_EXCLUSIVE and (
            user.client is None or entry.exclusive_client_id != user.client.client_id
        ):
            return AccessDecision(
                status="deny",
                reason=("BL-14: CLIENT_EXCLUSIVE slot not in viewer scope (stage-3c §1.5 Ex 4 — 404/HIDDEN-ENTIRELY)."),
            )

        # RETIRED: deny for allocation routes.
        if entry.lock_state == LockState.RETIRED and "/allocate" in route:
            return AccessDecision(
                status="deny",
                reason="BL-15: RETIRED lock_state — no new allocation",
            )

        # IM_RESERVED slot requested by non-im_desk: LOCKED-VISIBLE
        # so the catalogue surface knows the slot exists and shows the
        # upgrade path; not a 404 because it's not information leakage
        # about a specific client.
        if entry.lock_state == LockState.INVESTMENT_MANAGEMENT_RESERVED and user.audience != "im_desk":
            return AccessDecision(
                status="locked_visible",
                reason="INVESTMENT_MANAGEMENT_RESERVED — IM desk only.",
                upgrade_hint=("Slot reserved for Odum Investment Management — contact sales for IM-desk access."),
            )

    # Demo-universe LOCKED-VISIBLE check (stage-3c §1.5 Ex 3).
    if user.persona is not None and item is None:
        universe = demo_universe(
            user.persona,
            user.flavour,
            capability_registry=capability_registry,
        )
        # Routes-only check — item-less routes always respect the profile.
        route_match = any(r.path == route for r in universe.visible_routes)
        if not route_match:
            for r in universe.locked_visible_routes:
                if r.path == route:
                    return AccessDecision(
                        status="locked_visible",
                        reason=f"route {route} visible-locked by {user.persona.commercial_path.value}",
                        upgrade_hint="Available in full DART — contact sales.",
                    )

    return AccessDecision(status="allow")


def _allowed_phases(entitlements: Iterable[str]) -> frozenset[Phase]:
    """Compute allowed phases per stage-3c §1.5 formula.

    ``live`` always. ``research`` requires block-6 entitlement. ``paper``
    requires either block-6 or the paper_surface entitlement.
    """

    ents = set(entitlements)
    result: set[Phase] = {"live"}
    if _BLOCK_6_ENTITLEMENT in ents:
        result.add("research")
        result.add("paper")
    elif _PAPER_SURFACE_ENTITLEMENT in ents:
        result.add("paper")
    return frozenset(result)


__all__ = ["access_control"]
