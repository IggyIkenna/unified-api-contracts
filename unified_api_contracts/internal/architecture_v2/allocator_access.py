"""Allocator-gate adapter — composes ``access_control`` visibility logic
for internal portfolio-allocator callers.

G1.6 Wave E closure (2026-04-20). The portfolio allocator is an
internal server-side process, not a user-facing route, so the
``access_control(user, route, item, phase)`` surface doesn't map
cleanly:

* The allocator has no JWT-carrying caller — the ``UserContext`` has to
  be synthesised from the allocator's ``business_unit`` + ``client_id``.
* There is no ``route`` in the rule-12 service-family sense — the
  allocator writes to an event bus, not a URL allow-list.
* The ``phase`` is always ``"live"`` — allocators don't run in the
  research or paper phases (those are strategy-service responsibilities).

This helper exists to keep the allocator's defence-in-depth aligned
with UAC SSOT without pulling in the full route-based gating that
access_control layers on top of item visibility. It applies:

1. Admin short-circuit — admin business-unit passes every check.
2. Audience → ``UserContext`` synthesis using the same mapping
   ``validate_allocation_authorised`` uses internally (``saas`` →
   ``trading_platform_subscriber``, ``im_desk`` → ``im_desk``, ``admin``
   → ``admin``).
3. The exact item-visibility block from ``access_control`` (CLIENT_EXCLUSIVE
   404, RETIRED allocation-route deny, IM_RESERVED LOCKED-VISIBLE).

It intentionally SKIPS service-family scope (rule 12) and the phase
entitlement gate — those are user-request concepts and don't apply to
an internal allocator tick. A deny from the allocator_access helper
still raises fail-loud in the allocator before the legacy
``validate_allocation_authorised`` runs, preserving the two-layer
defence model.

SSOT: ``codex/14-playbooks/infra-spec/stage-3c-derivation-engine.md``
§1.5 (the item-visibility sub-section).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from unified_api_contracts.internal.architecture_v2.derivation import (
    AccessDecision,
    ClientContext,
    ItemRef,
    UserContext,
)
from unified_api_contracts.internal.architecture_v2.strategy_availability import (
    STRATEGY_AVAILABILITY_REGISTRY,
    LockState,
    StrategyAvailabilityEntry,
    availability_for,
)

_BUSINESS_UNIT_TO_AUDIENCE: dict[
    Literal["saas", "im_desk", "admin"],
    Literal["trading_platform_subscriber", "im_desk", "admin"],
] = {
    "saas": "trading_platform_subscriber",
    "im_desk": "im_desk",
    "admin": "admin",
}


def user_context_for_allocator(
    *,
    client_id: str,
    business_unit: Literal["saas", "im_desk", "admin"],
) -> UserContext:
    """Synthesise a :class:`UserContext` for internal allocator calls.

    The allocator carries no JWT — we build one from its declared
    ``business_unit`` so downstream UAC helpers (including this module's
    :func:`allocator_access_control`) see a consistent shape.
    """

    audience = _BUSINESS_UNIT_TO_AUDIENCE[business_unit]
    client = ClientContext(
        org_id=client_id,
        client_id=client_id,
        audience=audience,
        business_unit=business_unit,
    )
    return UserContext(audience=audience, client=client)


def allocator_access_control(
    *,
    user: UserContext,
    slot_label: str,
    availability_registry: Iterable[StrategyAvailabilityEntry] = STRATEGY_AVAILABILITY_REGISTRY,
) -> AccessDecision:
    """Item-visibility gate for the portfolio allocator pre-check.

    Composes the three CLIENT_EXCLUSIVE / RETIRED / IM_RESERVED branches
    from ``access_control`` into a standalone callable that does NOT
    require a route, phase, or capability registry. This is the
    documented Wave E "allocator-swap" adapter — see module docstring.

    Callers should raise fail-loud when ``status != 'allow'`` and NOT
    route the allocation directive.
    """

    if user.audience == "admin":
        return AccessDecision(status="allow", reason="admin audience — unrestricted")

    entry = availability_for(slot_label, registry=availability_registry)

    if entry.lock_state == LockState.CLIENT_EXCLUSIVE and (
        user.client is None or entry.exclusive_client_id != user.client.client_id
    ):
        return AccessDecision(
            status="deny",
            reason=("BL-14: CLIENT_EXCLUSIVE slot not in allocator scope (stage-3c §1.5 Ex 4)."),
        )

    if entry.lock_state == LockState.RETIRED:
        return AccessDecision(
            status="deny",
            reason="BL-15: RETIRED lock_state — no new allocation",
        )

    if entry.lock_state == LockState.INVESTMENT_MANAGEMENT_RESERVED and user.audience != "im_desk":
        return AccessDecision(
            status="locked_visible",
            reason="INVESTMENT_MANAGEMENT_RESERVED — IM desk only.",
            upgrade_hint=("Slot reserved for Odum Investment Management — contact sales for IM-desk access."),
        )

    return AccessDecision(status="allow")


__all__ = [
    "ItemRef",
    "allocator_access_control",
    "user_context_for_allocator",
]
