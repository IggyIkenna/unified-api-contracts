"""CeFi exchanges, aggregators, and FIX protocol capability declarations."""

from __future__ import annotations

from ..capability import SourceCapability

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
]
