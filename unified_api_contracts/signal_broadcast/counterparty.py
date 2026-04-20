"""Counterparty domain entity for signal-broadcast (signal-leasing).

A :class:`Counterparty` is a new domain entity per D9 of
``signal_leasing_broadcast_architecture_2026_04_20.plan.md`` — distinct
from ``ClientDefinition`` / ``ClientRegistry`` (which describe Odum's
paying Investment-Management clients or SaaS subscribers).
Counterparties consume emitted strategy signals via the signal-leasing
channel and pay per-slot subscription fees; they do NOT have portfolio
allocations, share-class mappings, or any capital routed through Odum's
infra.

The :class:`CounterpartyStatus` enum controls the lifecycle gate
(ACTIVE/SUSPENDED/REVOKED). ``SUSPENDED`` is the soft operational pause
(temporary SLA breach, rate-limit violation); ``REVOKED`` is the
permanent termination state used post-contract-termination or after a
security incident. Only ``ACTIVE`` counterparties receive emissions.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

__all__ = ["Counterparty", "CounterpartyStatus"]


class CounterpartyStatus(StrEnum):
    """Lifecycle state of a signal-broadcast counterparty.

    * ``ACTIVE`` — emissions flow normally.
    * ``SUSPENDED`` — temporary pause (SLA breach / ops decision).
      Re-activatable without a new onboarding cycle.
    * ``REVOKED`` — permanent termination. Entitlements are invalidated
      and a fresh onboarding is required to resume.
    """

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class Counterparty(BaseModel):
    """Signal-broadcast counterparty registered in UAC.

    Frozen so callers cannot mutate entitlement / endpoint / status
    after lookup from the registry. Mutations flow through Secret
    Manager + UAC re-import, never in-process.

    The ``hmac_secret_ref`` points at a Secret Manager resource name
    (``projects/{proj}/secrets/{name}``) rather than the secret value
    itself — emitters resolve the live secret through
    ``ApiKeyReloader`` at runtime.

    The ``rate_limit_ref`` is the logical name of a
    :class:`RateLimitConfig` profile applied per ``(counterparty_id,
    strategy_id)`` pair (D7).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    """Stable counterparty identifier — used as ``counterparty_id`` in
    emissions + UTL events."""

    name: str = Field(min_length=1)
    """Human-readable label; displayed in the admin UI and billing
    reports."""

    status: CounterpartyStatus = CounterpartyStatus.ACTIVE
    """Lifecycle gate. Only ``ACTIVE`` receives emissions."""

    endpoint: HttpUrl
    """Primary webhook URL. POST target for emissions."""

    allowed_slots: frozenset[str] = Field(default_factory=frozenset)
    """Allowlist of ``slot_label`` values this counterparty may receive
    (D4 — per-counterparty allowlist in UAC registry)."""

    hmac_secret_ref: str = Field(min_length=1)
    """Secret Manager resource name holding the HMAC-SHA256 signing
    key. The emitter never sees this as a plaintext literal."""

    rate_limit_ref: str = Field(min_length=1)
    """Logical name of the :class:`RateLimitConfig` profile applied per
    ``(counterparty_id, strategy_id)``. Resolved at runtime against the
    service-local rate-limit registry (D7)."""

    created_at: datetime
    updated_at: datetime
