"""Cambrian Network restaking API response schemas.

Endpoint: https://api.cambrian.network (Solana AVS restaking primitives).
Reference: https://docs.cambrian.network/
Note: adapter not yet implemented in MTDS — capability declared in UAC _defi.py.
"""

__api_version__ = "v1"

from pydantic import BaseModel


class CambrianOperatorSet(BaseModel):
    """A single operator set from the Cambrian restaking registry."""

    operator_set_id: str | None = None
    name: str | None = None
    total_staked_usd: float | None = None
    apy: float | None = None
    slash_conditions: list[str] | None = None


class CambrianRestakingResponse(BaseModel):
    """GET https://api.cambrian.network/... — AVS restaking operator sets."""

    operator_sets: list[CambrianOperatorSet] | None = None
    total_restaked_usd: float | None = None
