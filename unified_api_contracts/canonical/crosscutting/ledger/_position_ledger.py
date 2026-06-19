"""PositionLedger — the derived as-if-filled position/balance view.

`PositionLedgerRow` is NOT an SSOT ledger. It is the materialised
``Σ delta GROUP BY (account, asset, venue, instrument)`` projection of the
``InstructionLedger`` (the trade tape) + ``PassiveLedger`` (accruals), marked by
the ``PricingLedger``. It is the operator-facing "current positions / balances"
surface — updated as-if-filled — that a paper run keeps alongside the historical
trade tape.

One row = the net position of one asset on one (account, venue, instrument) at
one ``as_of`` instant. Balances per venue / instrument / share_class are
``GROUP BY`` rollups of these rows.

GCS partition key: ``ledger_type=position``.

SSOT: ``codex/09-strategy/operational/paper-batch-live-reconciliation.md`` §4.3 +
``codex/04-architecture/global-ledger-architecture.md`` (the derived views).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.canonical.crosscutting.ledger._enums import AssetClass


class PositionLedgerRow(BaseModel):
    """Net as-if-filled position of one asset on one (account, venue, instrument).

    All datetime fields are tz-aware UTC. ``net_qty`` is the signed sum of all
    ``LedgerRow.delta`` for this key (positive = long/supplied, negative =
    short/borrowed). ``realized_pnl`` accumulates closed-position PnL;
    ``unrealized_pnl`` = ``net_qty * (mark_price - avg_cost)`` when both are
    present.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: datetime = Field(description="UTC instant this snapshot is valid at.")
    account_id: str = Field(description="The custody/venue account holding the position.")
    client_id: str = Field(description="Single client_id — never cross-client.")
    venue: str = Field(description="UAC canonical venue.")
    instrument_key: str = Field(description="VENUE:INSTRUMENT_TYPE:SYMBOL.")
    asset_canonical_id: str = Field(description="Canonical asset id (matches the ledger).")
    asset_symbol: str
    asset_class: AssetClass
    share_class: str = Field(
        description="The wallet-hierarchy share_class (USDC/ETH/SOL/BTC) this "
        "position rolls up under (codex wallet-hierarchy-and-capital-flow).",
    )
    net_qty: Decimal = Field(description="Σ LedgerRow.delta for this key (signed).")
    avg_cost: Decimal | None = Field(
        default=None,
        description="VWAP entry cost in quote currency (None for non-priced legs).",
    )
    mark_price: Decimal | None = Field(
        default=None,
        description="Current mark from the PricingLedger (None if unmarked).",
    )
    quote_currency: str | None = Field(default=None, description="Quote ccy for cost/mark.")
    realized_pnl: Decimal = Field(
        default=Decimal("0"),
        description="Accumulated realised PnL from closed quantity, in quote ccy.",
    )
    unrealized_pnl: Decimal = Field(
        default=Decimal("0"),
        description="net_qty * (mark_price - avg_cost) when both present, else 0.",
    )


__all__ = ["PositionLedgerRow"]
