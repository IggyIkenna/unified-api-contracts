"""Signal-broadcast internal domain schemas (Phase 2, D1-D10 locked).

New domain entity ``Counterparty`` is distinct from
``ClientDefinition`` / ``ClientRegistry`` — counterparties consume
emitted strategy signals via signal-leasing and pay per-slot subscription
fees; they do NOT have portfolio allocations or any capital routed
through Odum's infra.

SSOT: ``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.md``.
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.signal_broadcast.counterparty import (
    Counterparty,
    CounterpartyStatus,
)
from unified_api_contracts.internal.domain.signal_broadcast.emission import (
    SignalAcknowledgement,
    SignalEmission,
)
from unified_api_contracts.internal.domain.signal_broadcast.entitlements_v2 import (
    CounterpartyEntitlement,
    CounterpartyEntitlementProfile,
    RateLimitConfig,
)
from unified_api_contracts.internal.domain.signal_broadcast.payload import (
    SignalPayloadMinimal,
    SignalPayloadRich,
    SignalPayloadStandard,
)
from unified_api_contracts.internal.domain.signal_broadcast.registry import (
    COUNTERPARTY_ENTITLEMENT_PROFILES,
    COUNTERPARTY_ENTITLEMENTS,
    COUNTERPARTY_REGISTRY,
    RATE_LIMIT_CONFIGS,
    active_counterparties,
    counterparty_for,
    entitled_slots_for,
    entitlement_profile_for,
    entitlements_for,
    rate_limit_config_for,
)
from unified_api_contracts.internal.domain.signal_broadcast.schema_depth import SchemaDepth

__all__ = [
    "COUNTERPARTY_ENTITLEMENTS",
    "COUNTERPARTY_ENTITLEMENT_PROFILES",
    "COUNTERPARTY_REGISTRY",
    "RATE_LIMIT_CONFIGS",
    "Counterparty",
    "CounterpartyEntitlement",
    "CounterpartyEntitlementProfile",
    "CounterpartyStatus",
    "RateLimitConfig",
    "SchemaDepth",
    "SignalAcknowledgement",
    "SignalEmission",
    "SignalPayloadMinimal",
    "SignalPayloadRich",
    "SignalPayloadStandard",
    "active_counterparties",
    "counterparty_for",
    "entitled_slots_for",
    "entitlement_profile_for",
    "entitlements_for",
    "rate_limit_config_for",
]
