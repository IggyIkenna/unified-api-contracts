"""Counterparty domain entity for signal leasing.

A ``Counterparty`` is a *new domain entity* (D9) — distinct from
``ClientDefinition`` / ``ClientRegistry`` (which describe Odum's paying
Investment-Management clients or SaaS subscribers). Counterparties
consume emitted strategy signals via the signal-leasing channel and pay
per-slot subscription fees; they do NOT have portfolio allocations,
share-class mappings, or any capital routed through Odum's infra.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from unified_api_contracts.internal.domain.signal_broadcast.schema_depth import SchemaDepth

__all__ = ["Counterparty"]


class Counterparty(BaseModel):
    """Signal-leasing counterparty registered in UAC.

    Frozen so callers cannot mutate entitlement / endpoint after lookup
    from ``COUNTERPARTY_REGISTRY``. Mutations flow through Secret-Manager
    + UAC re-import, never in-process.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    """Stable UUID — used as ``counterparty_id`` in emissions + events."""

    name: str
    """Human-readable label; displayed in admin UI + billing reports."""

    endpoint: HttpUrl
    """Webhook URL. POST target for :class:`SignalEmission` deliveries."""

    auth_method: Literal["hmac_webhook"] = "hmac_webhook"
    """Auth scheme. Extensible later (mTLS / OAuth); launch tier is HMAC only."""

    hmac_secret_ref: str
    """Secret Manager resource name holding the HMAC-SHA256 signing key."""

    allowed_slots: frozenset[str] = Field(default_factory=frozenset)
    """Allowlist of ``slot_label`` values the counterparty may receive."""

    schema_depth: SchemaDepth
    """Per-counterparty payload shape. Fixed at onboarding."""

    active: bool = True
    """Soft-disable switch. Inactive counterparties receive zero emissions."""

    rate_limit_per_strategy_per_sec: int = Field(default=10, ge=1)
    """Token-bucket rate limit per ``(counterparty_id, strategy_id)`` pair (D7)."""

    created_at: datetime
    updated_at: datetime
