"""Polymarket crypto and macro market tag mappings.

BTC up/down markets (5m to 1d timeframes) and S&P up/down markets
use specific Gamma API tags for runtime discovery. Markets are ephemeral
(created daily/hourly) — no static condition_id lookup tables.

This module provides tag constants and helpers for dynamic resolution.
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
    }
)

# BTC up/down market timeframes available on Polymarket
POLYMARKET_BTC_TIMEFRAMES: tuple[str, ...] = ("5m", "15m", "1h", "4h", "1d")

# S&P up/down timeframes (typically daily close)
POLYMARKET_SPX_TIMEFRAMES: tuple[str, ...] = ("1d",)


def get_polymarket_tags_for_underlying(underlying: str) -> frozenset[str]:
    """Return Gamma API tag slugs to filter markets for a given underlying asset."""
    underlying_to_tags: dict[str, frozenset[str]] = {
        "BTC": frozenset({"bitcoin", "btc", "crypto-prices"}),
        "ETH": frozenset({"ethereum", "eth", "crypto-prices"}),
        "SOL": frozenset({"solana", "crypto-prices"}),
        "SPX": frozenset({"s-and-p-500", "sp500", "stocks"}),
        "FED": frozenset({"fed", "interest-rates"}),
        "CPI": frozenset({"inflation", "economics"}),
        "GDP": frozenset({"gdp", "economics"}),
    }
    return underlying_to_tags.get(underlying.upper(), frozenset())
