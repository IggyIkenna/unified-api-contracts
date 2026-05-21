"""Pydantic schemas for Orca Whirlpool API (api.mainnet.orca.so/v1/whirlpool/list)."""

from pydantic import BaseModel, Field


class OrcaWhirlpoolToken(BaseModel):
    """Token in an Orca Whirlpool."""

    mint: str = Field(description="Solana SPL token mint address (base58)")
    symbol: str
    decimals: int


class OrcaWhirlpool(BaseModel):
    """A single Orca Concentrated Liquidity (Whirlpool) pool."""

    address: str = Field(description="Whirlpool account address on Solana")
    tokenA: OrcaWhirlpoolToken
    tokenB: OrcaWhirlpoolToken
    tickSpacing: int = Field(description="Tick spacing — determines fee tier (1, 8, 64, 128)")
    price: str = Field(description="Current pool price (token A per token B, string-encoded)")
    lpFeeRate: float = Field(description="LP fee rate as a decimal (e.g. 0.003 = 0.3%)")
    tvl: float | None = Field(default=None, description="Total value locked in USD")


class OrcaWhirlpoolListResponse(BaseModel):
    """Response from GET /v1/whirlpool/list."""

    whirlpools: list[OrcaWhirlpool]
