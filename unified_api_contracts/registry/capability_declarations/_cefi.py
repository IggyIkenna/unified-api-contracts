"""CeFi exchanges, aggregators, and FIX protocol capability declarations."""

from __future__ import annotations

from datetime import date

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
    chain=None,
    kind="perp_cex",
    # Tardis archive starts 2019-01-01 for Binance Spot; venue launched 2017-07-14 but
    # the Tardis historical capture did not begin until Jan 2019. Applies to BINANCE-SPOT
    # oracle lookups; BINANCE-FUTURES dates pre-2019-09-08 are handled by NOT_YET_LIVE
    # via venue_launch_dates (venue_launch_dates["BINANCE-FUTURES"] = 2019-09-08).
    coverage_start={"trades": date(2019, 1, 1), "book_snapshot_5": date(2019, 1, 1)},
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
    chain=None,
    kind="perp_cex",
    # Tardis archive starts 2019-01-01 for Bybit Spot; venue launched 2018-12-01.
    # Perp derivatives (inverse perps) also from 2019-01-01 on Tardis.
    coverage_start={
        "candles": date(2018, 12, 1),
        "trades": date(2019, 1, 1),
        "book_snapshot_5": date(2019, 1, 1),
        "derivative_ticker": date(2019, 1, 1),
        "liquidations": date(2019, 1, 1),
        # ERA-B: futures_chain = instrument_type captured as trades (see Deribit
        # note); retained for legacy data_type coverage lookups. NOTE — BYBIT
        # FUTURE is captured per-contract, not bundled (F2, cefi-owner); that
        # venue-grain question is owned by slot-3, separate from this Era-B re-key.
        "futures_chain": date(2019, 1, 1),
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
    chain=None,
    kind="perp_cex",
    # Tardis archive starts 2020-01-01 for OKX (was OKEx); venue launched 2017-01-01
    # but Tardis historical capture for OKEx began in early 2020. All data types
    # (spot + derivatives) from the same Tardis collection start date.
    coverage_start={
        "trades": date(2020, 1, 1),
        "book_snapshot_5": date(2020, 1, 1),
        "derivative_ticker": date(2020, 1, 1),
        "liquidations": date(2020, 1, 1),
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
    chain=None,
    kind="spot_cex",
    # Tardis archive starts 2019-01-01 for Coinbase (was GDAX/Coinbase Pro); venue
    # launched 2014-12-08 but Tardis historical capture began in 2019.
    coverage_start={"trades": date(2019, 1, 1), "book_snapshot_5": date(2019, 1, 1)},
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
    chain=None,
    kind="options_cex",
    # Tardis archive starts 2019-01-01 for Deribit; venue launched 2016-06-29 but Tardis
    # historical capture began in 2019. All data types (spot trades + options/futures
    # derivatives) from the same Tardis collection start date.
    # ERA-B (operator 2026-06-07): options_chain / futures_chain are
    # INSTRUMENT_TYPES (per-underlying chain bundles) captured as data_type=trades,
    # so the bundle's coverage is the venue ``trades`` start above. The two
    # chain-keyed entries are retained only for legacy data_type=options_chain /
    # data_type=futures_chain coverage lookups pending the per-AG v8→v9 relabel
    # (OUT OF SCOPE here); they carry the same start date as trades.
    coverage_start={
        "trades": date(2019, 1, 1),
        "book_snapshot_5": date(2019, 1, 1),
        "derivative_ticker": date(2019, 1, 1),
        "liquidations": date(2019, 1, 1),
        "options_chain": date(2019, 1, 1),
        "futures_chain": date(2019, 1, 1),
    },
)

# OPTIONS: not supported — venue does not offer listed options contracts
# FUTURE: not supported — Hyperliquid only offers perpetual futures (no fixed-expiry contracts)
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
    chain="hyperevm",
    kind="perp_dex",
    # Tardis archive starts at Hyperliquid mainnet launch 2023-06-14 (venue + Tardis
    # collection both began on this date). All data types from launch.
    coverage_start={
        "candles": date(2023, 6, 14),
        "trades": date(2023, 6, 14),
        "book_snapshot_5": date(2023, 6, 14),
        "derivative_ticker": date(2023, 6, 14),
        "liquidations": date(2023, 6, 14),
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
    chain=None,
    kind="perp_cex",
    coverage_start={"candles": date(2019, 4, 1)},
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
    chain=None,
    kind="spot_cex",
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
    chain=None,
    kind="perp_cex",
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
    chain=None,
    kind="spot_cex",
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
    chain=None,
    kind="spot_cex",
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
    chain=None,
    kind="spot_cex",
    # Tardis archive starts 2019-06-01 for Upbit; venue launched 2017-10-24 but
    # Tardis historical capture for Upbit began mid-2019.
    coverage_start={"trades": date(2019, 6, 1), "book_snapshot_5": date(2019, 6, 1)},
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
    chain=None,
    kind=None,
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
        # ERA-B: "options_chain" is the chain-bundle INSTRUMENT_TYPE this Tardis
        # market op fetches (per-underlying), captured as data_type=trades.
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
    chain=None,
    kind=None,
)

# OPTIONS: not supported — venue does not offer listed options contracts
# FUTURE: not supported — Aster only offers perpetual futures (CLOB model, no fixed-expiry contracts)
# Extended (Starknet L2 perp DEX, formerly X10).
# Hybrid CLOB: off-chain matching + on-chain settlement via StarkEx. Read endpoints
# (market data) authed by X-Api-Key header; write endpoints (orders/transfers)
# additionally require a SNIP-12 typed-data signature with a Stark private key.
# Entity binding: odum-group-cayman (Odum Research UK is on Extended's restricted
# territory list — see memory/project_trading_entities.md). Account identifiers
# (non-secret, operator 2026-05-20): stark_public_key
# 0x276f6bb00fa3f451988872959ee5cf24031bb96d5a0aa6ed9e7a07d24f36e03, vault_id 380539,
# client_id 263651, wallet 0x992ebFe04DB05f964C45BCE3D73Ca4c81715a79f.
# Secrets resolved at runtime via GCP Secret Manager (project from GCP_PROJECT_ID config):
#   - extended-starknet-api-key/versions/latest
#   - extended-starknet-stark-private-key/versions/latest
# (versions/latest so rotation flows without redeploy — mirrors workspace pattern.)
# Mandatory request header: User-Agent (required by Extended API gateway).
# Coverage: candles since 2024-07-26, funding since 2025-07-18
# (per extended_starknet_historical_data_path_2026_05_20.md). Live=batch via REST
# pagination on the same endpoints.
# OPTIONS / FUTURE: not supported — Extended only offers perpetual futures.
_EXTENDED = SourceCapability(
    source="extended",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key", "wallet_private_key"],
    auth_environments={"test": "testnet_key", "prod": "prod_key"},
    operations={
        "market": [
            "ticker",
            "orderbook",
            "trades",
            "candles",
            "funding_rates",
            "derivative_ticker",
            "ws_ticker",
            "ws_orderbook",
            "ws_trades",
        ],
        "execution": ["place_order", "cancel_order", "open_orders", "order_status"],
        "position": ["account", "positions", "balances"],
        "reference": ["markets", "instruments", "server_time"],
    },
    base_urls={
        "mainnet": "https://api.starknet.extended.exchange/api/v1",
        "testnet": "https://api.starknet.sepolia.extended.exchange/api/v1",
    },
    margin_model={"mainnet": "cross", "testnet": "cross"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="eip712",
                    required_credential="wallet_private_key",
                    notes="X-Api-Key header + SNIP-12 typed-data signature (Stark key). Entity: odum-group-cayman.",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="eip712",
                    required_credential="wallet_private_key",
                    data_fidelity="synthetic",
                    notes="Sepolia. X-Api-Key + SNIP-12 Stark signature.",
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="eip712", required_credential="wallet_private_key"),
                "testnet": OperationEnvDetail(signing_scheme="eip712", required_credential="wallet_private_key"),
            }
        ),
        "account": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="api_key_header", required_credential="api_key", data_fidelity="synthetic"
                ),
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
        "orderbook": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "candles": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes="Coverage start 2024-07-26. REST pagination — live=batch path.",
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
                    notes="Coverage start 2025-07-18. 1h funding interval.",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
        "ws_orderbook": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    base_url="wss://api.starknet.extended.exchange/stream.extended.exchange/v1",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    base_url="wss://starknet.sepolia.extended.exchange/stream.extended.exchange/v1",
                    data_fidelity="synthetic",
                ),
            }
        ),
        "ws_trades": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    base_url="wss://api.starknet.extended.exchange/stream.extended.exchange/v1",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    base_url="wss://starknet.sepolia.extended.exchange/stream.extended.exchange/v1",
                    data_fidelity="synthetic",
                ),
            }
        ),
    },
    chain="starknet",
    kind="perp_dex",
    mandatory_user_agent="odum-group-unified-trading/extended-mtds",
    coverage_start={"candles": date(2024, 7, 26), "funding_rates": date(2025, 7, 18)},
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
        # NOTE: liquidations removed from scope 2026-05-04 — Aster's
        # /fapi/v1/forceOrders endpoint returns maintenance error and our
        # _fetch_aster_rest dispatcher does not wire it. Re-add when (if) we
        # ship a working adapter path.
        "market": [
            "ticker",
            "orderbook",
            "trades",
            "ohlcv",
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
    chain=None,
    kind="perp_cex",
    # Aster genesis 2023-07-22 (operator-confirmed 2026-06-17 = Astherus pre-rebrand
    # genesis). IMPORTANT — pre-2024 Aster funding is BINANCE-PROXIED (Astherus
    # pre-rebrand mirrored Binance funding); imported, NOT Aster-native — label
    # source honestly. SSOT: perp_funding_data_semantics_and_cadence_2026_06_16.md §GAP 2.
    coverage_start={
        "candles": date(2023, 7, 22),
        "trades": date(2023, 7, 22),
        "book_snapshot_5": date(2023, 7, 22),
        "derivative_ticker": date(2023, 7, 22),
        "liquidations": date(2023, 7, 22),
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
    chain=None,
    kind=None,
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
    chain=None,
    kind=None,
)


# ---------------------------------------------------------------------------
# Kraken — direct REST + WebSocket (BLOCKED-CREDENTIALS scaffold 2026-05-14)
# ---------------------------------------------------------------------------
# BLOCKED-CREDENTIALS: Requires Kraken Pro API key (read-only scope for May-23 SLA).
# See: ikenna_orchestrator/pings/slot_11.md — CREDENTIAL APPROVAL REQUEST filed.
# CCXT fallback (kraken) exists but is insufficient: rate-limit handling +
# ticker normalization gaps (Kraken uses XBT not BTC; USDT pairs suffixed differently).
# This capability entry supports the direct REST+WS adapter in execution-service.
# Note: Kraken futures are offered via the "cryptofacilities" CCXT id (see venue_mapping.py).
_KRAKEN = SourceCapability(
    source="kraken",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,  # Kraken does not offer a public testnet for REST/WS
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["ticker", "orderbook", "trades", "ohlc", "ws_ticker", "ws_book", "ws_trade"],
        "execution": ["add_order", "cancel_order", "query_orders", "open_orders"],
        "position": ["balance", "trade_balance", "open_positions"],
        "reference": ["asset_pairs", "assets", "server_time", "system_status"],
    },
    base_urls={
        "mainnet": "https://api.kraken.com",
        "ws_public": "wss://ws.kraken.com",
        "ws_private": "wss://ws-auth.kraken.com",
    },
    margin_model={},
    operation_details={
        "add_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha512", required_credential="api_key"),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha512", required_credential="api_key"),
            }
        ),
        "ticker": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
        "balance": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha512", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind="spot_cex",
)

# Kraken Futures (via cryptofacilities CCXT id / Kraken Futures REST API)
# BLOCKED-CREDENTIALS: same credential request as _KRAKEN above.
_KRAKEN_FUTURES = SourceCapability(
    source="kraken-futures",
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
        "market": ["ticker", "orderbook", "trades", "ohlc", "funding_rate", "ws_ticker", "ws_book"],
        "execution": ["place_order", "cancel_order", "open_orders", "fill_history"],
        "position": ["account", "open_positions", "notifications"],
        "reference": ["instruments", "fee_schedules"],
    },
    base_urls={
        "mainnet": "https://futures.kraken.com",
        "testnet": "https://demo-futures.kraken.com",
    },
    margin_model={"mainnet": "cross"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha512", required_credential="api_key"),
                "testnet": OperationEnvDetail(
                    signing_scheme="hmac_sha512", required_credential="api_key", data_fidelity="synthetic"
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="hmac_sha512", required_credential="api_key"),
                "testnet": OperationEnvDetail(signing_scheme="hmac_sha512", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind="perp_cex",
    coverage_start={"candles": date(2019, 9, 1)},
)


# ---------------------------------------------------------------------------
# CFTC-regulated crypto perp venues (kalshi_perp + polymarket_perp)
# ---------------------------------------------------------------------------

_KALSHI_PERP = SourceCapability(
    source="kalshi_perp",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],  # public-read for market data (no auth required)
    auth_environments={"prod": "none"},
    operations={
        # REST ops (no ws_ prefix → BATCH; rest_ ops are cursor-paginated REST).
        # trades: also streams via WS (ws_trades → LIVE reachable for trades).
        # funding_rates / perp_funding: REST-ONLY (periodic settlements, no WS stream).
        "market": [
            "markets",  # GET /markets?category=CRYPTO&status=active (universe)
            "trades",  # GET /markets/{ticker}/trades (cursor-paginated REST + WS)
            "ws_trades",  # WS live trade stream (confirms LIVE capability for trades)
            "funding_rates",  # GET /markets/{ticker}/funding_rates (cursor-paginated REST ONLY)
        ],
        "reference": [
            "market_detail",  # GET /markets/{ticker} (single-instrument detail)
        ],
    },
    base_urls={"mainnet": "https://api.elections.kalshi.com/trade-api/v2"},
    operation_details={
        "markets": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes="Public read — no auth. Launched 2026-05-29. CFTC-regulated crypto perps.",
                ),
            }
        ),
        "trades": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes="Cursor-paginated; ≤1000 per call. Also available via WS (ws_trades).",
                ),
            }
        ),
        "ws_trades": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes="Live WS trade stream. Makes LIVE mode reachable for data_type=trades.",
                ),
            }
        ),
        "funding_rates": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes=(
                        "Cursor-paginated periodic funding settlements (REST ONLY — no WS stream). "
                        "modes_for(kalshi_perp, funding_rates) → {BATCH} (no ws_funding_rates op)."
                    ),
                ),
            }
        ),
    },
    chain=None,
    kind="perp_cex",
    coverage_start={"trades": date(2026, 5, 29), "funding_rates": date(2026, 5, 29)},
)

_POLYMARKET_PERP = SourceCapability(
    source="polymarket_perp",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=False,  # BLOCKED-UPSTREAM-OUTAGE: DNS NXDOMAIN 2026-06-21
    supports_batch=False,  # BLOCKED-UPSTREAM-OUTAGE: DNS NXDOMAIN 2026-06-21
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],  # public-read expected when endpoint recovers
    auth_environments={"prod": "none"},
    operations={
        # BLOCKED-UPSTREAM-OUTAGE: endpoint (perps-api.polymarket.com) is DNS NXDOMAIN
        # as of 2026-06-21. Operations scaffolded based on the expected API surface
        # (mirrors Polymarket CLOB API patterns); verify when endpoint recovers.
        # trades: REST + WS stream expected (ws_trades declared → LIVE reachable for trades).
        # funding_rates: REST-ONLY (periodic settlements, no WS stream — like kalshi_perp).
        "market": [
            "markets",  # GET /markets (universe listing)
            "trades",  # GET /markets/{ticker}/trades (expected cursor-paginated REST)
            "ws_trades",  # Expected WS live trade stream (scaffold; verify on recovery)
            "funding_rates",  # GET /markets/{ticker}/funding_rates (expected REST ONLY)
        ],
        "reference": [
            "market_detail",  # GET /markets/{ticker}
        ],
    },
    base_urls={"mainnet": "https://perps-api.polymarket.com"},
    operation_details={
        "markets": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes=(
                        "BLOCKED-UPSTREAM-OUTAGE: DNS NXDOMAIN 2026-06-21. "
                        "Polymarket-perp CFTC crypto perps, launched 2026-04-21. "
                        "Scaffold registered; verify when endpoint recovers."
                    ),
                ),
            }
        ),
        "ws_trades": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="none",
                    required_credential="none",
                    notes=(
                        "Expected WS live trade stream (scaffold — BLOCKED-UPSTREAM-OUTAGE 2026-06-21). "
                        "Makes LIVE mode reachable for data_type=trades when endpoint recovers. "
                        "funding_rates has no ws_funding_rates op → {BATCH} only for that data_type."
                    ),
                ),
            }
        ),
    },
    chain=None,
    kind="perp_cex",
    coverage_start={"trades": date(2026, 4, 21), "funding_rates": date(2026, 4, 21)},
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
    _HUOBI,
    _KUCOIN,
    _MEXC,
    _UPBIT,
    # Kraken (BLOCKED-CREDENTIALS scaffold 2026-05-14 — see slot_11.md ping)
    _KRAKEN,
    _KRAKEN_FUTURES,
    # CeFi aggregators / connectors
    _CCXT,
    _TARDIS,
    _ASTER,
    _EXTENDED,
    # FIX protocol / trading connectors
    _FIX,
    _NAUTILUS,
    # CFTC-regulated crypto perp venues (kalshi_perp + polymarket_perp)
    _KALSHI_PERP,
    _POLYMARKET_PERP,
]
