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

``COUNTERPARTY_ENTITLEMENT_PROFILES`` carries the v2 entitlement
profile per counterparty — the tuple of ``(allowed_slots,
payload_depth, rate_limit_ref, entitlement windows)`` — which
strategy-service looks up to decide payload shape + throttle profile
per emission.

Pre-launch the registry is seeded with two stub counterparties for the
September 2026 go-live. Real endpoint URLs + Secret Manager references
are injected at deploy time by ``deployment-service`` (never checked
in).

SSOT: ``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.internal.domain.signal_broadcast.counterparty import (
    Counterparty,
    CounterpartyStatus,
)
from unified_api_contracts.internal.domain.signal_broadcast.entitlements_v2 import (
    CounterpartyEntitlement,
    CounterpartyEntitlementProfile,
    RateLimitConfig,
)
from unified_api_contracts.internal.domain.signal_broadcast.signal_payload import PayloadDepth

__all__ = [
    "COUNTERPARTY_ENTITLEMENTS",
    "COUNTERPARTY_ENTITLEMENT_PROFILES",
    "COUNTERPARTY_REGISTRY",
    "RATE_LIMIT_CONFIGS",
    "active_counterparties",
    "counterparty_for",
    "entitled_slots_for",
    "entitlement_profile_for",
    "entitlements_for",
    "rate_limit_config_for",
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
        status=CounterpartyStatus.SUSPENDED,
        endpoint="https://webhook.example.invalid/counterparty-stub-1",
        allowed_slots=frozenset({"stat-arb-pairs-fixed-cefi-spot-btc-eth"}),
        hmac_secret_ref="projects/-/secrets/signal-broadcast-counterparty-stub-1-hmac",
        rate_limit_ref="default",
        created_at=_REGISTRY_SEED_TS,
        updated_at=_REGISTRY_SEED_TS,
    ),
    Counterparty(
        id="counterparty-stub-2",
        name="Signal-Leasing Counterparty 2 (stub)",
        status=CounterpartyStatus.SUSPENDED,
        endpoint="https://webhook.example.invalid/counterparty-stub-2",
        allowed_slots=frozenset({"stat-arb-pairs-fixed-cefi-spot-btc-eth"}),
        hmac_secret_ref="projects/-/secrets/signal-broadcast-counterparty-stub-2-hmac",
        rate_limit_ref="minimal",
        created_at=_REGISTRY_SEED_TS,
        updated_at=_REGISTRY_SEED_TS,
    ),
)


COUNTERPARTY_REGISTRY: dict[str, Counterparty] = {cp.id: cp for cp in _COUNTERPARTY_SEED}
"""Counterparty id -> :class:`Counterparty`. Read-only lookup surface."""


# ---------------------------------------------------------------------------
# Entitlement profiles: (allowed_slots + payload_depth + rate_limit_ref +
# time-windowed entitlements). Strategy-service looks these up to decide
# payload projection depth + throttle bucket per (counterparty, slot) pair.
# ---------------------------------------------------------------------------

_PAYLOAD_DEPTHS: dict[str, PayloadDepth] = {
    "counterparty-stub-1": PayloadDepth.STANDARD,
    "counterparty-stub-2": PayloadDepth.MINIMAL,
}


COUNTERPARTY_ENTITLEMENT_PROFILES: dict[str, CounterpartyEntitlementProfile] = {
    cp.id: CounterpartyEntitlementProfile(
        counterparty_id=cp.id,
        allowed_slots=cp.allowed_slots,
        payload_depth=_PAYLOAD_DEPTHS[cp.id],
        rate_limit_ref=cp.rate_limit_ref,
        entitlements=tuple(
            CounterpartyEntitlement(
                counterparty_id=cp.id,
                slot_label=slot_label,
                active_from=_LAUNCH_WINDOW_START,
                active_to=None,
            )
            for slot_label in sorted(cp.allowed_slots)
        ),
    )
    for cp in _COUNTERPARTY_SEED
}
"""Counterparty id -> full entitlement profile (depth + rate-limit + windows)."""


COUNTERPARTY_ENTITLEMENTS: tuple[CounterpartyEntitlement, ...] = tuple(
    entitlement for profile in COUNTERPARTY_ENTITLEMENT_PROFILES.values() for entitlement in profile.entitlements
)
"""Flat list of all counterparty x slot entitlement windows (derived from profiles)."""


def counterparty_for(counterparty_id: str) -> Counterparty | None:
    """Return the :class:`Counterparty` for ``counterparty_id`` or ``None``."""

    return COUNTERPARTY_REGISTRY.get(counterparty_id)


def entitlement_profile_for(
    counterparty_id: str,
) -> CounterpartyEntitlementProfile | None:
    """Return the :class:`CounterpartyEntitlementProfile` for ``counterparty_id``."""

    return COUNTERPARTY_ENTITLEMENT_PROFILES.get(counterparty_id)


def active_counterparties() -> tuple[Counterparty, ...]:
    """Return all counterparties with ``status == ACTIVE``, in registry order."""

    return tuple(cp for cp in COUNTERPARTY_REGISTRY.values() if cp.status == CounterpartyStatus.ACTIVE)


def entitled_slots_for(counterparty_id: str) -> frozenset[str]:
    """Return the allowlist of slot labels for ``counterparty_id``.

    Returns an empty ``frozenset`` if the counterparty is unknown or
    non-ACTIVE. Used at emission time for the D4 allowlist gate.
    """

    cp = COUNTERPARTY_REGISTRY.get(counterparty_id)
    if cp is None or cp.status != CounterpartyStatus.ACTIVE:
        return frozenset()
    return cp.allowed_slots


def entitlements_for(counterparty_id: str) -> tuple[CounterpartyEntitlement, ...]:
    """Return all :class:`CounterpartyEntitlement` rows for ``counterparty_id``."""

    return tuple(e for e in COUNTERPARTY_ENTITLEMENTS if e.counterparty_id == counterparty_id)


# ---------------------------------------------------------------------------
# Rate-limit profile registry. Each ``Counterparty.rate_limit_ref`` points
# at a named profile here. Strategy-service emitter looks the profile up
# per emission to gate (counterparty_id, strategy_id) token-bucket capacity.
# ---------------------------------------------------------------------------

RATE_LIMIT_CONFIGS: dict[str, RateLimitConfig] = {
    "default": RateLimitConfig(name="default", requests_per_second=10.0, burst=10),
    "minimal": RateLimitConfig(name="minimal", requests_per_second=5.0, burst=5),
    "burst": RateLimitConfig(name="burst", requests_per_second=25.0, burst=50),
}
"""Named ``RateLimitConfig`` profiles referenced via ``Counterparty.rate_limit_ref``."""


def rate_limit_config_for(ref: str) -> RateLimitConfig | None:
    """Resolve a ``rate_limit_ref`` to its :class:`RateLimitConfig`."""

    return RATE_LIMIT_CONFIGS.get(ref)
