"""Signal-broadcast public facade.

Consumer repos import the public surface from this facade:

    from unified_api_contracts.signal_broadcast import (
        Counterparty,
        CounterpartyStatus,
        CounterpartyEntitlement,
        CounterpartyEntitlementProfile,
        RateLimitConfig,
        DeliveryAttempt,
        DeliveryStatus,
        WebhookDeliveryConfig,
        RestPullDeliveryConfig,
        PayloadDepth,
        SignalPayload,
        DirectionalIntent,
        StrategySignalEmittedExternal,
        StrategySignalAcknowledged,
        AckSource,
    )

Legacy symbols from the 2026-04-20 Phase 2a v1 ship under
``unified_api_contracts.internal.domain.signal_broadcast`` are also
re-exported here (``SchemaDepth``, ``SignalEmission``,
``SignalAcknowledgement``, ``SignalPayloadMinimal`` / ``Standard`` /
``Rich``, ``COUNTERPARTY_REGISTRY``, ``COUNTERPARTY_ENTITLEMENTS``,
``active_counterparties``, ``counterparty_for``, ``entitled_slots_for``,
``entitlements_for``) so existing strategy-service imports keep
resolving while Phase 3 consumers migrate to the new surface.

SSOT plan:
``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.plan.md``.
"""

from __future__ import annotations

# --- Legacy surface (Phase 2a v1 — retained for strategy-service) ----
from unified_api_contracts.internal.domain.signal_broadcast.emission import (
    SignalAcknowledgement as SignalAcknowledgement,
)
from unified_api_contracts.internal.domain.signal_broadcast.emission import (
    SignalEmission as SignalEmission,
)
from unified_api_contracts.internal.domain.signal_broadcast.payload import (
    SignalPayloadMinimal as SignalPayloadMinimal,
)
from unified_api_contracts.internal.domain.signal_broadcast.payload import (
    SignalPayloadRich as SignalPayloadRich,
)
from unified_api_contracts.internal.domain.signal_broadcast.payload import (
    SignalPayloadStandard as SignalPayloadStandard,
)
from unified_api_contracts.internal.domain.signal_broadcast.registry import (
    COUNTERPARTY_ENTITLEMENTS as COUNTERPARTY_ENTITLEMENTS,
)
from unified_api_contracts.internal.domain.signal_broadcast.registry import (
    COUNTERPARTY_REGISTRY as COUNTERPARTY_REGISTRY,
)
from unified_api_contracts.internal.domain.signal_broadcast.registry import (
    active_counterparties as active_counterparties,
)
from unified_api_contracts.internal.domain.signal_broadcast.registry import (
    counterparty_for as counterparty_for,
)
from unified_api_contracts.internal.domain.signal_broadcast.registry import (
    entitled_slots_for as entitled_slots_for,
)
from unified_api_contracts.internal.domain.signal_broadcast.registry import (
    entitlements_for as entitlements_for,
)
from unified_api_contracts.internal.domain.signal_broadcast.schema_depth import (
    SchemaDepth as SchemaDepth,
)

# --- New surface (Phase 2a v2 per task spec) ------------------------
# NOTE: Counterparty comes from the legacy internal.domain path during the
# migration window — strategy-service router.py / emitter.py / audit.py still
# reference the legacy ``schema_depth`` + ``active`` fields on the type. The
# v2 Counterparty (with ``rate_limit_ref`` + ``CounterpartyStatus``) is reached
# as ``CounterpartyV2`` below. Once strategy-service migrates to the v2 shape
# the v1 class is deleted and this alias flips back.
from unified_api_contracts.internal.domain.signal_broadcast.counterparty import (
    Counterparty as Counterparty,
)
from unified_api_contracts.signal_broadcast.counterparty import (
    Counterparty as CounterpartyV2,
)
from unified_api_contracts.signal_broadcast.counterparty import (
    CounterpartyStatus as CounterpartyStatus,
)
from unified_api_contracts.signal_broadcast.delivery import (
    DeliveryAttempt as DeliveryAttempt,
)
from unified_api_contracts.signal_broadcast.delivery import (
    DeliveryStatus as DeliveryStatus,
)
from unified_api_contracts.signal_broadcast.delivery import (
    RestPullDeliveryConfig as RestPullDeliveryConfig,
)
from unified_api_contracts.signal_broadcast.delivery import (
    WebhookDeliveryConfig as WebhookDeliveryConfig,
)
from unified_api_contracts.signal_broadcast.entitlements import (
    CounterpartyEntitlement as CounterpartyEntitlement,
)
from unified_api_contracts.signal_broadcast.entitlements import (
    CounterpartyEntitlementProfile as CounterpartyEntitlementProfile,
)
from unified_api_contracts.signal_broadcast.entitlements import (
    RateLimitConfig as RateLimitConfig,
)
from unified_api_contracts.signal_broadcast.events import (
    AckSource as AckSource,
)
from unified_api_contracts.signal_broadcast.events import (
    StrategySignalAcknowledged as StrategySignalAcknowledged,
)
from unified_api_contracts.signal_broadcast.events import (
    StrategySignalEmittedExternal as StrategySignalEmittedExternal,
)
from unified_api_contracts.signal_broadcast.observability import (
    BacktestPaperLiveEnvelope as BacktestPaperLiveEnvelope,
)
from unified_api_contracts.signal_broadcast.observability import (
    BacktestPaperLiveRow as BacktestPaperLiveRow,
)
from unified_api_contracts.signal_broadcast.observability import (
    DeliveryHealth as DeliveryHealth,
)
from unified_api_contracts.signal_broadcast.observability import (
    DeliveryHealthEnvelope as DeliveryHealthEnvelope,
)
from unified_api_contracts.signal_broadcast.observability import (
    PnlAttributionEnvelope as PnlAttributionEnvelope,
)
from unified_api_contracts.signal_broadcast.observability import (
    PnlAttributionReport as PnlAttributionReport,
)
from unified_api_contracts.signal_broadcast.observability import (
    PnlAttributionRow as PnlAttributionRow,
)
from unified_api_contracts.signal_broadcast.signal_payload import (
    DirectionalIntent as DirectionalIntent,
)
from unified_api_contracts.signal_broadcast.signal_payload import (
    PayloadDepth as PayloadDepth,
)
from unified_api_contracts.signal_broadcast.signal_payload import (
    SignalPayload as SignalPayload,
)

__all__ = [
    "COUNTERPARTY_ENTITLEMENTS",
    "COUNTERPARTY_REGISTRY",
    "AckSource",
    "BacktestPaperLiveEnvelope",
    "BacktestPaperLiveRow",
    "Counterparty",
    "CounterpartyEntitlement",
    "CounterpartyEntitlementProfile",
    "CounterpartyStatus",
    "DeliveryAttempt",
    "DeliveryHealth",
    "DeliveryHealthEnvelope",
    "DeliveryStatus",
    "DirectionalIntent",
    "PayloadDepth",
    "PnlAttributionEnvelope",
    "PnlAttributionReport",
    "PnlAttributionRow",
    "RateLimitConfig",
    "RestPullDeliveryConfig",
    "SchemaDepth",
    "SignalAcknowledgement",
    "SignalEmission",
    "SignalPayload",
    "SignalPayloadMinimal",
    "SignalPayloadRich",
    "SignalPayloadStandard",
    "StrategySignalAcknowledged",
    "StrategySignalEmittedExternal",
    "WebhookDeliveryConfig",
    "active_counterparties",
    "counterparty_for",
    "entitled_slots_for",
    "entitlements_for",
]
