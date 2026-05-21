"""Pydantic schemas for Lifinity API (api.lifinity.io/pools)."""

from pydantic import BaseModel, Field


class LifinityToken(BaseModel):
    """A token in a Lifinity pool."""

    mint: str = Field(description="Solana token mint address")
    symbol: str
    decimals: int


class LifinityPool(BaseModel):
    """A single Lifinity proactive market-making pool."""

    pubkey: str = Field(description="Pool account address on Solana")
    tokenA: LifinityToken
    tokenB: LifinityToken
    tradeFeeRate: float = Field(description="Trade fee rate (e.g. 0.003 = 0.3%)")
    tvl: float | None = Field(default=None, description="Total value locked in USD")
    price: float | None = Field(default=None, description="Current pool price")


class LifinityPoolsResponse(BaseModel):
    """Response from GET /pools."""

    pools: list[LifinityPool]
