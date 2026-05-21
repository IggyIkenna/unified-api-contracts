"""Pydantic schemas for Balancer V3 API (api-v3.balancer.fi/graphql)."""

from pydantic import BaseModel, Field


class BalancerPoolToken(BaseModel):
    """A single token in a Balancer pool."""

    address: str
    symbol: str
    decimals: int


class BalancerPoolDynamicData(BaseModel):
    """Dynamic (market) data for a Balancer pool."""

    totalLiquidity: str = Field(description="Total pool TVL in USD (string-encoded float)")
    swapFee: str = Field(description="Swap fee as a decimal string (e.g. '0.003')")


class BalancerPool(BaseModel):
    """A single Balancer liquidity pool from poolGetPools query."""

    id: str
    name: str
    type: str = Field(description="Pool type: WEIGHTED, STABLE, COMPOSABLE_STABLE, etc.")
    address: str
    chain: str
    protocolVersion: int
    createTime: int = Field(description="Unix timestamp of pool creation")
    dynamicData: BalancerPoolDynamicData
    poolTokens: list[BalancerPoolToken]


class BalancerPoolsResponse(BaseModel):
    """Top-level GraphQL response from poolGetPools query."""

    poolGetPools: list[BalancerPool]
