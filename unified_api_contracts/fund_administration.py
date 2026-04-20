"""Fund administration domain facade.

Public citadel-import path for the subscription / redemption / allocation
domain types + lifecycle-state enums, plus FastAPI request-body schemas.
Internal canonical definitions live under
``unified_api_contracts.internal.domain.fund_administration``; this facade
exposes them at the public path so consumer services can use either
``from unified_api_contracts.fund_administration import X`` or the
top-level re-export (``from unified_api_contracts import X``).

See:
  - ``codex/14-playbooks/shared-core/treasury-and-subaccount-model.md``
  - ``plans/active/fund_administration_service_and_pooled_subscription_redemption_2026_04_20.plan.md``
"""

from __future__ import annotations

from unified_api_contracts.internal.domain.fund_administration import (
    AllocationExecutionStatus as AllocationExecutionStatus,
)
from unified_api_contracts.internal.domain.fund_administration import (
    AllocatorRedemption as AllocatorRedemption,
)
from unified_api_contracts.internal.domain.fund_administration import (
    AllocatorSubscription as AllocatorSubscription,
)
from unified_api_contracts.internal.domain.fund_administration import (
    ApproveSubscriptionRequest as ApproveSubscriptionRequest,
)
from unified_api_contracts.internal.domain.fund_administration import (
    FundAllocation as FundAllocation,
)
from unified_api_contracts.internal.domain.fund_administration import (
    ProcessRedemptionRequest as ProcessRedemptionRequest,
)
from unified_api_contracts.internal.domain.fund_administration import (
    RebalanceRequest as RebalanceRequest,
)
from unified_api_contracts.internal.domain.fund_administration import (
    RedeemRequest as RedeemRequest,
)
from unified_api_contracts.internal.domain.fund_administration import (
    RedemptionStatus as RedemptionStatus,
)
from unified_api_contracts.internal.domain.fund_administration import (
    RejectRequest as RejectRequest,
)
from unified_api_contracts.internal.domain.fund_administration import (
    SubscribeRequest as SubscribeRequest,
)
from unified_api_contracts.internal.domain.fund_administration import (
    SubscriptionStatus as SubscriptionStatus,
)

__all__ = [
    "AllocationExecutionStatus",
    "AllocatorRedemption",
    "AllocatorSubscription",
    "ApproveSubscriptionRequest",
    "FundAllocation",
    "ProcessRedemptionRequest",
    "RebalanceRequest",
    "RedeemRequest",
    "RedemptionStatus",
    "RejectRequest",
    "SubscribeRequest",
    "SubscriptionStatus",
]
