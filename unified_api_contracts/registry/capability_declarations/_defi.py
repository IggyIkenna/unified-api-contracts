"""DeFi protocol and on-chain analytics capability declarations."""

from __future__ import annotations

from enum import StrEnum

from ..capability import OperationDetail, OperationEnvDetail, SourceCapability


class DeFiDataSource(StrEnum):
    """Supported data sources for DeFi protocol access.

    Classifies external data providers used by DeFi connectors to resolve
    RPC endpoints, The Graph subgraphs, and other data access methods.
    """

    ALCHEMY = "alchemy"
    SELF_HOSTED = "self_hosted"
    THEGRAPH = "thegraph"
    HYPERLIQUID_API = "hyperliquid_api"  # Hyperliquid REST/WebSocket


# ---------------------------------------------------------------------------
# The Graph subgraph IDs (SSOT)
#
# Consolidated from UMI adapters (aave_utils.py, uniswap_v3_adapter.py,
# uniswapv2_adapter.py, uniswapv4_adapter.py, balancer_adapter.py,
# morpho_adapter.py, curve_adapter.py) and UMI clients/subgraph_service.py.
# All callers should import from here instead of hardcoding IDs.
#
# Format: protocol -> chain -> subgraph ID
# Default chain is "ETHEREUM" when protocol only has one deployment.
# ---------------------------------------------------------------------------
SUBGRAPH_IDS: dict[str, dict[str, str]] = {
    # ── Lending protocols ──────────────────────────────────────────
    "aave_v3": {  # Verified from github.com/aave/protocol-subgraphs README
        "ETHEREUM": "Cd2gEDVeqnjBn1hSeqFMitw8Q1iiyV9FYUZkLNRcL87g",
        "ARBITRUM": "DLuE98kEb5pQNXAcKFQGQgfSQ57Xdou4jnVbAEqMfy3B",
        "OPTIMISM": "DSfLz8oQBUeU5atALgUFQKMTSYV9mZAVYp4noLSXAfvb",
        "POLYGON": "Co2URyXjnxaw8WqxKyVHdirq9Ahhm5vcTs4dMedAq211",
        "AVALANCHE": "2h9woxy8RTjHu1HJsCEnmzpPHFArU33avmUh4f71JpVn",
        "BASE": "GQFbb95cE6d8mV989mL5figjaGaKCQB3xqYrr1bRyXqF",
        "LINEA": "Gz2kjnmRV1fQj3R8cssoZa5y9VTanhrDo4Mh7nWW1wHa",
        "BSC": "7Jk85XgkV1MQ7u56hD8rr65rfASbayJXopugWkUoBMnZ",
    },
    "compound_v3": {  # Verified from github.com/papercliplabs/compound-v3-subgraph
        "ETHEREUM": "5nwMCSHaTqG3Kd2gHznbTXEnZ9QNWsssQfbHhDqQSQFp",
        "ARBITRUM": "Ff7ha9ELmpmg81D6nYxy4t8aGP26dPztqD1LDJNPqjLS",
        "BASE": "2hcXhs36pTBDVUmk5K2Zkr6N4UYGwaHuco2a6jyTsijo",
        # POLYGON removed: subgraph returns 0 markets (Compound V3 not active on Polygon)
        "OPTIMISM": "FhHNkfh5z6Z2WCEBxB6V3s8RPxnJfWZ9zAfM5bVvbvbb",
    },
    "morpho": {
        # Morpho adapter uses blue-api.morpho.org (NOT The Graph subgraphs).
        # IDs here are subgraph IDs from docs.morpho.org but only used to declare
        # which chains instruments-service should query. Only list chains where
        # Morpho Blue has markets with major assets (DEFI_MAJOR_ASSET_SYMBOLS).
        # ARBITRUM/OPTIMISM/POLYGON: 0 major-asset markets as of 2026-03.
        "ETHEREUM": "8Lz789DP5VKLXumTMTgygjU2xtuzx8AhbaacgN5PYCAs",
        "BASE": "71ZTy1veF9twER9CLMnPWeLQ7GZcwKsjmygejrgKirqs",
    },
    "fluid": {
        "ETHEREUM": "fluid-mainnet",
        # Multi-chain: Fluid subgraph IDs need verification
    },
    # ── DEX protocols ──────────────────────────────────────────────
    "uniswap_v2": {
        "ETHEREUM": "A3Np3RQbaBA6oKJgiwDJeo5T3zrYfGHPWFYayMwtNDum",
    },
    "uniswap_v3": {  # Verified via The Graph gateway
        "ETHEREUM": "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
        "ARBITRUM": "FbCGRftH4a3yZugY7TnbYgPJVEv2LvMT6oF1fxPe9aJM",
        "BASE": "HMuAwufqZ1YCRmzL2SfHTVkzZovC9VL2UAKhjvRqKiR1",  # UniV3-Base (official schema)
        "OPTIMISM": "Cghf4LfVqPiFw6fp6Y5X5Ubc8UpmUhSfJL82zwiBFLaj",
        "POLYGON": "3hCPRGf4z88VC5rsBKU5AA9FBBq5nF3jbKJG7VZCbhjm",
    },
    "uniswap_v4": {
        "ETHEREUM": "DiYPVdygkfjDWhbxGSqAQxwBKmfKnkWQojqeM2rkLb3G",
    },
    "balancer": {  # Verified from docs-v2.balancer.fi/reference/subgraph/
        "ETHEREUM": "C4ayEZP2yTXRAB8vSaTrgN4m9anTe9Mdm2ViyiAuV9TV",
        "ARBITRUM": "98cQDy6tufTJtshDCuhh9z2kWXsQWBHVh2bqnLHsGAeS",
        "POLYGON": "H9oPAbXnobBRq1cB3HDmbZ1E8MWQyJYQjT1QDJMrdbNp",
        "OPTIMISM": "FsmdxmvBJLGjUQPxKMRtcWKzuCNpomKuMTbSbtRtggZ7",
        "AVALANCHE": "7asfmtQA1KYu6CP7YVm5kv4bGxVyfAHEiptt2HMFgkHu",
        "BASE": "E7XyutxXVLrp8njmjF16Hh38PCJuHm12RRyMt5ma4ctX",
    },
    "curve": {  # Verified from thegraph.com/explorer (Messari schema)
        "ETHEREUM": "3fy93eAT56UJsRCEht8iFhfi6wjHWXtZ9dnnbQmvFopF",
        "OPTIMISM": "CXDZPduZE6nWuWEkSzWkRoJSSJ6CneSqiDxdnhhURShX",
        "AVALANCHE": "2Vt8WtdXNZUEeaVtzyEd1dpioJf44nvomzkd4HhubfKS",
        # ARB/POLY only on hosted service (deprecated) — use api.curve.fi instead
    },
    # ── Additional DEX protocols (chain-dominant) ─────────────────
    "pancakeswap_v3": {  # UniV3-fork schema (poolDayDatas) — from pancakeswap/pancake-frontend
        "BSC": "Hv1GncLY5docZoGtXjo4kwbTvxm3MAhVZqBZE4sUT9eZ",
        "ETHEREUM": "CJYGNhb7RvnhfBDjqpRnD3oxgyhibzc7fkAMa38YV3oS",
        "BASE": "5YYKGBcRkJs6tmDfB3RpHdbK2R5KBACHQebXVgbUcYQp",
    },
    "sushiswap_v3": {  # Mixed schemas: ETH/AVAX = Messari DEX, BASE = SushiSwap custom (pairDaySnapshots)
        "ETHEREUM": "2tGWMrDha4164KkFAfkU3rDCtuxGb4q1emXmFdLLzJ8x",
        "BASE": "H6SjXCnZxJhaVHw4VDuXqtzWZ2JEBDvhwA3qysnUEjSV",
        "AVALANCHE": "9WGqYsU8h1KVZeKz32663gFrbjVUNhBgmhRavMFqiSZz",
    },
    "sushiswap": {  # Messari schema (liquidityPoolDailySnapshots) — legacy V2
        "ARBITRUM": "9tSS5FaePZnjmnXnSKCCqKVLAqA6eGg6jA2oRojsXUbP",
    },
    "aerodrome_v3": {  # UniV3-style schema (poolDayDatas) — "Aerodrome Base Full"
        "BASE": "GENunSHWLBXm59mBSgPzQ8metBEp9YDfdqwFr91Av1UM",
    },
    "velodrome_v2": {  # Messari schema (liquidityPoolDailySnapshots)
        "OPTIMISM": "A4Y1A82YhSLTn998BVVELC8eWzhi992k4ZitByvssxqA",
    },
    "camelot_v3": {  # Algebra CL schema (poolDayDatas — UniV3-compatible)
        "ARBITRUM": "7mPnp1UqmefcCycB8umy4uUkTkFxMoHn1Y7ncBUscePp",
    },
    "trader_joe_v2": {  # Messari schema (liquidityPoolDailySnapshots)
        "AVALANCHE": "H2VGe2tYavUEosSjomHwxbvCKy3LaNaW8Kjw2KhhHs1K",
    },
    # ── Additional perps ──────────────────────────────────────────
    "gmx": {  # Messari schema
        "ARBITRUM": "DiR5cWwB3pwXXQWWdus7fDLR2mnFRQLiBFsVmHAH9VAs",
        "AVALANCHE": "6pXgnXcL6mkXBjKX7NyHN7tCudv2JGFnXZ8wf8WbjPXv",
    },
    # ── Additional lending ────────────────────────────────────────
    "spark": {  # Messari lending schema (same as Aave V3 — MakerDAO fork)
        "ETHEREUM": "GbKdmBe4ycCYCQLQSjqGg6UHYoYfbyJyq5WrG35pv1si",
    },
}


def get_supported_chains_for_protocol(protocol: str) -> list[str]:
    """Get all chains that have subgraph IDs for a protocol."""
    return list(SUBGRAPH_IDS.get(protocol, {}).keys())


def get_subgraph_id(protocol: str, chain: str = "ETHEREUM") -> str | None:
    """Look up a subgraph ID by protocol and chain.

    Args:
        protocol: Protocol slug (e.g. "aave_v3", "uniswap_v3").
        chain: Chain name (e.g. "ETHEREUM", "ARBITRUM"). Defaults to "ETHEREUM".

    Returns:
        Subgraph ID string, or None if not found.
    """
    protocol_ids = SUBGRAPH_IDS.get(protocol)
    if protocol_ids is None:
        return None
    return protocol_ids.get(chain.upper())


# ---------------------------------------------------------------------------
# Protocol capability declarations (SSOT)
#
# Single source of truth for:
#   - instrument_types: what InstrumentType each protocol produces
#   - data_types: what MTDS data types each protocol produces
#   - mtds_operation: which MTDS --operation collects data for this protocol
#   - venue_prefix: canonical venue prefix (e.g. "AAVEV3")
#   - protocol_class: classification for filtering/routing
#   - required_tokens: protocol-native tokens that MUST be in the major assets
#     filter (governance, reward, staking tokens that our strategies need)
#   - chain_native_tokens: per-chain tokens auto-included when protocol is
#     deployed on that chain (e.g. SOL for Solana, BNB for BSC)
#
# Consumers:
#   - instruments-service orchestrator: builds venue list from this
#   - MTDS handlers: validate which data types to collect per protocol
#   - market_data_categories.py: derives VENUES_BY_CATEGORY from this
#   - deployment-ui data-status: shows expected data coverage matrix
# ---------------------------------------------------------------------------

from ..._instrument_enums import InstrumentType as _IT  # noqa: E402, N814


class ProtocolClass(StrEnum):
    """Protocol classification for filtering and routing."""

    LENDING = "lending"
    DEX = "dex"
    YIELD = "yield"
    STAKING = "staking"
    PERPS = "perps"
    RESTAKING = "restaking"


class _ProtocolCapability:
    """Capability declaration for a single DeFi protocol."""

    __slots__ = (
        "data_types",
        "instrument_types",
        "mtds_operations",
        "protocol_class",
        "required_tokens",
        "venue_prefix",
    )

    def __init__(
        self,
        venue_prefix: str,
        protocol_class: ProtocolClass,
        instrument_types: list[str],
        data_types: list[str],
        mtds_operations: list[str],
        required_tokens: frozenset[str] | None = None,
    ) -> None:
        self.venue_prefix = venue_prefix
        self.protocol_class = protocol_class
        self.instrument_types = instrument_types
        self.data_types = data_types
        self.mtds_operations = mtds_operations
        self.required_tokens = required_tokens or frozenset()


# Instrument type shorthands
_LENDING = [_IT.LENDING]
_POOL = [_IT.POOL]
_YIELD = [_IT.YIELD_BEARING]
_STAKING = [_IT.STAKING]
_PERPS = [_IT.PERPETUAL, _IT.SPOT_PAIR]
_RESTAKING = [_IT.SPOT_ASSET]

# Data type groups
#
# These describe ALL data types a protocol CAN produce — both what MTDS
# collects today and what's available on-chain/via APIs.  "Aspirational"
# entries are marked with inline comments; MTDS handlers for those may
# not exist yet but the data IS available at the source.
#
# Key distinctions:
#   tvl           — totalValueLockedUSD (pool/market level, from snapshots)
#   swaps         — individual swap events (amount0, amount1, amountUSD, sender, ts)
#   dex_pools     — daily pool aggregates (volume24h, fees24h, tvl) from poolDayDatas
#   oracle_prices — external price feeds (Chainlink, protocol exchange rates)
#                   needed to compute yield on non-rebasing tokens (sUSDe, wstETH)
#   gas_fees      — chain-level gas price data (baseFee, priorityFee, gasUsed)
#
_LENDING_DATA = ["rate_indices", "utilization", "liquidations", "risk_params", "tvl"]
_DEX_DATA = ["dex_pools", "swaps", "tvl"]
_YIELD_DATA = ["lst_rates", "oracle_prices"]
_STAKING_DATA = ["lst_rates", "oracle_prices"]
_PERPS_DATA = ["perp_funding"]

PROTOCOL_CAPABILITIES: dict[str, _ProtocolCapability] = {
    # ── EVM Lending ──────────────────────────────────────────────
    "aave_v3": _ProtocolCapability(
        venue_prefix="AAVEV3",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "evm_defi", "gas_fees"],
        mtds_operations=["collect-evm-defi", "collect-lending-indices", "collect-liquidations", "collect-gas-fees"],
        required_tokens=frozenset({"AAVE", "GHO"}),
    ),
    "spark": _ProtocolCapability(
        venue_prefix="SPARK",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "gas_fees"],
        mtds_operations=["collect-lending-indices", "collect-liquidations", "collect-gas-fees"],
        required_tokens=frozenset({"MKR", "DAI"}),
    ),
    "compound_v3": _ProtocolCapability(
        venue_prefix="COMPOUNDV3",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "evm_defi", "gas_fees"],
        mtds_operations=["collect-evm-defi", "collect-lending-indices", "collect-liquidations", "collect-gas-fees"],
        required_tokens=frozenset({"COMP"}),
    ),
    "morpho": _ProtocolCapability(
        venue_prefix="MORPHO",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "evm_defi", "gas_fees"],
        mtds_operations=["collect-evm-defi", "collect-liquidations", "collect-gas-fees"],
    ),
    "fluid": _ProtocolCapability(
        venue_prefix="FLUID",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "evm_defi", "gas_fees"],
        mtds_operations=["collect-evm-defi", "collect-liquidations", "collect-gas-fees"],
    ),
    # ── EVM DEX — Native schema ─────────────────────────────────
    "uniswap_v2": _ProtocolCapability(
        venue_prefix="UNISWAPV2",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"UNI"}),
    ),
    "uniswap_v3": _ProtocolCapability(
        venue_prefix="UNISWAPV3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"UNI"}),
    ),
    "uniswap_v4": _ProtocolCapability(
        venue_prefix="UNISWAPV4",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"UNI"}),
    ),
    "balancer": _ProtocolCapability(
        venue_prefix="BALANCER",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"BAL"}),
    ),
    "curve": _ProtocolCapability(
        venue_prefix="CURVE",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"CRV", "CRVUSD"}),
    ),
    # ── EVM DEX — Forks (reuse uniswap_v3 adapter) ─────────────
    "pancakeswap_v3": _ProtocolCapability(
        venue_prefix="PANCAKESWAPV3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "sushiswap_v3": _ProtocolCapability(
        venue_prefix="SUSHISWAPV3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"SUSHI"}),
    ),
    "sushiswap": _ProtocolCapability(
        venue_prefix="SUSHISWAP",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"SUSHI"}),
    ),
    "aerodrome_v3": _ProtocolCapability(
        venue_prefix="AERODROMEV3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "camelot_v3": _ProtocolCapability(
        venue_prefix="CAMELOTV3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "velodrome_v2": _ProtocolCapability(
        venue_prefix="VELODROMEV2",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "trader_joe_v2": _ProtocolCapability(
        venue_prefix="TRADERJOEV2",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "gmx": _ProtocolCapability(
        venue_prefix="GMX",
        protocol_class=ProtocolClass.PERPS,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, *_PERPS_DATA, "liquidations", "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-perp-funding", "collect-gas-fees"],
    ),
    # ── EVM Yield/Staking (static adapters, no subgraph) ────────
    "lido": _ProtocolCapability(
        venue_prefix="LIDO",
        protocol_class=ProtocolClass.YIELD,
        instrument_types=_YIELD,
        data_types=[*_YIELD_DATA, "rewards", "gas_fees"],
        mtds_operations=["collect-lst-rates", "collect-oracle-prices", "collect-gas-fees"],
        required_tokens=frozenset({"LDO", "STETH", "WSTETH"}),
    ),
    "etherfi": _ProtocolCapability(
        venue_prefix="ETHERFI",
        protocol_class=ProtocolClass.YIELD,
        instrument_types=_YIELD,
        data_types=[*_YIELD_DATA, "rewards", "gas_fees"],
        mtds_operations=["collect-lst-rates", "collect-oracle-prices", "collect-gas-fees"],
        required_tokens=frozenset({"ETHFI", "EETH", "WEETH"}),
    ),
    "ethena": _ProtocolCapability(
        venue_prefix="ETHENA",
        protocol_class=ProtocolClass.YIELD,
        instrument_types=_YIELD,
        data_types=[*_YIELD_DATA, "gas_fees"],
        mtds_operations=["collect-lst-rates", "collect-oracle-prices", "collect-gas-fees"],
        required_tokens=frozenset({"USDE", "SUSDE"}),
    ),
    "eigenlayer": _ProtocolCapability(
        venue_prefix="EIGENLAYER",
        protocol_class=ProtocolClass.RESTAKING,
        instrument_types=_RESTAKING,
        data_types=["rewards", "oracle_prices", "gas_fees"],
        mtds_operations=["collect-eigenlayer-rewards", "collect-oracle-prices", "collect-gas-fees"],
        required_tokens=frozenset({"EIGEN", "ETHFI"}),
    ),
    # ── CeFi-style Perps (API-based, not on-chain) ─────────────
    "hyperliquid": _ProtocolCapability(
        venue_prefix="HYPERLIQUID",
        protocol_class=ProtocolClass.PERPS,
        instrument_types=_PERPS,
        data_types=["perp_funding", "oracle_prices"],
        mtds_operations=["collect-perp-funding"],
    ),
    "aster": _ProtocolCapability(
        venue_prefix="ASTER",
        protocol_class=ProtocolClass.PERPS,
        instrument_types=_PERPS,
        data_types=["perp_funding"],
        mtds_operations=["collect-perp-funding"],
    ),
    # ── Solana DeFi ─────────────────────────────────────────────
    "drift": _ProtocolCapability(
        venue_prefix="DRIFT",
        protocol_class=ProtocolClass.PERPS,
        instrument_types=_PERPS,
        data_types=["perp_funding", "oracle_prices", "solana_defi"],
        mtds_operations=["collect-solana-defi", "collect-perp-funding"],
        required_tokens=frozenset({"DRIFT"}),
    ),
    "kamino": _ProtocolCapability(
        venue_prefix="KAMINO",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=["solana_defi", "swaps", "tvl"],
        mtds_operations=["collect-solana-defi"],
        required_tokens=frozenset({"KMNO"}),
    ),
    "raydium": _ProtocolCapability(
        venue_prefix="RAYDIUM",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=["solana_defi", "swaps", "tvl"],
        mtds_operations=["collect-solana-defi"],
        required_tokens=frozenset({"RAY"}),
    ),
    "orca": _ProtocolCapability(
        venue_prefix="ORCA",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=["solana_defi", "swaps", "tvl"],
        mtds_operations=["collect-solana-defi"],
        required_tokens=frozenset({"ORCA"}),
    ),
    "marinade": _ProtocolCapability(
        venue_prefix="MARINADE",
        protocol_class=ProtocolClass.STAKING,
        instrument_types=_STAKING,
        data_types=["solana_defi", "lst_rates", "oracle_prices"],
        mtds_operations=["collect-solana-defi"],
        required_tokens=frozenset({"MNDE", "MSOL"}),
    ),
    "jito": _ProtocolCapability(
        venue_prefix="JITO",
        protocol_class=ProtocolClass.STAKING,
        instrument_types=_STAKING,
        data_types=["solana_defi", "lst_rates", "oracle_prices"],
        mtds_operations=["collect-solana-defi"],
        required_tokens=frozenset({"JTO", "JITOSOL", "JSOL"}),
    ),
}

# Chain-native tokens — auto-included in major assets for any protocol on that chain.
# These are gas tokens and wrapped variants needed for ANY pool on that chain.
CHAIN_REQUIRED_TOKENS: dict[str, frozenset[str]] = {
    "ETHEREUM": frozenset({"ETH", "WETH"}),
    "ARBITRUM": frozenset({"ETH", "WETH"}),
    "OPTIMISM": frozenset({"ETH", "WETH"}),
    "BASE": frozenset({"ETH", "WETH"}),
    "POLYGON": frozenset({"MATIC", "WMATIC"}),
    "AVALANCHE": frozenset({"AVAX", "WAVAX"}),
    "BSC": frozenset({"BNB", "WBNB"}),
    "LINEA": frozenset({"ETH", "WETH"}),
    "SOLANA": frozenset({"SOL", "WSOL"}),
}

# Wrapped/staked token equivalence groups — for major assets matching,
# any token in the same group counts as a match. This means if ETH is in
# the major assets list, pools with WETH/stETH/wstETH/cbETH/rETH/weETH
# all pass the filter without needing every variant listed explicitly.
TOKEN_EQUIVALENCE_GROUPS: dict[str, frozenset[str]] = {
    "ETH": frozenset(
        {
            "ETH",
            "WETH",
            "STETH",
            "WSTETH",
            "CBETH",
            "RETH",
            "WEETH",
            "EETH",
            "SFRXETH",
            "FRXETH",
            "OETH",
            "OSETH",
            "SWETH",
            "ETHX",
            "METH",
            "EZETH",
            "RSETH",
            "PUFETH",
            "ANKRETH",
            "WETH.E",  # Avalanche/Polygon bridged
        }
    ),
    "BTC": frozenset(
        {
            "BTC",
            "WBTC",
            "TBTC",
            "CBBTC",
            "LBTC",
        }
    ),
    "USD": frozenset(
        {
            "USDT",
            "USDC",
            "DAI",
            "FRAX",
            "USDE",
            "SUSDE",
            "GHO",
            "CRVUSD",
            "LUSD",
            "PYUSD",
            "EURC",
            "SUSD",
            "TUSD",
            "USDP",
            "USDC.E",
            "USDT.E",  # Bridged variants
        }
    ),
    "SOL": frozenset(
        {
            "SOL",
            "WSOL",
            "MSOL",
            "STSOL",
            "JITOSOL",
            "BSOL",
            "JSOL",
        }
    ),
    "MATIC": frozenset({"MATIC", "WMATIC"}),
    "AVAX": frozenset({"AVAX", "WAVAX"}),
    "BNB": frozenset({"BNB", "WBNB"}),
}

# Reverse lookup: token → equivalence group base
_TOKEN_TO_GROUP: dict[str, str] = {tok: group for group, tokens in TOKEN_EQUIVALENCE_GROUPS.items() for tok in tokens}


def get_protocol_capability(protocol: str) -> _ProtocolCapability | None:
    """Get capability declaration for a protocol."""
    return PROTOCOL_CAPABILITIES.get(protocol)


def get_venue_prefix(protocol: str) -> str | None:
    """Get the canonical venue prefix for a protocol (e.g. 'aave_v3' -> 'AAVEV3')."""
    cap = PROTOCOL_CAPABILITIES.get(protocol)
    return cap.venue_prefix if cap else None


def get_data_types_for_protocol(protocol: str) -> list[str]:
    """Get the data types that MTDS should collect for a protocol."""
    cap = PROTOCOL_CAPABILITIES.get(protocol)
    return list(cap.data_types) if cap else []


def get_mtds_operations_for_protocol(protocol: str) -> list[str]:
    """Get the MTDS operations that should run for a protocol."""
    cap = PROTOCOL_CAPABILITIES.get(protocol)
    return list(cap.mtds_operations) if cap else []


def get_required_tokens_for_protocol(protocol: str) -> frozenset[str]:
    """Get protocol-native tokens that must be in the major assets filter."""
    cap = PROTOCOL_CAPABILITIES.get(protocol)
    return cap.required_tokens if cap else frozenset()


def get_required_tokens_for_venue(venue: str) -> frozenset[str]:
    """Get all required tokens for a venue (protocol + chain tokens).

    Args:
        venue: Canonical venue name (e.g. "AAVEV3-ETHEREUM", "DRIFT-SOLANA").

    Returns:
        Union of protocol-required tokens + chain-native tokens.
    """
    parts = venue.split("-", 1)
    if len(parts) != 2:
        return frozenset()

    # Find protocol by venue prefix
    prefix = parts[0]
    chain = parts[1]
    protocol_tokens: frozenset[str] = frozenset()
    for cap in PROTOCOL_CAPABILITIES.values():
        if cap.venue_prefix == prefix:
            protocol_tokens = cap.required_tokens
            break

    chain_tokens = CHAIN_REQUIRED_TOKENS.get(chain, frozenset())
    return protocol_tokens | chain_tokens


def is_token_equivalent(token_a: str, token_b: str) -> bool:
    """Check if two tokens are in the same equivalence group.

    Used for major-assets filtering with tolerance for wrapped/staked variants.
    E.g. is_token_equivalent("WETH", "stETH") -> True (both in ETH group).
    """
    upper_a = token_a.upper()
    upper_b = token_b.upper()
    if upper_a == upper_b:
        return True
    group_a = _TOKEN_TO_GROUP.get(upper_a)
    group_b = _TOKEN_TO_GROUP.get(upper_b)
    return bool(group_a is not None and group_a == group_b)


def token_matches_major_assets(token: str, major_assets: frozenset[str]) -> bool:
    """Check if a token passes the major assets filter with equivalence tolerance.

    Returns True if:
    1. The token itself is in major_assets, OR
    2. Any token in the same equivalence group is in major_assets.

    This means a pool with WETH passes even if only "ETH" is in the filter,
    because WETH and ETH are in the same equivalence group.
    """
    upper = token.upper()
    if upper in major_assets:
        return True
    group = _TOKEN_TO_GROUP.get(upper)
    if group is None:
        return False
    return bool(TOKEN_EQUIVALENCE_GROUPS[group] & major_assets)


def build_complete_major_assets() -> frozenset[str]:
    """Build the complete major assets set including all protocol and chain tokens.

    Combines:
    1. All tokens from TOKEN_EQUIVALENCE_GROUPS (ETH/BTC/USD/SOL families)
    2. All protocol required_tokens (governance tokens, reward tokens)
    3. All chain native tokens
    """
    tokens: set[str] = set()

    # All equivalence group tokens
    for group_tokens in TOKEN_EQUIVALENCE_GROUPS.values():
        tokens |= group_tokens

    # All protocol-required tokens
    for cap in PROTOCOL_CAPABILITIES.values():
        tokens |= cap.required_tokens

    # All chain-native tokens
    for chain_tokens in CHAIN_REQUIRED_TOKENS.values():
        tokens |= chain_tokens

    return frozenset(tokens)


def build_defi_venues() -> list[str]:
    """Build the full DeFi venue list from protocol capabilities + SUBGRAPH_IDS.

    This is the SSOT for the expected venue set. Generates PROTOCOL-CHAIN
    for each protocol that has subgraph IDs, plus static venues.
    """
    venues: list[str] = []
    for protocol, cap in PROTOCOL_CAPABILITIES.items():
        chains = get_supported_chains_for_protocol(protocol)
        if chains:
            for chain in chains:
                venues.append(f"{cap.venue_prefix}-{chain}")
        elif protocol in _STATIC_VENUE_CHAINS:
            # Protocols without subgraph IDs — static chain mapping
            for chain in _STATIC_VENUE_CHAINS[protocol]:
                venues.append(f"{cap.venue_prefix}-{chain}")
    return venues


# Static chain assignments for protocols that don't use The Graph
_STATIC_VENUE_CHAINS: dict[str, list[str]] = {
    "lido": ["ETHEREUM"],
    "etherfi": ["ETHEREUM"],
    "ethena": ["ETHEREUM"],
    "eigenlayer": ["ETHEREUM"],
    "hyperliquid": ["HYPERLIQUID"],
    "aster": ["ASTER"],
    "drift": ["SOLANA"],
    "kamino": ["SOLANA"],
    "raydium": ["SOLANA"],
    "orca": ["SOLANA"],
    "marinade": ["SOLANA"],
    "jito": ["SOLANA"],
}


# Reverse lookup: venue_prefix → protocol slug (for parse_defi_venue)
_PREFIX_TO_PROTOCOL: dict[str, str] = {cap.venue_prefix: slug for slug, cap in PROTOCOL_CAPABILITIES.items()}

# All known chain names (from SUBGRAPH_IDS + _STATIC_VENUE_CHAINS)
KNOWN_CHAINS: frozenset[str] = frozenset(
    {chain for chains in SUBGRAPH_IDS.values() for chain in chains}
    | {chain for chains in _STATIC_VENUE_CHAINS.values() for chain in chains}
)


def parse_defi_venue(venue_str: str) -> tuple[str, str]:
    """Split a DeFi venue string into (protocol_slug, chain).

    Parses "AAVEV3-ETHEREUM" → ("aave_v3", "ETHEREUM"),
    "UNISWAPV3-BASE" → ("uniswap_v3", "BASE"), etc.

    Uses the PROTOCOL_CAPABILITIES venue_prefix as the authority
    for how to split the string. Falls back to splitting on the
    last hyphen if no prefix match.

    Returns:
        (protocol_slug, chain_name) — protocol_slug matches PROTOCOL_CAPABILITIES keys.
    """
    # Try known prefixes (longest match first to handle UNISWAPV3 vs UNISWAPV2)
    for prefix in sorted(_PREFIX_TO_PROTOCOL, key=len, reverse=True):
        if venue_str.startswith(prefix + "-"):
            chain = venue_str[len(prefix) + 1 :]
            return _PREFIX_TO_PROTOCOL[prefix], chain
    # Fallback: split on last hyphen
    if "-" in venue_str:
        idx = venue_str.rfind("-")
        prefix_part = venue_str[:idx]
        chain_part = venue_str[idx + 1 :]
        # Check if chain_part is a known chain
        if chain_part in KNOWN_CHAINS:
            slug = _PREFIX_TO_PROTOCOL.get(prefix_part, prefix_part.lower())
            return slug, chain_part
    return venue_str.lower(), ""


def get_all_defi_chains() -> list[str]:
    """Return all chains with DeFi protocol deployments, sorted."""
    return sorted(KNOWN_CHAINS)


# ---------------------------------------------------------------------------
# Chain-specific Alchemy RPC URL templates (SSOT)
#
# Used by execution-service to resolve a fully-qualified RPC URL before
# injecting it into UDEI connector config.  Interfaces never touch these
# directly — they receive a pre-resolved ``rpc_url`` from the service layer.
# ---------------------------------------------------------------------------
CHAIN_RPC_TEMPLATES: dict[int, str] = {
    # ── Tier 1: Core ETH + L2s (strategy-critical) ───────────────
    1: "https://eth-mainnet.g.alchemy.com/v2/{api_key}",
    10: "https://opt-mainnet.g.alchemy.com/v2/{api_key}",
    8453: "https://base-mainnet.g.alchemy.com/v2/{api_key}",
    42161: "https://arb-mainnet.g.alchemy.com/v2/{api_key}",
    # ── Tier 2: Major non-ETH EVM chains ─────────────────────────
    56: "https://bnb-mainnet.g.alchemy.com/v2/{api_key}",
    137: "https://polygon-mainnet.g.alchemy.com/v2/{api_key}",
    43114: "https://avax-mainnet.g.alchemy.com/v2/{api_key}",
    100: "https://gnosis-mainnet.g.alchemy.com/v2/{api_key}",
    # ── Tier 3: ETH-native L2s + zkEVMs ──────────────────────────
    130: "https://unichain-mainnet.g.alchemy.com/v2/{api_key}",
    324: "https://zksync-mainnet.g.alchemy.com/v2/{api_key}",
    480: "https://worldchain-mainnet.g.alchemy.com/v2/{api_key}",
    1101: "https://polygonzkevm-mainnet.g.alchemy.com/v2/{api_key}",
    2741: "https://abstract-mainnet.g.alchemy.com/v2/{api_key}",
    34443: "https://mode-mainnet.g.alchemy.com/v2/{api_key}",
    57073: "https://ink-mainnet.g.alchemy.com/v2/{api_key}",
    59144: "https://linea-mainnet.g.alchemy.com/v2/{api_key}",
    81457: "https://blast-mainnet.g.alchemy.com/v2/{api_key}",
    534352: "https://scroll-mainnet.g.alchemy.com/v2/{api_key}",
    7777777: "https://zora-mainnet.g.alchemy.com/v2/{api_key}",
    # ── Testnets (EVM) — same key, different endpoints ───────────
    11155111: "https://eth-sepolia.g.alchemy.com/v2/{api_key}",  # ETH Sepolia
    11155420: "https://opt-sepolia.g.alchemy.com/v2/{api_key}",  # OP Sepolia
    84532: "https://base-sepolia.g.alchemy.com/v2/{api_key}",  # Base Sepolia
    421614: "https://arb-sepolia.g.alchemy.com/v2/{api_key}",  # Arbitrum Sepolia
    80002: "https://polygon-amoy.g.alchemy.com/v2/{api_key}",  # Polygon Amoy
    43113: "https://avax-fuji.g.alchemy.com/v2/{api_key}",  # Avalanche Fuji
    300: "https://zksync-sepolia.g.alchemy.com/v2/{api_key}",  # zkSync Sepolia
    168587773: "https://blast-sepolia.g.alchemy.com/v2/{api_key}",  # Blast Sepolia
    534351: "https://scroll-sepolia.g.alchemy.com/v2/{api_key}",  # Scroll Sepolia
    59141: "https://linea-sepolia.g.alchemy.com/v2/{api_key}",  # Linea Sepolia
}

# ---------------------------------------------------------------------------
# Solana RPC templates — same pattern as EVM, keyed by network name.
# Uses the same alchemy-api-key from Secret Manager (one key covers all chains).
# SSOT for all Solana RPC URLs — services import from here, never hardcode.
# ---------------------------------------------------------------------------
SOLANA_RPC_TEMPLATES: dict[str, str] = {
    # ── Mainnet ──────────────────────────────────────────────────
    "alchemy": "https://solana-mainnet.g.alchemy.com/v2/{api_key}",
    "helius": "https://mainnet.helius-rpc.com/?api-key={api_key}",
    # ── Devnet (Solana testnet equivalent) ────────────────────────
    "alchemy_devnet": "https://solana-devnet.g.alchemy.com/v2/{api_key}",
    "helius_devnet": "https://devnet.helius-rpc.com/?api-key={api_key}",
    "public_devnet": "https://api.devnet.solana.com",
}

# All RPC templates use secret: alchemy-api-key (DATA_SOURCE_TO_SECRET in canonical_mappings)
# Same key works for EVM + Solana on Alchemy.

# ---------------------------------------------------------------------------
# Protected RPC URLs for MEV-resistant transaction submission (SSOT)
#
# Used by execution-service MEV protection layer (mev/protection.py).
# Connectors must NOT hardcode these — import from here.
# ETHEREUM: Flashbots Protect (free, no auth needed, blocks sandwich attacks)
# ETHEREUM_BUNDLE: Flashbots Bundle relay (requires ethers signing for bundles)
# MEV_BLOCKER: CoW Protocol MEV Blocker (aggregates multiple builders)
# ---------------------------------------------------------------------------
PROTECTED_RPC_URLS: dict[str, str] = {
    "ETHEREUM": "https://rpc.flashbots.net",  # Flashbots Protect (MEV Blocker)
    "ETHEREUM_BUNDLE": "https://relay.flashbots.net",  # Flashbots Bundle relay
    "MEV_BLOCKER": "https://rpc.mevblocker.io",  # CoW Protocol MEV Blocker
}

# ---------------------------------------------------------------------------
# Chain native gas tokens (SSOT)
# Gas is paid in the native token — ETH on L2s, BNB/MATIC/AVAX on alt-L1s
# ---------------------------------------------------------------------------
CHAIN_NATIVE_GAS_TOKEN: dict[int, str] = {
    1: "ETH",
    10: "ETH",
    56: "BNB",
    130: "ETH",
    137: "MATIC",
    324: "ETH",
    480: "ETH",
    1101: "ETH",
    2741: "ETH",
    8453: "ETH",
    34443: "ETH",
    42161: "ETH",
    43114: "AVAX",
    57073: "ETH",
    59144: "ETH",
    81457: "ETH",
    534352: "ETH",
    7777777: "ETH",
    11155111: "ETH",
}

# ---------------------------------------------------------------------------
# WETH addresses per chain (SSOT for wrap/unwrap)
# DeFi protocols require WETH (ERC20); gas is paid in native ETH.
# On non-ETH chains, this is the wrapped native token (WBNB, WMATIC, WAVAX).
# ---------------------------------------------------------------------------
WETH_ADDRESSES: dict[int, str] = {
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    10: "0x4200000000000000000000000000000000000006",
    56: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
    130: "0x4200000000000000000000000000000000000006",
    137: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
    324: "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
    480: "0x4200000000000000000000000000000000000006",
    1101: "0x4F9A0e7FD2Bf6067db6994CF12E4495Df938E6e9",
    2741: "0x4200000000000000000000000000000000000006",
    8453: "0x4200000000000000000000000000000000000006",
    34443: "0x4200000000000000000000000000000000000006",
    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    43114: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",  # WAVAX
    57073: "0x4200000000000000000000000000000000000006",
    59144: "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f",
    81457: "0x4300000000000000000000000000000000000004",
    534352: "0x5300000000000000000000000000000000000004",
    7777777: "0x4200000000000000000000000000000000000006",
    11155111: "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14",
}

# ---------------------------------------------------------------------------
# WBTC / cbBTC addresses per chain (BTC on EVM — first-class instruments)
# ---------------------------------------------------------------------------
WBTC_ADDRESSES: dict[int, str] = {
    1: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    10: "0x68f180fcCe6836688e9084f035309E29Bf0A2095",
    137: "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
    42161: "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
    43114: "0x50b7545627a5162F82A992c33b87aDc75187B218",
}

CBBTC_ADDRESSES: dict[int, str] = {
    1: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    8453: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    42161: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
}


def get_native_gas_token(chain_id: int) -> str:
    """Get the native gas token symbol for a chain."""
    return CHAIN_NATIVE_GAS_TOKEN.get(chain_id, "ETH")


def get_weth_address(chain_id: int) -> str | None:
    """Get the WETH (wrapped native) contract address for a chain."""
    return WETH_ADDRESSES.get(chain_id)


# ---------------------------------------------------------------------------
# Non-EVM chains (SSOT)
#
# Solana and Bitcoin are fundamentally different from EVM chains:
# - Different RPC protocols, transaction models, token standards
# - Separate adapter stacks required (not The Graph subgraphs)
# - Chain IDs are conventional strings, not EVM uint256
# ---------------------------------------------------------------------------


class NonEvmChain(StrEnum):
    """Non-EVM chain identifiers."""

    SOLANA = "SOLANA"
    BITCOIN = "BITCOIN"


# Solana RPC templates — SSOT is SOLANA_RPC_TEMPLATES defined above (line ~162)
# alongside CHAIN_RPC_TEMPLATES for consistency.

# Solana key program/token addresses (symbol → mint)
SOLANA_TOKEN_ADDRESSES: dict[str, str] = {
    # Native + wrapped
    "WSOL": "So11111111111111111111111111111111111111112",
    "SOL": "So11111111111111111111111111111111111111112",
    # Stablecoins
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "PYUSD": "2b1kV6DkPAnxd5ixfnExCx2PdhTtQER4hSsd53Ky7Adr",
    "USDE": "DEkqHyPN7GMRJ5cAU54aqYySacfiMkNy3asF1JEvp2up",
    "SUSDE": "Eh6XEPhSwoLv5kaAtbuvv6EaVHm11Yjhed2BNSHBBBiA",
    "USDH": "USDH1SM1ojwWUga67PBrgQe7PYQMjdiBJKgnGFmsDs7F",
    "EURC": "HzwqbKZw8HxMN6bF2yFZNrht3c2iXXzpKcFu7uBEDKtr",
    # BTC wrapped
    "WETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
    "WBTC": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
    "WBTC_PORTAL": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
    "CBBTC": "cbbtcn3Keb2DW3ZsmLmrsPGsRRhQ3HmFsRJhKqLm1bq",
    "TBTC": "6DNSN2BJsaPFdFFc1zP37kkeNe4Usc1Sqkzr9C9vPWcU",
    # Liquid staking
    "MSOL": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "JITOSOL": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
    "BSOL": "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
    "STSOL": "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",
    "JSOL": "7Q2afV64in6N6SeZsAAB81TJzwpeLmhBf8u3mE2ip1Fh",
    "BNSOL": "BNso1VUJnh4zcfpZa6986Ea66P6TCp59hvtNJ8b1X85",
    # Top ecosystem tokens
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "HNT": "hntyVP6YFm1Hg25TN9WGLqM12b8TQv3TXsxg8HBatYS",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "MNDE": "MNDEFzGvMt87ueuHvVU9VcTqsAP5b3fTGPsHuuPA5ey",
    "KMNO": "KMNo3nJsBXfcpJTVhZcXLW7RmTwTt4GVFE7suUBo9sS",
    "RNDR": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    # Bridged
    "AVAX": "AUrMpCDYYcPuGMvN8P8PQkpHf3AqiL54ziiPPWQr3XXR",
    "WSTETH": "ZScHuTtqZukUrtZS43teTKGs2VqkKL8k4QCouR2n6Uo",
    "BNB": "9gP2kCy3wA1ctvYWQk75guqXuHfrEomqydHLtcTCqiLa",
}

# Reverse mapping: mint → symbol (for parsing on-chain / API responses)
SOLANA_MINT_TO_SYMBOL: dict[str, str] = {v: k for k, v in SOLANA_TOKEN_ADDRESSES.items()}
# Fix WSOL/SOL collision — prefer SOL
SOLANA_MINT_TO_SYMBOL["So11111111111111111111111111111111111111112"] = "SOL"

# Solana DeFi protocol metadata — SSOT for all API endpoints.
# Services import these URLs; never hardcode them.
SOLANA_DEFI_PROTOCOLS: dict[str, dict[str, str]] = {
    "drift": {
        "name": "Drift Protocol",
        "type": "perps_dex",
        "program_id": "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",
        "api_url": "https://data.api.drift.trade",
        "dlob_url": "https://dlob.drift.trade",
        "ws_url": "wss://dlob.drift.trade/ws",
        "s3_historical_url": (
            "https://drift-historical-data-v2.s3.eu-west-1.amazonaws.com"
            "/program/dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
        ),
        "data_source": "drift_api",
    },
    "raydium": {
        "name": "Raydium",
        "type": "dex",
        "program_id": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
        "api_url": "https://api-v3.raydium.io",
        "data_source": "raydium_api",
    },
    "orca": {
        "name": "Orca (Whirlpool)",
        "type": "dex",
        "program_id": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
        "api_url": "https://api.mainnet.orca.so",
        "data_source": "orca_api",
    },
    "marinade": {
        "name": "Marinade Finance",
        "type": "liquid_staking",
        "program_id": "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD",
        "api_url": "https://api.marinade.finance",
        "data_source": "marinade_api",
    },
    "kamino": {
        "name": "Kamino Finance",
        "type": "lending",
        "program_id": "KLend2g3cP87ber41GXWsSZQhDqc7juFGkhGJk2HRFUj",
        "api_url": "https://api.kamino.finance",
        "data_source": "kamino_api",
    },
    "jupiter": {
        "name": "Jupiter",
        "type": "aggregator",
        "api_url": "https://lite-api.jup.ag/swap/v1",
        "data_source": "jupiter_api",
    },
    "jito": {
        "name": "Jito",
        "type": "liquid_staking",
        "api_url": "https://kobe.mainnet.jito.network",
        "program_id": "Jito4APyf642JPZPx3hGc6WWJ8zPKtRbRs4P3eg9gB",
        "data_source": "helius",
    },
}


def get_solana_protocol_url(protocol: str, url_type: str = "api_url") -> str | None:
    """Get a Solana DeFi protocol URL by protocol name and URL type.

    Args:
        protocol: Protocol key (drift, raydium, orca, kamino, marinade, jupiter).
        url_type: URL type key (api_url, dlob_url, ws_url, s3_historical_url).
    """
    proto = SOLANA_DEFI_PROTOCOLS.get(protocol)
    if proto is None:
        return None
    return proto.get(url_type)


def resolve_solana_mint(mint: str) -> str:
    """Resolve a Solana token mint address to its symbol.

    Returns empty string for unknown mints — callers should reject instruments
    where either token can't be resolved to a known symbol.
    """
    return SOLANA_MINT_TO_SYMBOL.get(mint, "")


# Bitcoin metadata — native BTC DeFi is minimal; we focus on wrapped BTC on EVM.
# Stacks (STX) has some Bitcoin DeFi but is too small for our system.
BITCOIN_RPC_TEMPLATES: dict[str, str] = {
    "blockstream": "https://blockstream.info/api",
    "mempool": "https://mempool.space/api",
}

# Wrapped BTC tokens on EVM chains (already in WBTC_ADDRESSES / CBBTC_ADDRESSES above)
# tBTC is another wrapped BTC option on Ethereum
TBTC_ADDRESSES: dict[int, str] = {
    1: "0x18084fbA666a33d37592fA2633fD49a74DD93a88",
    42161: "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40",
    137: "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b",
    10: "0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40",
    8453: "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b",
}


def get_solana_rpc_url(provider: str = "alchemy", api_key: str = "") -> str | None:
    """Get a Solana RPC URL for the given provider."""
    template = SOLANA_RPC_TEMPLATES.get(provider)
    if template is None:
        return None
    return template.format(api_key=api_key)


def get_solana_token_address(symbol: str) -> str | None:
    """Get a Solana SPL token address by symbol."""
    return SOLANA_TOKEN_ADDRESSES.get(symbol.upper())


# ---------------------------------------------------------------------------
# DeFi protocols (5)
# ---------------------------------------------------------------------------

_UNISWAP = SourceCapability(
    source="uniswap",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["pool_state", "tick_data", "swap_events", "liquidity_positions", "prices"],
        "reference": ["factory", "pools", "tokens", "fee_tiers"],
    },
    base_urls={
        "mainnet": "https://api.thegraph.com/subgraphs/name/uniswap",
        "testnet": "https://api.thegraph.com/subgraphs/name/uniswap",
    },
    operation_details={
        "pool_state": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    data_fidelity="synthetic",
                    notes="Sepolia subgraph — different pool addresses, low liquidity",
                ),
            }
        ),
        "swap_events": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_AAVE = SourceCapability(
    source="aave",
    domains=["market", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["reserve_data", "user_reserve_data", "rates", "utilization"],
        "position": ["user_account_data", "health_factor", "collateral", "debt"],
        "reference": ["reserves_list", "protocol_data", "incentives"],
    },
    base_urls={"mainnet": "https://aave-api-v2.aave.com", "testnet": "https://aave-api-v2.aave.com"},
    operation_details={
        "reserve_data": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="on_chain",
                    required_credential="none",
                    notes="Read-only eth_call via Alchemy RPC",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain",
                    required_credential="none",
                    data_fidelity="synthetic",
                    notes="Sepolia — different contract addresses via testnet_contracts.yaml",
                ),
            }
        ),
        "user_account_data": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="on_chain", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "health_factor": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="on_chain", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "supply": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="on_chain", required_credential="wallet_private_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="wallet_private_key", data_fidelity="synthetic"
                ),
            }
        ),
        "borrow": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="on_chain", required_credential="wallet_private_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="wallet_private_key", data_fidelity="synthetic"
                ),
            }
        ),
        "repay": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="on_chain", required_credential="wallet_private_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="wallet_private_key", data_fidelity="synthetic"
                ),
            }
        ),
        "flash_loan": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="on_chain",
                    required_credential="wallet_private_key",
                    notes="Atomic — all-or-nothing within single tx",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="wallet_private_key", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_CURVE = SourceCapability(
    source="curve",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["pool_state", "exchange_rates", "volumes", "virtual_price", "liquidity"],
        "reference": ["registry", "pools", "gauges", "factory_pools"],
    },
    base_urls={"mainnet": "https://api.curve.fi"},
    operation_details={
        "pool_state": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "exchange": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="on_chain", required_credential="wallet_private_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="wallet_private_key", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_DYDX = SourceCapability(
    source="dydx",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "testnet_key", "prod": "prod_key"},
    operations={
        "market": ["orderbook", "trades", "candles", "ws_orderbook", "ws_trades"],
        "execution": ["place_order", "cancel_order", "list_orders", "get_order"],
        "position": ["account", "positions", "fills", "funding_payments"],
        "reference": ["markets", "stats"],
    },
    base_urls={"mainnet": "https://indexer.dydx.trade", "testnet": "https://indexer.v4testnet.dydx.exchange"},
    margin_model={"mainnet": "cross", "testnet": "cross"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="eip712", required_credential="wallet_private_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="eip712", required_credential="wallet_private_key", data_fidelity="synthetic"
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="eip712", required_credential="wallet_private_key"),
                "testnet": OperationEnvDetail(signing_scheme="eip712", required_credential="wallet_private_key"),
            }
        ),
        "orderbook": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_INSTADAPP = SourceCapability(
    source="instadapp",
    domains=["market", "position", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["reserve_data", "rates"],
        "position": ["smart_account", "positions", "balances"],
        "reference": ["protocols", "tokens"],
    },
    base_urls={"mainnet": "https://api.instadapp.io"},
    operation_details={
        "smart_account": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="on_chain", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="on_chain", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

# ---------------------------------------------------------------------------
# DeFi data / on-chain analytics (4)
# ---------------------------------------------------------------------------

_MEV = SourceCapability(
    source="mev",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["bundle_results", "mev_metrics", "flashbots_blocks"],
        "reference": ["searchers", "builders"],
    },
    base_urls={"mainnet": "https://relay.flashbots.net"},
    operation_details={
        "bundle_results": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="eip712", required_credential="wallet_private_key"),
            }
        ),
    },
)

_VERSIFI = SourceCapability(
    source="versifi",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "testnet_key", "prod": "prod_key"},
    operations={
        "market": ["trades", "ws_trades"],
        "execution": ["orders", "fills"],
        "reference": ["instruments"],
    },
    base_urls={"mainnet": "https://api.versifi.com", "testnet": "https://testnet.versifi.com"},
    operation_details={
        "orders": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
    },
)


# ---------------------------------------------------------------------------
# Ordered list -- DeFi
# ---------------------------------------------------------------------------

DEFI_CAPABILITIES: list[SourceCapability] = [
    # DeFi protocols
    _UNISWAP,
    _AAVE,
    _CURVE,
    _DYDX,
    _INSTADAPP,
    # DeFi data / on-chain analytics
    _MEV,
    _VERSIFI,
]
