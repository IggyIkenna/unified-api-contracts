"""Invoice lifecycle schemas for client reporting.

Covers the full invoice state machine (DRAFT → ISSUED → PAID),
dual HWM tracking, and audit trail entries.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class InvoiceStatus(StrEnum):
    """Invoice lifecycle states."""

    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    ACCEPTED = "ACCEPTED"
    DISPUTED = "DISPUTED"
    PAID = "PAID"
    VOIDED = "VOIDED"


class FeeLineType(StrEnum):
    """Classification of fee line items on an invoice."""

    TRADER_FEE = "TRADER_FEE"
    ODUM_FEE = "ODUM_FEE"
    INTRODUCER_FEE = "INTRODUCER_FEE"
    SERVER_COST = "SERVER_COST"


class InvoiceLineItem(BaseModel, frozen=True):
    """Single line item on an invoice."""

    description: str = Field(description="Human-readable description of the charge")
    fee_type: FeeLineType = Field(description="Type of fee")
    amount: Decimal = Field(description="Amount in invoice currency")
    rate_pct: Decimal | None = Field(
        default=None,
        description="Fee rate applied (e.g. 0.40 = 40%), if applicable",
    )
    pnl_basis: Decimal | None = Field(
        default=None,
        description="P&L amount this fee was calculated on",
    )


class Invoice(BaseModel, frozen=True):
    """Client invoice with dual HWM fee calculations.

    Follows the mr_report billing model:
    - Trader fee: % of PnL above trader HWM
    - Odum fee: % of PnL above Odum HWM
    - Introducer fee: % of Odum fee (if configured)
    - Server cost: flat monthly cost for underwater accounts
    """

    invoice_id: str = Field(description="Invoice number (INV-YYYY-NNN format)")
    client_id: str = Field(description="Client identifier (e.g. 'PR', 'ET')")
    client_name: str = Field(default="", description="Human-readable client name")
    period_month: str = Field(description="Billing period (YYYY-MM format)")
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT)
    currency: str = Field(default="USD", description="Invoice currency")

    # AUM and HWM tracking
    opening_aum: Decimal = Field(description="Account value at start of period")
    closing_aum: Decimal = Field(description="Account value at end of period")
    pnl: Decimal = Field(description="closing_aum - opening_aum (before transfers)")
    net_deposits: Decimal = Field(
        default=Decimal("0"),
        description="Net deposits during period (deposits - withdrawals)",
    )
    trader_hwm_before: Decimal = Field(description="Trader HWM at start of period")
    odum_hwm_before: Decimal = Field(description="Odum HWM at start of period")
    trader_hwm_after: Decimal = Field(description="New trader HWM (set on payment)")
    odum_hwm_after: Decimal = Field(description="New Odum HWM (set on payment)")
    is_underwater: bool = Field(
        default=False,
        description="True if closing_aum < both HWMs",
    )

    # Fee breakdown
    line_items: list[InvoiceLineItem] = Field(
        default_factory=list,
        description="Itemized fee breakdown",
    )
    subtotal: Decimal = Field(description="Sum of all line items")
    tax: Decimal = Field(default=Decimal("0"), description="Tax amount (if applicable)")
    total: Decimal = Field(description="subtotal + tax")

    # Timestamps
    created_at: AwareDatetime = Field(description="When the invoice was created")
    issued_at: AwareDatetime | None = Field(default=None, description="When the invoice was sent to client")
    accepted_at: AwareDatetime | None = Field(default=None, description="When the client accepted the invoice")
    paid_at: AwareDatetime | None = Field(default=None, description="When payment was received")
    voided_at: AwareDatetime | None = Field(default=None, description="When the invoice was voided")

    # Payment tracking
    payment_txid: str | None = Field(default=None, description="Blockchain transaction ID of payment")
    notes: str = Field(default="", description="Free-form notes / dispute reason")


class InvoiceHistoryEntry(BaseModel, frozen=True):
    """Audit trail entry for an invoice state transition."""

    invoice_id: str = Field(description="Invoice this entry belongs to")
    action: str = Field(description="Action taken (e.g. 'CREATED', 'ISSUED', 'PAID', 'DISPUTED')")
    actor: str = Field(description="Who performed the action (user ID or 'system')")
    timestamp: AwareDatetime = Field(description="When the action occurred")
    previous_status: InvoiceStatus | None = Field(default=None, description="Status before this action")
    new_status: InvoiceStatus = Field(description="Status after this action")
    note: str = Field(default="", description="Optional note or reason")


class HWMState(BaseModel, frozen=True):
    """Current high-water mark state for a client.

    Tracks both independent HWMs (Odum and Trader) as described
    in client_specifics.md. HWMs advance only when invoices are paid.
    """

    client_id: str = Field(description="Client identifier")
    trader_hwm: Decimal = Field(description="Current trader high-water mark in account currency")
    odum_hwm: Decimal = Field(description="Current Odum high-water mark in account currency")
    last_updated: AwareDatetime = Field(description="When HWMs were last updated")
    last_invoice_id: str = Field(
        default="",
        description="Invoice ID that caused the last HWM update",
    )
    period_month: str = Field(
        default="",
        description="Billing period of last HWM update",
    )
    trader_credits: Decimal = Field(
        default=Decimal("0"),
        description="Accumulated trader credits from underwater periods (negative = owed)",
    )
