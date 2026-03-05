"""Pydantic schemas for The Graph subgraph query responses. Full surface: pools, swaps, reserves, errors."""

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction


class GraphQLError(BaseModel):
    """GraphQL error entry."""

    message: str = Field(..., description="Error message")
    locations: list[dict[str, object]] | None = None
    path: list[str | int] | None = None
    extensions: dict[str, object] | None = None

    @classmethod
    def classify(cls, message: str | None = None, http_status: int | None = None) -> ErrorAction:
        """Map GraphQL/The Graph error to retry action."""
        if http_status == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        if message and "not found" in (message or "").lower():
            return ErrorAction.FAIL_HARD
        if message and "rate" in (message or "").lower():
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


class TheGraphResponse(BaseModel):
    """Wrapper for GraphQL response (data + errors)."""

    data: dict[str, object] | None = None
    errors: list[GraphQLError] | None = None


# --- Uniswap-style subgraph entities ---
class SubgraphPool(BaseModel):
    """Pool entity (Uniswap V2/V3 style)."""

    id: str | None = None
    token0: dict[str, object] | None = None
    token1: dict[str, object] | None = None
    reserve0: str | None = None
    reserve1: str | None = None
    totalSupply: str | None = None
    liquidity: str | None = None
    sqrtPriceX96: str | None = None
    tick: int | None = None
    info: dict[str, object] | None = None


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
    pair: dict[str, object] | None = None
    timestamp: str | int | None = None
    info: dict[str, object] | None = None


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
    info: dict[str, object] | None = None


class SubgraphAaveUserPosition(BaseModel):
    """Aave user position (subgraph)."""

    id: str | None = None
    user: str | None = None
    reserve: dict[str, object] | None = None
    currentATokenBalance: str | None = None
    currentTotalDebt: str | None = None
    scaledATokenBalance: str | None = None
    scaledVariableDebt: str | None = None
    principalStableDebt: str | None = None
    liquidityRate: str | None = None
    info: dict[str, object] | None = None


# --- Uniswap V3 ---
class SubgraphUniV3Position(BaseModel):
    """Uniswap V3 LP position."""

    id: str | None = None
    owner: str | None = None
    pool: dict[str, object] | None = None
    token0: dict[str, object] | None = None
    token1: dict[str, object] | None = None
    liquidity: str | None = None
    tickLower: int | None = None
    tickUpper: int | None = None
    depositedToken0: str | None = None
    depositedToken1: str | None = None
    withdrawnToken0: str | None = None
    withdrawnToken1: str | None = None
    collectedFeesToken0: str | None = None
    collectedFeesToken1: str | None = None
    info: dict[str, object] | None = None


class SubgraphUniV3PoolTick(BaseModel):
    """Uniswap V3 pool tick."""

    id: str | None = None
    pool: dict[str, object] | None = None
    tickIdx: int | None = None
    liquidityGross: str | None = None
    liquidityNet: str | None = None
    price0: str | None = None
    price1: str | None = None
    info: dict[str, object] | None = None


# --- Curve ---
class SubgraphCurveGauge(BaseModel):
    """Curve gauge (gauge voting / rewards)."""

    id: str | None = None
    pool: dict[str, object] | None = None
    totalSupply: str | None = None
    workingSupply: str | None = None
    inflationRate: str | None = None
    info: dict[str, object] | None = None


class SubgraphCurveVotingEscrow(BaseModel):
    """Curve veCRV locking."""

    id: str | None = None
    user: str | None = None
    lockedBalance: str | None = None
    unlockTime: int | None = None
    info: dict[str, object] | None = None


# --- Morpho ---
class SubgraphMorphoPosition(BaseModel):
    """Morpho supply/borrow position."""

    id: str | None = None
    user: str | None = None
    market: dict[str, object] | None = None
    supplyShares: str | None = None
    borrowShares: str | None = None
    collateral: str | None = None
    info: dict[str, object] | None = None


# --- Lido ---
class SubgraphLidoRebase(BaseModel):
    """Lido stETH rebase event."""

    id: str | None = None
    postTotalShares: str | None = None
    postTotalPooledEther: str | None = None
    timeElapsed: str | None = None
    sharesMintedAsFees: str | None = None
    info: dict[str, object] | None = None


# --- Ethena ---
class SubgraphEthenaYield(BaseModel):
    """Ethena yield / sUSDe data."""

    id: str | None = None
    amount: str | None = None
    apy: str | None = None
    timestamp: int | None = None
    info: dict[str, object] | None = None


# --- ERC20 ---
class SubgraphERC20Transfer(BaseModel):
    """ERC20 Transfer event."""

    id: str | None = None
    from_: str | None = Field(None, alias="from")
    to: str | None = None
    value: str | None = None
    token: dict[str, object] | None = None
    blockNumber: int | None = None
    timestamp: int | None = None
    transactionHash: str | None = None
    info: dict[str, object] | None = None

    model_config = {"populate_by_name": True}


class SubgraphERC20Approval(BaseModel):
    """ERC20 Approval event."""

    id: str | None = None
    owner: str | None = None
    spender: str | None = None
    value: str | None = None
    token: dict[str, object] | None = None
    blockNumber: int | None = None
    timestamp: int | None = None
    transactionHash: str | None = None
    info: dict[str, object] | None = None


class TheGraphWsNext(BaseModel):
    """GraphQL WebSocket next message payload."""

    type: str = "next"
    id: str | None = None
    payload: dict[str, object] | None = None
    data: dict[str, object] | None = None
