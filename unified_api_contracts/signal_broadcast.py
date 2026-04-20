"""Domain facade — signal-broadcast (signal-leasing) contracts.

Consumer repos import from here:

    from unified_api_contracts.signal_broadcast import (
        Counterparty,
        CounterpartyEntitlement,
        SchemaDepth,
        SignalEmission,
        SignalAcknowledgement,
        SignalPayloadMinimal,
        SignalPayloadStandard,
        SignalPayloadRich,
    )

All types live under ``unified_api_contracts.internal.domain.signal_broadcast``
(UAC-internal). The facade re-exports the public surface so consumers
never reach into the ``internal.*`` path.

SSOT plan: ``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.plan.md``.
"""

from unified_api_contracts.internal.domain.signal_broadcast import (
    Counterparty,
    CounterpartyEntitlement,
    SchemaDepth,
    SignalAcknowledgement,
    SignalEmission,
    SignalPayloadMinimal,
    SignalPayloadRich,
    SignalPayloadStandard,
)

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
