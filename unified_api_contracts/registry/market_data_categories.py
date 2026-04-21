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

# Base (native) granularity per data type — the finest meaningful timeframe
# that can be produced from the raw source data for each data type.
# Tick-level data (trades, book snapshots) → 15s base.
# Pre-aggregated OHLCV → native period is the base.
# DeFi on-chain data → depends on block time; 15m is safe default for ETH (~12s blocks).
# Sports odds → horizon-based buckets, not standard timeframes.
BASE_GRANULARITY_BY_DATA_TYPE: dict[str, str] = {
    # CeFi — tick-level from Tardis
    "trades": "15s",
    "book_snapshot_5": "15s",
    "derivative_ticker": "15s",
    "liquidations": "15s",
    "options_chain": "15s",
    "futures_chain": "15s",
    # TradFi — pre-aggregated candles
    "ohlcv_1m": "1m",
    "ohlcv_15m": "15m",
    "ohlcv_24h": "24h",
    "tbbo": "15s",
    # DeFi — on-chain sampled (ETH ~12s blocks → 15m safe default)
    # Note: "liquidations" already declared in CeFi section above (same 15s granularity)
    "dex_pools": "15m",
    "dex_swaps": "15s",
    "lending_indices": "15m",
    "perp_funding": "15m",
    "lst_rates": "15m",
    "oracle_prices": "15m",
    "gas_fees": "15m",
    "rewards": "24h",
    "risk_params": "24h",
    # Sports — horizon-based, not standard timeframes
    "odds_snapshot": "15m",
    "odds_movement": "15m",
    "arbitrage_opportunity": "15m",
    # Prediction — tick-level from CLOB (uses canonical "trades" / "book_snapshot_5",
    # aligned with CeFi; no category-specific data_type names).
}

# Timeframe ordering in seconds (used for validation and aggregation)
TIMEFRAME_SECONDS: dict[str, int] = {
    "15s": 15,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "24h": 86400,
}


def get_valid_timeframes_for_data_type(data_type: str) -> list[str]:
    """Return the list of valid output timeframes for a data type.

    Only timeframes >= the base granularity are valid. Requesting 15s candles
    from ohlcv_15m source data would produce NaN-filled garbage.
    """
    base = BASE_GRANULARITY_BY_DATA_TYPE.get(data_type)
    if base is None:
        return list(TIMEFRAMES)  # Unknown data type — allow all
    base_seconds = TIMEFRAME_SECONDS.get(base, 0)
    return [tf for tf in TIMEFRAMES if TIMEFRAME_SECONDS.get(tf, 0) >= base_seconds]


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
        "dex_pools",  # DEX pool metrics (TVL, liquidity depth)
        "dex_swaps",  # DEX swap events (requires candle sampling)
        "lending_indices",  # Lending rate indices (supply/borrow APY, utilization)
        "liquidations",  # DeFi liquidation events
        "perp_funding",  # Perpetual funding rates (Hyperliquid, Aster, GMX)
        "lst_rates",  # Liquid staking token exchange rates
        "oracle_prices",  # Chainlink oracle price snapshots
        "gas_fees",  # EVM gas fee history
        "rewards",  # Protocol reward emissions (pass-through, OHLCV=NaN)
        "risk_params",  # Protocol risk parameters (pass-through, OHLCV=NaN)
    ],
    "sports": [
        "odds",  # Raw bookmaker odds from Odds API (MTDS raw tick data)
        "odds_snapshot",  # Point-in-time bookmaker odds (LOCF sampled)
        "odds_movement",  # Odds line movement OHLC candles
        "arbitrage_opportunity",  # Cross-bookmaker arbitrage detection
    ],
    "prediction": [
        # Canonical names — aligned with CeFi. Prediction markets are CLOBs so the
        # "trades" + "book_snapshot_5" taxonomy would apply uniformly. Legacy
        # "prediction_trades" / "prediction_book_snapshot" names retired 2026-04-19.
        # NOTE: book_snapshot_5 removed 2026-04-19 alongside the POLYMARKET +
        # KALSHI venue-capability trim — we don't currently capture CLOB order
        # book snapshots from either venue, and leaving it here phantom-
        # inflated the MTDS PREDICTION completion_pct denominator (35k vs
        # 5.7k observed shards). Re-add if a prediction adapter grows book
        # snapshot collection.
        "trades",  # CLOB trade fills (price, size, side, timestamp)
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
        "COMPOUNDV3-ETHEREUM",
        "COMPOUNDV3-ARBITRUM",
        "COMPOUNDV3-BASE",
        "COMPOUNDV3-OPTIMISM",
        "COMPOUNDV3-POLYGON",
        "MORPHO-ETHEREUM",
        "MORPHO-ARBITRUM",
        "MORPHO-BASE",
        "MORPHO-OPTIMISM",
        "MORPHO-POLYGON",
        "FLUID-ETHEREUM",
        # --- LST/Yield protocols ---
        "LIDO-ETHEREUM",
        "ETHERFI-ETHEREUM",
        "ETHENA-ETHEREUM",
        "JITO-SOLANA",
    ],
    "sports": [
        # Sports betting exchanges and bookmakers
        "ODDS_API",  # Multi-bookmaker odds aggregator (raw tick data source)
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


# --- Candle processing classification ---
# True = MDPS should process this data type through a candle adapter.
# False = bypass (pre-bucketed data written directly by MTDS, no OHLCV conversion needed).
NEEDS_CANDLE_PROCESSING: dict[str, bool] = {
    # CeFi — all need candle processing from raw ticks
    "trades": True,
    "book_snapshot_5": True,
    "derivative_ticker": True,
    "liquidations": True,
    "options_chain": True,
    "futures_chain": True,
    # TradFi — pre-aggregated but still processed (timeframe re-aggregation)
    "ohlcv_1m": True,
    "ohlcv_15m": True,
    "ohlcv_24h": True,
    "tbbo": True,
    # DeFi — candle-sampled types need processing; pass-through types do not
    "dex_pools": False,
    "dex_swaps": True,
    "lending_indices": False,
    # Note: "liquidations" already declared in CeFi section above (True — same for DeFi)
    "perp_funding": False,
    "lst_rates": False,
    "oracle_prices": False,
    "gas_fees": False,
    "rewards": False,
    "risk_params": False,
    # Sports — candle adapters process these
    "odds": False,  # Raw tick data, not directly processed (bucket adapter handles)
    "odds_snapshot": True,
    "odds_movement": True,
    "arbitrage_opportunity": True,
    # Prediction — uses canonical "trades" / "book_snapshot_5" (same keys as CeFi).
}


def needs_candle_processing(data_type: str) -> bool:
    """Return True if the data type requires MDPS candle adapter processing.

    Data types not in NEEDS_CANDLE_PROCESSING default to True (process by default).
    """
    return NEEDS_CANDLE_PROCESSING.get(data_type, True)


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
        "volume_analysis": "dex_swaps",
        "vwap": "dex_swaps",
        "candlestick_patterns": "oracle_prices",
        "market_structure": "oracle_prices",
        "returns": "oracle_prices",
        "round_numbers": "oracle_prices",
        "streaks": "oracle_prices",
        "microstructure": "dex_swaps",
        "funding_oi": "perp_funding",
        "liquidations": "liquidations",
        "temporal": "oracle_prices",
        "economic_events": "oracle_prices",
        "targets": "oracle_prices",
    },
    # "prediction": no overrides needed — prediction markets use "trades" (same as CeFi)
    # for all delta-one feature groups, and the default FEATURE_GROUP_DATA_TYPES already
    # maps them to "trades". Aligning with CeFi per single-source-of-truth rule.
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


# --- Per-venue data type capabilities with start dates ---
# SSOT for which data types each venue can produce and when that capability started.
# Used by MTDS for shard-level skip logic and deployment UI for multi-dimensional status.
#
# Structure: {venue: {data_type: start_date_YYYY_MM_DD}}
# Default rule: if a venue is NOT in this dict, fall back to category-level
# DATA_TYPES_BY_CATEGORY with VenueMapping.venue_start_dates as the start date.
# Only venues with non-default data type availability need explicit entries.
#
# ── MVP Data Type Overrides ──
# In MVP mode, we limit downloads to reduce cost and API calls.
# Key decision: Deribit options — only download options_chain (IV/greeks, bulk 1-call)
# not trades/book_snapshot_5/derivative_ticker/liquidations per individual option strike
# (~12,000 API calls/day → 1 call/day). Full tick data for individual options is
# only needed for execution quality analysis, not for strategy/ML.
# Perpetuals still get all data types (trades, book, deriv_ticker, liquidations).

MVP_VENUE_DATA_TYPES: dict[str, list[str]] = {
    # Deribit: perpetual data types + only bulk-downloadable chain types (no per-strike tick data)
    "DERIBIT": ["trades", "book_snapshot_5", "derivative_ticker", "liquidations", "options_chain", "futures_chain"],
    # For other CeFi venues, perpetuals get all data types (same as full mode)
    # TradFi: controlled by tick_windows + MVP_CME_EXCHANGE_CODES (ES-only)
}

# Deribit MVP: which instrument types get which data types.
# Options/futures only get chain data types (bulk download).
# Perpetuals get all data types (per-symbol download, but only ~20 perps).
DERIBIT_MVP_INSTRUMENT_TYPE_DATA_TYPES: dict[str, list[str]] = {
    "perpetual": ["trades", "book_snapshot_5", "derivative_ticker", "liquidations"],
    "options_chain": ["options_chain"],  # Bulk only — no per-strike trades/book
    "futures_chain": ["futures_chain"],  # Bulk only — no per-contract trades/book
}


# Override entries needed when:
# - A venue's data type started later than the venue itself (e.g. Deribit options added later)
# - A venue only supports a subset of its category's data types (e.g. CBOE has ohlcv_15m only)
# - A data type has a different start date per venue (e.g. TradFi venues)

VENUE_DATA_TYPE_CAPABILITIES: dict[str, dict[str, str]] = {
    # ── CeFi — Tardis exchanges ──
    # Most CeFi venues support all cefi data types from their launch date.
    # Exceptions: only DERIBIT has options_chain/futures_chain.
    # HYPERLIQUID/ASTER: perpetual-focused, no options/futures chain.
    "BINANCE-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "BINANCE-FUTURES": {
        "trades": "2019-11-17",
        "book_snapshot_5": "2019-11-17",
        "derivative_ticker": "2019-11-17",
        "liquidations": "2019-11-17",
        "futures_chain": "2019-11-17",
    },
    "DERIBIT": {
        "trades": "2019-03-30",
        "book_snapshot_5": "2019-03-30",
        "derivative_ticker": "2019-03-30",
        "liquidations": "2019-03-30",
        "options_chain": "2019-03-30",
        "futures_chain": "2019-03-30",
    },
    "BYBIT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
        "futures_chain": "2020-01-01",
    },
    "OKX": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
    },
    # Canonical suffixed variants (VenueMapping.tardis_to_venue returns
    # these forms — OKX-SPOT/OKX-FUTURES/OKX-SWAP — to disambiguate market
    # types). Bare "OKX" kept above for execution-context / client-config
    # callers that don't split by market. MTDS per-venue lookups hit the
    # suffixed form.
    "OKX-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "OKX-FUTURES": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
    },
    "OKX-SWAP": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
        "derivative_ticker": "2020-01-01",
        "liquidations": "2020-01-01",
    },
    "UPBIT": {
        "trades": "2021-03-03",
        "book_snapshot_5": "2021-03-03",
    },
    "COINBASE": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "COINBASE-SPOT": {
        "trades": "2020-01-01",
        "book_snapshot_5": "2020-01-01",
    },
    "HYPERLIQUID": {
        "trades": "2023-11-01",
        "book_snapshot_5": "2023-11-01",
        "derivative_ticker": "2023-11-01",
        "liquidations": "2023-11-01",
    },
    "ASTER": {
        "trades": "2024-10-01",
        "book_snapshot_5": "2024-10-01",
        "derivative_ticker": "2024-10-01",
        "liquidations": "2024-10-01",
    },
    # ── TradFi — Databento + external providers ──
    # Each TradFi venue has specific data types and start dates.
    "NASDAQ": {
        "trades": "2023-04-15",
        "ohlcv_1m": "2023-04-15",
        "tbbo": "2023-04-15",
    },
    "NYSE": {
        "trades": "2023-04-15",
        "ohlcv_1m": "2023-04-15",
        "tbbo": "2023-04-15",
    },
    "CME": {
        "trades": "2020-01-01",
        "ohlcv_1m": "2020-01-01",
        "tbbo": "2020-01-01",
    },
    "ICE": {
        "trades": "2020-01-01",
        "ohlcv_1m": "2020-01-01",
        "tbbo": "2020-01-01",
    },
    "CBOE": {
        "ohlcv_15m": "2020-01-07",  # VIX — Barchart CSV start
    },
    "FX": {
        "ohlcv_24h": "2020-01-01",  # KRW/USD daily via Yahoo Finance
    },
    "BARCHART": {
        "ohlcv_15m": "2020-01-02",  # VIX 15m historical CSV (discontinued 2025-11-12)
    },
    "YAHOO_FINANCE": {
        "ohlcv_15m": "2021-04-22",  # VIX 15m rolling 60-day window
        "ohlcv_24h": "2020-01-01",  # KRW/USD daily rates
    },
    # ── DeFi — DEX protocols (dex_swaps + dex_pools) ──
    "UNISWAPV2-ETHEREUM": {"dex_swaps": "2020-05-06", "dex_pools": "2020-05-06"},
    "UNISWAPV3-ETHEREUM": {"dex_swaps": "2021-05-05", "dex_pools": "2021-05-05"},
    "UNISWAPV3-ARBITRUM": {"dex_swaps": "2021-06-18", "dex_pools": "2021-06-18"},
    "UNISWAPV3-BASE": {"dex_swaps": "2023-09-03", "dex_pools": "2023-09-03"},
    "UNISWAPV3-OPTIMISM": {"dex_swaps": "2021-11-12", "dex_pools": "2021-11-12"},
    "UNISWAPV3-POLYGON": {"dex_swaps": "2021-12-22", "dex_pools": "2021-12-22"},
    "UNISWAPV4-ETHEREUM": {"dex_swaps": "2025-01-30", "dex_pools": "2025-01-30"},
    "CURVE-ETHEREUM": {"dex_swaps": "2020-01-20", "dex_pools": "2020-01-20"},
    "CURVE-AVALANCHE": {"dex_swaps": "2021-11-10", "dex_pools": "2021-11-10"},
    "CURVE-OPTIMISM": {"dex_swaps": "2022-01-13", "dex_pools": "2022-01-13"},
    "BALANCER-ETHEREUM": {"dex_swaps": "2021-04-22", "dex_pools": "2021-04-22"},
    "BALANCER-ARBITRUM": {"dex_swaps": "2021-08-27", "dex_pools": "2021-08-27"},
    "BALANCER-AVALANCHE": {"dex_swaps": "2023-08-17", "dex_pools": "2023-08-17"},
    "BALANCER-BASE": {"dex_swaps": "2023-07-29", "dex_pools": "2023-07-29"},
    "BALANCER-OPTIMISM": {"dex_swaps": "2022-05-20", "dex_pools": "2022-05-20"},
    "BALANCER-POLYGON": {"dex_swaps": "2021-06-24", "dex_pools": "2021-06-24"},
    # ── DeFi — Lending protocols ──
    "AAVEV3-ETHEREUM": {
        "lending_indices": "2023-01-27",
        "oracle_prices": "2023-01-27",
        "rewards": "2023-01-27",
        "risk_params": "2023-01-27",
    },
    "AAVEV3-ARBITRUM": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVEV3-AVALANCHE": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVEV3-BASE": {
        "lending_indices": "2023-08-23",
        "oracle_prices": "2023-08-23",
        "rewards": "2023-08-23",
        "risk_params": "2023-08-23",
    },
    "AAVEV3-BSC": {
        "lending_indices": "2024-01-24",
        "oracle_prices": "2024-01-24",
        "rewards": "2024-01-24",
        "risk_params": "2024-01-24",
    },
    "AAVEV3-LINEA": {
        "lending_indices": "2025-02-12",
        "oracle_prices": "2025-02-12",
        "rewards": "2025-02-12",
        "risk_params": "2025-02-12",
    },
    "AAVEV3-OPTIMISM": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "AAVEV3-POLYGON": {
        "lending_indices": "2022-03-12",
        "oracle_prices": "2022-03-12",
        "rewards": "2022-03-12",
        "risk_params": "2022-03-12",
    },
    "COMPOUNDV3-ETHEREUM": {
        "lending_indices": "2022-08-14",
        "oracle_prices": "2022-08-14",
    },
    "COMPOUNDV3-ARBITRUM": {
        "lending_indices": "2023-05-05",
        "oracle_prices": "2023-05-05",
    },
    "COMPOUNDV3-BASE": {
        "lending_indices": "2023-08-20",
        "oracle_prices": "2023-08-20",
    },
    "COMPOUNDV3-OPTIMISM": {
        "lending_indices": "2024-04-07",
        "oracle_prices": "2024-04-07",
    },
    "COMPOUNDV3-POLYGON": {
        "lending_indices": "2024-04-07",
        "oracle_prices": "2024-04-07",
    },
    "MORPHO-ETHEREUM": {
        "lending_indices": "2024-01-08",
        "oracle_prices": "2024-01-08",
    },
    "MORPHO-ARBITRUM": {
        "lending_indices": "2024-06-01",
        "oracle_prices": "2024-06-01",
    },
    "MORPHO-BASE": {
        "lending_indices": "2024-06-01",
        "oracle_prices": "2024-06-01",
    },
    "MORPHO-OPTIMISM": {
        "lending_indices": "2024-06-01",
        "oracle_prices": "2024-06-01",
    },
    "MORPHO-POLYGON": {
        "lending_indices": "2024-06-01",
        "oracle_prices": "2024-06-01",
    },
    "FLUID-ETHEREUM": {
        "lending_indices": "2024-02-27",
        "oracle_prices": "2024-02-27",
    },
    "SPARK-ETHEREUM": {
        "lending_indices": "2024-01-01",
        "oracle_prices": "2024-01-01",
    },
    # ── DeFi — Additional DEX protocols (dex_swaps + dex_pools only) ──
    # Observed populated across sub-dim buckets 2026-04-20.
    "SUSHISWAPV3-ETHEREUM": {"dex_swaps": "2021-11-01", "dex_pools": "2021-11-01"},
    "SUSHISWAPV3-BASE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "SUSHISWAPV3-AVALANCHE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "SUSHISWAP-ARBITRUM": {"dex_swaps": "2021-08-31", "dex_pools": "2021-08-31"},
    "PANCAKESWAPV3-ETHEREUM": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAPV3-ARBITRUM": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAPV3-BASE": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "PANCAKESWAPV3-BSC": {"dex_swaps": "2023-04-12", "dex_pools": "2023-04-12"},
    "PANCAKESWAPV3-ZKSYNC": {"dex_swaps": "2023-08-15", "dex_pools": "2023-08-15"},
    "CAMELOTV3-ARBITRUM": {"dex_swaps": "2023-05-01", "dex_pools": "2023-05-01"},
    "AERODROMEV3-BASE": {"dex_swaps": "2023-08-28", "dex_pools": "2023-08-28"},
    "VELODROMEV2-OPTIMISM": {"dex_swaps": "2022-06-01", "dex_pools": "2022-06-01"},
    "TRADER_JOEV2-AVALANCHE": {"dex_swaps": "2022-01-01", "dex_pools": "2022-01-01"},
    # ── DeFi — Perpetual DEXes (funding + liquidations) ──
    "GMX-ARBITRUM": {
        "perp_funding": "2021-09-01",
        "liquidations": "2021-09-01",
        "oracle_prices": "2021-09-01",
    },
    "GMX-AVALANCHE": {
        "perp_funding": "2021-12-31",
        "liquidations": "2021-12-31",
        "oracle_prices": "2021-12-31",
    },
    # ── DeFi — L2/Alt-chain AAVE + Compound ──
    "AAVEV3-SCROLL": {
        "lending_indices": "2024-07-22",
        "oracle_prices": "2024-07-22",
    },
    "COMPOUNDV3-SCROLL": {
        "lending_indices": "2024-07-22",
        "oracle_prices": "2024-07-22",
    },
    "AAVEV3-ZKSYNC": {
        "lending_indices": "2024-12-12",
        "oracle_prices": "2024-12-12",
    },
    # ── DeFi — Solana ──
    "KAMINO-SOLANA": {
        "lending_indices": "2023-06-01",
        "oracle_prices": "2023-06-01",
    },
    "MARINADE-SOLANA": {"lst_rates": "2021-08-01", "oracle_prices": "2021-08-01"},
    "ORCA-SOLANA": {"dex_swaps": "2021-03-01", "dex_pools": "2021-03-01"},
    "RAYDIUM-SOLANA": {"dex_swaps": "2021-02-21", "dex_pools": "2021-02-21"},
    # ── DeFi — LST/Yield protocols ──
    "LIDO-ETHEREUM": {"lst_rates": "2020-12-18", "oracle_prices": "2020-12-18"},
    "ETHERFI-ETHEREUM": {"lst_rates": "2023-11-01", "oracle_prices": "2023-11-01"},
    "ETHENA-ETHEREUM": {"lst_rates": "2024-02-19", "oracle_prices": "2024-02-19"},
    "JITO-SOLANA": {"lst_rates": "2021-11-01", "oracle_prices": "2021-11-01"},
    # ── Sports ──
    "ODDS_API": {
        "odds_snapshot": "2024-01-01",
        "odds_movement": "2024-01-01",
        "arbitrage_opportunity": "2024-01-01",
    },
    "PINNACLE": {"odds_snapshot": "2024-01-01", "odds_movement": "2024-01-01"},
    "BETFAIR": {"odds_snapshot": "2024-01-01", "odds_movement": "2024-01-01"},
    "DRAFTKINGS": {"odds_snapshot": "2024-01-01", "odds_movement": "2024-01-01"},
    "FANDUEL": {"odds_snapshot": "2024-01-01", "odds_movement": "2024-01-01"},
    "BET365": {"odds_snapshot": "2024-01-01", "odds_movement": "2024-01-01"},
    # ── Prediction (market data only — metadata is reference data, see below) ──
    # Prediction CLOBs emit canonical "trades" data type (same key as CeFi).
    # Legacy "prediction_trades" name retired 2026-04-19 for cross-category
    # alignment. NOTE: book_snapshot_5 removed 2026-04-19 — neither the
    # Polymarket CLOB adapter nor the Kalshi adapter currently captures order
    # book snapshots. Declaring them here phantom-inflated the
    # market-tick-data-service PREDICTION completion_pct denominator
    # (35k expected vs 5.7k actually observable shards). Re-add when + if
    # either adapter grows a book-snapshot collection path.
    "POLYMARKET": {
        "trades": "2024-06-01",
    },
    "KALSHI": {
        "trades": "2024-06-01",
    },
}

# Reference data capabilities — static/structural data collected by
# instruments-service.  Separate from market data capabilities above.
# Market shards (BTC, ETH, SPX, etc.) are emergent from the data and
# not declared here — only explicitly-typed reference data goes here.
# Reference data capabilities — reserved for instruments-service reference
# data types that are genuinely separate from the instruments themselves.
# Prediction market metadata is NOT separate — the instruments parquet IS
# the metadata (market question, outcomes, expiry are InstrumentRecord fields).
VENUE_REFERENCE_DATA_CAPABILITIES: dict[str, dict[str, str]] = {}


# TradFi tick data windows — dates where expensive tick data (tbbo, trades) is collected.
# Outside these windows, only ohlcv_1m (pre-aggregated, cheaper) is downloaded.
# Cost rationale: Databento tbbo/trades charges per-symbol per-day; ohlcv_1m is
# significantly cheaper. We collect tick data only for specific training/validation
# windows to manage Databento costs while still having representative tick-level data.
TRADFI_TICK_DATA_WINDOWS: list[dict[str, str]] = [
    {"start": "2023-05-01", "end": "2023-05-31"},  # Training window
    {"start": "2024-07-01", "end": "2024-07-31"},  # Validation window
]


def is_in_tradfi_tick_window(date_str: str) -> bool:
    """Check if a date falls within any TradFi tick data window.

    Tick windows are date ranges where expensive tick data (tbbo, trades) is
    collected from Databento. Outside these windows, only cheaper ohlcv_1m
    is downloaded.
    """
    return any(w["start"] <= date_str <= w["end"] for w in TRADFI_TICK_DATA_WINDOWS)


def get_venue_data_type_start_date(venue: str, data_type: str) -> str | None:
    """Return the start date for a specific (venue, data_type) pair.

    Priority:
    1. VENUE_DATA_TYPE_CAPABILITIES[venue][data_type] — market data
    2. VENUE_REFERENCE_DATA_CAPABILITIES[venue][data_type] — reference data
    3. VenueMapping.venue_start_dates[venue] — venue-level default (lazy import)
    4. None — unknown venue/data_type (permissive)
    """
    caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
    if data_type in caps:
        return caps[data_type]
    ref_caps = VENUE_REFERENCE_DATA_CAPABILITIES.get(venue, {})
    if data_type in ref_caps:
        return ref_caps[data_type]
    # Fall back to venue start date from VenueMapping
    from .venue_mapping import VenueMapping  # noqa: qg-inside-import

    vm = VenueMapping()
    # Check compound key first (e.g. POLYMARKET:CRUDE_OIL) for per-shard start dates
    compound = f"{venue}:{data_type}" if data_type else venue
    compound_start = vm.get_venue_start_date(compound)
    if compound_start:
        return compound_start
    return vm.get_venue_start_date(venue)


def get_expected_data_types_for_venue(
    venue: str,
    service: str = "",
) -> list[str]:
    """Return the list of data types a venue is expected to produce.

    The capabilities registry is split by service layer:
    - instruments-service → VENUE_REFERENCE_DATA_CAPABILITIES (static metadata)
    - MTDS/MDPS/features → VENUE_DATA_TYPE_CAPABILITIES (market data)

    Market shards (BTC, ETH, SPX for prediction) are emergent from the index
    and not declared in either registry — they appear automatically.
    """
    if service == "instruments-service":
        ref_caps = VENUE_REFERENCE_DATA_CAPABILITIES.get(venue, {})
        return sorted(ref_caps.keys()) if ref_caps else []
    caps = VENUE_DATA_TYPE_CAPABILITIES.get(venue, {})
    if caps:
        return sorted(caps.keys())
    return get_valid_data_types_for_venue(venue)
