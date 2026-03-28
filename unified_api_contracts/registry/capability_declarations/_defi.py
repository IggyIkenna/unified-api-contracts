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
        "SCROLL": "74JwenoHZb2aAYVGCCSdPWzi9mm745dyHyQQVoZ7Sbub",
        "LINEA": "Gz2kjnmRV1fQj3R8cssoZa5y9VTanhrDo4Mh7nWW1wHa",
        "BSC": "7Jk85XgkV1MQ7u56hD8rr65rfASbayJXopugWkUoBMnZ",
        "ZKSYNC": "ENYSc8G3WvrbhWH8UZHrqPWYRcuyCaNmaTmoVp7uzabM",
    },
    # compound_v3: subgraph IDs need verification — adapter not yet implemented
    "morpho": {
        "ETHEREUM": "8Lz789DP5VKLXumTMTgygjU2xtuzx8AhbaacgN5PYCAs",
        # Multi-chain: Morpho uses its own API (not The Graph) for Base/ARB/POLY/OP
        # The adapter already handles this via morpho.org API
    },
    "euler_v2": {
        # Euler uses Goldsky (not The Graph). Adapter queries Goldsky URLs directly.
        "ETHEREUM": "euler-v2-mainnet",
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
        "BASE": "FUbEPQw1oMghy39fwWBFY5fE6MXPXZQtjncQy2cXdrNS",
        "OPTIMISM": "Cghf4LfVqPiFw6fp6Y5X5Ubc8UpmUhSfJL82zwiBFLaj",
        "POLYGON": "3hCPRGf4z88VC5rsBKU5AA9FBBq5nF3jbKJG7VZCbhjm",
    },
    "uniswap_v4": {
        "ETHEREUM": "DiYPVdygkfjDWhbxGSqAQxwBKmfKnkWQojqeM2rkLb3G",
    },
    "balancer": {  # Non-ETH IDs need verification
        "ETHEREUM": "C4ayEZP2yTXRAB8vSaTrgN4m9anTe9Mdm2ViyiAuV9TV",
    },
    "curve": {  # Curve uses its own API, not The Graph subgraphs
        "ETHEREUM": "3fy93eAT56UJsRCEht8iFhfi6wjHWXtZ9dnnbQmvFopF",
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
# Chain-specific Alchemy RPC URL templates (SSOT)
#
# Used by execution-service to resolve a fully-qualified RPC URL before
# injecting it into UDEI connector config.  Interfaces never touch these
# directly — they receive a pre-resolved ``rpc_url`` from the service layer.
# ---------------------------------------------------------------------------
CHAIN_RPC_TEMPLATES: dict[int, str] = {
    # ── Tier 1: Core ETH-native L2s ───────────────────────────────
    1: "https://eth-mainnet.g.alchemy.com/v2/{api_key}",
    10: "https://opt-mainnet.g.alchemy.com/v2/{api_key}",
    8453: "https://base-mainnet.g.alchemy.com/v2/{api_key}",
    42161: "https://arb-mainnet.g.alchemy.com/v2/{api_key}",
    # ── Tier 2: Major non-ETH chains ──────────────────────────────
    56: "https://bnb-mainnet.g.alchemy.com/v2/{api_key}",
    137: "https://polygon-mainnet.g.alchemy.com/v2/{api_key}",
    43114: "https://avax-mainnet.g.alchemy.com/v2/{api_key}",
    # ── Tier 3: ETH-native L2s + zkEVMs ───────────────────────────
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
    # ── Testnets ──────────────────────────────────────────────────
    11155111: "https://eth-sepolia.g.alchemy.com/v2/{api_key}",
}

# ---------------------------------------------------------------------------
# Chain native gas tokens (SSOT)
# Gas is paid in the native token — ETH on L2s, BNB/MATIC/AVAX on alt-L1s
# ---------------------------------------------------------------------------
CHAIN_NATIVE_GAS_TOKEN: dict[int, str] = {
    1: "ETH", 10: "ETH", 56: "BNB", 130: "ETH", 137: "MATIC",
    324: "ETH", 480: "ETH", 1101: "ETH", 2741: "ETH",
    8453: "ETH", 34443: "ETH", 42161: "ETH", 43114: "AVAX",
    57073: "ETH", 59144: "ETH", 81457: "ETH", 534352: "ETH",
    7777777: "ETH", 11155111: "ETH",
}

# ---------------------------------------------------------------------------
# WETH addresses per chain (SSOT for wrap/unwrap)
# DeFi protocols require WETH (ERC20); gas is paid in native ETH.
# On non-ETH chains, this is the wrapped native token (WBNB, WMATIC, WAVAX).
# ---------------------------------------------------------------------------
WETH_ADDRESSES: dict[int, str] = {
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    10: "0x4200000000000000000000000000000000000006",
    56: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",       # WBNB
    130: "0x4200000000000000000000000000000000000006",
    137: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",      # WMATIC
    324: "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
    480: "0x4200000000000000000000000000000000000006",
    1101: "0x4F9A0e7FD2Bf6067db6994CF12E4495Df938E6e9",
    2741: "0x4200000000000000000000000000000000000006",
    8453: "0x4200000000000000000000000000000000000006",
    34443: "0x4200000000000000000000000000000000000006",
    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    43114: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",    # WAVAX
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
