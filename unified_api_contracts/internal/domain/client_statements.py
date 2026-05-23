"""Client daily statement schema.

SSOT for the ClientDailyStatement Pydantic dataclass written by
``unified_trading_library.post_trade.statement_emitter.DailyStatementEmitter``.

Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 5.A.

GCS path:
  gs://{pid}-client-statements/{client_id}/{YYYY-MM-DD}/statement.parquet
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from unified_api_contracts.internal.domain.hwm_ledger import (
    FeeRecognitionRow,
    HighWaterMarkLedgerRow,
)


@dataclass(frozen=True)
class ClientDailyStatement:
    """Daily statement for a single client.

    Written by ``DailyStatementEmitter.emit_daily_statement()`` once per
    (client_id, as_of_date).

    Fields:
        client_id: Client identifier.
        as_of_date: Statement date (UTC calendar date).
        positions: symbol → quantity held at end of day.
        pnl_today_usd: Total PnL for the day (USD).
        fees_today_breakdown: fee_type → USD amount for the day.
        hwm_section: All HighWaterMarkLedgerRow snapshots for this client across share classes.
        recent_crystallizations: share_class_id → most recent FeeRecognitionRow (may be None
            if no crystallization has occurred for that share class yet).
        generated_at: Wall-clock timestamp when statement was generated (UTC-aware).
    """

    client_id: str
    as_of_date: date
    positions: dict[str, Decimal]
    pnl_today_usd: Decimal
    fees_today_breakdown: dict[str, Decimal]
    hwm_section: list[HighWaterMarkLedgerRow]
    recent_crystallizations: dict[str, FeeRecognitionRow | None]
    generated_at: datetime = field(
        default_factory=lambda: __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc)
    )

    def total_fees_today_usd(self) -> Decimal:
        """Sum of all fee types for the day."""
        return sum(self.fees_today_breakdown.values(), Decimal("0"))

    def net_pnl_today_usd(self) -> Decimal:
        """PnL after fees."""
        return self.pnl_today_usd - self.total_fees_today_usd()

    def crystallization_summary(self) -> dict[str, Decimal]:
        """Return share_class_id → perf_fee_amount for share classes with a recent crystallization.

        Returns empty dict for share classes with no crystallization.
        """
        result: dict[str, Decimal] = {}
        for sc_id, row in self.recent_crystallizations.items():
            if row is not None:
                result[sc_id] = row.amount_usd
        return result
