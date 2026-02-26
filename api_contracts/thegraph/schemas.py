"""Pydantic schemas for The Graph subgraph query responses. Full surface: pools, swaps, reserves, errors."""

from pydantic import BaseModel, Field


class GraphQLError(BaseModel):
    """GraphQL error entry."""

    message: str = Field(..., description="Error message")
    locations: list[dict] | None = None
    path: list[str | int] | None = None
    extensions: dict | None = None


class TheGraphResponse(BaseModel):
    """Wrapper for GraphQL response (data + errors)."""

    data: dict | None = None
    errors: list[GraphQLError] | None = None


# --- Uniswap-style subgraph entities ---
class SubgraphPool(BaseModel):
    """Pool entity (Uniswap V2/V3 style)."""

    id: str | None = None
    token0: dict | None = None
    token1: dict | None = None
    reserve0: str | None = None
    reserve1: str | None = None
    totalSupply: str | None = None
    liquidity: str | None = None
    sqrtPriceX96: str | None = None
    tick: int | None = None
    info: dict | None = None


class SubgraphSwap(BaseModel):
    """Swap transaction."""

    id: str | None = None
    amount0In: str | None = None
    amount1In: str | None = None
    amount0Out: str | None = None
    amount1Out: str | None = None
    amountUSD: str | None = None
    sender: str | None = None
    to: str | None = None
    pair: dict | None = None
    timestamp: str | int | None = None
    info: dict | None = None


class SubgraphToken(BaseModel):
    """Token entity."""

    id: str | None = None
    symbol: str | None = None
    name: str | None = None
    decimals: int | None = None


# --- Aave-style (lending) ---
class SubgraphReserve(BaseModel):
    """Reserve / lending pool."""

    id: str | None = None
    symbol: str | None = None
    totalLiquidity: str | None = None
    availableLiquidity: str | None = None
    totalBorrows: str | None = None
    liquidityRate: str | None = None
    info: dict | None = None
