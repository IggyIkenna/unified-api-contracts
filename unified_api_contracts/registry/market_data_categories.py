"""Market data category reference data (SSOT).

Canonical data types, venues, and timeframes organized by market category.
Used by market-data-processing-service, features-delta-one-service, and
other data pipeline services.

Previously hardcoded in market-data-processing-service/config.py with
comment 'NOTE: Keep in sync with unified-trading-deployment-v2/configs/venues.yaml'.
Centralized here as the system SSOT per UAC registry pattern.
"""

from __future__ import annotations

# Default timeframes for candle processing (used by sharding and CLI)
TIMEFRAMES: list[str] = ["15s", "1m", "5m", "15m", "1h", "4h", "24h"]

# Data types per category
DATA_TYPES_BY_CATEGORY: dict[str, list[str]] = {
    "cefi": [
        "trades",
        "book_snapshot_5",
        "derivative_ticker",
        "liquidations",
        "options_chain",  # Deribit options - LOCF sampled to candles
        "futures_chain",  # Deribit/CME futures - LOCF sampled to candles
    ],
    "tradfi": [
        "trades",
        "ohlcv_1m",  # Databento 1m candles (base timeframe)
        "ohlcv_15m",  # VIX 15m: Barchart CSV (2020-01-07→2021-04-21, discontinued) then Yahoo Finance; KRW rates
        "ohlcv_24h",  # Yahoo Finance daily rates (KRW/USD, etc.)
        "tbbo",  # Top-of-book quotes
    ],
    "defi": [
        # Candle-sampled data types (OHLCV from mid_price):
        "swaps",  # DEX trades - requires candle sampling
        "liquidity",  # Pool liquidity depth - OHLCV from mid_price
        # Pass-through data types (already in sampled form from upstream):
        "rate_indices",  # Funding rates, interest rates
        "oracle_prices",  # Chainlink oracle prices
        "utilization",  # AAVE/Morpho utilization rates
        "yields",  # LST yields (EtherFi, Lido)
        "rewards",  # Protocol reward emissions (pass-through, OHLCV=NaN)
        "risk_params",  # Protocol risk parameters (pass-through, OHLCV=NaN)
    ],
    "sports": [
        "odds_snapshot",  # Point-in-time bookmaker odds (LOCF sampled)
        "odds_movement",  # Odds line movement OHLC candles
        "arbitrage_opportunity",  # Cross-bookmaker arbitrage detection
    ],
    "prediction": [
        "prediction_trades",  # CLOB trade fills (price, size, side, timestamp)
        "prediction_book_snapshot",  # Order book snapshot (bids/asks)
        "prediction_market_metadata",  # Market metadata (question, outcomes, status)
    ],
}

# Venues per category
VENUES_BY_CATEGORY: dict[str, list[str]] = {
    "cefi": [
        # Centralized exchanges (Tardis API)
        "BINANCE-SPOT",
        "BINANCE-FUTURES",
        "BYBIT",
        "OKX",
        "DERIBIT",
        "UPBIT",
        "COINBASE",
        # On-chain CLOBs (reclassified from DEFI - CLOB-style data like CeFi)
        "HYPERLIQUID",
        "ASTER",
    ],
    "tradfi": [
        # Databento venues
        "NASDAQ",
        "NYSE",
        "CME",
        "ICE",
        "CBOE",
        # External data providers
        "FX",  # FX rates (KRW/USD via Yahoo Finance data provider)
        "BARCHART",  # VIX 15m historical: 2020-01-02→2025-11-12 (CSV download, discontinued; pre-loaded to GCS)
        "YAHOO_FINANCE",  # VIX 15m ongoing: rolling 60-day window; KRW/USD daily rates
    ],
    "defi": [
        # --- DEX protocols (swaps + liquidity) ---
        "UNISWAPV2-ETHEREUM",
        "UNISWAPV3-ETHEREUM",
        "UNISWAPV3-ARBITRUM",
        "UNISWAPV3-BASE",
        "UNISWAPV3-OPTIMISM",
        "UNISWAPV3-POLYGON",
        "UNISWAPV4-ETHEREUM",
        "CURVE-ETHEREUM",
        "CURVE-AVALANCHE",
        "CURVE-OPTIMISM",
        "BALANCER-ETHEREUM",
        "BALANCER-ARBITRUM",
        "BALANCER-AVALANCHE",
        "BALANCER-BASE",
        "BALANCER-OPTIMISM",
        "BALANCER-POLYGON",
        # --- Lending protocols ---
        "AAVEV3-ETHEREUM",
        "AAVEV3-ARBITRUM",
        "AAVEV3-AVALANCHE",
        "AAVEV3-BASE",
        "AAVEV3-BSC",
        "AAVEV3-LINEA",
        "AAVEV3-OPTIMISM",
        "AAVEV3-POLYGON",
        "AAVEV3-SCROLL",
        "AAVEV3-ZKSYNC",
        "COMPOUNDV3-ETHEREUM",
        "COMPOUNDV3-ARBITRUM",
        "COMPOUNDV3-BASE",
        "COMPOUNDV3-OPTIMISM",
        "COMPOUNDV3-POLYGON",
        "COMPOUNDV3-SCROLL",
        "MORPHO-ETHEREUM",
        "MORPHO-ARBITRUM",
        "MORPHO-BASE",
        "MORPHO-OPTIMISM",
        "MORPHO-POLYGON",
        "MORPHO-SCROLL",
        "EULER-ETHEREUM",
        "FLUID-ETHEREUM",
        # --- LST/Yield protocols ---
        "LIDO-ETHEREUM",
        "ETHERFI-ETHEREUM",
        "ETHENA-ETHEREUM",
    ],
    "sports": [
        # Sports betting exchanges and bookmakers
        "PINNACLE",
        "BETFAIR",
        "DRAFTKINGS",
        "FANDUEL",
        "BET365",
    ],
    "prediction": [
        # Prediction markets (binary / multi-outcome)
        "POLYMARKET",
        "KALSHI",
    ],
}

# All supported data types (union of all categories)
ALL_DATA_TYPES: list[str] = sorted({dt for dts in DATA_TYPES_BY_CATEGORY.values() for dt in dts})

# All supported venues (union of all categories)
ALL_VENUES: list[str] = sorted({v for vs in VENUES_BY_CATEGORY.values() for v in vs})


# --- Venue → Category reverse lookup ---

VENUE_TO_CATEGORY: dict[str, str] = {venue: cat for cat, venues in VENUES_BY_CATEGORY.items() for venue in venues}


# --- Feature-group → data_type mappings (SSOT for all feature services) ---
# Previously hardcoded in features-delta-one-service orchestrator.

FEATURE_GROUP_DATA_TYPES: dict[str, str] = {
    # Default (CEFI) — most feature groups use trades
    "technical_indicators": "trades",
    "moving_averages": "trades",
    "oscillators": "trades",
    "volatility_realized": "trades",
    "momentum": "trades",
    "volume_analysis": "trades",
    "vwap": "trades",
    "candlestick_patterns": "trades",
    "market_structure": "trades",
    "returns": "trades",
    "round_numbers": "trades",
    "streaks": "trades",
    "microstructure": "book_snapshot_5",
    "funding_oi": "derivative_ticker",
    "liquidations": "liquidations",
    "futures_basis": "trades",
    "volume_flow": "trades",
    "temporal": "trades",
    "economic_events": "trades",
    "targets": "trades",
    # S/R level system feature groups
    "supply_demand_zones": "trades",
    "fibonacci": "trades",
    "level_confluence": "trades",
    "market_structure_sequence": "trades",
    # ML feature enhancement
    "risk_reward": "trades",
    "wedge_quality": "trades",
}

# Category-specific overrides (applied on top of FEATURE_GROUP_DATA_TYPES)
FEATURE_GROUP_DATA_TYPE_OVERRIDES: dict[str, dict[str, str]] = {
    "tradfi": {
        "microstructure": "tbbo",  # Top of Book for TradFi equities
    },
    "defi": {
        "technical_indicators": "oracle_prices",
        "moving_averages": "oracle_prices",
        "oscillators": "oracle_prices",
        "volatility_realized": "oracle_prices",
        "momentum": "oracle_prices",
        "volume_analysis": "swaps",
        "vwap": "swaps",
        "candlestick_patterns": "oracle_prices",
        "market_structure": "oracle_prices",
        "returns": "oracle_prices",
        "round_numbers": "oracle_prices",
        "streaks": "oracle_prices",
        "microstructure": "swaps",
        "funding_oi": "derivative_ticker",
        "liquidations": "derivative_ticker",
        "temporal": "oracle_prices",
        "economic_events": "oracle_prices",
        "targets": "oracle_prices",
    },
}


def resolve_data_type_for_feature_group(feature_group: str, category: str) -> str:
    """Resolve the correct data type for a feature group in a given category.

    Uses FEATURE_GROUP_DATA_TYPES as base, with per-category overrides.
    This is the SSOT — services should not hardcode data type mappings.
    """
    cat_lower = category.lower()
    overrides = FEATURE_GROUP_DATA_TYPE_OVERRIDES.get(cat_lower, {})
    if feature_group in overrides:
        return overrides[feature_group]
    return FEATURE_GROUP_DATA_TYPES.get(feature_group, "trades")


def get_valid_data_types_for_venue(venue: str) -> list[str]:
    """Return the valid data types for a venue based on its category.

    Looks up the venue's category, then returns the data types for that category.
    """
    cat = VENUE_TO_CATEGORY.get(venue, "")
    return DATA_TYPES_BY_CATEGORY.get(cat, [])


def validate_data_type_for_venue(venue: str, data_type: str) -> bool:
    """Check if a data type is valid for a venue.

    Returns True if the data type is in the venue's category's allowed data types.
    Returns True for unknown venues (permissive — validation is advisory).
    """
    valid = get_valid_data_types_for_venue(venue)
    if not valid:
        return True  # Unknown venue — don't block
    return data_type in valid
