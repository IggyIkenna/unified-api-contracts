"""Fund administration FastAPI request-body schemas.

These are thin input DTOs consumed by the ``fund-administration-service``
REST surface. They are kept in UAC (not the service) so the
schema-provenance scanner is satisfied: every BaseModel/dataclass visible
from service source must originate upstream in UAC / UIC.

They are NOT domain messages — the canonical subscription / redemption /
allocation payloads live in ``_types.py``. The request bodies here only
carry the user-supplied arguments needed to drive a lifecycle transition;
the route handler hydrates the canonical model from these fields.

SSOT:
  - ``codex/14-playbooks/shared-core/fund-administration-and-custody.md``
  - ``plans/active/fund_administration_service_and_pooled_subscription_redemption_2026_04_20.md``
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class SubscribeRequest(BaseModel):
    """Body for ``POST /subscriptions`` — create a PENDING subscription."""

    subscription_id: str
    fund_id: str
    allocator_id: str
    share_class: str
    requested_amount_usd: Decimal


class RedeemRequest(BaseModel):
    """Body for ``POST /redemptions`` — create a PENDING redemption."""

    redemption_id: str
    fund_id: str
    allocator_id: str
    share_class: str
    units_to_redeem: Decimal
    destination: str
    grace_period_days: int | None = None


class ApproveSubscriptionRequest(BaseModel):
    """Body for ``POST /subscriptions/{id}/approve`` — PENDING -> APPROVED."""

    nav_per_unit: Decimal


class ProcessRedemptionRequest(BaseModel):
    """Body for ``POST /redemptions/{id}/process`` — APPROVED -> PROCESSED."""

    settlement_nav: Decimal
    settlement_reference: str


class RejectRequest(BaseModel):
    """Body for ``POST /{kind}/{id}/reject`` — PENDING -> REJECTED."""

    reason: str


class RebalanceRequest(BaseModel):
    """Body for ``POST /funds/{fund_id}/allocations/rebalance``.

    ``targets`` is an opaque list of dict rows converted into
    ``AllocationTarget`` inside the route handler — avoids round-tripping
    the capital-router dataclass through pydantic at the seam.
    """

    share_class: str
    targets: list[dict[str, object]]


__all__ = [
    "ApproveSubscriptionRequest",
    "ProcessRedemptionRequest",
    "RebalanceRequest",
    "RedeemRequest",
    "RejectRequest",
    "SubscribeRequest",
]
