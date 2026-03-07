"""Venue classification constants for the unified trading system."""

from __future__ import annotations

# Binance venue name constants — always use these instead of bare "BINANCE"
BINANCE_SPOT = "BINANCE-SPOT"
BINANCE_FUTURES = "BINANCE-FUTURES"

# Other CeFi exchange constants (VENUE-PRODUCT split)
# Qualified names are canonical; bare names preserved for existing consumers.
OKX_SPOT = "OKX-SPOT"
OKX_FUTURES = "OKX-FUTURES"
BYBIT_SPOT = "BYBIT-SPOT"
BYBIT_FUTURES = "BYBIT-FUTURES"
COINBASE_SPOT = "COINBASE-SPOT"

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
    BINANCE_SPOT,
    BINANCE_FUTURES,
    OKX_SPOT,
    OKX_FUTURES,
    BYBIT_SPOT,
    BYBIT_FUTURES,
    COINBASE_SPOT,
    "DERIBIT",
    "HYPERLIQUID",
    "ASTER",
    # Backward compat: bare names still accepted for lookup
    "OKX",
    "BYBIT",
    # TradFi
    "NASDAQ",
    "NYSE",
    "CME",
    "ICE",
    "CBOE",
}

# Sports venues (odds, fixtures, execution — Betfair, Pinnacle, API-Football, Odds API, etc.)
# Used by features-sports-service and unified-sports-execution-interface
SPORTS_VENUES: set[str] = {
    "API_FOOTBALL",
    "BETFAIR",
    "PINNACLE",
    "ODDS_API",
    "FOOTYSTATS",
    "SOCCER_FOOTBALL_INFO",
    "OPEN_METEO",
    "UNDERSTAT",
    "TRANSFERMARKT",
    "SHARPAPI",
    "ODDS_ENGINE",
    "METABET",
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
    "BINANCE": "cefi",  # legacy key — new code should use BINANCE-SPOT or BINANCE-FUTURES
    BINANCE_SPOT: "cefi",
    BINANCE_FUTURES: "cefi",
    "OKX": "cefi",
    OKX_SPOT: "cefi",
    OKX_FUTURES: "cefi",
    "BYBIT": "cefi",
    BYBIT_SPOT: "cefi",
    BYBIT_FUTURES: "cefi",
    COINBASE_SPOT: "cefi",
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
    # Sports venues -> sports bucket
    "API_FOOTBALL": "sports",
    "BETFAIR": "sports",
    "PINNACLE": "sports",
    "ODDS_API": "sports",
    "FOOTYSTATS": "sports",
    "SOCCER_FOOTBALL_INFO": "sports",
    "OPEN_METEO": "sports",
    "UNDERSTAT": "sports",
    "TRANSFERMARKT": "sports",
    "SHARPAPI": "sports",
    "ODDS_ENGINE": "sports",
    "METABET": "sports",
}

# Map venue to supported instrument types
INSTRUMENT_TYPES_BY_VENUE: dict[str, set[str]] = {
    # CeFi spot
    BINANCE_SPOT: {"SPOT"},
    COINBASE_SPOT: {"SPOT"},
    OKX_SPOT: {"SPOT"},
    OKX_FUTURES: {"PERPETUAL", "FUTURE", "OPTION"},
    "OKX": {"SPOT", "PERPETUAL", "FUTURE", "OPTION"},  # legacy key
    BYBIT_SPOT: {"SPOT"},
    BYBIT_FUTURES: {"PERPETUAL", "FUTURE"},
    "BYBIT": {"SPOT", "PERPETUAL", "FUTURE"},  # legacy key
    "UPBIT": {"SPOT"},
    # CeFi derivatives
    BINANCE_FUTURES: {"PERPETUAL", "FUTURE"},
    "DERIBIT": {"PERPETUAL", "FUTURE", "OPTION"},
    "HYPERLIQUID": {"PERPETUAL"},
    "ASTER": {"PERPETUAL"},
    # TradFi
    "NASDAQ": {"EQUITY", "ETF"},
    "NYSE": {"EQUITY", "ETF"},
    "CME": {"FUTURE", "OPTION"},
    "CBOT": {"FUTURE", "OPTION"},
    "NYMEX": {"FUTURE", "OPTION"},
    "COMEX": {"FUTURE", "OPTION"},
    "CBOE": {"EQUITY", "ETF", "OPTION"},
    "XNAS": {"EQUITY", "ETF"},
    "XNYS": {"EQUITY", "ETF"},
    # DEX
    "UNISWAPV2-ETH": {"POOL"},
    "UNISWAPV3-ETH": {"POOL"},
    "UNISWAPV4-ETH": {"POOL"},
    "CURVE-ETH": {"POOL"},
    "AERODROME-BASE": {"POOL"},
    # Lending/Staking
    "AAVE_V3": {"LENDING"},
    "AAVE_V3_ETH": {"LENDING"},
    "MORPHO-ETHEREUM": {"LENDING"},
    "EULER-PLASMA": {"LENDING"},
    "FLUID-PLASMA": {"LENDING"},
    "LIDO": {"STAKING"},
    "ETHERFI": {"STAKING"},
    "ETHENA": {"STAKING"},
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
