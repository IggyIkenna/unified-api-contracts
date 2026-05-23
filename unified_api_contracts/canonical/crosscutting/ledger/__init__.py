"""Global Ledger + PnL Attribution — SSOT schema module.

Four SSOT ledgers share the :class:`~._ledger_row.LedgerRow` base schema.
Type aliases signal writer ownership and GCS partition key:

- :data:`InstructionLedger` — execution-service; ``ledger_type=instruction``
- :data:`PassiveLedger` — strategy-service synthesiser; ``ledger_type=passive``
- :data:`TreasuryLedger` — pending split decision; ``ledger_type=treasury``
- :data:`PricingLedger` — MTDS; ``ledger_type=pricing``

SSOT: ``plans/active/global_ledger_pnl_attribution_discovery_2026_05_21.md``
"""

from __future__ import annotations

from ._enums import AssetClass, Direction, EventOrigin, EventType, OptionRight
from ._ledger_row import (
    CrossClientTransferForbiddenError,
    InstructionLedger,
    LedgerRow,
    PassiveLedger,
    PricingLedger,
    TreasuryLedger,
    assert_no_cross_client_transfer,
)

__all__ = [
    "AssetClass",
    "CrossClientTransferForbiddenError",
    "Direction",
    "EventOrigin",
    "EventType",
    "InstructionLedger",
    "LedgerRow",
    "OptionRight",
    "PassiveLedger",
    "PricingLedger",
    "TreasuryLedger",
    "assert_no_cross_client_transfer",
]
