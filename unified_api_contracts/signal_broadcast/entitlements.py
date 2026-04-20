"""Counterparty entitlement + rate-limit schemas.

Entitlements pair a counterparty with a slot-label window (``active_from``
/ ``active_to``) for billing + audit. Rate-limit configs name a
token-bucket profile applied per ``(counterparty_id, strategy_id)``
pair per D7 — each :class:`Counterparty` carries a ``rate_limit_ref``
naming one of these profiles.

Both models are frozen so a caller cannot mutate the record after
lookup from the UAC registry.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.signal_broadcast.signal_payload import PayloadDepth

__all__ = [
    "CounterpartyEntitlement",
    "CounterpartyEntitlementProfile",
    "RateLimitConfig",
]


class RateLimitConfig(BaseModel):
    """Token-bucket rate-limit configuration.

    Applied per ``(counterparty_id, strategy_id)`` per D7. A
    :class:`Counterparty.rate_limit_ref` points at a named
    :class:`RateLimitConfig` in the service-local registry at runtime.

    ``burst`` is the bucket capacity; ``requests_per_second`` is the
    refill rate. A counterparty may burst up to ``burst`` emissions
    instantaneously, then sustained throughput is capped at
    ``requests_per_second``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    """Logical profile name — referenced from
    :class:`Counterparty.rate_limit_ref`."""

    requests_per_second: float = Field(gt=0.0)
    """Sustained refill rate, strictly positive."""

    burst: int = Field(gt=0)
    """Bucket capacity, strictly positive."""


class CounterpartyEntitlement(BaseModel):
    """Single counterparty x slot entitlement window.

    ``active_to`` of ``None`` means the entitlement is open-ended; a
    dated window closes the entitlement (contract expiry, revoked after
    missed payment, etc.).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    counterparty_id: str = Field(min_length=1)
    slot_label: str = Field(min_length=1)
    active_from: datetime
    active_to: datetime | None = None


class CounterpartyEntitlementProfile(BaseModel):
    """Full entitlement profile for a counterparty.

    Bundles the per-slot windows with the negotiated
    :class:`PayloadDepth` tier and the rate-limit profile name. Used by
    the emitter at routing time to decide what payload shape to
    construct and whether to throttle.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    counterparty_id: str = Field(min_length=1)
    allowed_slots: frozenset[str] = Field(default_factory=frozenset)
    payload_depth: PayloadDepth
    rate_limit_ref: str = Field(min_length=1)
    entitlements: tuple[CounterpartyEntitlement, ...] = Field(default_factory=tuple)
