"""Solayer restaking API response schemas.

Endpoint: https://app.solayer.org/api (public REST, no auth required for yield reads).
Reference: https://docs.solayer.org/
Note: adapter not yet implemented in MTDS — capability declared in UAC _defi.py.
"""

__api_version__ = "v1"

from pydantic import BaseModel


class SolayerPoolInfo(BaseModel):
    """Single pool from Solayer restaking API."""

    pool_id: str | None = None
    apy: float | None = None
    tvl_usd: float | None = None
    token_symbol: str | None = None
    epoch: int | None = None


class SolayerRestakingResponse(BaseModel):
    """GET https://app.solayer.org/api/... — restaking pool list."""

    pools: list[SolayerPoolInfo] | None = None
    total_tvl_usd: float | None = None
