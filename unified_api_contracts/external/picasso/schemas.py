"""Picasso Network cross-chain restaking API response schemas.

Endpoint: https://api.picasso.network (ICS cross-chain restaking, Solana-native).
Reference: https://docs.picasso.network/
Note: adapter not yet implemented in MTDS — capability declared in UAC _defi.py.
"""

__api_version__ = "v1"

from pydantic import BaseModel


class PicassoRestakingRoute(BaseModel):
    """A single cross-chain restaking route from Picasso Network."""

    route_id: str | None = None
    source_chain: str | None = None
    destination_chain: str | None = None
    token_symbol: str | None = None
    apy: float | None = None
    tvl_usd: float | None = None


class PicassoRestakingResponse(BaseModel):
    """GET https://api.picasso.network/... — cross-chain restaking routes."""

    routes: list[PicassoRestakingRoute] | None = None
    total_tvl_usd: float | None = None
