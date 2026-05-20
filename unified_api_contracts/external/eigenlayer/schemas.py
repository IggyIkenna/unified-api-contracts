"""EigenLayer Sidecar RPC response schemas.

Endpoint: https://sidecar-rpc.eigenlayer.xyz/eigenlayer/rewards/v1/earner-historical-rewards
Auth: Cloudflare-protected; requires production environment (not recordable in local dev).
Reference: https://docs.eigenlayer.xyz/eigenlayer/restaking-guides/restaking-user-guide/
"""

__api_version__ = "v1"

from pydantic import BaseModel


class EigenLayerRewardRecord(BaseModel):
    """Single reward record from EigenLayer sidecar."""

    token: str | None = None
    amount: str | None = None
    avs: str | None = None
    strategy: str | None = None
    snapshot_date: str | None = None


class EigenLayerRewardsResponse(BaseModel):
    """GET /eigenlayer/rewards/v1/earner-historical-rewards response."""

    rewards: list[EigenLayerRewardRecord] | None = None
