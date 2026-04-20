"""Signal-broadcast internal domain schemas (Phase 2, D1-D10 locked).

New domain entity ``Counterparty`` is distinct from
``ClientDefinition`` / ``ClientRegistry`` — counterparties consume
emitted strategy signals via signal-leasing and pay per-slot subscription
fees; they do NOT have portfolio allocations or any capital routed
through Odum's infra.

SSOT: ``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.plan.md``.
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.signal_broadcast.counterparty import Counterparty
from unified_api_contracts.internal.domain.signal_broadcast.emission import (
    SignalAcknowledgement,
    SignalEmission,
)
from unified_api_contracts.internal.domain.signal_broadcast.entitlement import (
    CounterpartyEntitlement,
)
from unified_api_contracts.internal.domain.signal_broadcast.payload import (
    SignalPayloadMinimal,
    SignalPayloadRich,
    SignalPayloadStandard,
)
from unified_api_contracts.internal.domain.signal_broadcast.schema_depth import SchemaDepth

__all__ = [
    "Counterparty",
    "CounterpartyEntitlement",
    "SchemaDepth",
    "SignalAcknowledgement",
    "SignalEmission",
    "SignalPayloadMinimal",
    "SignalPayloadRich",
    "SignalPayloadStandard",
]
