"""Fund administration domain — subscription / redemption / allocation rail (IM Pooled).

SSOT for:
- AllocatorSubscription: IM Pooled investor subscription lifecycle payload
- AllocatorRedemption: IM Pooled investor redemption lifecycle payload
- FundAllocation: fund → strategy capital-allocation rebalance record
- SubscriptionStatus / RedemptionStatus / AllocationExecutionStatus: state enums

These types are consumed by:
- fund-administration-service (subscription/redemption state machines,
  capital-routing orchestrator)
- client-reporting-api (allocator-facing subscription/redemption history)
- position-balance-monitor-service (target_allocations delta computation)
- UTL lifecycle events (SUBSCRIPTION_* / REDEMPTION_* / FUND_ALLOCATION_REBALANCED)

Scope is **IM Pooled ONLY**. SMA / DART / Reg Umbrella clients hold their
own venue accounts and do not touch this rail. See
``codex/14-playbooks/shared-core/fund-administration-and-custody.md``.
"""

from unified_api_contracts.internal.domain.fund_administration._types import (
    AllocationExecutionStatus,
    AllocatorRedemption,
    AllocatorSubscription,
    FundAllocation,
    RedemptionStatus,
    SubscriptionStatus,
)
from unified_api_contracts.internal.domain.fund_administration.api_requests import (
    ApproveSubscriptionRequest,
    ProcessRedemptionRequest,
    RebalanceRequest,
    RedeemRequest,
    RejectRequest,
    SubscribeRequest,
)
from unified_api_contracts.internal.domain.fund_administration.transfer_context import (
    FundTransferContext,
)

__all__ = [
    "AllocationExecutionStatus",
    "AllocatorRedemption",
    "AllocatorSubscription",
    "ApproveSubscriptionRequest",
    "FundAllocation",
    "FundTransferContext",
    "ProcessRedemptionRequest",
    "RebalanceRequest",
    "RedeemRequest",
    "RedemptionStatus",
    "RejectRequest",
    "SubscribeRequest",
    "SubscriptionStatus",
]
