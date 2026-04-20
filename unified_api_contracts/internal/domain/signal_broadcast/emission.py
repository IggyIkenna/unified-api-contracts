"""Emission + acknowledgement envelopes for counterparty signal delivery."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.domain.signal_broadcast.payload import (
    SignalPayloadMinimal,
    SignalPayloadRich,
    SignalPayloadStandard,
)
from unified_api_contracts.internal.domain.signal_broadcast.schema_depth import SchemaDepth

__all__ = ["SignalAcknowledgement", "SignalEmission"]


class SignalEmission(BaseModel):
    """Envelope posted to the counterparty webhook endpoint.

    ``emission_id`` doubles as the idempotency key (D5 — at-least-once
    with idempotency key). Retries reuse the same ``emission_id`` and
    increment ``delivery_attempt``.

    ``signal_payload`` is a discriminated union on :class:`SchemaDepth`.
    The signing-layer hash is stored in ``hmac_signature`` so the webhook
    body is self-verifying for the counterparty.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    emission_id: str
    strategy_id: str
    slot_label: str
    counterparty_id: str
    emission_timestamp: datetime
    schema_depth: SchemaDepth
    signal_payload: SignalPayloadMinimal | SignalPayloadStandard | SignalPayloadRich
    delivery_attempt: int = Field(default=1, ge=1)
    hmac_signature: str


class SignalAcknowledgement(BaseModel):
    """Counterparty-returned ack for a single emission.

    Emitted by the counterparty's webhook receiver when it has
    durably persisted the signal (``processed``) or is rejecting it
    (``rejected``; e.g. wrong schema, allowlist mismatch, duplicate).

    ``received`` is the intermediate state — the counterparty has the
    bytes but has not yet committed them. Useful for SLA tracking.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    emission_id: str
    counterparty_id: str
    ack_timestamp: datetime
    status: Literal["received", "processed", "rejected"]
    error_detail: str | None = None
