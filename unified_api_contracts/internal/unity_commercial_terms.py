"""Unity meta-broker commercial terms (SSOT).

Pulled from Unity pricing disclosure 2026-04-17 via
quant-portal.olesportsresearch.com/unity.

These terms govern API access + routing economics, independent of the
per-book commissions in :mod:`unified_api_contracts.internal.unity_child_books`.

Usage:
    from unified_api_contracts.internal import UNITY_COMMERCIAL_TERMS
    usd_terms = UNITY_COMMERCIAL_TERMS.for_currency("USD")
    # -> subscription 2600, waiver 260_000, connection fee 550
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

SupportedCurrency = Literal["EUR", "GBP", "USD", "CNY"]


@dataclass(frozen=True, slots=True)
class UnityCurrencyTerms:
    """Unity commercial terms for a single billing currency."""

    currency: SupportedCurrency
    monthly_subscription: Decimal
    #: Effective turnover (sum of absolute win + absolute loss amounts per
    #: Unity's definition — NOT gross traded volume) required in a given
    #: calendar month to waive that month's subscription fee.
    monthly_turnover_waiver: Decimal
    #: One-off fee to receive demo account credentials + free 2-month
    #: integration-period access. Non-refundable.
    connection_fee: Decimal


@dataclass(frozen=True, slots=True)
class UnityCommercialTerms:
    """Unity API access + billing terms (meta-broker-wide)."""

    #: Per-currency subscription / waiver / connection fees.
    currencies: tuple[UnityCurrencyTerms, ...]
    #: Months of free API access granted after paying the connection fee and
    #: receiving demo credentials. After this runs out the monthly
    #: subscription starts unless turnover waiver is met.
    free_integration_months: int
    #: Day-of-month cutoff for the prorated billing rule: if production
    #: cutover happens on or before this day, 50% of that month's fee is
    #: charged AND turnover requirement is halved for that month.
    prorated_cutoff_day: int
    #: Calendar day on/around which monthly subscription state is reviewed
    #: and previous month's fee is refunded/retained.
    subscription_review_day: int
    #: Required rollover multiple on the production-account deposit before
    #: first withdrawal (Unity's bond/rollover rule).
    deposit_rollover_multiple: int
    #: USD bond posted at production onboarding. Refundable at the lifetime
    #: turnover threshold.
    production_deposit_usd: Decimal
    #: Lifetime effective turnover (USD) at which the production deposit
    #: becomes refundable.
    production_deposit_refund_turnover_usd: Decimal

    def for_currency(self, currency: SupportedCurrency) -> UnityCurrencyTerms:
        for c in self.currencies:
            if c.currency == currency:
                return c
        msg = f"Unity does not bill in {currency!r}; supported: {[c.currency for c in self.currencies]}"
        raise KeyError(msg)


UNITY_COMMERCIAL_TERMS: UnityCommercialTerms = UnityCommercialTerms(
    currencies=(
        UnityCurrencyTerms(
            currency="EUR",
            monthly_subscription=Decimal("2500"),
            monthly_turnover_waiver=Decimal("250000"),
            connection_fee=Decimal("500"),
        ),
        UnityCurrencyTerms(
            currency="GBP",
            monthly_subscription=Decimal("2200"),
            monthly_turnover_waiver=Decimal("220000"),
            connection_fee=Decimal("450"),
        ),
        UnityCurrencyTerms(
            currency="USD",
            monthly_subscription=Decimal("2600"),
            monthly_turnover_waiver=Decimal("260000"),
            connection_fee=Decimal("550"),
        ),
        UnityCurrencyTerms(
            currency="CNY",
            monthly_subscription=Decimal("20000"),
            monthly_turnover_waiver=Decimal("2000000"),
            connection_fee=Decimal("4000"),
        ),
    ),
    free_integration_months=2,
    prorated_cutoff_day=15,
    subscription_review_day=2,
    deposit_rollover_multiple=1,
    production_deposit_usd=Decimal("10800"),
    production_deposit_refund_turnover_usd=Decimal("5300000"),
)


__all__ = [
    "UNITY_COMMERCIAL_TERMS",
    "SupportedCurrency",
    "UnityCommercialTerms",
    "UnityCurrencyTerms",
]
