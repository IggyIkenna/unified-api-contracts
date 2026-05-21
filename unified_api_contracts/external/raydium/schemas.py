"""Pydantic schemas for Raydium API (api-v3.raydium.io/pools/info/list)."""

from pydantic import BaseModel, Field


class RaydiumPoolToken(BaseModel):
    """A token in a Raydium pool."""

    address: str = Field(description="Solana token mint address")
    symbol: str
    decimals: int


class RaydiumPool(BaseModel):
    """A single Raydium liquidity pool."""

    id: str = Field(description="Pool account address on Solana")
    mintA: RaydiumPoolToken = Field(description="Token A mint metadata")
    mintB: RaydiumPoolToken = Field(description="Token B mint metadata")
    feeRate: float = Field(description="Trading fee rate as a decimal (e.g. 0.0025 = 0.25%)")
    tvl: float = Field(description="Total value locked in USD")
    price: float = Field(description="Current pool price (token A / token B)")
    type: str = Field(description="Pool type: Standard, Concentrated, etc.")


class RaydiumPoolsResponse(BaseModel):
    """Response from GET /pools/info/list."""

    data: list[RaydiumPool]
    hasNextPage: bool = False
