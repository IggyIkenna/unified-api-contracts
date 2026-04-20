"""Counterparty-by-slot entitlement record.

The ``Counterparty.allowed_slots`` field is the compact allowlist used at
routing time. For billing + audit we also keep a time-windowed history
record (activated when, deactivated when). Store-of-record is the UAC
registry loaded at strategy-service boot.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

__all__ = ["CounterpartyEntitlement"]


class CounterpartyEntitlement(BaseModel):
    """Single counterparty x slot entitlement window.

    ``active_to`` of ``None`` means the entitlement is open-ended; a
    dated window closes the entitlement (expires by contract, revoked
    after missed payment, etc.).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    counterparty_id: str
    slot_label: str
    active_from: datetime
    active_to: datetime | None = None
