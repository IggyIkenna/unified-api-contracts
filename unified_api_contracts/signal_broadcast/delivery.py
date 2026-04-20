"""Delivery transport configs + attempt tracking.

Models here describe the *transport* layer of signal-broadcast — how a
:class:`SignalPayload` is shipped to a counterparty and how that
delivery is tracked.

Two transports exist (D2 — hybrid):

* :class:`WebhookDeliveryConfig` — webhook HTTP POST (primary, emitter
  push). The emitter signs the payload with HMAC-SHA256 and POSTs it to
  ``endpoint``; the counterparty ACKs with 2xx.
* :class:`RestPullDeliveryConfig` — REST pull (fallback, counterparty
  push). The counterparty polls a strategy-service-hosted endpoint for
  queued unacknowledged emissions. Used for reconciliation + backfill
  after counterparty-side outages.

Every delivery produces one or more :class:`DeliveryAttempt` rows
(keyed by ``idempotency_key`` UUID) tracking attempt number + status
transitions. :class:`DeliveryStatus` is the state machine:
``PENDING -> SENT -> ACKED`` on the happy path; ``FAILED`` at any point
if the transport / ack fails permanently.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

__all__ = [
    "DeliveryAttempt",
    "DeliveryStatus",
    "RestPullDeliveryConfig",
    "WebhookDeliveryConfig",
]


class DeliveryStatus(StrEnum):
    """State-machine for a single :class:`DeliveryAttempt`.

    * ``PENDING`` — queued, not yet shipped.
    * ``SENT`` — transport layer reported 2xx but no application-level
      ack has been received yet. For webhook transport this collapses
      immediately into ``ACKED``; for REST pull it persists until the
      counterparty calls the ack endpoint.
    * ``ACKED`` — counterparty application-level acknowledgement
      received.
    * ``FAILED`` — permanent failure after retry budget exhausted, or
      hard rejection (4xx non-429, allowlist mismatch, signature
      mismatch).
    """

    PENDING = "PENDING"
    SENT = "SENT"
    ACKED = "ACKED"
    FAILED = "FAILED"


class WebhookDeliveryConfig(BaseModel):
    """HTTP POST webhook transport config (D2 primary).

    ``max_retries`` caps the exponential-backoff retry budget per
    emission; ``retry_backoff_base_seconds`` is the base factor for
    ``backoff = base * (2 ** attempt)``; ``timeout_seconds`` applies
    per individual HTTP request.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    transport: Literal["webhook"] = "webhook"
    endpoint: HttpUrl
    max_retries: int = Field(default=3, ge=0)
    retry_backoff_base_seconds: float = Field(default=1.0, gt=0.0)
    timeout_seconds: float = Field(default=5.0, gt=0.0)


class RestPullDeliveryConfig(BaseModel):
    """REST pull transport config (D2 fallback).

    The strategy-service hosts an HMAC-authenticated pull endpoint at
    ``pull_endpoint_path``; counterparties poll it at
    ``poll_interval_seconds`` cadence. Queued (unacked) emissions are
    retained for ``retention_hours`` before being purged from the
    per-counterparty ring buffer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    transport: Literal["rest_pull"] = "rest_pull"
    pull_endpoint_path: str = Field(min_length=1)
    poll_interval_seconds: float = Field(default=15.0, gt=0.0)
    retention_hours: int = Field(default=24, gt=0)


class DeliveryAttempt(BaseModel):
    """One attempt to deliver an emission to a counterparty.

    ``idempotency_key`` is a deterministic UUID derived from the
    emission (uuid5 over ``(counterparty_id, slot_label, emitted_at)``
    — the exact construction is set by the emitter). Retries reuse the
    same key + increment ``attempt_number``; counterparties MUST treat
    duplicate keys as idempotent.

    ``completed_at`` is ``None`` until the attempt reaches a terminal
    state (``ACKED`` or ``FAILED``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    idempotency_key: UUID
    """Deterministic UUID uniquely identifying this logical emission.
    Stable across retries; counterparty-side dedup hinges on it."""

    attempt_number: int = Field(ge=1)
    """1-indexed attempt counter. Retries increment."""

    status: DeliveryStatus
    """Current state-machine position."""

    started_at: datetime
    """UTC timestamp at which this attempt was initiated."""

    completed_at: datetime | None = None
    """UTC terminal-state timestamp. ``None`` while the attempt is in
    ``PENDING`` or ``SENT``."""

    http_status_code: int | None = None
    """Transport-level HTTP status for webhook attempts. ``None`` for
    REST pull attempts or attempts still in ``PENDING``."""

    error_reason: str | None = None
    """Short diagnostic classifier (matches UAC
    ``classify_venue_error()`` output codes). ``None`` on success."""
