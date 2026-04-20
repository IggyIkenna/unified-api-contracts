"""DTOs for the signal-broadcast UTL lifecycle events.

UTL registers two event names in
``unified_trading_library.events.event_types``:

* ``STRATEGY_SIGNAL_EMITTED_EXTERNAL`` — emitted when the broadcaster
  ships a :class:`SignalPayload` to a counterparty.
* ``STRATEGY_SIGNAL_ACKNOWLEDGED`` — emitted when a counterparty
  acknowledges receipt + processing.

Both carry structured ``details`` payloads; the Pydantic models here
are the canonical shape for those payloads, so strategy-service (and
consumer analytics surfaces) can validate them on the way in/out.

The ``signature`` field on :class:`StrategySignalEmittedExternal` is
the HMAC-SHA256 hex digest returned by
``unified_trading_library.security.hmac_signing.build_signed_envelope``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.signal_broadcast.signal_payload import SignalPayload

__all__ = [
    "AckSource",
    "StrategySignalAcknowledged",
    "StrategySignalEmittedExternal",
]


class AckSource(StrEnum):
    """Where an ack came from.

    * ``WEBHOOK_RESPONSE`` — 2xx + ack body returned on the original
      webhook POST (happy path).
    * ``REST_PULL_ACK`` — counterparty called the REST-pull ack
      endpoint explicitly (fallback reconciliation path).
    * ``OUT_OF_BAND`` — manual ack logged by ops (rare; forensic).
    """

    WEBHOOK_RESPONSE = "WEBHOOK_RESPONSE"
    REST_PULL_ACK = "REST_PULL_ACK"
    OUT_OF_BAND = "OUT_OF_BAND"


class StrategySignalEmittedExternal(BaseModel):
    """``details`` payload for the ``STRATEGY_SIGNAL_EMITTED_EXTERNAL``
    UTL event.

    The emitter serialises this via ``model_dump(mode="json")`` and
    passes it as the ``details`` dict on
    ``log_event("STRATEGY_SIGNAL_EMITTED_EXTERNAL", details=...)``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slot_label: str = Field(min_length=1)
    counterparty_id: str = Field(min_length=1)
    payload: SignalPayload
    signature: str = Field(min_length=1)
    """HMAC-SHA256 hex digest returned by
    :func:`unified_trading_library.security.hmac_signing.build_signed_envelope`."""

    idempotency_key: UUID
    """Same UUID that will appear on :class:`DeliveryAttempt` rows for
    this emission. Retries reuse it."""

    emitted_at: datetime
    """UTC timestamp at which the emitter signed + queued the
    payload."""


class StrategySignalAcknowledged(BaseModel):
    """``details`` payload for the ``STRATEGY_SIGNAL_ACKNOWLEDGED`` UTL
    event."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slot_label: str = Field(min_length=1)
    counterparty_id: str = Field(min_length=1)
    idempotency_key: UUID
    """Mirror of :class:`StrategySignalEmittedExternal.idempotency_key`
    so the two events can be joined for SLA analytics."""

    acked_at: datetime
    """UTC timestamp at which the counterparty's ack was received."""

    ack_source: AckSource
    """Which pathway produced the ack."""
