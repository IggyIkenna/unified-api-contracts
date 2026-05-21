"""Jupiter token list API schemas (tokens.jup.ag/tokens?tags=strict)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JupiterToken(BaseModel):
    """Single token from the Jupiter strict-tagged token registry."""

    address: str = Field(..., description="Solana mint address")
    chainId: int = Field(..., description="Chain ID (101 = mainnet-beta)")
    decimals: int = Field(..., description="Token decimal precision")
    name: str = Field(..., description="Human-readable token name")
    symbol: str = Field(..., description="Trading symbol (e.g. SOL, USDC)")
    logoURI: str | None = Field(None, description="HTTPS URL of token logo")
    tags: list[str] = Field(default_factory=list, description="Token tags (e.g. strict, lst)")


class JupiterTokenListResponse(BaseModel):
    """Top-level response from GET tokens.jup.ag/tokens?tags=strict.

    The endpoint returns a JSON array directly (no wrapper object).
    """

    tokens: list[JupiterToken] = Field(..., description="Flat array of strict-tagged tokens")
