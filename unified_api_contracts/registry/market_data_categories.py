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
        # DEX protocols (swaps)
        "UNISWAPV2-ETH",
        "UNISWAPV3-ETH",
        "UNISWAPV4-ETH",
        "CURVE-ETH",  # Curve Ethereum (MetaRegistry RPC)
        # FUTURE: BALANCER-ETH (The Graph deprecated)
        # Lending protocols
        "AAVE_V3_ETH",
        "MORPHO-ETHEREUM",
        # FUTURE: EULER-PLASMA, FLUID-PLASMA (adapters not implemented)
        # LST/Yield protocols
        "LIDO",
        "ETHERFI",
        "ETHENA",
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
