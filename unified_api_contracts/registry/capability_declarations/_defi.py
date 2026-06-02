"""DeFi protocol and on-chain analytics capability declarations."""

from __future__ import annotations

from enum import StrEnum

from ._defi_chain_data import (
    BITCOIN_RPC_TEMPLATES,
    CBBTC_ADDRESSES,
    CHAIN_CONFIGS,
    CHAIN_NATIVE_GAS_TOKEN,
    CHAIN_RPC_TEMPLATES,
    HYPERLIQUID_RPC_TEMPLATES,
    PROTECTED_RPC_URLS,
    SOLANA_DEFI_PROTOCOLS,
    SOLANA_MINT_TO_SYMBOL,
    SOLANA_RPC_TEMPLATES,
    SOLANA_TOKEN_ADDRESSES,
    STARKNET_RPC_TEMPLATES,
    TBTC_ADDRESSES,
    WBTC_ADDRESSES,
    WETH_ADDRESSES,
    ChainConfig,
    NonEvmChain,
    get_chain_config,
    get_native_gas_token,
    get_solana_protocol_url,
    get_solana_rpc_url,
    get_solana_token_address,
    get_weth_address,
    is_block_finalized,
    resolve_solana_mint,
    time_budget_to_block_offset,
)
from ._defi_source_capabilities import DEFI_CAPABILITIES


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
        # OPTIMISM: AAVE_V3-OPTIMISM canonical data source is the RPC fallback
        # (policy decision 2026-05-30). Subgraph state on this chain:
        #   • Aave github-README deployment `DSfLz8oQBUeU5atALgUFQKMTSYV9mZAVYp4noLSXAfvb`
        #     is at head with `hasIndexingErrors:false`, BUT both
        #     `reserveParamsHistoryItems` AND `reserves` return [] — Aave
        #     republished it to v0.0.5 (an "abandoned" empty entity store)
        #     between 2026-05-08 and 2026-05-29. Silent abandonment by the
        #     Aave team, NOT an indexing failure.
        #   • Messari-style deployment `3RWFxWNstn4nP3dXiDfKi9GgBoHx7xzc7APkXs1MLEgi`
        #     is also at head (verified 2026-05-30: `_meta.block.timestamp`
        #     ~1780110035 / ~03:00 UTC, no indexing errors). Coverage is
        #     sparse post-2024-12: rows present at 2024-12-01 + 2026-04-25
        #     but [] for 2025-06-01 / 2026-01-01 / 2026-05-01 windows. Also
        #     the nested `market { inputToken { symbol } }` join raises
        #     `Null value resolved for non-null field market` — handlers
        #     MUST query top-level snapshot fields only.
        # All sibling Aave V3 chains (ETH/ARB/POLY/BASE) work fine; only
        # OPTIMISM is in this abandoned state. RPC fallback (14-row daily
        # resolution) is operationally sufficient for the carry archetype
        # until a fresh rich deployment surfaces. Messari ID stays as the
        # cascade's 2nd variant for partial coverage; swap to a new rich
        # native ID + re-backfill if Aave revives the deployment.
        "OPTIMISM": "3RWFxWNstn4nP3dXiDfKi9GgBoHx7xzc7APkXs1MLEgi",
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
#   - venue_prefix: canonical venue prefix (e.g. "AAVE_V3")
#   - protocol_class: classification for filtering/routing
#   - required_tokens: protocol-native tokens that MUST be in the major assets
#     filter (governance, reward, staking tokens that our strategies need)
#   - chain_native_tokens: per-chain tokens auto-included when protocol is
#     deployed on that chain (e.g. SOL for Solana, BNB for BSC)
#
# Consumers:
#   - instruments-service orchestrator: builds venue list from this
#   - MTDS handlers: validate which data types to collect per protocol
#   - market_data_categories.py: derives VENUES_BY_ASSET_GROUP from this
#   - deployment-ui data-status: shows expected data coverage matrix
# ---------------------------------------------------------------------------

from ..._instrument_enums import InstrumentType as _IT  # noqa: N814


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
_LENDING = [_IT.LENDING.value]
_POOL = [_IT.POOL.value]
_YIELD = [_IT.YIELD_BEARING.value]
_STAKING = [_IT.STAKING.value]
_PERPS = [_IT.PERPETUAL.value, _IT.SPOT_PAIR.value]
_RESTAKING = [_IT.SPOT_ASSET.value]

# Data type groups
#
# These describe ALL data types a protocol CAN produce — both what MTDS
# collects today and what's available on-chain/via APIs.  "Aspirational"
# entries are marked with inline comments; MTDS handlers for those may
# not exist yet but the data IS available at the source.
#
# Key distinctions:
#   swaps         — individual swap events (amount0, amount1, amountUSD, sender, ts)
#   dex_pools     — daily pool aggregates (volume24h, fees24h, tvl) from poolDayDatas
#   oracle_prices — external price feeds (Chainlink, protocol exchange rates)
#                   needed to compute yield on non-rebasing tokens (sUSDe, wstETH)
#   gas_fees      — chain-level gas price data (baseFee, priorityFee, gasUsed)
#
# Removed phantom data types (not separate data types — they are columns):
#   tvl           — totalValueLockedUSD is a column in dex_pools, not a separate data type
#   utilization   — utilization_rate is a column in lending rate_indices, not a separate data type
#   evm_defi      — redundant with lending_indices (live snapshot of the same data)
#
_LENDING_DATA = ["lending_indices", "liquidations", "risk_params"]
_DEX_DATA = ["dex_pools", "dex_swaps"]
_YIELD_DATA = ["lst_rates", "oracle_prices"]
_STAKING_DATA = ["lst_rates", "oracle_prices"]
_PERPS_DATA = ["perp_funding"]

PROTOCOL_CAPABILITIES: dict[str, _ProtocolCapability] = {
    # ── EVM Lending ──────────────────────────────────────────────
    "aave_v3": _ProtocolCapability(
        venue_prefix="AAVE_V3",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "gas_fees"],
        mtds_operations=["collect-lending-indices", "collect-liquidations", "collect-gas-fees"],
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
        venue_prefix="COMPOUND_V3",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "gas_fees"],
        mtds_operations=["collect-lending-indices", "collect-liquidations", "collect-gas-fees"],
        required_tokens=frozenset({"COMP"}),
    ),
    "morpho": _ProtocolCapability(
        venue_prefix="MORPHO",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "gas_fees"],
        mtds_operations=["collect-liquidations", "collect-gas-fees"],
    ),
    "fluid": _ProtocolCapability(
        venue_prefix="FLUID",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=[*_LENDING_DATA, "gas_fees"],
        mtds_operations=["collect-liquidations", "collect-gas-fees"],
    ),
    # ── EVM DEX — Native schema ─────────────────────────────────
    "uniswap_v2": _ProtocolCapability(
        venue_prefix="UNISWAP_V2",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"UNI"}),
    ),
    "uniswap_v3": _ProtocolCapability(
        venue_prefix="UNISWAP_V3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
        required_tokens=frozenset({"UNI"}),
    ),
    "uniswap_v4": _ProtocolCapability(
        venue_prefix="UNISWAP_V4",
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
        venue_prefix="PANCAKESWAP_V3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "sushiswap_v3": _ProtocolCapability(
        venue_prefix="SUSHISWAP_V3",
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
        venue_prefix="AERODROME_V3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "camelot_v3": _ProtocolCapability(
        venue_prefix="CAMELOT_V3",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "velodrome_v2": _ProtocolCapability(
        venue_prefix="VELODROME_V2",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=[*_DEX_DATA, "gas_fees"],
        mtds_operations=["collect-dex-pools", "collect-dex-swaps", "collect-gas-fees"],
    ),
    "trader_joe_v2": _ProtocolCapability(
        venue_prefix="TRADER_JOE_V2",
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
    # OPTIONS: not supported — venue does not offer listed options contracts
    "hyperliquid": _ProtocolCapability(
        venue_prefix="HYPERLIQUID",
        protocol_class=ProtocolClass.PERPS,
        instrument_types=_PERPS,
        data_types=["perp_funding", "oracle_prices"],
        mtds_operations=["collect-perp-funding"],
    ),
    # OPTIONS: not supported — venue does not offer listed options contracts
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
        data_types=["perp_funding", "oracle_prices"],
        mtds_operations=["collect-perp-funding"],
        required_tokens=frozenset({"DRIFT"}),
    ),
    "kamino": _ProtocolCapability(
        venue_prefix="KAMINO",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=["dex_pools", "lending_indices"],
        mtds_operations=["collect-dex-pools", "collect-lending-indices"],
        required_tokens=frozenset({"KMNO"}),
    ),
    "raydium": _ProtocolCapability(
        venue_prefix="RAYDIUM",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=["dex_pools", "dex_swaps"],
        mtds_operations=["collect-dex-pools"],
        required_tokens=frozenset({"RAY"}),
    ),
    "orca": _ProtocolCapability(
        venue_prefix="ORCA",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=["dex_pools", "dex_swaps"],
        mtds_operations=["collect-dex-pools"],
        required_tokens=frozenset({"ORCA"}),
    ),
    "phoenix": _ProtocolCapability(
        venue_prefix="PHOENIX",
        protocol_class=ProtocolClass.DEX,
        instrument_types=_POOL,
        data_types=["dex_pools"],
        mtds_operations=["collect-dex-pools"],
    ),
    "marginfi": _ProtocolCapability(
        venue_prefix="MARGINFI",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=["lending_indices"],
        mtds_operations=["collect-lending-indices"],
    ),
    "solend": _ProtocolCapability(
        venue_prefix="SOLEND",
        protocol_class=ProtocolClass.LENDING,
        instrument_types=_LENDING,
        data_types=["lending_indices"],
        mtds_operations=["collect-lending-indices"],
    ),
    "marinade": _ProtocolCapability(
        venue_prefix="MARINADE",
        protocol_class=ProtocolClass.STAKING,
        instrument_types=_STAKING,
        data_types=["lst_rates", "oracle_prices"],
        mtds_operations=["collect-lst-rates"],
        required_tokens=frozenset({"MNDE", "MSOL"}),
    ),
    "jito": _ProtocolCapability(
        venue_prefix="JITO",
        protocol_class=ProtocolClass.STAKING,
        instrument_types=_STAKING,
        data_types=["lst_rates", "oracle_prices"],
        mtds_operations=["collect-lst-rates"],
        required_tokens=frozenset({"JTO", "JITOSOL", "JSOL"}),
    ),
    # ── Plan E: Solana restaking rewards coverage (2026-05-13) ────────────
    # Second-layer staking: stake LSTs into restaking vaults to earn AVS operator rewards
    # on top of base staking yield. Critical for carry_staked_basis archetype carry computation.
    "solayer": _ProtocolCapability(
        venue_prefix="SOLAYER",
        protocol_class=ProtocolClass.RESTAKING,
        instrument_types=_YIELD,
        data_types=["restaking_rewards", "lst_rates"],
        mtds_operations=["collect-staking-yields"],
        required_tokens=frozenset({"SSOL"}),
    ),
    # PICASSO + CAMBRIAN removed 2026-06-02 (operator decision): 2026-06-02 data-source
    # smoke tests found no usable public DeFi data source. Picasso = IBC bridge/restaking
    # program alive but ~3 tx/month + no public yield/rate API; Cambrian = a developer SDK
    # for building NCNs on Jito Restaking, not a DeFi venue (no TVL/pools/rates/program to
    # query). Excluded from the venue registry. SSOT:
    # plans/active/issues/issue_docs_remediation_sweep_2026_06_02.md (venue smoke-test results).
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


# LST / LRT genesis dates + venue->token mapping live in ``_defi_lst`` (extracted
# to keep this file under the 900-line cap). Re-exported here so callers can
# still ``from unified_api_contracts.registry import LST_TOKEN_GENESIS`` etc.
# Empty / deprecated DeFi venue metadata lives in ``_defi_coverage`` (co-located
# re-export). Used by data-status to suppress missing-coverage flags for venues
# whose subgraph is retired or whose parquets haven't been collected yet.
from ._defi_coverage import (  # placed after conditional setup to avoid circular import at load time
    DEFI_INSTRUMENTS_NOT_YET_COLLECTED,
    DEPRECATED_DEFI_GHOST_VENUE_NAMES,
    EMPTY_OR_DEPRECATED_DEFI_VENUES,
    venue_has_no_expected_defi_coverage,
)
from ._defi_lst import (  # placed after conditional setup to avoid circular import at load time
    LST_TOKEN_GENESIS,
    LST_VENUE_TO_TOKENS,
    get_lst_token_genesis,
    get_lst_venue_genesis,
)


def get_protocol_capability(protocol: str) -> _ProtocolCapability | None:
    """Get capability declaration for a protocol."""
    return PROTOCOL_CAPABILITIES.get(protocol)


def get_venue_prefix(protocol: str) -> str | None:
    """Get the canonical venue prefix for a protocol (e.g. 'aave_v3' -> 'AAVE_V3')."""
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
        venue: Canonical venue name (e.g. "AAVE_V3-ETHEREUM", "DRIFT-SOLANA").

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
    "phoenix": ["SOLANA"],
    "marginfi": ["SOLANA"],
    "solend": ["SOLANA"],
    "marinade": ["SOLANA"],
    "jito": ["SOLANA"],
    # Plan E: Solana restaking rewards coverage (2026-05-13)
    "solayer": ["SOLANA"],
    # picasso + cambrian removed 2026-06-02 (operator decision; no usable DeFi
    # data source — see PROTOCOL_CAPABILITIES header note above).
}


# Reverse lookup: venue_prefix → protocol slug (for parse_defi_venue)
_PREFIX_TO_PROTOCOL: dict[str, str] = {cap.venue_prefix: slug for slug, cap in PROTOCOL_CAPABILITIES.items()}

# Chain tokens that exist in the DeFi data (GCS venue= partitions, manifest rows)
# but have NO subgraph/static-protocol mapping, so they would not otherwise be in
# KNOWN_CHAINS. These are needed by the combined-venue parsers/canonicalizers
# (parse_defi_venue, canonicalize_defi_venue_combined) to split "<PROTOCOL>-<CHAIN>"
# correctly. KNOWN_CHAINS is a chain-TOKEN recognition set; membership here does NOT
# imply a subgraph deployment nor expand any expected-coverage matrix (that lives in
# EXPECTED_COVERAGE_BY_ASSET_GROUP, keyed by explicit venue tokens).
#   ZKSYNC — present in IS partitions (PANCAKESWAP_V3-ZKSYNC, AAVE_V3-ZKSYNC) and the
#   LIGHTER-ZKSYNC perp venue; canonical ChainKind.ZKSYNC = "zksync" (chain id 324).
_EXTRA_VENUE_PARTITION_CHAINS: frozenset[str] = frozenset({"ZKSYNC"})

# All known chain names (from SUBGRAPH_IDS + _STATIC_VENUE_CHAINS + extra partition chains)
KNOWN_CHAINS: frozenset[str] = frozenset(
    {chain for chains in SUBGRAPH_IDS.values() for chain in chains}
    | {chain for chains in _STATIC_VENUE_CHAINS.values() for chain in chains}
    | _EXTRA_VENUE_PARTITION_CHAINS
)


def parse_defi_venue(venue_str: str) -> tuple[str, str]:
    """Split a DeFi venue string into (protocol_slug, chain).

    Parses "AAVE_V3-ETHEREUM" → ("aave_v3", "ETHEREUM"),
    "UNISWAP_V3-BASE" → ("uniswap_v3", "BASE"), etc.

    Uses the PROTOCOL_CAPABILITIES venue_prefix as the authority
    for how to split the string. Falls back to splitting on the
    last hyphen if no prefix match.

    Returns:
        (protocol_slug, chain_name) — protocol_slug matches PROTOCOL_CAPABILITIES keys.
    """
    # Try known prefixes (longest match first to handle UNISWAP_V3 vs UNISWAP_V2)
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


# Strip-underscore lookup: "AAVEV3" → "AAVE_V3" (the authoritative venue_prefix).
# Built from PROTOCOL_CAPABILITIES venue_prefix set (33 prefixes, verified zero
# strip-underscore collisions 2026-05-26). VELODROME_V2 / TRADER_JOE_V2 carry the
# underscore-canonical prefix (operator 2026-06-01 — DF-17 glued-canonical reversed);
# the stripped legacy form (VELODROMEV2 / TRADERJOEV2) maps back to the canonical.
_STRIPPED_PREFIX_TO_CANONICAL: dict[str, str] = {
    prefix.replace("_", "").upper(): prefix for prefix in {cap.venue_prefix for cap in PROTOCOL_CAPABILITIES.values()}
}


def canonicalize_defi_venue_combined(raw: str) -> str:
    """Map a combined DeFi venue (glued OR canonical) to the canonical combined form.

    Examples:
        "AAVEV3-ARBITRUM"     -> "AAVE_V3-ARBITRUM"
        "UNISWAPV3-ETHEREUM"  -> "UNISWAP_V3-ETHEREUM"
        "COMPOUNDV3-BASE"     -> "COMPOUND_V3-BASE"
        "AAVE_V3-ARBITRUM"    -> "AAVE_V3-ARBITRUM"   (already canonical → passthrough)
        "VELODROMEV2-OPTIMISM"-> "VELODROME_V2-OPTIMISM" (legacy glued → underscore-canonical)
        "BINANCE"             -> "BINANCE"            (no known chain → passthrough)

    Algorithm:
        1. Split into (protocol, chain): the chain is the suffix after the last "-"
           that is a known chain (``KNOWN_CHAINS``). If no known-chain suffix, return
           ``raw`` unchanged (non-DeFi / unrecognised → surface honestly).
        2. Canonicalise the protocol via strip-underscore match against the
           authoritative ``venue_prefix`` set. If no match, return ``raw`` unchanged
           (unknown protocol → surface honestly, never guess).

    The authoritative venue_prefix set is ``PROTOCOL_CAPABILITIES`` — the same source
    ``parse_defi_venue`` splits on. This function additionally inserts the missing
    underscore that ``parse_defi_venue`` does NOT (it preserves the glued protocol).

    Returns:
        Canonical ``f"{venue_prefix}-{chain}"`` or ``raw`` unchanged when no
        known-chain suffix / no protocol match.
    """
    if "-" not in raw:
        return raw
    idx = raw.rfind("-")
    chain = raw[idx + 1 :]
    if chain not in KNOWN_CHAINS:
        return raw
    protocol = raw[:idx]
    canonical_prefix = _STRIPPED_PREFIX_TO_CANONICAL.get(protocol.upper().replace("_", ""))
    if canonical_prefix is None:
        return raw
    return f"{canonical_prefix}-{chain}"


def get_all_defi_chains() -> list[str]:
    """Return all chains with DeFi protocol deployments, sorted."""
    return sorted(KNOWN_CHAINS)


# Chain data, Solana data, Bitcoin data, and SourceCapability declarations
# are in _defi_chain_data.py and _defi_source_capabilities.py respectively.
# All public symbols are re-exported above so the external API is unchanged.

# Re-export everything needed by __init__.py
__all__ = [
    "BITCOIN_RPC_TEMPLATES",
    "CBBTC_ADDRESSES",
    "CHAIN_CONFIGS",
    "CHAIN_NATIVE_GAS_TOKEN",
    "CHAIN_REQUIRED_TOKENS",
    "CHAIN_RPC_TEMPLATES",
    "DEFI_CAPABILITIES",
    "DEFI_INSTRUMENTS_NOT_YET_COLLECTED",
    "DEPRECATED_DEFI_GHOST_VENUE_NAMES",
    "EMPTY_OR_DEPRECATED_DEFI_VENUES",
    "HYPERLIQUID_RPC_TEMPLATES",
    "HYPERLIQUID_RPC_TEMPLATES",
    "KNOWN_CHAINS",
    "LST_TOKEN_GENESIS",
    "LST_VENUE_TO_TOKENS",
    "PROTECTED_RPC_URLS",
    "PROTOCOL_CAPABILITIES",
    "SOLANA_DEFI_PROTOCOLS",
    "SOLANA_MINT_TO_SYMBOL",
    "SOLANA_RPC_TEMPLATES",
    "SOLANA_TOKEN_ADDRESSES",
    "STARKNET_RPC_TEMPLATES",
    "STARKNET_RPC_TEMPLATES",
    "SUBGRAPH_IDS",
    "TBTC_ADDRESSES",
    "TOKEN_EQUIVALENCE_GROUPS",
    "WBTC_ADDRESSES",
    "WETH_ADDRESSES",
    "ChainConfig",
    "DeFiDataSource",
    "NonEvmChain",
    "ProtocolClass",
    "build_complete_major_assets",
    "build_defi_venues",
    "canonicalize_defi_venue_combined",
    "get_all_defi_chains",
    "get_chain_config",
    "get_data_types_for_protocol",
    "get_lst_token_genesis",
    "get_lst_venue_genesis",
    "get_mtds_operations_for_protocol",
    "get_native_gas_token",
    "get_protocol_capability",
    "get_required_tokens_for_protocol",
    "get_required_tokens_for_venue",
    "get_solana_protocol_url",
    "get_solana_rpc_url",
    "get_solana_token_address",
    "get_subgraph_id",
    "get_supported_chains_for_protocol",
    "get_venue_prefix",
    "get_weth_address",
    "is_block_finalized",
    "is_token_equivalent",
    "parse_defi_venue",
    "resolve_solana_mint",
    "time_budget_to_block_offset",
    "token_matches_major_assets",
    "venue_has_no_expected_defi_coverage",
]
