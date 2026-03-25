"""Polymarket crypto and macro market tag mappings.

BTC up/down markets (5m to monthly timeframes), S&P/NDX/DJIA up/down markets,
commodity up/down (crude oil, gold, silver), and forex up/down (EUR/USD, GBP/USD,
USD/JPY) use specific Gamma API series slugs for runtime discovery. Markets are
ephemeral (created daily/hourly) — no static condition_id lookup tables.

This module provides tag constants, slug patterns, and helpers for dynamic resolution.
"""

from __future__ import annotations

POLYMARKET_CRYPTO_TAG_SLUGS: frozenset[str] = frozenset(
    {
        "crypto",
        "bitcoin",
        "btc",
        "ethereum",
        "eth",
        "solana",
        "crypto-prices",
        "xrp",
        "dogecoin",
        "bnb",
        "hyperliquid",
    }
)

POLYMARKET_MACRO_TAG_SLUGS: frozenset[str] = frozenset(
    {
        "economics",
        "finance",
        "stocks",
        "s-and-p-500",
        "sp500",
        "fed",
        "interest-rates",
        "inflation",
        "gdp",
        "treasury",
        "crude-oil",
        "gold",
        "silver",
        "forex",
    }
)

# ---------------------------------------------------------------------------
# Timeframes by underlying (from Polymarket series discovery)
# ---------------------------------------------------------------------------

POLYMARKET_TIMEFRAMES: dict[str, tuple[str, ...]] = {
    # Crypto
    "BTC": ("5m", "15m", "1h", "4h", "1d", "1w", "1M"),
    "ETH": ("5m", "15m", "1h", "4h", "1d", "1w", "1M"),
    "SOL": ("5m", "15m", "1h", "4h", "1d"),
    "XRP": ("5m", "15m", "1h", "4h", "1w"),
    "DOGE": ("5m", "15m", "1d", "1M"),
    "BNB": ("5m", "15m", "4h", "1d"),
    "HYPE": ("5m", "15m", "1h", "4h", "1d"),
    # Equity indices
    "SPX": ("1d", "1M"),
    "NDX": ("1d", "1M"),
    "DJIA": ("1d",),
    "DAX": ("1d",),
    "HANG_SENG": ("1d",),
    "RUSSELL_2000": ("1d",),
    # Commodities
    "CRUDE_OIL": ("1d",),
    "GOLD": ("1d",),
    "SILVER": ("1d",),
    # Forex
    "GBPUSD": ("1d",),
    "EURUSD": ("1d",),
    "USDJPY": ("1d",),
    "USDKRW": ("1d",),
}

# Backwards-compatible aliases
POLYMARKET_BTC_TIMEFRAMES: tuple[str, ...] = POLYMARKET_TIMEFRAMES["BTC"]
POLYMARKET_SPX_TIMEFRAMES: tuple[str, ...] = POLYMARKET_TIMEFRAMES["SPX"]

# ---------------------------------------------------------------------------
# Slug patterns for runtime market discovery via Gamma API
# ---------------------------------------------------------------------------

POLYMARKET_SLUG_PATTERNS: dict[str, list[str]] = {
    # Crypto 5m: "btc-updown-5m-{unix_ts}"
    "BTC_5M": ["btc-updown-5m-"],
    "BTC_15M": ["btc-updown-15m-"],
    "BTC_HOURLY": ["bitcoin-up-or-down-"],
    "BTC_4H": ["bitcoin-up-or-down-4h"],
    "BTC_DAILY": ["btc-up-or-down-daily"],
    "BTC_WEEKLY": ["bitcoin-up-or-down-weekly"],
    "ETH_5M": ["eth-updown-5m-"],
    "ETH_15M": ["eth-up-or-down-15m"],
    "ETH_HOURLY": ["eth-up-or-down-hourly"],
    "SOL_5M": ["sol-updown-5m-"],
    "SOL_HOURLY": ["solana-up-or-down-hourly"],
    "XRP_5M": ["xrp-updown-5m-"],
    "DOGE_5M": ["doge-updown-5m-"],
    "BNB_5M": ["bnb-updown-5m-"],
    "HYPE_5M": ["hype-updown-5m-"],
    # Equity indices
    "SPX_DAILY": ["spx-daily-up-or-down", "spx-open-daily-up-or-down"],
    "SPX_MONTHLY": ["spx-hit-price-monthly", "sp-500-monthly-hit"],
    "NDX_DAILY": ["ndx-daily-up-or-down"],
    "DJIA_DAILY": ["dow-jones-daily-up-or-down"],
    "DAX_DAILY": ["dax-daily-up-or-down"],
    "HANG_SENG_DAILY": ["hang-seng-daily-up-or-down"],
    "RUSSELL_DAILY": ["russell-2000-daily-up-or-down"],
    # Commodities
    "CRUDE_OIL_DAILY": ["oil-daily-up-or-down", "crude-oil-cl-up-or-down"],
    "GOLD_DAILY": ["gold-daily-up-or-down"],
    "SILVER_DAILY": ["silver-daily-up-or-down"],
    # Forex
    "GBPUSD_DAILY": ["gbpusd-daily-up-or-down", "gbpusd-up-or-down-daily"],
    "EURUSD_DAILY": ["eurusd-daily-up-or-down", "eurusd-up-or-down-daily"],
    "USDJPY_DAILY": ["usdjpy-daily-up-or-down"],
    "USDKRW_DAILY": ["usdkrw-up-or-down-daily"],
}

# ---------------------------------------------------------------------------
# Series slugs for Gamma API series-based discovery
# ---------------------------------------------------------------------------

POLYMARKET_SERIES_SLUGS: dict[str, list[str]] = {
    "BTC": [
        "btc-up-or-down-hourly",
        "btc-up-or-down-daily",
        "btc-up-or-down-4h",
        "bitcoin-up-or-down-4h",
        "bitcoin-up-or-down-weekly",
        "bitcoin-hit-price-monthly",
        "bitcoin-hit-price-weekly",
        "bitcoin-neg-risk-weekly",
        "btc-multi-strikes-weekly",
    ],
    "ETH": [
        "eth-up-or-down-hourly",
        "eth-up-or-down-daily",
        "eth-up-or-down-15m",
        "eth-up-or-down-monthly",
        "ethereum-up-or-down-4h",
        "ethereum-up-or-down-weekly",
        "ethereum-hit-price-monthly",
        "ethereum-neg-risk-weekly",
        "ethereum-multi-strikes-weekly",
    ],
    "SOL": [
        "solana-up-or-down-hourly",
        "solana-up-or-down-4h",
        "solana-hit-price-monthly",
        "solana-neg-risk-weekly",
        "sol-up-or-down-4h",
    ],
    "XRP": [
        "xrp-up-or-down-hourly",
        "xrp-up-or-down-4h",
        "xrp-hit-price-monthly",
        "xrp-neg-risk-weekly",
        "xrp-multi-strikes-weekly",
    ],
    "DOGE": [
        "doge-up-or-down-15m",
        "doge-up-or-down-5m",
        "dogecoin-hit-price-monthly",
        "dogecoin-up-or-down-daily",
    ],
    "BNB": [
        "bnb-up-or-down-5m",
        "bnb-up-or-down-15m",
        "bnb-up-or-down-4h",
        "bnb-up-or-down-daily",
        "bnb-hit-price-monthly",
    ],
    "HYPE": [
        "hype-up-or-down-5m",
        "hype-up-or-down-15m",
        "hype-up-or-down-hourly",
        "hype-up-or-down-4h",
        "hype-up-or-down-daily",
        "hyperliquid-hit-price-monthly",
        "hyperliquid-up-or-down-daily",
    ],
    "SPX": [
        "spx-daily-up-or-down",
        "spx-open-daily-up-or-down",
        "spx-hit-price-monthly",
        "spx-multi-strikes-weekly",
        "sp-500-monthly-hit",
        "sp-500-monthly-ou",
        "sp-500-monthly-close-negrisk",
        "spy-daily-up-or-down",
    ],
    "NDX": [
        "ndx-daily-up-or-down",
        "ndx-hit-price-monthly",
        "ndx-multi-strikes-weekly",
    ],
    "DJIA": ["dow-jones-daily-up-or-down"],
    "DAX": ["dax-daily-up-or-down"],
    "HANG_SENG": ["hang-seng-daily-up-or-down"],
    "RUSSELL_2000": ["russell-2000-daily-up-or-down"],
    "CRUDE_OIL": [
        "oil-daily-up-or-down",
        "crude-oil-cl-up-or-down",
        "crude-oil-cl-hit",
        "crude-oil-cl-settle",
        "nymex-crude-oil-futures-wti-daily-up-or-down",
        "ice-brent-crude-oil-futures-daily-up-or-down",
    ],
    "GOLD": [
        "gold-daily-up-or-down",
        "what-will-gold-gc-hit",
        "what-will-gold-gc-settle-at",
        "comex-gold-futures-daily-up-or-down",
    ],
    "SILVER": [
        "silver-daily-up-or-down",
        "will-silver-si-hit",
        "what-will-silver-si-settle-at",
        "silver-hit-price-weekly",
    ],
    "GBPUSD": ["gbpusd-daily-up-or-down", "gbpusd-up-or-down-daily"],
    "EURUSD": ["eurusd-daily-up-or-down", "eurusd-up-or-down-daily", "eurusd-hit-price-weekly"],
    "USDJPY": ["usdjpy-daily-up-or-down"],
    "USDKRW": ["usdkrw-up-or-down-daily", "usdkrw-hit-price-weekly"],
}

# All supported underlyings
ALL_PREDICTION_UNDERLYINGS: frozenset[str] = frozenset(POLYMARKET_TIMEFRAMES.keys())


def get_polymarket_tags_for_underlying(underlying: str) -> frozenset[str]:
    """Return Gamma API tag slugs to filter markets for a given underlying asset."""
    underlying_to_tags: dict[str, frozenset[str]] = {
        "BTC": frozenset({"bitcoin", "btc", "crypto-prices"}),
        "ETH": frozenset({"ethereum", "eth", "crypto-prices"}),
        "SOL": frozenset({"solana", "crypto-prices"}),
        "XRP": frozenset({"xrp", "crypto-prices"}),
        "DOGE": frozenset({"dogecoin", "crypto-prices"}),
        "BNB": frozenset({"bnb", "crypto-prices"}),
        "HYPE": frozenset({"hyperliquid", "crypto-prices"}),
        "SPX": frozenset({"s-and-p-500", "sp500", "stocks"}),
        "NDX": frozenset({"stocks"}),
        "DJIA": frozenset({"stocks"}),
        "DAX": frozenset({"stocks"}),
        "HANG_SENG": frozenset({"stocks"}),
        "RUSSELL_2000": frozenset({"stocks"}),
        "CRUDE_OIL": frozenset({"crude-oil", "finance"}),
        "GOLD": frozenset({"gold", "finance"}),
        "SILVER": frozenset({"silver", "finance"}),
        "GBPUSD": frozenset({"forex", "finance"}),
        "EURUSD": frozenset({"forex", "finance"}),
        "USDJPY": frozenset({"forex", "finance"}),
        "USDKRW": frozenset({"forex", "finance"}),
        "FED": frozenset({"fed", "interest-rates"}),
        "CPI": frozenset({"inflation", "economics"}),
        "GDP": frozenset({"gdp", "economics"}),
    }
    return underlying_to_tags.get(underlying.upper(), frozenset())
