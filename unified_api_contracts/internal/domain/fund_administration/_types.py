"""Fund administration schemas — subscription / redemption / allocation (IM Pooled).

All models are frozen pydantic BaseModels for wire-safe serialisation (matching
the conventions of neighbouring ``client_reporting/nav_snapshot.py`` and
``client_reporting/invoice.py``). Decimal for every money field; AwareDatetime
for every timestamp.

State machines:

    AllocatorSubscription    PENDING → APPROVED | REJECTED → SETTLED
    AllocatorRedemption      PENDING → APPROVED | REJECTED → PROCESSED → SETTLED
    FundAllocation           PENDING → IN_PROGRESS → COMPLETED | FAILED

Idempotency keys: ``subscription_id`` / ``redemption_id`` / ``allocation_id``.

SSOT: codex/14-playbooks/shared-core/treasury-and-subaccount-model.md
      §"Contract surface (to be built — Pooled scope only)".
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class SubscriptionStatus(StrEnum):
    """Subscription lifecycle state.

    PENDING  → initial state after request landed, pre-AML/KYC gate.
    APPROVED → AML/KYC cleared, NAV strike resolved, units computed.
    REJECTED → AML/KYC failed or mandate blocked; terminal.
    SETTLED  → funds landed in treasury wallet, units credited; terminal.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SETTLED = "SETTLED"


class RedemptionStatus(StrEnum):
    """Redemption lifecycle state.

    PENDING   → initial state after request landed, pre-liquidity gate.
    APPROVED  → liquidity + mandate gates cleared, grace-period scheduled.
    REJECTED  → mandate limit exceeded or liquidity unavailable; terminal.
    PROCESSED → grace-period expired, funds wired/transferred, awaiting
                counterparty confirmation.
    SETTLED   → counterparty confirmed receipt; terminal.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSED = "PROCESSED"
    SETTLED = "SETTLED"


class AllocationExecutionStatus(StrEnum):
    """Fund → strategy allocation rebalance execution state.

    PENDING     → allocation directive recorded, not yet dispatched.
    IN_PROGRESS → transfers in flight between treasury / trading wallets.
    COMPLETED   → executed_amount_usd reconciled with target; terminal.
    FAILED      → transfer adapter reported a terminal error; terminal.
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AllocatorSubscription(BaseModel, frozen=True):
    """Investor subscription into an IM Pooled fund.

    ``allocator_id`` == ``client_id``; a subscription joins a specific
    ``(fund_id, share_class)`` pair. ``units_issued`` is populated only on
    the APPROVED → SETTLED transition after NAV strike resolves.
    """

    subscription_id: str = Field(description="Idempotency key — uuid recommended")
    fund_id: str = Field(description="Fund identifier (SSOT in fund-administration-service)")
    allocator_id: str = Field(description="Client id — the allocator = subscribing investor")
    share_class: str = Field(description="Share-class key e.g. 'USDC', 'ETH', 'BTC', 'USD-A'")
    requested_amount_usd: Decimal = Field(description="Requested subscription amount in USD")
    requested_timestamp: AwareDatetime = Field(description="UTC timestamp of request")
    status: SubscriptionStatus = Field(description="Current lifecycle state")
    nav_strike_snapshot_id: str | None = Field(
        default=None,
        description="FundNAVSnapshot id used to price unit issuance; None pre-APPROVED",
    )
    units_issued: Decimal | None = Field(
        default=None,
        description="Units credited on SETTLED; requested_amount_usd / nav_per_unit",
    )
    approval_timestamp: AwareDatetime | None = Field(
        default=None, description="UTC timestamp at which status moved to APPROVED"
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Free-text reason when status=REJECTED; None otherwise",
    )


class AllocatorRedemption(BaseModel, frozen=True):
    """Investor redemption request from an IM Pooled fund.

    Grace-period (default 5 business days, configurable per fund) lets the
    fund liquidate positions before NAV strike. ``cash_amount_due_usd`` is
    resolved at grace-period expiry using a FundNAVSnapshot and redemption
    fees computed via ``FeeStructure``.
    """

    redemption_id: str = Field(description="Idempotency key — uuid recommended")
    fund_id: str = Field(description="Fund identifier")
    allocator_id: str = Field(description="Client id — the allocator = redeeming investor")
    share_class: str = Field(description="Share-class key (must match existing holding)")
    units_to_redeem: Decimal = Field(description="Units the investor wants to redeem")
    destination: str = Field(description="Bank account reference (IBAN / wire ref) or on-chain address")
    requested_timestamp: AwareDatetime = Field(description="UTC timestamp of request")
    status: RedemptionStatus = Field(description="Current lifecycle state")
    grace_period_days: int = Field(
        description="Grace-period length for liquidity preparation (default 5 business days)"
    )
    redemption_nav_snapshot_id: str | None = Field(
        default=None,
        description="FundNAVSnapshot id used at settlement NAV strike",
    )
    cash_amount_due_usd: Decimal | None = Field(
        default=None,
        description="Settlement cash due in USD (units * settlement_nav - fees)",
    )
    settlement_timestamp: AwareDatetime | None = Field(
        default=None, description="UTC timestamp at which status moved to SETTLED"
    )
    settlement_reference: str | None = Field(
        default=None,
        description="On-chain tx hash or wire reference populated on PROCESSED",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Free-text reason when status=REJECTED; None otherwise",
    )


class FundAllocation(BaseModel, frozen=True):
    """Fund → strategy capital allocation directive + execution status.

    Emitted by the ``CapitalRouter`` orchestrator in fund-administration-service
    when ``TreasurySnapshot.allocation_deltas`` indicates a top-up or sweep is
    needed. Idempotent on ``allocation_id``.
    """

    allocation_id: str = Field(description="Idempotency key — uuid recommended")
    fund_id: str = Field(description="Fund identifier")
    share_class: str = Field(description="Share-class key")
    strategy_id: str = Field(description="Strategy receiving the allocation")
    target_amount_usd: Decimal = Field(description="Target strategy balance in USD post-rebalance")
    allocation_timestamp: AwareDatetime = Field(description="UTC timestamp the directive was emitted")
    execution_status: AllocationExecutionStatus = Field(description="Current execution state")
    executed_amount_usd: Decimal | None = Field(
        default=None,
        description="Actual rebalance delta transferred; populated on COMPLETED",
    )
    executed_timestamp: AwareDatetime | None = Field(
        default=None,
        description="UTC timestamp at which execution_status moved to COMPLETED",
    )


class CashAccountMovement(BaseModel, frozen=True):
    """A single row in the allocator's cash-account ledger.

    Flattens a subscription or redemption lifecycle event into a chronological
    ledger row. Consumed by `client-reporting-api` to build the allocator-facing
    cash-account view and by the platform UI history page. Signed `amount_usd`:
    positive for subscriptions (cash into the fund from the allocator's
    perspective) and negative for redemptions.
    """

    reference_id: str = Field(
        description="Subscription or redemption id this movement represents",
    )
    movement_type: str = Field(
        description="'SUBSCRIPTION' or 'REDEMPTION' — which lifecycle emitted this row",
    )
    status: str = Field(
        description="String form of SubscriptionStatus / RedemptionStatus at movement time",
    )
    amount_usd: Decimal = Field(
        description="Signed USD — positive for SUBSCRIPTION, negative for REDEMPTION",
    )
    timestamp: AwareDatetime = Field(
        description="UTC timestamp of the underlying lifecycle event (requested / settled)",
    )


class AllocatorCashAccountView(BaseModel, frozen=True):
    """Derived reporting projection of an allocator's cash position in one share class.

    Built by `client-reporting-api` from the allocator's subscription + redemption
    history (sourced from `fund-administration-service`). Current-balance is
    settled-only (pending flows never move cash). YTD aggregates include only
    SETTLED movements. Consumed by the platform UI history page and by allocator
    REST callers.
    """

    client_id: str = Field(description="Allocator identifier — matches AuthContext.org_id")
    share_class: str = Field(description="Share-class key within the fund")
    current_balance_usd: Decimal = Field(
        description="Net settled-movement balance in USD for this client + share class",
    )
    subscriptions_ytd_usd: Decimal = Field(
        description="Year-to-date settled subscription total in USD",
    )
    redemptions_ytd_usd: Decimal = Field(
        description="Year-to-date settled redemption total in USD (positive magnitude)",
    )
    last_settlement_timestamp: AwareDatetime | None = Field(
        default=None,
        description="Latest settled-movement timestamp across subscriptions + redemptions",
    )
    movements: tuple[CashAccountMovement, ...] = Field(
        default=(),
        description="Chronologically sorted ledger — oldest first",
    )
