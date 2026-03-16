"""DeFi protocol and on-chain analytics capability declarations."""

from __future__ import annotations

from ..capability import SourceCapability

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
    _PYTH,
    _BLOXROUTE,
    _MEV,
    _VERSIFI,
]
