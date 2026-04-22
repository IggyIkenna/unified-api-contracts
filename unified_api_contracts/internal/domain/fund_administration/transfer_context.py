"""FundTransferContext — fund + share-class + allocation coordinates for treasury transfers.

Attached to every capital-routing transfer (internal deposit / withdrawal)
so PBMS can attribute the flow to the right fund/share-class/allocation.
"""

from pydantic import BaseModel


class FundTransferContext(BaseModel, frozen=True):
    """Fund + share-class + allocation coordinates for treasury transfers.

    Attached to each ``TransferResult`` so downstream (PBMS, reporting) can
    reconcile flows against the originating fund / share-class / allocation.

    Fields
    ------
    fund_id:
        IM Pooled fund identifier.
    share_class:
        Share class within the fund (e.g. "A", "B", currency-denominated).
    allocation_id:
        Optional FundAllocation id — set for internal rebalance transfers;
        ``None`` for subscription/redemption flows which have no allocation.
    """

    fund_id: str
    share_class: str
    allocation_id: str | None = None
