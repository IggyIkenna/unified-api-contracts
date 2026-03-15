"""Capability declarations for the top 20 external data sources.

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
# CeFi exchanges (6)
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

# ---------------------------------------------------------------------------
# Sports / prediction markets (4)
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

# ---------------------------------------------------------------------------
# TradFi (4)
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

# ---------------------------------------------------------------------------
# DeFi (3)
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

# ---------------------------------------------------------------------------
# Alt data (3)
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

# ---------------------------------------------------------------------------
# All declarations (ordered)
# ---------------------------------------------------------------------------

CAPABILITY_DECLARATIONS: list[SourceCapability] = [
    # CeFi
    _BINANCE,
    _BYBIT,
    _OKX,
    _COINBASE,
    _DERIBIT,
    _HYPERLIQUID,
    # Sports
    _BETFAIR,
    _PINNACLE,
    _KALSHI,
    _POLYMARKET,
    # TradFi
    _IBKR,
    _DATABENTO,
    _FRED,
    _POLYGON,
    # DeFi
    _UNISWAP,
    _AAVE,
    _CURVE,
    # Alt data
    _ALCHEMY,
    _THEGRAPH,
    _COINGECKO,
]


def bootstrap_capabilities() -> None:
    """Register all built-in capability declarations."""
    for cap in CAPABILITY_DECLARATIONS:
        register_capability(cap)
