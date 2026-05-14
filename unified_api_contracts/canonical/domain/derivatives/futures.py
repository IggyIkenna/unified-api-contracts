"""TradFi futures contract canonical schema — hard-required expiry / lifecycle.

`CanonicalFuturesContract` is the per-contract identity record (one row per
futures contract, e.g. "ESH26"). Hard-required date fields drive contract roll
detection + odds settlement timing + lifecycle-phase-aware features.

Schema design references the predictions market lifecycle (gold standard) which
already has `market_created_at` / `resolution_time` / `settlement_time` as
hard-required fields per `predictions_master_2026_05_07.md`. This module brings
tradfi futures to the same bar.

## Plan SSOT

`plans/active/tradfi_canonical_futures_contract_hard_required_fields_2026_05_13.md`
(Phase 1A: greenfield class + enum)

## Cross-plan banner

This is a NEW schema; no migration needed for futures (Q1). The companion
flip on `CanonicalOptionsChainEntry.expiration` nullable→required (Q2) ships
separately in Phase 1B once per-callsite expiration-derivation engineering is
done (8 callsites; 2 known to need expiry parsing from instrument symbols).
"""

from __future__ import annotations

from datetime import date as _date
from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, Field

from .._base import CanonicalBase


class FuturesContractLifecyclePhase(StrEnum):
    """Closed-set lifecycle phase for a futures contract.

    Phase transitions are driven by relative ordering of (today, expiry_date,
    last_trading_date, first_notice_date, delivery_date, settlement_date):

    - `LISTED`: Contract is listed and tradeable, but pre-active (long-dated).
    - `ACTIVE`: Front-month or near-active contract; primary roll target.
    - `IN_FIRST_NOTICE`: Past `first_notice_date`; physical-delivery risk for
      longs. Most algorithmic strategies roll BEFORE this phase to avoid
      delivery.
    - `IN_DELIVERY`: Past `delivery_date`; physical settlement in progress.
    - `EXPIRED`: Past `expiry_date` / `last_trading_date`; no longer tradeable.
    - `SETTLED`: Cash/physical settlement complete; final P&L booked.
    """

    LISTED = "listed"
    ACTIVE = "active"
    IN_FIRST_NOTICE = "in_first_notice"
    IN_DELIVERY = "in_delivery"
    EXPIRED = "expired"
    SETTLED = "settled"


class CanonicalFuturesContract(CanonicalBase):
    """Per-contract futures identity record with hard-required lifecycle dates.

    One row per (venue, root, contract_month, contract_year). Used by:
    - instruments-service futures factory (write-time stamp)
    - market-tick-data-service Databento bridge (read for staleness gates)
    - features-service (lifecycle-phase-aware contract roll features)
    - strategy-service (FuturesRollInstruction binding via lifecycle_phase)

    All date fields carry explicit timezone awareness. CME products use
    America/Chicago for delivery / first-notice dates and CME settlement
    convention for `settlement_date`; non-CME venues use venue-local timezone.
    """

    venue: str = Field(description="Exchange venue code (e.g. 'CME', 'ICE', 'CBOE').")
    root: str = Field(description="Futures root symbol (e.g. 'ES', 'CL', 'GC').")
    contract_symbol: str = Field(description="Full contract symbol (e.g. 'ESH26' = E-mini S&P 500 March 2026).")
    contract_month: int = Field(
        ge=1, le=12, description="Contract delivery month (1-12). 'H' = 3, 'M' = 6, 'U' = 9, 'Z' = 12."
    )
    contract_year: int = Field(ge=2000, le=2100, description="Contract delivery year (4 digits, e.g. 2026).")
    expiry_date: _date = Field(
        description=(
            "Date the contract expires and is no longer tradeable. For physically-settled "
            "contracts, equals last_trading_date for most products; for cash-settled, may "
            "differ slightly per venue rulebook."
        )
    )
    last_trading_date: _date = Field(
        description=(
            "Last day on which the contract may be traded. Bounds the live-pipeline window; "
            "after this date, the contract feed goes silent (no more ticks)."
        )
    )
    first_notice_date: _date = Field(
        description=(
            "First date on which a long position can be assigned for physical delivery. "
            "Most algorithmic strategies must roll out of the contract BEFORE this date "
            "to avoid receiving delivery."
        )
    )
    delivery_date: _date = Field(
        description=(
            "Date on which physical delivery (or cash settlement equivalent) is scheduled. "
            "For cash-settled contracts, this is the settlement-fixing date."
        )
    )
    settlement_date: _date = Field(
        description=(
            "Date on which final cash flows settle. Always >= delivery_date; typically "
            "delivery_date + 1-3 business days depending on venue convention."
        )
    )
    lifecycle_phase: FuturesContractLifecyclePhase = Field(
        description=(
            "Current lifecycle phase derived from (today, expiry_date, last_trading_date, "
            "first_notice_date, delivery_date, settlement_date)."
        )
    )
    tick_size: Decimal | None = Field(default=None, description="Minimum price increment (per venue rulebook).")
    contract_size: Decimal | None = Field(
        default=None,
        description="Notional contract size (e.g. ES = $50 x index; CL = 1000 barrels).",
    )
    listed_at: AwareDatetime | None = Field(
        default=None,
        description="Timestamp the contract was first listed (informational; pre-LISTED state).",
    )
    schema_version: str = "1.0"


__all__ = [
    "CanonicalFuturesContract",
    "FuturesContractLifecyclePhase",
]
