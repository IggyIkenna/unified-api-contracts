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
    "aave_v3": {
        "ETHEREUM": "Cd2gEDVeqnjBn1hSeqFMitw8Q1iiyV9FYUZkLNRcL87g",
    },
    "uniswap_v2": {
        "ETHEREUM": "A3Np3RQbaBA6oKJgiwDJeo5T3zrYfGHPWFYayMwtNDum",
    },
    "uniswap_v3": {
        "ETHEREUM": "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
        "ARBITRUM": "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
        "BASE": "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
    },
    "uniswap_v4": {
        "ETHEREUM": "DiYPVdygkfjDWhbxGSqAQxwBKmfKnkWQojqeM2rkLb3G",
    },
    "balancer": {
        "ETHEREUM": "C4ayEZP2yTXRAB8vSaTrgN4m9anTe9Mdm2ViyiAuV9TV",
    },
    "morpho": {
        "ETHEREUM": "8Lz789DP5VKLXumTMTgygjU2xtuzx8AhbaacgN5PYCAs",
    },
    "curve": {
        "ETHEREUM": "3fy93eAT56UJsRCEht8iFhfi6wjHWXtZ9dnnbQmvFopF",
    },
}


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
    1: "https://eth-mainnet.g.alchemy.com/v2/{api_key}",
    11155111: "https://eth-sepolia.g.alchemy.com/v2/{api_key}",
    42161: "https://arb-mainnet.g.alchemy.com/v2/{api_key}",
    10: "https://opt-mainnet.g.alchemy.com/v2/{api_key}",
    137: "https://polygon-mainnet.g.alchemy.com/v2/{api_key}",
    8453: "https://base-mainnet.g.alchemy.com/v2/{api_key}",
}

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
