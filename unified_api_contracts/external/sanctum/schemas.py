"""Pydantic schemas for Sanctum LST marketplace (static on-chain registry).

Sanctum has no public REST API for LST rates. Instrument discovery is a pure
static registry of Solana mint addresses. APY data flows through DeFiLlama
or per-LST protocol adapters (jito, marinade, etc.).
"""

from pydantic import BaseModel, Field


class SanctumLstToken(BaseModel):
    """A single LST listed on Sanctum's marketplace."""

    symbol: str = Field(description="LST token symbol (e.g. INF, JUPSOL, LAINESOL)")
    mint_address: str = Field(description="Solana SPL token mint address (base58)")
    underlying: str = Field(default="SOL", description="Underlying asset (always SOL for Sanctum LSTs)")
    decimals: int = Field(default=9, description="SPL token decimal precision")


class SanctumStaticRegistry(BaseModel):
    """Static registry of active Sanctum-listed LSTs for carry_staked_basis instrumentation."""

    tokens: list[SanctumLstToken]
    deploy_date: str = Field(default="2023-06-01", description="Sanctum v1 mainnet launch floor")
