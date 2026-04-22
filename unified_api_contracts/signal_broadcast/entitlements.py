"""Signal-broadcast entitlement + rate-limit re-exports.

Canonical classes live at
:mod:`unified_api_contracts.internal.domain.signal_broadcast.entitlements_v2`
(kept there to let the internal registry import them without a circular
import through the facade). This file is a thin re-export for the public
surface.
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.signal_broadcast.entitlements_v2 import (
    CounterpartyEntitlement,
    CounterpartyEntitlementProfile,
    RateLimitConfig,
)

__all__ = [
    "CounterpartyEntitlement",
    "CounterpartyEntitlementProfile",
    "RateLimitConfig",
]
