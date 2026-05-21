"""Copper custody platform API schemas (api.copper.co/platform/)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CopperBalance(BaseModel):
    """Single asset balance in a Copper wallet."""

    currency: str = Field(..., description="Asset ticker (e.g. ETH, BTC, USDC)")
    amount: str = Field(..., description="Total balance as decimal string")
    available: str = Field(..., description="Available (unlocked) balance")
    locked: str = Field(..., description="Locked balance (pending orders)")


class CopperWalletBalancesResponse(BaseModel):
    """Response from GET /platform/wallets/{wallet_id}/balances.

    Requires HMAC-signed Authorization header (api-key + timestamp + signature).
    """

    walletId: str = Field(..., description="Copper wallet UUID")
    balances: list[CopperBalance] = Field(default_factory=list)
