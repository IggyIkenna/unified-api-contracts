"""Tenderly Virtual TestNet API schemas (api.tenderly.co/api/v1/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TenderlyVnetRpcUrls(BaseModel):
    """RPC URL details for a created Virtual TestNet."""

    admin: str | None = Field(None, description="Admin RPC URL (full transaction control)")
    public: str | None = Field(None, description="Public RPC URL (read-only)")


class TenderlyVnetResponse(BaseModel):
    """Response from POST /api/v1/account/{account}/project/{project}/vnets.

    Requires X-Access-Key header (Tenderly API key).
    """

    id: str = Field(..., description="Virtual TestNet UUID")
    slug: str = Field(..., description="Human-readable slug for the vnet")
    status: str = Field(..., description="Vnet status (e.g. ACTIVE)")
    rpcs: list[TenderlyVnetRpcUrls] = Field(default_factory=list, description="Available RPC endpoints")
    fork_config: dict[str, object] = Field(default_factory=dict, description="Fork configuration (chain, block)")
