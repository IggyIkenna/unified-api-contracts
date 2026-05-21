"""Pydantic schemas for Jito Network REST API (kobe.mainnet.jito.network)."""

from pydantic import BaseModel, Field


class JitoStakePoolStats(BaseModel):
    """Response from GET /api/v1/stake_pool_stats — JitoSOL stake pool summary."""

    pool_address: str = Field(description="Jito stake pool program address on Solana mainnet")
    apy: float = Field(description="JitoSOL annualised staking yield (base + MEV tips), e.g. 7.12")
    staked_validator_count: int = Field(description="Number of validators delegated to the Jito stake pool")
    total_lamports: int = Field(description="Total SOL staked (in lamports, 1 SOL = 1e9 lamports)")


class JitoMevRewards(BaseModel):
    """Response from GET /api/v1/mev_rewards — aggregate MEV tip rewards for the epoch."""

    epoch: int = Field(description="Solana epoch number")
    total_mev_lamports: int = Field(description="Total MEV rewards distributed in epoch (lamports)")
    mev_apy_contribution: float = Field(description="MEV-only APY contribution (percentage points)")
