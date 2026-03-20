"""Alt data, macro/commodity, and infrastructure capability declarations."""

from __future__ import annotations

from ..capability import OperationDetail, OperationEnvDetail, SourceCapability

# ---------------------------------------------------------------------------
# Alt data / on-chain analytics (9)
# ---------------------------------------------------------------------------

_ALCHEMY = SourceCapability(
    source="alchemy",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "testnet_key", "prod": "prod_key"},
    operations={
        "market": ["token_balances", "token_transfers", "transaction_receipts", "ws_pending_txns"],
        "reference": ["token_metadata", "nft_metadata", "contract_metadata", "block_data"],
    },
    base_urls={"mainnet": "https://eth-mainnet.g.alchemy.com", "testnet": "https://eth-sepolia.g.alchemy.com"},
    operation_details={
        "token_balances": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="api_key_header",
                    required_credential="api_key",
                    data_fidelity="synthetic",
                    notes="Sepolia testnet — different token addresses, test balances",
                ),
            }
        ),
        "token_transfers": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="api_key_header", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
        "transaction_receipts": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="api_key_header", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_THEGRAPH = SourceCapability(
    source="thegraph",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["subgraph_query", "indexed_events", "entity_data"],
        "reference": ["subgraphs", "deployments", "schema_introspection"],
    },
    base_urls={"mainnet": "https://gateway.thegraph.com"},
    operation_details={
        "subgraph_query": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_COINGECKO = SourceCapability(
    source="coingecko",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key", "none"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["price", "market_chart", "ohlc", "global_market_data"],
        "reference": ["coins_list", "coins_markets", "categories", "exchanges", "asset_platforms"],
    },
    base_urls={"mainnet": "https://api.coingecko.com"},
    operation_details={
        "price": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_COINGLASS = SourceCapability(
    source="coinglass",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["liquidations", "liquidation_clusters", "open_interest", "funding_rates"],
        "reference": ["supported_exchanges", "supported_coins"],
    },
    base_urls={"mainnet": "https://open-api-v3.coinglass.com"},
    operation_details={
        "liquidations": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_GLASSNODE = SourceCapability(
    source="glassnode",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["on_chain_metrics", "active_addresses", "transaction_volume", "mvrv"],
        "reference": ["metrics_list", "assets"],
    },
    base_urls={"mainnet": "https://api.glassnode.com"},
    operation_details={
        "on_chain_metrics": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_CRYPTOQUANT = SourceCapability(
    source="cryptoquant",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["on_chain_metrics", "exchange_flows", "miner_flows", "network_data"],
        "reference": ["metric_list", "exchanges"],
    },
    base_urls={"mainnet": "https://api.cryptoquant.com"},
    operation_details={
        "on_chain_metrics": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_HYBLOCK = SourceCapability(
    source="hyblock",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["liquidation_clusters", "orderbook_heatmap", "cumulative_delta"],
        "reference": ["supported_exchanges", "supported_pairs"],
    },
    base_urls={"mainnet": "https://api.hyblock.co"},
    operation_details={
        "liquidation_clusters": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_DEFILLAMA = SourceCapability(
    source="defillama",
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
        "market": ["tvl", "on_chain_metrics", "protocol_revenue", "yields"],
        "reference": ["protocols", "chains", "stablecoins"],
    },
    base_urls={"mainnet": "https://api.llama.fi"},
    operation_details={
        "tvl": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
        "yields": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
    },
)

# ---------------------------------------------------------------------------
# Macro / commodity data (4)
# ---------------------------------------------------------------------------

_BAKER_HUGHES = SourceCapability(
    source="baker_hughes",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["rig_count"],
        "reference": ["rig_count_series"],
    },
    base_urls={"mainnet": "https://rigcount.bakerhughes.com"},
    operation_details={},
)

_CFTC = SourceCapability(
    source="cftc",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["cot_report", "commitments_of_traders"],
        "reference": ["markets_list", "report_types"],
    },
    base_urls={"mainnet": "https://publicreporting.cftc.gov"},
    operation_details={},
)

_EIA = SourceCapability(
    source="eia",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["ohlcv", "on_chain_metrics", "energy_data"],
        "reference": ["series", "categories", "geosets"],
    },
    base_urls={"mainnet": "https://api.eia.gov"},
    operation_details={
        "energy_data": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_FEAR_GREED = SourceCapability(
    source="fear_greed",
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
        "market": ["fear_greed_index", "historical_readings"],
        "reference": ["index_metadata"],
    },
    base_urls={"mainnet": "https://api.alternative.me"},
    operation_details={},
)

_OPEN_METEO = SourceCapability(
    source="open_meteo",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "reference": ["forecast", "historical_weather", "feature_records"],
    },
    base_urls={"mainnet": "https://api.open-meteo.com"},
    operation_details={},
)

# ---------------------------------------------------------------------------
# Infrastructure / cloud (2)
# ---------------------------------------------------------------------------

_AWS = SourceCapability(
    source="aws",
    domains=["reference"],
    crosscutting=["errors", "rate_limits", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "test_creds", "prod": "prod_creds"},
    operations={
        "reference": ["s3_buckets", "ec2_instances", "ecr_repos", "codebuild_projects"],
    },
    base_urls={},
    operation_details={},
)

_GCP = SourceCapability(
    source="gcp",
    domains=["reference"],
    crosscutting=["errors", "rate_limits", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "test_creds", "prod": "prod_creds"},
    operations={
        "reference": ["storage_buckets", "compute_instances", "artifact_registry", "cloud_build"],
    },
    base_urls={},
    operation_details={},
)

_GITHUB = SourceCapability(
    source="github",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "github_token"},
    operations={
        "reference": ["repositories", "pull_requests", "workflow_runs", "commits"],
    },
    base_urls={"mainnet": "https://api.github.com"},
    operation_details={
        "repositories": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)


# ---------------------------------------------------------------------------
# Ordered list -- Alt data / Macro / Infrastructure
# ---------------------------------------------------------------------------

ALTDATA_CAPABILITIES: list[SourceCapability] = [
    # Alt data / on-chain analytics
    _ALCHEMY,
    _THEGRAPH,
    _COINGECKO,
    _COINGLASS,
    _GLASSNODE,
    _CRYPTOQUANT,
    _HYBLOCK,
    _DEFILLAMA,
    # Macro / commodity data
    _BAKER_HUGHES,
    _CFTC,
    _EIA,
    _FEAR_GREED,
    _OPEN_METEO,
    # Infrastructure / cloud
    _AWS,
    _GCP,
    _GITHUB,
]
