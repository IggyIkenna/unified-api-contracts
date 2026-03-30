"""CeFi exchanges, aggregators, and FIX protocol capability declarations."""

from __future__ import annotations

from ..capability import OperationDetail, OperationEnvDetail, SourceCapability

# ---------------------------------------------------------------------------
# CeFi exchanges (15)
# ---------------------------------------------------------------------------

_BINANCE = SourceCapability(
    source="binance",
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
        "market": ["ticker", "orderbook", "klines", "trades", "agg_trades", "ws_ticker", "ws_depth", "ws_trades"],
        "execution": ["new_order", "cancel_order", "query_order", "open_orders", "all_orders"],
        "position": ["account", "balances", "positions", "margin_account"],
        "reference": ["exchange_info", "server_time", "system_status"],
    },
    base_urls={"mainnet": "https://api.binance.com", "testnet": "https://testnet.binance.vision"},
    margin_model={"mainnet": "cross", "testnet": "cross"},
    operation_details={
        "new_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
        "ticker": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "account": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
    },
)

_BYBIT = SourceCapability(
    source="bybit",
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
        "market": ["ticker", "orderbook", "klines", "trades", "ws_ticker", "ws_depth", "ws_trades"],
        "execution": ["place_order", "cancel_order", "amend_order", "open_orders", "order_history"],
        "position": ["wallet_balance", "positions", "pnl"],
        "reference": ["instruments_info", "server_time"],
    },
    base_urls={"mainnet": "https://api.bybit.com", "testnet": "https://api-testnet.bybit.com"},
    margin_model={"mainnet": "cross", "testnet": "cross"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
        "wallet_balance": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
    },
)

_OKX = SourceCapability(
    source="okx",
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
        "market": ["ticker", "orderbook", "candles", "trades", "ws_ticker", "ws_books", "ws_trades"],
        "execution": ["place_order", "cancel_order", "amend_order", "pending_orders", "order_history"],
        "position": ["balance", "positions", "account_config"],
        "reference": ["instruments", "system_status"],
    },
    base_urls={"mainnet": "https://www.okx.com", "testnet": "https://www.okx.com"},
    margin_model={"mainnet": "cross", "testnet": "cross"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256",
                    required_credential="api_key",
                    data_fidelity="synthetic",
                    notes="OKX testnet uses same URL with x-simulated-trading header",
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
    },
)

_COINBASE = SourceCapability(
    source="coinbase",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key", "oauth"],
    auth_environments={"test": "sandbox_key", "prod": "prod_key"},
    operations={
        "market": ["ticker", "orderbook", "candles", "trades", "ws_ticker", "ws_matches"],
        "execution": ["create_order", "cancel_order", "list_orders"],
        "position": ["accounts", "balances"],
        "reference": ["products", "currencies"],
    },
    base_urls={"mainnet": "https://api.coinbase.com", "testnet": "https://api-public.sandbox.exchange.coinbase.com"},
    margin_model={},
    operation_details={
        "create_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_DERIBIT = SourceCapability(
    source="deribit",
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
        "market": ["ticker", "orderbook", "trades", "index_price", "funding_rate", "ws_ticker", "ws_book"],
        "execution": ["buy", "sell", "cancel", "edit", "open_orders", "order_history"],
        "position": ["positions", "account_summary", "margins"],
        "reference": ["instruments", "currencies", "settlement_history"],
    },
    base_urls={"mainnet": "https://www.deribit.com", "testnet": "https://test.deribit.com"},
    margin_model={"mainnet": "portfolio", "testnet": "portfolio"},
    operation_details={
        "buy": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
        "sell": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
        "cancel": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
    },
)

_HYPERLIQUID = SourceCapability(
    source="hyperliquid",
    domains=["market", "execution", "position"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "testnet_key", "prod": "prod_key"},
    operations={
        "market": [
            "all_mids",
            "l2_book",
            "candles",
            "recent_trades",
            "ws_trades",
            "ws_l2_book",
            "derivative_ticker",
            "funding_rates",
        ],
        "execution": ["place_order", "cancel_order", "modify_order", "open_orders", "order_status"],
        "position": ["user_state", "clearinghouse_state", "funding_history"],
    },
    base_urls={"mainnet": "https://api.hyperliquid.xyz", "testnet": "https://api.hyperliquid-testnet.xyz"},
    margin_model={"mainnet": "cross", "testnet": "unified"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="l1_action", required_credential="api_wallet"),
                "testnet": OperationEnvDetail(
                    signing_scheme="l1_action", required_credential="api_wallet", data_fidelity="synthetic"
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="l1_action", required_credential="api_wallet"),
                "testnet": OperationEnvDetail(signing_scheme="l1_action", required_credential="api_wallet"),
            }
        ),
        "modify_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="l1_action", required_credential="api_wallet"),
                "testnet": OperationEnvDetail(signing_scheme="l1_action", required_credential="api_wallet"),
            }
        ),
        "usd_class_transfer": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="user_signed", required_credential="main_wallet"),
                "testnet": OperationEnvDetail(
                    supported=False, notes="API wallet cannot transfer; requires main wallet key or use UI"
                ),
            }
        ),
        "withdraw": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="user_signed", required_credential="main_wallet"),
                "testnet": OperationEnvDetail(signing_scheme="user_signed", required_credential="main_wallet"),
            }
        ),
        "all_mids": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "l2_book": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "user_state": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", notes="Public — pass user address as param"
                ),
                "testnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
        "clearinghouse_state": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
        "funding_history": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
        "derivative_ticker": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes="Funding rates, OI, mark/index price. Sources: S3 archive (historical) + REST API (recent)",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "funding_rates": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes="8-hourly funding rates via info.funding_history(). No API key required.",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "open_orders": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
        "order_status": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
        "spot_transfer": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="user_signed_eip712",
                    required_credential="wallet_private_key",
                    data_fidelity="production",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="user_signed_eip712",
                    required_credential="wallet_private_key",
                    data_fidelity="synthetic",
                ),
            }
        ),
        "approve_agent": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="user_signed_eip712",
                    required_credential="wallet_private_key",
                    data_fidelity="production",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="user_signed_eip712",
                    required_credential="wallet_private_key",
                    data_fidelity="synthetic",
                ),
            }
        ),
        "approve_builder_fee": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="user_signed_eip712",
                    required_credential="wallet_private_key",
                    data_fidelity="production",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="user_signed_eip712",
                    required_credential="wallet_private_key",
                    data_fidelity="synthetic",
                ),
            }
        ),
    },
)


_BITGET = SourceCapability(
    source="bitget",
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
        "market": ["ticker", "orderbook", "trades", "candles", "ws_ticker", "ws_depth", "ws_trade"],
        "execution": ["place_order", "cancel_order", "modify_order", "open_orders", "order_history"],
        "position": ["account", "positions", "fills"],
        "reference": ["symbols", "server_time"],
    },
    base_urls={"mainnet": "https://api.bitget.com", "testnet": "https://api.bitget.com"},
    margin_model={"mainnet": "cross"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256",
                    required_credential="api_key",
                    data_fidelity="synthetic",
                    notes="Testnet uses same base URL with simulated header",
                ),
            }
        ),
    },
)

_BITSTAMP = SourceCapability(
    source="bitstamp",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["ticker", "orderbook", "transactions", "ohlc", "ws_ticker", "ws_order_book", "ws_live_trades"],
        "execution": ["buy_market", "sell_market", "cancel_order", "open_orders", "order_status"],
        "position": ["balance", "user_transactions"],
        "reference": ["trading_pairs_info"],
    },
    base_urls={"mainnet": "https://www.bitstamp.net"},
    operation_details={
        "buy_market": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
    },
)

_KRAKEN = SourceCapability(
    source="kraken",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["ticker", "orderbook", "trades", "ohlc", "ws_ticker", "ws_book", "ws_trade"],
        "execution": ["add_order", "cancel_order", "open_orders", "closed_orders", "query_orders"],
        "position": ["balance", "extended_balance", "trade_balance", "open_positions"],
        "reference": ["asset_pairs", "assets", "system_status"],
    },
    base_urls={"mainnet": "https://api.kraken.com"},
    operation_details={
        "add_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha512", required_credential="api_key"),
            }
        ),
    },
)

_HUOBI = SourceCapability(
    source="huobi",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["tickers", "depth", "trade", "kline", "ws_market_detail", "ws_depth", "ws_trade_detail"],
        "execution": ["place_order", "cancel_order", "open_orders", "orders_list"],
        "position": ["accounts", "account_balance", "account_history"],
        "reference": ["common_symbols", "common_timestamp"],
    },
    base_urls={"mainnet": "https://api.huobi.pro"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
    },
)

_KUCOIN = SourceCapability(
    source="kucoin",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "sandbox_key", "prod": "prod_key"},
    operations={
        "market": ["ticker", "order_book", "trade_histories", "klines", "ws_ticker", "ws_orderbook", "ws_match"],
        "execution": ["post_order", "cancel_order", "list_orders", "get_order_by_id"],
        "position": ["list_accounts", "get_account", "account_ledger"],
        "reference": ["symbols_list", "currencies", "server_time"],
    },
    base_urls={"mainnet": "https://api.kucoin.com", "testnet": "https://openapi-sandbox.kucoin.com"},
    operation_details={
        "post_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha256", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_MEXC = SourceCapability(
    source="mexc",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["ticker", "orderbook", "trades", "klines", "ws_deals", "ws_depth", "ws_ticker"],
        "execution": ["create_order", "cancel_order", "open_orders", "all_orders"],
        "position": ["account", "balances"],
        "reference": ["exchange_info", "server_time"],
    },
    base_urls={"mainnet": "https://api.mexc.com"},
    operation_details={
        "create_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha256", required_credential="api_key"),
            }
        ),
    },
)

_UPBIT = SourceCapability(
    source="upbit",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": [
            "ticker",
            "orderbook",
            "trades",
            "candles_minutes",
            "candles_days",
            "ws_ticker",
            "ws_orderbook",
            "ws_trade",
        ],
        "execution": ["orders", "cancel_order", "chance"],
        "position": ["accounts"],
        "reference": ["market_all"],
    },
    base_urls={"mainnet": "https://api.upbit.com"},
    operation_details={
        "orders": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="jwt", required_credential="api_key"),
            }
        ),
    },
)

# ---------------------------------------------------------------------------
# CeFi aggregators / connectors (3)
# ---------------------------------------------------------------------------

_CCXT = SourceCapability(
    source="ccxt",
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
        "market": [
            "fetch_ticker",
            "fetch_order_book",
            "fetch_trades",
            "fetch_ohlcv",
            "watch_ticker",
            "watch_order_book",
        ],
        "execution": ["create_order", "cancel_order", "fetch_order", "fetch_open_orders", "fetch_orders"],
        "position": ["fetch_balance", "fetch_positions"],
        "reference": ["fetch_markets", "fetch_currencies", "load_markets"],
    },
    base_urls={},
    operation_details={},
)

_TARDIS = SourceCapability(
    source="tardis",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["trades", "orderbook", "quotes", "derivative_ticker", "liquidations", "options_chain", "ws_replay"],
        "reference": ["exchanges", "instruments", "data_types"],
    },
    base_urls={"mainnet": "https://api.tardis.dev"},
    operation_details={
        "trades": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
)

_ASTER = SourceCapability(
    source="aster",
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
        "market": [
            "ticker",
            "orderbook",
            "trades",
            "ohlcv",
            "liquidations",
            "derivative_ticker",
            "ws_ticker",
            "ws_depth",
            "ws_trades",
        ],
        "execution": ["place_order", "cancel_order", "open_orders", "order_status"],
        "position": ["account", "positions", "balances"],
        "reference": ["instruments", "server_time"],
    },
    base_urls={"mainnet": "https://api.aster.finance", "testnet": "https://testnet-api.aster.finance"},
    margin_model={"mainnet": "cross", "testnet": "cross"},
    operation_details={
        "place_order": OperationDetail(
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
# FIX protocol / trading connectors (2)
# ---------------------------------------------------------------------------

_FIX = SourceCapability(
    source="fix",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=False,
    supports_historical=False,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key", "cert"],
    auth_environments={"test": "uat_creds", "prod": "prod_creds"},
    operations={
        "market": ["market_data_request", "market_data_incremental_refresh", "market_data_snapshot"],
        "execution": ["new_order_single", "order_cancel_request", "order_cancel_replace_request", "execution_report"],
        "reference": ["security_definition_request", "security_status_request"],
    },
    base_urls={},
    operation_details={
        "new_order_single": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="fix_logon", required_credential="cert"),
                "testnet": OperationEnvDetail(
                    signing_scheme="fix_logon", required_credential="cert", data_fidelity="synthetic"
                ),
            }
        ),
    },
)

_NAUTILUS = SourceCapability(
    source="nautilus",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "testnet_key", "prod": "prod_key"},
    operations={
        "market": ["quotes", "trades", "bars", "order_book", "ws_quotes", "ws_trades", "ws_bars"],
        "execution": ["submit_order", "cancel_order", "modify_order", "open_orders", "fills"],
        "reference": ["instruments", "venues"],
    },
    base_urls={},
    operation_details={
        "submit_order": OperationDetail(
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
# Ordered list -- CeFi
# ---------------------------------------------------------------------------

CEFI_CAPABILITIES: list[SourceCapability] = [
    # CeFi exchanges
    _BINANCE,
    _BYBIT,
    _OKX,
    _COINBASE,
    _DERIBIT,
    _HYPERLIQUID,
    _BITGET,
    _BITSTAMP,
    _KRAKEN,
    _HUOBI,
    _KUCOIN,
    _MEXC,
    _UPBIT,
    # CeFi aggregators / connectors
    _CCXT,
    _TARDIS,
    _ASTER,
    # FIX protocol / trading connectors
    _FIX,
    _NAUTILUS,
]
