"""In-memory ``COUNTERPARTY_REGISTRY`` and lookup helpers.

The registry is the UAC-owned source-of-truth for the set of
:class:`Counterparty` entities currently onboarded onto signal-leasing.
Strategy-service reads from here at boot (via the facade) to decide
which slots are leasable to which counterparties (D4 — per-counterparty
allowlist of slot labels).

Entitlement windows are stored alongside the counterparty record. The
compact ``Counterparty.allowed_slots`` set is the fast-path allowlist
consulted at emission time; the time-windowed
:class:`CounterpartyEntitlement` entries are retained for billing and
audit (activation / deactivation timestamps).

Pre-launch the registry is seeded with two stub counterparties for the
September 2026 go-live. Real endpoint URLs + Secret Manager references
are injected at deploy time by ``deployment-service`` (never checked
in).

SSOT: ``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.plan.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.internal.domain.signal_broadcast.counterparty import Counterparty
from unified_api_contracts.internal.domain.signal_broadcast.entitlement import (
    CounterpartyEntitlement,
)
from unified_api_contracts.internal.domain.signal_broadcast.schema_depth import SchemaDepth

__all__ = [
    "COUNTERPARTY_ENTITLEMENTS",
    "COUNTERPARTY_REGISTRY",
    "active_counterparties",
    "counterparty_for",
    "entitled_slots_for",
    "entitlements_for",
]


# ---------------------------------------------------------------------------
# Seed data — placeholder counterparties for the September 2026 launch window.
# Real webhook URLs + Secret Manager references are injected by
# deployment-service at provisioning time (see
# ``deployment-service/scripts/provision-signal-broadcast-secrets.sh``).
# ---------------------------------------------------------------------------

_LAUNCH_WINDOW_START: datetime = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
_REGISTRY_SEED_TS: datetime = datetime(2026, 4, 20, 0, 0, 0, tzinfo=UTC)


_COUNTERPARTY_SEED: tuple[Counterparty, ...] = (
    Counterparty(
        id="counterparty-stub-1",
        name="Signal-Leasing Counterparty 1 (stub)",
        endpoint="https://webhook.example.invalid/counterparty-stub-1",
        hmac_secret_ref="projects/-/secrets/signal-broadcast-counterparty-stub-1-hmac",
        allowed_slots=frozenset({"stat-arb-pairs-fixed-cefi-spot-btc-eth"}),
        schema_depth=SchemaDepth.STANDARD,
        active=False,
        rate_limit_per_strategy_per_sec=10,
        created_at=_REGISTRY_SEED_TS,
        updated_at=_REGISTRY_SEED_TS,
    ),
    Counterparty(
        id="counterparty-stub-2",
        name="Signal-Leasing Counterparty 2 (stub)",
        endpoint="https://webhook.example.invalid/counterparty-stub-2",
        hmac_secret_ref="projects/-/secrets/signal-broadcast-counterparty-stub-2-hmac",
        allowed_slots=frozenset({"stat-arb-pairs-fixed-cefi-spot-btc-eth"}),
        schema_depth=SchemaDepth.MINIMAL,
        active=False,
        rate_limit_per_strategy_per_sec=5,
        created_at=_REGISTRY_SEED_TS,
        updated_at=_REGISTRY_SEED_TS,
    ),
)


COUNTERPARTY_REGISTRY: dict[str, Counterparty] = {cp.id: cp for cp in _COUNTERPARTY_SEED}
"""Counterparty id -> :class:`Counterparty`. Read-only lookup surface."""


COUNTERPARTY_ENTITLEMENTS: tuple[CounterpartyEntitlement, ...] = tuple(
    CounterpartyEntitlement(
        counterparty_id=cp.id,
        slot_label=slot_label,
        active_from=_LAUNCH_WINDOW_START,
        active_to=None,
    )
    for cp in _COUNTERPARTY_SEED
    for slot_label in sorted(cp.allowed_slots)
)
"""Flat list of all counterparty x slot entitlement windows."""


def counterparty_for(counterparty_id: str) -> Counterparty | None:
    """Return the :class:`Counterparty` for ``counterparty_id`` or ``None``."""

    return COUNTERPARTY_REGISTRY.get(counterparty_id)


def active_counterparties() -> tuple[Counterparty, ...]:
    """Return all counterparties with ``active=True``, in registry order."""

    return tuple(cp for cp in COUNTERPARTY_REGISTRY.values() if cp.active)


def entitled_slots_for(counterparty_id: str) -> frozenset[str]:
    """Return the allowlist of slot labels for ``counterparty_id``.

    Returns an empty ``frozenset`` if the counterparty is unknown or
    inactive. Used at emission time for the D4 allowlist gate.
    """

    cp = COUNTERPARTY_REGISTRY.get(counterparty_id)
    if cp is None or not cp.active:
        return frozenset()
    return cp.allowed_slots


def entitlements_for(counterparty_id: str) -> tuple[CounterpartyEntitlement, ...]:
    """Return all :class:`CounterpartyEntitlement` rows for ``counterparty_id``."""

    return tuple(e for e in COUNTERPARTY_ENTITLEMENTS if e.counterparty_id == counterparty_id)
