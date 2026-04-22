"""Signal-broadcast counterparty re-export.

Canonical class lives at
:mod:`unified_api_contracts.internal.domain.signal_broadcast.counterparty`
so the internal registry module can import it without a circular import
through the facade. This file is a thin re-export for the public surface.
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.signal_broadcast.counterparty import (
    Counterparty,
    CounterpartyStatus,
)

__all__ = ["Counterparty", "CounterpartyStatus"]
