"""Venue classification constants for the unified trading system."""

from __future__ import annotations

# DEX Venues (for SWAP instruction type)
# Fee is derived from pool_fee_tier in instrument definition, NOT maker/taker fees
DEX_VENUES: set[str] = {
    "UNISWAPV2-ETH",
    "UNISWAPV3-ETH",
    "UNISWAPV4-ETH",
    "CURVE-ETH",
    "AERODROME-BASE",
}

# CLOB Venues (for TRADE instruction type)
# Uses maker_fee, taker_fee in venue config
CLOB_VENUES: set[str] = {
    # CeFi
    "BINANCE-SPOT",
    "BINANCE-FUTURES",
    "OKX",
    "BYBIT",
    "DERIBIT",
    "HYPERLIQUID",
    "ASTER",
    # TradFi
    "NASDAQ",
    "NYSE",
    "CME",
    "ICE",
    "CBOE",
}

# Zero-Alpha Venues (for LEND/BORROW/STAKE instruction types - lending, staking)
# No execution algorithm needed, fills at benchmark
ZERO_ALPHA_VENUES: set[str] = {
    "AAVE_V3",
    "AAVE_V3_ETH",
    "MORPHO-ETHEREUM",
    "EULER-PLASMA",
    "FLUID-PLASMA",
    "AAVE-PLASMA",
    "LIDO",
    "ETHERFI",
    "ETHENA",
}

# Map venue to its market category bucket (cefi/tradfi/defi)
VENUE_CATEGORY_MAP: dict[str, str] = {
    # CeFi venues -> cefi bucket
    "BINANCE": "cefi",
    "BINANCE-SPOT": "cefi",
    "BINANCE-FUTURES": "cefi",
    "OKX": "cefi",
    "BYBIT": "cefi",
    "HYPERLIQUID": "cefi",
    "DERIBIT": "cefi",
    "ASTER": "cefi",
    # TradFi venues -> tradfi bucket
    "NASDAQ": "tradfi",
    "NYSE": "tradfi",
    "CME": "tradfi",
    "ICE": "tradfi",
    "CBOE": "tradfi",
    # DeFi venues -> defi bucket
    "UNISWAPV2-ETH": "defi",
    "UNISWAPV3-ETH": "defi",
    "UNISWAPV4-ETH": "defi",
    "CURVE-ETH": "defi",
    "AERODROME-BASE": "defi",
    "AAVE_V3": "defi",
    "AAVE_V3_ETH": "defi",
    "MORPHO-ETHEREUM": "defi",
    "EULER-PLASMA": "defi",
    "LIDO": "defi",
    "ETHERFI": "defi",
    "ETHENA": "defi",
}

# Map instrument type to GCS folder name
INSTRUMENT_TYPE_FOLDER_MAP: dict[str, str] = {
    "PERPETUAL": "perpetuals",
    "SPOT": "spot",
    "ETF": "etf",
    "EQUITY": "equities",
    "FUTURE": "futures_chain",
    "OPTION": "options_chain",
    "POOL": "pools",
}
