"""The Graph subgraph API response schemas. Originally in unified-market-interface adapters.

Full surface: pools, swaps, reserves, errors (Uniswap V2/V3/V4, Balancer, Curve, Aave, Morpho).
"""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from pydantic import BaseModel, Field

from unified_api_contracts.canonical.errors import ErrorAction


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
            return ErrorAction.RETRY
        if message and "not found" in (message or "").lower():
            return ErrorAction.FAIL
        if message and "rate" in (message or "").lower():
            return ErrorAction.RETRY
        return ErrorAction.FAIL


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


# ---------------------------------------------------------------------------
# Originally in unified-market-interface adapters/defi/_defi_graph_models.py
# Covers: Uniswap V2/V3/V4, Balancer, Curve subgraph schemas.
# ---------------------------------------------------------------------------


class GraphToken(BaseModel, frozen=True):
    """Token object nested inside pool/pair responses."""

    id: str = ""
    symbol: str = ""
    name: str = ""
    decimals: int | str = 18


# ---------------------------------------------------------------------------
# Uniswap V3 / V4 pool models
# ---------------------------------------------------------------------------


class GraphUniswapPool(BaseModel, frozen=True):
    """Pool object from Uniswap V3/V4 subgraph."""

    id: str = ""
    token0: GraphToken = Field(default_factory=GraphToken)
    token1: GraphToken = Field(default_factory=GraphToken)
    feeTier: str | int | None = None
    liquidity: str = "0"
    totalValueLockedUSD: str = "0"
    createdAtTimestamp: str | int | None = None


class GraphUniswapPoolsData(BaseModel, frozen=True):
    """The 'data' wrapper for Uniswap pool queries."""

    pools: list[GraphUniswapPool] = Field(default_factory=list)


class GraphUniswapPoolsResponse(BaseModel, frozen=True):
    """Full GraphQL response for Uniswap pool queries."""

    data: GraphUniswapPoolsData = Field(default_factory=GraphUniswapPoolsData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Uniswap V3/V4 swap models
# ---------------------------------------------------------------------------


class GraphSwapTransaction(BaseModel, frozen=True):
    """Transaction nested inside a swap."""

    id: str = ""
    blockNumber: str | int = 0
    gasPrice: str | None = None


class GraphUniswapSwap(BaseModel, frozen=True):
    """Swap object from Uniswap V3/V4 subgraph."""

    id: str = ""
    timestamp: str | int = 0
    amount0: str | float = 0
    amount1: str | float = 0
    amountUSD: str | float = 0
    sqrtPriceX96: str = ""
    tick: str | int = 0
    transaction: GraphSwapTransaction = Field(default_factory=GraphSwapTransaction)


class GraphUniswapSwapsData(BaseModel, frozen=True):
    """The 'data' wrapper for Uniswap swap queries."""

    swaps: list[GraphUniswapSwap] = Field(default_factory=list)


class GraphUniswapSwapsResponse(BaseModel, frozen=True):
    """Full GraphQL response for Uniswap swap queries."""

    data: GraphUniswapSwapsData = Field(default_factory=GraphUniswapSwapsData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Uniswap V3/V4 pool hour data
# ---------------------------------------------------------------------------


class GraphPoolHourData(BaseModel, frozen=True):
    """Pool hourly data from Uniswap V3/V4 subgraph."""

    id: str = ""
    periodStartUnix: int = 0
    liquidity: str = "0"
    sqrtPrice: str = "0"
    token0Price: str | float = 0
    token1Price: str | float = 0
    tick: str | int = 0
    tvlUSD: str | float = 0
    volumeToken0: str | float = 0
    volumeToken1: str | float = 0
    volumeUSD: str | float = 0
    feesUSD: str | float = 0
    open: str | float = 0
    high: str | float = 0
    low: str | float = 0
    close: str | float = 0


class GraphPoolHourDatasData(BaseModel, frozen=True):
    """The 'data' wrapper for pool hour data queries."""

    poolHourDatas: list[GraphPoolHourData] = Field(default_factory=list)


class GraphPoolHourDatasResponse(BaseModel, frozen=True):
    """Full GraphQL response for pool hour data queries."""

    data: GraphPoolHourDatasData = Field(default_factory=GraphPoolHourDatasData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Uniswap V2 pair models
# ---------------------------------------------------------------------------


class GraphUniswapV2Pair(BaseModel, frozen=True):
    """Pair object from Uniswap V2 subgraph."""

    id: str = ""
    token0: GraphToken = Field(default_factory=GraphToken)
    token1: GraphToken = Field(default_factory=GraphToken)
    reserve0: str | float = 0
    reserve1: str | float = 0
    reserveUSD: str | float = 0
    txCount: str | int = 0
    createdAtTimestamp: str | int | None = None


class GraphUniswapV2PairsData(BaseModel, frozen=True):
    """The 'data' wrapper for Uniswap V2 pair queries."""

    pairs: list[GraphUniswapV2Pair] = Field(default_factory=list)


class GraphUniswapV2PairsResponse(BaseModel, frozen=True):
    """Full GraphQL response for Uniswap V2 pair queries."""

    data: GraphUniswapV2PairsData = Field(default_factory=GraphUniswapV2PairsData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Uniswap V2 swap models
# ---------------------------------------------------------------------------


class GraphV2SwapPairToken(BaseModel, frozen=True):
    """Token nested inside a V2 swap pair."""

    symbol: str = ""
    id: str = ""


class GraphV2SwapPair(BaseModel, frozen=True):
    """Pair nested inside a V2 swap."""

    token0: GraphV2SwapPairToken = Field(default_factory=GraphV2SwapPairToken)
    token1: GraphV2SwapPairToken = Field(default_factory=GraphV2SwapPairToken)


class GraphV2SwapTransaction(BaseModel, frozen=True):
    """Transaction nested inside a V2 swap."""

    id: str = ""
    blockNumber: str | int = 0


class GraphUniswapV2Swap(BaseModel, frozen=True):
    """Swap object from Uniswap V2 subgraph."""

    id: str = ""
    timestamp: str | int = 0
    amount0In: str | float = 0
    amount0Out: str | float = 0
    amount1In: str | float = 0
    amount1Out: str | float = 0
    amountUSD: str | float = 0
    to: str = ""
    sender: str = ""
    transaction: GraphV2SwapTransaction = Field(default_factory=GraphV2SwapTransaction)
    pair: GraphV2SwapPair = Field(default_factory=GraphV2SwapPair)


class GraphUniswapV2SwapsData(BaseModel, frozen=True):
    """The 'data' wrapper for Uniswap V2 swap queries."""

    swaps: list[GraphUniswapV2Swap] = Field(default_factory=list)


class GraphUniswapV2SwapsResponse(BaseModel, frozen=True):
    """Full GraphQL response for Uniswap V2 swap queries."""

    data: GraphUniswapV2SwapsData = Field(default_factory=GraphUniswapV2SwapsData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Uniswap V2 pair hour data
# ---------------------------------------------------------------------------


class GraphPairHourData(BaseModel, frozen=True):
    """Hourly pair data from Uniswap V2 subgraph."""

    id: str = ""
    hourStartUnix: int = 0
    reserve0: str | float = 0
    reserve1: str | float = 0
    reserveUSD: str | float = 0
    hourlyVolumeToken0: str | float = 0
    hourlyVolumeToken1: str | float = 0
    hourlyVolumeUSD: str | float = 0
    hourlyTxns: str | int = 0


class GraphPairHourDatasData(BaseModel, frozen=True):
    """The 'data' wrapper for pair hour data queries."""

    pairHourDatas: list[GraphPairHourData] = Field(default_factory=list)


class GraphPairHourDatasResponse(BaseModel, frozen=True):
    """Full GraphQL response for V2 pair hour data queries."""

    data: GraphPairHourDatasData = Field(default_factory=GraphPairHourDatasData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Balancer models
# ---------------------------------------------------------------------------


class GraphBalancerPoolToken(BaseModel, frozen=True):
    """Token in a Balancer pool."""

    address: str = ""
    symbol: str = ""
    decimals: int | str = 18
    name: str = ""


class GraphBalancerDynamicData(BaseModel, frozen=True):
    """Dynamic data for a Balancer pool."""

    totalLiquidity: str | float = 0
    volume24h: str | float = 0


class GraphBalancerPool(BaseModel, frozen=True):
    """Pool from Balancer API v3."""

    id: str = ""
    address: str = ""
    name: str = ""
    poolTokens: list[GraphBalancerPoolToken] = Field(default_factory=list)
    dynamicData: GraphBalancerDynamicData = Field(default_factory=GraphBalancerDynamicData)


class GraphBalancerPoolGetPoolsData(BaseModel, frozen=True):
    """The 'data' wrapper for Balancer pool queries."""

    poolGetPools: list[GraphBalancerPool] = Field(default_factory=list)


class GraphBalancerPoolsResponse(BaseModel, frozen=True):
    """Full GraphQL response for Balancer pool queries."""

    data: GraphBalancerPoolGetPoolsData = Field(default_factory=GraphBalancerPoolGetPoolsData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Balancer swap models (The Graph subgraph)
# ---------------------------------------------------------------------------


class GraphBalancerSwap(BaseModel, frozen=True):
    """Swap from Balancer V2 subgraph."""

    id: str = ""
    timestamp: str | int = 0
    tokenIn: str = ""
    tokenOut: str = ""
    tokenAmountIn: str | float = 0
    tokenAmountOut: str | float = 0
    tx: str = ""


class GraphBalancerSwapsData(BaseModel, frozen=True):
    """The 'data' wrapper for Balancer swap queries."""

    swaps: list[GraphBalancerSwap] = Field(default_factory=list)


class GraphBalancerSwapsResponse(BaseModel, frozen=True):
    """Full GraphQL response for Balancer swap queries."""

    data: GraphBalancerSwapsData = Field(default_factory=GraphBalancerSwapsData)
    errors: list[object] | None = None


# ---------------------------------------------------------------------------
# Curve swap models
# ---------------------------------------------------------------------------


class GraphCurveSwapToken(BaseModel, frozen=True):
    """Token in a Curve swap."""

    symbol: str = ""
    id: str = ""


class GraphCurveSwap(BaseModel, frozen=True):
    """Swap from Curve subgraph."""

    id: str = ""
    hash: str = ""
    timestamp: str | int = 0
    tokenIn: GraphCurveSwapToken = Field(default_factory=GraphCurveSwapToken)
    tokenOut: GraphCurveSwapToken = Field(default_factory=GraphCurveSwapToken)
    amountIn: str | float = 0
    amountOut: str | float = 0
    amountInUSD: str | float = 0
    amountOutUSD: str | float = 0


class GraphCurveSwapsData(BaseModel, frozen=True):
    """The 'data' wrapper for Curve swap queries."""

    swaps: list[GraphCurveSwap] = Field(default_factory=list)


class GraphCurveSwapsResponse(BaseModel, frozen=True):
    """Full GraphQL response for Curve swap queries."""

    data: GraphCurveSwapsData = Field(default_factory=GraphCurveSwapsData)
    errors: list[object] | None = None
