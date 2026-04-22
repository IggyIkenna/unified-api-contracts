"""Signal-broadcast payload re-exports.

Canonical module lives at
:mod:`unified_api_contracts.internal.domain.signal_broadcast.signal_payload`
so the internal registry + entitlements modules can import
``PayloadDepth`` without a circular import through the facade.
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.signal_broadcast.signal_payload import (
    DirectionalIntent,
    PayloadDepth,
    SignalPayload,
)

__all__ = ["DirectionalIntent", "PayloadDepth", "SignalPayload"]
