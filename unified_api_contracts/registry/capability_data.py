"""Capability declarations for all external data sources.

Each declaration describes what the source provides: domains, crosscutting
concerns, live/batch/historical support, auth, and per-domain operations.
"""

from __future__ import annotations

from .capability import SourceCapability, register_capability

__all__ = [
    "CAPABILITY_DECLARATIONS",
    "bootstrap_capabilities",
]

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
        "market": ["all_mids", "l2_book", "candles", "recent_trades", "ws_trades", "ws_l2_book"],
        "execution": ["place_order", "cancel_order", "modify_order", "open_orders", "order_status"],
        "position": ["user_state", "clearinghouse_state", "funding_history"],
    },
)

_BITFINEX = SourceCapability(
    source="bitfinex",
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
        "market": ["ticker", "orderbook", "trades", "candles", "ws_ticker", "ws_book", "ws_trades"],
        "execution": ["submit_order", "cancel_order", "update_order", "open_orders", "order_history"],
        "position": ["wallets", "positions", "fills"],
        "reference": ["symbols", "tickers_history"],
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
)

_GATEIO = SourceCapability(
    source="gateio",
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
        "market": ["ticker", "orderbook", "trades", "candlesticks", "ws_tickers", "ws_order_book", "ws_trades"],
        "execution": ["create_order", "cancel_order", "list_orders", "get_order"],
        "position": ["spot_accounts", "futures_accounts", "positions"],
        "reference": ["list_currency_pairs", "get_currency_pair"],
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
)

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
)

# ---------------------------------------------------------------------------
# DeFi data / on-chain analytics (5)
# ---------------------------------------------------------------------------

_PYTH = SourceCapability(
    source="pyth",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["price_feed", "latest_price", "price_updates", "ws_price_updates"],
        "reference": ["price_feeds", "asset_types"],
    },
)

_BLOXROUTE = SourceCapability(
    source="bloxroute",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "connectivity"],
    supports_live=True,
    supports_batch=False,
    supports_historical=False,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "testnet_key", "prod": "prod_key"},
    operations={
        "market": ["oracle_price_feed", "pending_txns", "new_txns", "ws_pending_txns"],
        "reference": ["network_info"],
    },
)

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
)

# ---------------------------------------------------------------------------
# Sports / prediction markets (13)
# ---------------------------------------------------------------------------

_BETFAIR = SourceCapability(
    source="betfair",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits", "latency"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key", "cert"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["list_market_catalogue", "list_market_book", "list_runner_book", "streaming"],
        "execution": ["place_orders", "cancel_orders", "replace_orders", "list_current_orders"],
        "reference": ["list_event_types", "list_competitions", "list_events", "list_countries", "list_venues"],
    },
)

_BETDAQ = SourceCapability(
    source="betdaq",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["list_markets", "get_prices", "streaming"],
        "execution": ["place_orders", "cancel_orders", "settle_orders"],
        "reference": ["list_sports", "list_events"],
    },
)

_PINNACLE = SourceCapability(
    source="pinnacle",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["odds", "fixtures", "settled_fixtures", "line"],
        "reference": ["sports", "leagues", "periods"],
    },
)

_KALSHI = SourceCapability(
    source="kalshi",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "demo_key", "prod": "prod_key"},
    operations={
        "market": ["markets", "market_orderbook", "trades", "series", "ws_orderbook"],
        "execution": ["create_order", "cancel_order", "batch_create_orders"],
        "position": ["portfolio", "positions", "fills", "settlements"],
        "reference": ["events", "series", "categories"],
    },
)

_POLYMARKET = SourceCapability(
    source="polymarket",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["markets", "orderbook", "prices", "trades", "ws_prices"],
        "execution": ["create_order", "cancel_order", "open_orders"],
        "position": ["positions", "balances", "pnl"],
        "reference": ["events", "markets_metadata", "tags"],
    },
)

_ODDS_API = SourceCapability(
    source="odds_api",
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
        "market": ["odds", "scores", "historical_odds"],
        "reference": ["sports", "participants"],
    },
)

_ODDS_ENGINE = SourceCapability(
    source="odds_engine",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["markets", "odds_lines"],
        "reference": ["sports", "leagues"],
    },
)

_ODDSJAM = SourceCapability(
    source="oddsjam",
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
        "market": ["odds", "game_lines", "player_props", "arb_opportunities"],
        "reference": ["sports", "leagues", "books"],
    },
)

_OPTICODDS = SourceCapability(
    source="opticodds",
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
        "market": ["odds", "fixtures", "player_props"],
        "reference": ["sports", "leagues", "books"],
    },
)

_MATCHBOOK = SourceCapability(
    source="matchbook",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["events", "markets", "runners", "prices"],
        "execution": ["offer", "cancel_offer", "current_offers"],
        "reference": ["sports", "events_list"],
    },
)

_SMARKETS = SourceCapability(
    source="smarkets",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["events", "markets", "quotes", "streaming"],
        "execution": ["create_order", "cancel_order", "open_orders"],
        "reference": ["sports", "competitions"],
    },
)

_MANIFOLD = SourceCapability(
    source="manifold",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["markets", "market_bets", "trades", "odds"],
        "execution": ["bet", "cancel_bet", "sell_shares"],
        "reference": ["users", "groups", "tags"],
    },
)

_PREDICTIT = SourceCapability(
    source="predictit",
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
        "market": ["markets", "market_contracts", "price_history"],
        "reference": ["all_markets"],
    },
)

_ONEXBET = SourceCapability(
    source="onexbet",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["prematch_odds", "live_odds"],
        "reference": ["sports", "tournaments"],
    },
)

_METABET = SourceCapability(
    source="metabet",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["markets", "instruments"],
        "reference": ["sports", "markets_list"],
    },
)

# ---------------------------------------------------------------------------
# Sports reference data (5)
# ---------------------------------------------------------------------------

_API_FOOTBALL = SourceCapability(
    source="api_football",
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
        "market": ["fixtures", "odds", "predictions"],
        "reference": ["leagues", "teams", "players", "venues", "standings"],
    },
)

_FOOTYSTATS = SourceCapability(
    source="footystats",
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
        "market": ["matches", "odds"],
        "reference": ["leagues", "teams", "players", "standings"],
    },
)

_SOCCER_FOOTBALL_INFO = SourceCapability(
    source="soccer_football_info",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "reference": ["fixtures", "teams", "leagues", "players", "referees", "venues"],
    },
)

_TRANSFERMARKT = SourceCapability(
    source="transfermarkt",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "reference": ["players", "teams", "transfers", "market_values"],
    },
)

_UNDERSTAT = SourceCapability(
    source="understat",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "reference": ["fixtures", "teams", "leagues", "players", "xg_stats"],
    },
)

_SHARPAPI = SourceCapability(
    source="sharpapi",
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
        "market": ["odds", "markets"],
        "reference": ["sports", "leagues"],
    },
)

# ---------------------------------------------------------------------------
# TradFi (6)
# ---------------------------------------------------------------------------

_IBKR = SourceCapability(
    source="ibkr",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "paper_account", "prod": "live_account"},
    operations={
        "market": ["market_data", "historical_data", "realtime_bars", "scanner", "ws_market_data"],
        "execution": ["place_order", "cancel_order", "modify_order", "open_orders", "executions"],
        "position": ["portfolio", "positions", "account_summary", "pnl"],
        "reference": ["contract_details", "matching_symbols", "market_rules"],
    },
)

_DATABENTO = SourceCapability(
    source="databento",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["mbp_1", "mbp_10", "trades", "ohlcv", "tbbo", "imbalance", "statistics"],
        "reference": ["symbology", "datasets", "metadata", "publishers"],
    },
)

_FRED = SourceCapability(
    source="fred",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "reference": ["series", "observations", "releases", "categories", "tags", "sources"],
    },
)

_POLYGON = SourceCapability(
    source="polygon",
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
        "market": ["aggregates", "trades", "quotes", "last_trade", "last_quote", "snapshot", "ws_trades", "ws_quotes"],
        "reference": ["tickers", "ticker_details", "exchanges", "conditions", "dividends", "splits"],
    },
)

_BARCHART = SourceCapability(
    source="barchart",
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
        "market": ["ohlcv", "quotes", "dividends", "earnings"],
        "reference": ["symbols", "sectors", "indices"],
    },
)

_YAHOO_FINANCE = SourceCapability(
    source="yahoo_finance",
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
        "market": ["ohlcv", "options_chain", "streaming_quotes"],
        "reference": ["ticker_info", "balance_sheet", "income_statement", "cash_flow"],
    },
)

_ECB = SourceCapability(
    source="ecb",
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
        "market": ["yield_curve"],
        "reference": ["exchange_rates", "interest_rates", "monetary_aggregates"],
    },
)

_OPENBB = SourceCapability(
    source="openbb",
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
        "market": ["bond_data", "yield_curves", "fixed_income"],
        "reference": ["bond_indices", "government_bonds"],
    },
)

_OFR = SourceCapability(
    source="ofr",
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
        "market": ["cds_spreads", "repo_rates"],
        "reference": ["financial_stability_data"],
    },
)

_REGULATORY = SourceCapability(
    source="regulatory",
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
        "market": ["trade_reports"],
        "reference": ["regulatory_filings", "compliance_data"],
    },
)

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
)

_ARKHAM = SourceCapability(
    source="arkham",
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
        "market": ["on_chain_metrics", "whale_alerts", "entity_transfers"],
        "reference": ["entities", "addresses", "exchange_flows"],
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
        "reference": ["gcs_buckets", "compute_instances", "artifact_registry", "cloud_build"],
    },
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
)

# ---------------------------------------------------------------------------
# All declarations (ordered)
# ---------------------------------------------------------------------------

CAPABILITY_DECLARATIONS: list[SourceCapability] = [
    # CeFi exchanges
    _BINANCE,
    _BYBIT,
    _OKX,
    _COINBASE,
    _DERIBIT,
    _HYPERLIQUID,
    _BITFINEX,
    _BITGET,
    _BITSTAMP,
    _KRAKEN,
    _GATEIO,
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
    # DeFi protocols
    _UNISWAP,
    _AAVE,
    _CURVE,
    _DYDX,
    _INSTADAPP,
    # DeFi data / on-chain analytics
    _PYTH,
    _BLOXROUTE,
    _MEV,
    _VERSIFI,
    # Sports / prediction markets
    _BETFAIR,
    _BETDAQ,
    _PINNACLE,
    _KALSHI,
    _POLYMARKET,
    _ODDS_API,
    _ODDS_ENGINE,
    _ODDSJAM,
    _OPTICODDS,
    _MATCHBOOK,
    _SMARKETS,
    _MANIFOLD,
    _PREDICTIT,
    _ONEXBET,
    _METABET,
    # Sports reference data
    _API_FOOTBALL,
    _FOOTYSTATS,
    _SOCCER_FOOTBALL_INFO,
    _TRANSFERMARKT,
    _UNDERSTAT,
    _SHARPAPI,
    # TradFi
    _IBKR,
    _DATABENTO,
    _FRED,
    _POLYGON,
    _BARCHART,
    _YAHOO_FINANCE,
    _ECB,
    _OPENBB,
    _OFR,
    _REGULATORY,
    # Alt data / on-chain analytics
    _ALCHEMY,
    _THEGRAPH,
    _COINGECKO,
    _COINGLASS,
    _GLASSNODE,
    _ARKHAM,
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


def bootstrap_capabilities() -> None:
    """Register all built-in capability declarations."""
    for cap in CAPABILITY_DECLARATIONS:
        register_capability(cap)
