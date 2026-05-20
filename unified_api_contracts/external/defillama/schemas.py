"""DefiLlama protocol analytics.

Free, no auth required.
Multiple base URLs: api.llama.fi (TVL), stablecoins.llama.fi, yields.llama.fi, bridges.llama.fi
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


class DefiLlamaProtocol(BaseModel):
    """GET https://api.llama.fi/protocols.

    Category: Dexes/Lending/CDP/Yield etc.
    """

    id: str | None = None
    name: str | None = None
    slug: str | None = None
    address: str | None = None
    symbol: str | None = None
    url: str | None = None
    description: str | None = None
    chain: str | None = None
    logo: str | None = None
    audits: str | None = None
    category: str | None = None
    chains: list[str] | None = None
    tvl: float | None = None
    change_1h: float | None = None
    change_1d: float | None = None
    change_7d: float | None = None
    tvlPrevDay: float | None = None
    tvlPrevWeek: float | None = None
    tvlPrevMonth: float | None = None
    # Additional fields observed in API responses
    gecko_id: str | None = None
    cmcId: str | None = None
    twitter: str | None = None
    listedAt: int | None = None
    mcap: float | None = None
    methodology: str | None = None
    module: str | None = None
    misrepresentedTokens: bool | None = None
    chainTvls: dict[str, float] | None = None
    tokenBreakdowns: dict[str, object] | None = None
    tvlCodePath: str | None = None


class DefiLlamaChainTvl(BaseModel):
    """GET https://api.llama.fi/v2/chains."""

    name: str | None = None
    tvl: float | None = None
    tokenSymbol: str | None = None
    cmcId: str | None = None
    gecko_id: str | None = None


class DefiLlamaTvlHistoryPoint(BaseModel):
    """Per-protocol TVL history. GET https://api.llama.fi/protocol/{slug}."""

    date: int | None = None
    totalLiquidityUSD: float | None = None


class DefiLlamaStablecoin(BaseModel):
    """GET https://stablecoins.llama.fi/stablecoins?includePrices=true."""

    id: str | None = None
    name: str | None = None
    symbol: str | None = None
    gecko_id: str | None = None
    peg_type: str | None = None  # peggedUSD/peggedEUR/algorithmic
    peg_mechanism: str | None = None  # fiat-backed/crypto-backed/algorithmic
    circulating: dict[str, float] | None = None
    circulatingPrevDay: dict[str, float] | None = None
    circulatingPrevWeek: dict[str, float] | None = None
    circulatingPrevMonth: dict[str, float] | None = None
    chains: list[str] | None = None
    price: float | None = None
    chain_circulating: dict[str, float] | None = None


class DefiLlamaStablecoinChartPoint(BaseModel):
    """GET https://stablecoins.llama.fi/stablecoincharts/{chain} or /all."""

    date: int | None = None
    totalCirculating: dict[str, float] | None = None
    totalCirculatingUSD: dict[str, float] | None = None


class DefiLlamaYieldPool(BaseModel):
    """GET https://yields.llama.fi/pools."""

    chain: str | None = None
    project: str | None = None
    symbol: str | None = None
    tvlUsd: float | None = None
    apy: float | None = None
    apyBase: float | None = None
    apyReward: float | None = None
    apyMean30d: float | None = None
    il7d: float | None = None
    apyBase7d: float | None = None
    volumeUsd1d: float | None = None
    volumeUsd7d: float | None = None
    pool: str | None = None
    poolMeta: str | None = None
    exposure: str | None = None  # single/multi
    underlyingTokens: list[str] | None = None
    rewardTokens: list[str] | None = None
    # Additional fields observed in API responses
    stablecoin: bool | None = None
    ilRisk: str | None = None
    predictions: dict[str, object] | None = None
    outlier: bool | None = None
    mu: float | None = None
    sigma: float | None = None
    count: int | None = None
    apyPct1D: float | None = None
    apyPct7D: float | None = None
    apyPct30D: float | None = None
    apyBaseInception: float | None = None


class DefiLlamaBridge(BaseModel):
    """GET https://bridges.llama.fi/bridges."""

    id: int | None = None
    name: str | None = None
    displayName: str | None = None
    volumePrevDay: float | None = None
    volumePrev2Day: float | None = None
    lastHourlyVolume: float | None = None
    currentDayVolume: float | None = None
    lastDailyVolume: float | None = None
    weeklyVolume: float | None = None
    monthlyVolume: float | None = None
    chains: list[str] | None = None
    destinationChain: str | None = None


class DefiLlamaBridgeActivityPoint(BaseModel):
    """GET https://bridges.llama.fi/bridgevolume/{chain}."""

    date: int | None = None
    depositUSD: float | None = None
    withdrawUSD: float | None = None
    depositTxs: int | None = None
    withdrawTxs: int | None = None


class DefiLlamaCoinsPrice(BaseModel):
    """Single coin entry from GET https://coins.llama.fi/prices/historical/{timestamp}/{coin_id}."""

    price: float | None = None
    symbol: str | None = None
    timestamp: int | None = None
    confidence: float | None = None
    decimals: int | None = None


class DefiLlamaCoinsResponse(BaseModel):
    """GET https://coins.llama.fi/prices/historical/{timestamp}/{coin_id}.

    Keys of `coins` are DeFiLlama coin IDs e.g. 'solana:bSo13r4T...'.
    """

    coins: dict[str, DefiLlamaCoinsPrice] | None = None


class DefiLlamaError(BaseModel):
    """DefiLlama API error."""

    message: str | None = None

    @classmethod
    def classify(cls, status_code: int | None) -> ErrorAction:
        """429->RETRY, 404->FAIL."""
        if status_code == 429:
            return ErrorAction.RETRY
        if status_code == 404:
            return ErrorAction.FAIL
        return ErrorAction.FAIL
