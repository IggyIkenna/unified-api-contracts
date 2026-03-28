"""Venue classification constants for the unified trading system."""

from __future__ import annotations

from enum import StrEnum

from ._odds_api_maps import ODDS_API_KEY_MAP as ODDS_API_KEY_MAP
from ._odds_api_maps import ODDS_API_REGION_MAP as ODDS_API_REGION_MAP

# CeFi Exchange Constants (VENUE-PRODUCT split)
BINANCE_SPOT = "BINANCE-SPOT"
BINANCE_FUTURES = "BINANCE-FUTURES"
OKX_SPOT = "OKX-SPOT"
OKX_FUTURES = "OKX-FUTURES"
BYBIT_SPOT = "BYBIT-SPOT"
BYBIT_FUTURES = "BYBIT-FUTURES"
COINBASE_SPOT = "COINBASE-SPOT"
DERIBIT = "DERIBIT"
HYPERLIQUID = "HYPERLIQUID"
ASTER = "ASTER"
UPBIT = "UPBIT"

# TradFi Exchange Constants
NASDAQ = "NASDAQ"
NYSE = "NYSE"
CME = "CME"
CBOT = "CBOT"
NYMEX = "NYMEX"
COMEX = "COMEX"
ICE = "ICE"
CBOE = "CBOE"
XNAS = "XNAS"
XNYS = "XNYS"

# DEX Constants
UNISWAPV2_ETH = "UNISWAPV2-ETHEREUM"
UNISWAPV3_ETH = "UNISWAPV3-ETHEREUM"
UNISWAPV4_ETH = "UNISWAPV4-ETHEREUM"
CURVE_ETH = "CURVE-ETHEREUM"
AERODROME_BASE = "AERODROME-BASE"

# DeFi Lending/Staking Constants
AAVE_V3 = "AAVE_V3"
AAVE_V3_ETH = "AAVEV3-ETHEREUM"
MORPHO_ETHEREUM = "MORPHO-ETHEREUM"
EULER_PLASMA = "EULER-PLASMA"
FLUID_PLASMA = "FLUID-PLASMA"
AAVE_PLASMA = "AAVE-PLASMA"
LIDO = "LIDO"
ETHERFI = "ETHERFI"
ETHENA = "ETHENA"

# Sports Betting Exchanges — two-sided markets with API access
BETFAIR = "BETFAIR"
SMARKETS = "SMARKETS"
MATCHBOOK = "MATCHBOOK"
BETDAQ = "BETDAQ"

# Prediction Markets — crypto/blockchain-based prediction exchanges
POLYMARKET = "POLYMARKET"
KALSHI = "KALSHI"
NOVIG = "NOVIG"
BETOPENLY = "BETOPENLY"
PROPHETX = "PROPHETX"

# Sports Bookmaker APIs — proper REST API for bet placement
PINNACLE = "PINNACLE"
ONEXBET = "ONEXBET"

# Sports Bookmakers — US (web-form / scraper-based bet placement)
DRAFTKINGS = "DRAFTKINGS"
FANDUEL = "FANDUEL"
BETMGM = "BETMGM"
BOVADA = "BOVADA"
CAESARS = "CAESARS"
BETRIVERS = "BETRIVERS"
BETONLINEAG = "BETONLINEAG"
BETUS = "BETUS"
LOWVIG = "LOWVIG"
MYBOOKIEAG = "MYBOOKIEAG"
FANATICS = "FANATICS"
BALLYBET = "BALLYBET"
BETANYSPORTS = "BETANYSPORTS"
BETPARX = "BETPARX"
ESPNBET = "ESPNBET"
FLIFF = "FLIFF"
HARDROCKBET = "HARDROCKBET"
REBET = "REBET"

# Daily Fantasy Sports (DFS) — US prop-based platforms
PRIZEPICKS = "PRIZEPICKS"
UNDERDOG = "UNDERDOG"
DRAFTKINGS_PICK6 = "DRAFTKINGS_PICK6"
BETR_DFS = "BETR_DFS"

# Sports Bookmakers — UK (web-form / scraper-based bet placement)
BET365 = "BET365"
WILLIAMHILL = "WILLIAMHILL"
LADBROKES = "LADBROKES"
CORAL = "CORAL"
PADDYPOWER = "PADDYPOWER"
SKYBET = "SKYBET"
BETWAY = "BETWAY"
BETVICTOR = "BETVICTOR"
BOYLESPORTS = "BOYLESPORTS"
BET888SPORT = "BET888SPORT"
UNIBET = "UNIBET"
BETFRED = "BETFRED"
CASUMO = "CASUMO"
GROSVENOR = "GROSVENOR"
LEOVEGAS = "LEOVEGAS"
LIVESCOREBET = "LIVESCOREBET"
VIRGINBET = "VIRGINBET"

# Sports Bookmakers — EU (web-form / scraper-based bet placement)
BETCLIC = "BETCLIC"
BETSSON = "BETSSON"
COOLBET = "COOLBET"
EVERYGAME = "EVERYGAME"
GTBETS = "GTBETS"
MARATHONBET = "MARATHONBET"
NORDICBET = "NORDICBET"
PARIONSSPORT = "PARIONSSPORT"
PMU = "PMU"
SUPRABETS = "SUPRABETS"
TIPICO = "TIPICO"
WINAMAX = "WINAMAX"
CODERE = "CODERE"
NETBET = "NETBET"
BWIN = "BWIN"
SBOBET = "SBOBET"

# Sports Bookmakers — SE (web-form / scraper-based)
ATG = "ATG"
MRGREEN = "MRGREEN"
SVENSKASPEL = "SVENSKASPEL"

# Sports Bookmakers — AU (web-form / scraper-based)
BETR_AU = "BETR_AU"
BETRIGHT = "BETRIGHT"
DABBLE = "DABBLE"
NEDS = "NEDS"
PLAYUP = "PLAYUP"
POINTSBET = "POINTSBET"
SPORTSBET_AU = "SPORTSBET_AU"
TAB = "TAB"
TABTOUCH = "TABTOUCH"

# Sports Data / Odds Aggregator Sources — read-only, no bet placement
API_FOOTBALL = "API_FOOTBALL"
ODDS_API = "ODDS_API"
FOOTYSTATS = "FOOTYSTATS"
SOCCER_FOOTBALL_INFO = "SOCCER_FOOTBALL_INFO"
OPEN_METEO = "OPEN_METEO"
UNDERSTAT = "UNDERSTAT"
TRANSFERMARKT = "TRANSFERMARKT"
SHARPAPI = "SHARPAPI"
ODDS_ENGINE = "ODDS_ENGINE"
METABET = "METABET"
OPTICODDS = "OPTICODDS"
ODDSJAM = "ODDSJAM"

# Sports Venue Sub-Sets — grouped by execution semantics
SPORTS_EXCHANGE_VENUES: set[str] = {BETFAIR, SMARKETS, MATCHBOOK, BETDAQ}

SPORTS_PREDICTION_MARKET_VENUES: set[str] = {POLYMARKET, KALSHI, NOVIG, BETOPENLY, PROPHETX}

SPORTS_BOOKMAKER_API_VENUES: set[str] = {PINNACLE, ONEXBET}

SPORTS_BOOKMAKER_WEB_VENUES: set[str] = {
    # US
    DRAFTKINGS,
    FANDUEL,
    BETMGM,
    BOVADA,
    CAESARS,
    BETRIVERS,
    BETONLINEAG,
    BETUS,
    LOWVIG,
    MYBOOKIEAG,
    FANATICS,
    BALLYBET,
    BETANYSPORTS,
    BETPARX,
    ESPNBET,
    FLIFF,
    HARDROCKBET,
    REBET,
    # UK
    BET365,
    WILLIAMHILL,
    LADBROKES,
    CORAL,
    PADDYPOWER,
    SKYBET,
    BETWAY,
    BETVICTOR,
    BOYLESPORTS,
    BET888SPORT,
    UNIBET,
    BETFRED,
    CASUMO,
    GROSVENOR,
    LEOVEGAS,
    LIVESCOREBET,
    VIRGINBET,
    # EU
    BETCLIC,
    BETSSON,
    COOLBET,
    EVERYGAME,
    GTBETS,
    MARATHONBET,
    NORDICBET,
    PARIONSSPORT,
    PMU,
    SUPRABETS,
    TIPICO,
    WINAMAX,
    CODERE,
    NETBET,
    BWIN,
    SBOBET,
    # SE
    ATG,
    MRGREEN,
    SVENSKASPEL,
    # AU
    BETR_AU,
    BETRIGHT,
    DABBLE,
    NEDS,
    PLAYUP,
    POINTSBET,
    SPORTSBET_AU,
    TAB,
    TABTOUCH,
}

SPORTS_DFS_VENUES: set[str] = {PRIZEPICKS, UNDERDOG, DRAFTKINGS_PICK6, BETR_DFS}

SPORTS_DATA_VENUES: set[str] = {
    API_FOOTBALL,
    ODDS_API,
    FOOTYSTATS,
    SOCCER_FOOTBALL_INFO,
    OPEN_METEO,
    UNDERSTAT,
    TRANSFERMARKT,
    SHARPAPI,
    ODDS_ENGINE,
    METABET,
    OPTICODDS,
    ODDSJAM,
}

SPORTS_BET_PLACEMENT_VENUES: set[str] = (
    SPORTS_EXCHANGE_VENUES | SPORTS_PREDICTION_MARKET_VENUES | SPORTS_BOOKMAKER_API_VENUES | SPORTS_BOOKMAKER_WEB_VENUES
)

SPORTS_VENUES: set[str] = SPORTS_BET_PLACEMENT_VENUES | SPORTS_DFS_VENUES | SPORTS_DATA_VENUES

# Venue Sets — grouped by execution semantics (non-sports)

DEX_VENUES: set[str] = {
    UNISWAPV2_ETH,
    UNISWAPV3_ETH,
    UNISWAPV4_ETH,
    CURVE_ETH,
    AERODROME_BASE,
}

CLOB_VENUES: set[str] = {
    BINANCE_SPOT,
    BINANCE_FUTURES,
    OKX_SPOT,
    OKX_FUTURES,
    BYBIT_SPOT,
    BYBIT_FUTURES,
    COINBASE_SPOT,
    DERIBIT,
    HYPERLIQUID,
    ASTER,
    UPBIT,
    "OKX",
    "BYBIT",
    NASDAQ,
    NYSE,
    CME,
    ICE,
    CBOE,
}

ZERO_ALPHA_VENUES: set[str] = {
    AAVE_V3,
    AAVE_V3_ETH,
    MORPHO_ETHEREUM,
    EULER_PLASMA,
    FLUID_PLASMA,
    AAVE_PLASMA,
    LIDO,
    ETHERFI,
    ETHENA,
}

VENUE_CATEGORY_MAP: dict[str, str] = {
    "BINANCE": "cefi",
    BINANCE_SPOT: "cefi",
    BINANCE_FUTURES: "cefi",
    "OKX": "cefi",
    OKX_SPOT: "cefi",
    OKX_FUTURES: "cefi",
    "BYBIT": "cefi",
    BYBIT_SPOT: "cefi",
    BYBIT_FUTURES: "cefi",
    COINBASE_SPOT: "cefi",
    HYPERLIQUID: "cefi",
    DERIBIT: "cefi",
    ASTER: "cefi",
    UPBIT: "cefi",
    NASDAQ: "tradfi",
    NYSE: "tradfi",
    CME: "tradfi",
    CBOT: "tradfi",
    NYMEX: "tradfi",
    COMEX: "tradfi",
    ICE: "tradfi",
    CBOE: "tradfi",
    XNAS: "tradfi",
    XNYS: "tradfi",
    UNISWAPV2_ETH: "defi",
    UNISWAPV3_ETH: "defi",
    UNISWAPV4_ETH: "defi",
    CURVE_ETH: "defi",
    AERODROME_BASE: "defi",
    AAVE_V3: "defi",
    AAVE_V3_ETH: "defi",
    MORPHO_ETHEREUM: "defi",
    EULER_PLASMA: "defi",
    FLUID_PLASMA: "defi",
    AAVE_PLASMA: "defi",
    LIDO: "defi",
    ETHERFI: "defi",
    ETHENA: "defi",
}
VENUE_CATEGORY_MAP.update(dict.fromkeys(SPORTS_VENUES, "sports"))

INSTRUMENT_TYPES_BY_VENUE: dict[str, set[str]] = {
    BINANCE_SPOT: {"SPOT"},
    COINBASE_SPOT: {"SPOT"},
    OKX_SPOT: {"SPOT"},
    OKX_FUTURES: {"PERPETUAL", "FUTURE", "OPTION"},
    "OKX": {"SPOT", "PERPETUAL", "FUTURE", "OPTION"},
    BYBIT_SPOT: {"SPOT"},
    BYBIT_FUTURES: {"PERPETUAL", "FUTURE"},
    "BYBIT": {"SPOT", "PERPETUAL", "FUTURE"},
    UPBIT: {"SPOT"},
    BINANCE_FUTURES: {"PERPETUAL", "FUTURE"},
    DERIBIT: {"PERPETUAL", "FUTURE", "OPTION"},
    HYPERLIQUID: {"PERPETUAL"},
    ASTER: {"PERPETUAL"},
    NASDAQ: {"EQUITY", "ETF", "INDEX"},
    NYSE: {"EQUITY", "ETF", "INDEX"},
    CME: {"FUTURE", "OPTION", "INDEX", "BOND"},
    CBOT: {"FUTURE", "OPTION", "BOND"},
    NYMEX: {"FUTURE", "OPTION", "COMMODITY"},
    COMEX: {"FUTURE", "OPTION", "COMMODITY"},
    ICE: {"FUTURE", "OPTION", "COMMODITY"},
    CBOE: {"EQUITY", "ETF", "OPTION", "INDEX"},
    XNAS: {"EQUITY", "ETF"},
    XNYS: {"EQUITY", "ETF"},
    UNISWAPV2_ETH: {"POOL"},
    UNISWAPV3_ETH: {"POOL"},
    UNISWAPV4_ETH: {"POOL"},
    CURVE_ETH: {"POOL"},
    AERODROME_BASE: {"POOL"},
    AAVE_V3: {"LENDING"},
    AAVE_V3_ETH: {"LENDING"},
    MORPHO_ETHEREUM: {"LENDING"},
    EULER_PLASMA: {"LENDING"},
    FLUID_PLASMA: {"LENDING"},
    AAVE_PLASMA: {"LENDING"},
    LIDO: {"STAKING"},
    ETHERFI: {"STAKING"},
    ETHENA: {"STAKING"},
}
INSTRUMENT_TYPES_BY_VENUE.update({v: {"EXCHANGE_ODDS"} for v in SPORTS_EXCHANGE_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"PREDICTION_MARKET"} for v in SPORTS_PREDICTION_MARKET_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"FIXED_ODDS"} for v in SPORTS_BOOKMAKER_API_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"FIXED_ODDS"} for v in SPORTS_BOOKMAKER_WEB_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"PROP"} for v in SPORTS_DFS_VENUES})

INSTRUMENT_TYPE_FOLDER_MAP: dict[str, str] = {
    "PERPETUAL": "perpetuals",
    "PERP": "perpetuals",
    "SPOT": "spot",
    "SPOT_PAIR": "spot_pairs",
    "ETF": "etf",
    "EQUITY": "equities",
    "INDEX": "indices",
    "FUTURE": "futures_chain",
    "OPTION": "options_chain",
    "POOL": "pools",
    "LENDING": "lending",
    "STAKING": "staking",
    "BOND": "bonds",
    "COMMODITY": "commodities",
    "CURRENCY": "currencies",
    "CDS": "cds",
    "SPOT_ASSET": "spot_assets",
    "YIELD_BEARING": "yield_bearing",
    "DEBT_TOKEN": "debt_tokens",
    "LST": "lst",
    "A_TOKEN": "a_tokens",
    "EXCHANGE_ODDS": "exchange_odds",
    "FIXED_ODDS": "fixed_odds",
    "PREDICTION_MARKET": "prediction_markets",
    "PROP": "props",
}


class VenueCapability(StrEnum):
    SPOT_TRADE = "spot_trade"
    PERP_TRADE = "perp_trade"
    FUTURES_TRADE = "futures_trade"
    OPTIONS_TRADE = "options_trade"
    SWAP = "swap"
    LEND = "lend"
    BORROW = "borrow"
    STAKE = "stake"
    UNSTAKE = "unstake"
    FLASH_LOAN = "flash_loan"
    PROVIDE_LIQUIDITY = "provide_liquidity"
    SPORTS_EXCHANGE = "sports_exchange"
    SPORTS_BOOKMAKER_API = "sports_bookmaker_api"
    SPORTS_BOOKMAKER_WEB = "sports_bookmaker_web"
    PREDICTION_MARKET = "prediction_market"
    SPORTS_DFS = "sports_dfs"
    SPORTS_DATA = "sports_data"


class VenueOrderCapability(StrEnum):
    """Order-type-level sub-capabilities for venues."""

    POST_ONLY = "post_only"
    REDUCE_ONLY = "reduce_only"
    CANCEL_REPLACE = "cancel_replace"
    BATCH_PLACE = "batch_place"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    TWAP = "twap"


VENUE_CAPABILITIES: dict[str, set[VenueCapability]] = {
    BINANCE_SPOT: {VenueCapability.SPOT_TRADE},
    COINBASE_SPOT: {VenueCapability.SPOT_TRADE},
    OKX_SPOT: {VenueCapability.SPOT_TRADE},
    BYBIT_SPOT: {VenueCapability.SPOT_TRADE},
    BINANCE_FUTURES: {VenueCapability.PERP_TRADE, VenueCapability.FUTURES_TRADE},
    OKX_FUTURES: {VenueCapability.PERP_TRADE, VenueCapability.FUTURES_TRADE, VenueCapability.OPTIONS_TRADE},
    BYBIT_FUTURES: {VenueCapability.PERP_TRADE, VenueCapability.FUTURES_TRADE},
    DERIBIT: {VenueCapability.PERP_TRADE, VenueCapability.FUTURES_TRADE, VenueCapability.OPTIONS_TRADE},
    HYPERLIQUID: {VenueCapability.PERP_TRADE},
    ASTER: {VenueCapability.PERP_TRADE},
    UPBIT: {VenueCapability.SPOT_TRADE},
    NASDAQ: {VenueCapability.SPOT_TRADE},
    NYSE: {VenueCapability.SPOT_TRADE},
    CME: {VenueCapability.FUTURES_TRADE, VenueCapability.OPTIONS_TRADE},
    CBOT: {VenueCapability.FUTURES_TRADE, VenueCapability.OPTIONS_TRADE},
    NYMEX: {VenueCapability.FUTURES_TRADE, VenueCapability.OPTIONS_TRADE},
    COMEX: {VenueCapability.FUTURES_TRADE, VenueCapability.OPTIONS_TRADE},
    ICE: {VenueCapability.FUTURES_TRADE, VenueCapability.OPTIONS_TRADE},
    CBOE: {VenueCapability.SPOT_TRADE, VenueCapability.OPTIONS_TRADE},
    UNISWAPV2_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    UNISWAPV3_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    UNISWAPV4_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    CURVE_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    AERODROME_BASE: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    AAVE_V3: {VenueCapability.LEND, VenueCapability.BORROW, VenueCapability.FLASH_LOAN},
    AAVE_V3_ETH: {VenueCapability.LEND, VenueCapability.BORROW, VenueCapability.FLASH_LOAN},
    MORPHO_ETHEREUM: {VenueCapability.LEND, VenueCapability.BORROW, VenueCapability.FLASH_LOAN},
    EULER_PLASMA: {VenueCapability.LEND, VenueCapability.BORROW},
    FLUID_PLASMA: {VenueCapability.LEND, VenueCapability.BORROW},
    AAVE_PLASMA: {VenueCapability.LEND, VenueCapability.BORROW},
    LIDO: {VenueCapability.STAKE, VenueCapability.UNSTAKE},
    ETHERFI: {VenueCapability.STAKE, VenueCapability.UNSTAKE},
    ETHENA: {VenueCapability.STAKE, VenueCapability.UNSTAKE},
}
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_EXCHANGE} for v in SPORTS_EXCHANGE_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.PREDICTION_MARKET} for v in SPORTS_PREDICTION_MARKET_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_BOOKMAKER_API} for v in SPORTS_BOOKMAKER_API_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_BOOKMAKER_WEB} for v in SPORTS_BOOKMAKER_WEB_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_DFS} for v in SPORTS_DFS_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_DATA} for v in SPORTS_DATA_VENUES})

# ---------------------------------------------------------------------------
# Venue Order-Type Sub-Capabilities
# ---------------------------------------------------------------------------

_CEFI_FULL: frozenset[VenueOrderCapability] = frozenset(
    {
        VenueOrderCapability.POST_ONLY,
        VenueOrderCapability.REDUCE_ONLY,
        VenueOrderCapability.CANCEL_REPLACE,
        VenueOrderCapability.BATCH_PLACE,
        VenueOrderCapability.STOP_LIMIT,
        VenueOrderCapability.TRAILING_STOP,
        VenueOrderCapability.ICEBERG,
        VenueOrderCapability.TWAP,
    }
)

_CEFI_STANDARD: frozenset[VenueOrderCapability] = frozenset(
    {
        VenueOrderCapability.POST_ONLY,
        VenueOrderCapability.REDUCE_ONLY,
        VenueOrderCapability.CANCEL_REPLACE,
        VenueOrderCapability.STOP_LIMIT,
    }
)

_CEFI_BASIC: frozenset[VenueOrderCapability] = frozenset(
    {
        VenueOrderCapability.POST_ONLY,
        VenueOrderCapability.STOP_LIMIT,
    }
)

_TRADFI_EXCHANGE: frozenset[VenueOrderCapability] = frozenset(
    {
        VenueOrderCapability.CANCEL_REPLACE,
        VenueOrderCapability.STOP_LIMIT,
        VenueOrderCapability.TRAILING_STOP,
        VenueOrderCapability.ICEBERG,
        VenueOrderCapability.TWAP,
    }
)

_TRADFI_DERIVATIVES: frozenset[VenueOrderCapability] = frozenset(
    {
        VenueOrderCapability.CANCEL_REPLACE,
        VenueOrderCapability.STOP_LIMIT,
        VenueOrderCapability.ICEBERG,
    }
)

_DEX_AMM: frozenset[VenueOrderCapability] = frozenset[VenueOrderCapability]()

_DEFI_LENDING: frozenset[VenueOrderCapability] = frozenset[VenueOrderCapability]()

_DEFI_STAKING: frozenset[VenueOrderCapability] = frozenset[VenueOrderCapability]()

_SPORTS_EXCHANGE: frozenset[VenueOrderCapability] = frozenset(
    {
        VenueOrderCapability.CANCEL_REPLACE,
        VenueOrderCapability.BATCH_PLACE,
    }
)

_PREDICTION_MARKET: frozenset[VenueOrderCapability] = frozenset(
    {
        VenueOrderCapability.BATCH_PLACE,
    }
)

_SPORTS_BOOKMAKER: frozenset[VenueOrderCapability] = frozenset[VenueOrderCapability]()

VENUE_ORDER_CAPABILITIES: dict[str, frozenset[VenueOrderCapability]] = {
    # CeFi exchanges -- full featured
    BINANCE_SPOT: _CEFI_FULL,
    BINANCE_FUTURES: _CEFI_FULL,
    OKX_SPOT: _CEFI_FULL,
    OKX_FUTURES: _CEFI_FULL,
    BYBIT_SPOT: _CEFI_FULL,
    BYBIT_FUTURES: _CEFI_FULL,
    COINBASE_SPOT: _CEFI_STANDARD,
    DERIBIT: frozenset(
        {
            VenueOrderCapability.POST_ONLY,
            VenueOrderCapability.REDUCE_ONLY,
            VenueOrderCapability.CANCEL_REPLACE,
            VenueOrderCapability.STOP_LIMIT,
            VenueOrderCapability.TRAILING_STOP,
        }
    ),
    HYPERLIQUID: frozenset(
        {
            VenueOrderCapability.POST_ONLY,
            VenueOrderCapability.REDUCE_ONLY,
            VenueOrderCapability.CANCEL_REPLACE,
            VenueOrderCapability.BATCH_PLACE,
            VenueOrderCapability.STOP_LIMIT,
            VenueOrderCapability.TWAP,
        }
    ),
    ASTER: frozenset(
        {
            VenueOrderCapability.POST_ONLY,
            VenueOrderCapability.REDUCE_ONLY,
            VenueOrderCapability.CANCEL_REPLACE,
            VenueOrderCapability.STOP_LIMIT,
        }
    ),
    UPBIT: _CEFI_BASIC,
    # TradFi exchanges
    NASDAQ: _TRADFI_EXCHANGE,
    NYSE: _TRADFI_EXCHANGE,
    CME: _TRADFI_DERIVATIVES,
    CBOT: _TRADFI_DERIVATIVES,
    NYMEX: _TRADFI_DERIVATIVES,
    COMEX: _TRADFI_DERIVATIVES,
    ICE: _TRADFI_DERIVATIVES,
    CBOE: _TRADFI_EXCHANGE,
    # DEX / AMM venues (no order-level sub-capabilities)
    UNISWAPV2_ETH: _DEX_AMM,
    UNISWAPV3_ETH: _DEX_AMM,
    UNISWAPV4_ETH: _DEX_AMM,
    CURVE_ETH: _DEX_AMM,
    AERODROME_BASE: _DEX_AMM,
    # DeFi lending
    AAVE_V3: _DEFI_LENDING,
    AAVE_V3_ETH: _DEFI_LENDING,
    MORPHO_ETHEREUM: _DEFI_LENDING,
    EULER_PLASMA: _DEFI_LENDING,
    FLUID_PLASMA: _DEFI_LENDING,
    AAVE_PLASMA: _DEFI_LENDING,
    # DeFi staking
    LIDO: _DEFI_STAKING,
    ETHERFI: _DEFI_STAKING,
    ETHENA: _DEFI_STAKING,
}
# Sports exchanges
VENUE_ORDER_CAPABILITIES.update(dict.fromkeys(SPORTS_EXCHANGE_VENUES, _SPORTS_EXCHANGE))
# Prediction markets
VENUE_ORDER_CAPABILITIES.update(dict.fromkeys(SPORTS_PREDICTION_MARKET_VENUES, _PREDICTION_MARKET))
# Bookmaker API / web venues
VENUE_ORDER_CAPABILITIES.update(dict.fromkeys(SPORTS_BOOKMAKER_API_VENUES, _SPORTS_BOOKMAKER))
VENUE_ORDER_CAPABILITIES.update(dict.fromkeys(SPORTS_BOOKMAKER_WEB_VENUES, _SPORTS_BOOKMAKER))
# DFS and data venues
VENUE_ORDER_CAPABILITIES.update(dict.fromkeys(SPORTS_DFS_VENUES, frozenset[VenueOrderCapability]()))
VENUE_ORDER_CAPABILITIES.update(dict.fromkeys(SPORTS_DATA_VENUES, frozenset[VenueOrderCapability]()))

# DeFi Protocol Classification


class DefiProtocolType(StrEnum):
    DEX_AMM = "dex_amm"
    LENDING = "lending"
    LIQUID_STAKING = "liquid_staking"
    YIELD = "yield"


VENUE_PROTOCOL_TYPE: dict[str, DefiProtocolType] = {
    UNISWAPV2_ETH: DefiProtocolType.DEX_AMM,
    UNISWAPV3_ETH: DefiProtocolType.DEX_AMM,
    UNISWAPV4_ETH: DefiProtocolType.DEX_AMM,
    CURVE_ETH: DefiProtocolType.DEX_AMM,
    AERODROME_BASE: DefiProtocolType.DEX_AMM,
    AAVE_V3: DefiProtocolType.LENDING,
    AAVE_V3_ETH: DefiProtocolType.LENDING,
    MORPHO_ETHEREUM: DefiProtocolType.LENDING,
    EULER_PLASMA: DefiProtocolType.LENDING,
    FLUID_PLASMA: DefiProtocolType.LENDING,
    AAVE_PLASMA: DefiProtocolType.LENDING,
    LIDO: DefiProtocolType.LIQUID_STAKING,
    ETHERFI: DefiProtocolType.LIQUID_STAKING,
    ETHENA: DefiProtocolType.YIELD,
}

# Venue -> Blockchain (DeFi smart order routing: shared wallet)
VENUE_CHAIN_MAP: dict[str, str] = {
    UNISWAPV2_ETH: "ethereum",
    UNISWAPV3_ETH: "ethereum",
    UNISWAPV4_ETH: "ethereum",
    CURVE_ETH: "ethereum",
    AERODROME_BASE: "base",
    AAVE_V3: "ethereum",
    AAVE_V3_ETH: "ethereum",
    MORPHO_ETHEREUM: "ethereum",
    EULER_PLASMA: "ethereum",
    FLUID_PLASMA: "ethereum",
    AAVE_PLASMA: "ethereum",
    LIDO: "ethereum",
    ETHERFI: "ethereum",
    ETHENA: "ethereum",
    HYPERLIQUID: "hyperliquid_l1",
}

SHARED_WALLET_GROUPS: dict[str, set[str]] = {}
for _venue, _chain in VENUE_CHAIN_MAP.items():
    SHARED_WALLET_GROUPS.setdefault(_chain, set()).add(_venue)

DEX_FEE_TIERS: dict[str, list[int]] = {
    UNISWAPV2_ETH: [30],
    UNISWAPV3_ETH: [1, 5, 30, 100],
    UNISWAPV4_ETH: [1, 5, 30, 100],
    CURVE_ETH: [1, 4],
    AERODROME_BASE: [1, 5, 30, 100],
}

# Venue Fee Model


class VenueFeeModel(StrEnum):
    MAKER_TAKER = "maker_taker"
    POOL_FEE = "pool_fee"
    RATE_BASED = "rate_based"
    COMMISSION = "commission"


VENUE_FEE_MODEL_MAP: dict[str, VenueFeeModel] = {
    BINANCE_SPOT: VenueFeeModel.MAKER_TAKER,
    BINANCE_FUTURES: VenueFeeModel.MAKER_TAKER,
    OKX_SPOT: VenueFeeModel.MAKER_TAKER,
    OKX_FUTURES: VenueFeeModel.MAKER_TAKER,
    BYBIT_SPOT: VenueFeeModel.MAKER_TAKER,
    BYBIT_FUTURES: VenueFeeModel.MAKER_TAKER,
    COINBASE_SPOT: VenueFeeModel.MAKER_TAKER,
    DERIBIT: VenueFeeModel.MAKER_TAKER,
    HYPERLIQUID: VenueFeeModel.MAKER_TAKER,
    ASTER: VenueFeeModel.MAKER_TAKER,
    UPBIT: VenueFeeModel.MAKER_TAKER,
    NASDAQ: VenueFeeModel.COMMISSION,
    NYSE: VenueFeeModel.COMMISSION,
    CME: VenueFeeModel.COMMISSION,
    CBOT: VenueFeeModel.COMMISSION,
    NYMEX: VenueFeeModel.COMMISSION,
    COMEX: VenueFeeModel.COMMISSION,
    ICE: VenueFeeModel.COMMISSION,
    CBOE: VenueFeeModel.COMMISSION,
    UNISWAPV2_ETH: VenueFeeModel.POOL_FEE,
    UNISWAPV3_ETH: VenueFeeModel.POOL_FEE,
    UNISWAPV4_ETH: VenueFeeModel.POOL_FEE,
    CURVE_ETH: VenueFeeModel.POOL_FEE,
    AERODROME_BASE: VenueFeeModel.POOL_FEE,
    AAVE_V3: VenueFeeModel.RATE_BASED,
    AAVE_V3_ETH: VenueFeeModel.RATE_BASED,
    MORPHO_ETHEREUM: VenueFeeModel.RATE_BASED,
    EULER_PLASMA: VenueFeeModel.RATE_BASED,
    FLUID_PLASMA: VenueFeeModel.RATE_BASED,
    AAVE_PLASMA: VenueFeeModel.RATE_BASED,
    LIDO: VenueFeeModel.RATE_BASED,
    ETHERFI: VenueFeeModel.RATE_BASED,
    ETHENA: VenueFeeModel.RATE_BASED,
}
VENUE_FEE_MODEL_MAP.update(dict.fromkeys(SPORTS_EXCHANGE_VENUES, VenueFeeModel.COMMISSION))
VENUE_FEE_MODEL_MAP.update(dict.fromkeys(SPORTS_PREDICTION_MARKET_VENUES, VenueFeeModel.COMMISSION))
VENUE_FEE_MODEL_MAP.update(dict.fromkeys(SPORTS_BOOKMAKER_API_VENUES, VenueFeeModel.COMMISSION))
VENUE_FEE_MODEL_MAP.update(dict.fromkeys(SPORTS_BOOKMAKER_WEB_VENUES, VenueFeeModel.COMMISSION))

# Instruction Type -> Valid Domains / Instrument Types (canonical rules)

INSTRUCTION_VALID_DOMAINS: dict[str, set[str]] = {
    "TRADE": {"cefi", "tradfi"},
    "SWAP": {"defi"},
    "LEND": {"defi"},
    "BORROW": {"defi"},
    "STAKE": {"defi"},
    "UNSTAKE": {"defi"},
    "FLASH_LOAN": {"defi"},
    "TRANSFER": {"defi"},
    "BET": {"sports"},
    "PREDICTION_BET": {"sports"},
    "SPORTS_BET": {"sports"},
    "SPORTS_EXCHANGE_ORDER": {"sports"},
    "FUTURES_ROLL": {"cefi", "tradfi"},
    "OPTIONS_COMBO": {"cefi", "tradfi"},
    "ADD_LIQUIDITY": {"defi"},
    "REMOVE_LIQUIDITY": {"defi"},
    "COLLECT_FEES": {"defi"},
}

INSTRUCTION_VALID_INSTRUMENT_TYPES: dict[str, set[str]] = {
    "TRADE": {
        "PERPETUAL",
        "SPOT",
        "SPOT_PAIR",
        "FUTURE",
        "OPTION",
        "EQUITY",
        "ETF",
        "INDEX",
        "BOND",
        "COMMODITY",
        "CURRENCY",
        "CDS",
    },
    "SWAP": {"POOL"},
    "LEND": {"LENDING"},
    "BORROW": {"LENDING"},
    "STAKE": {"STAKING"},
    "UNSTAKE": {"STAKING"},
    "FLASH_LOAN": {"LENDING"},
    "ZERO_ALPHA": {"YIELD_BEARING", "DEBT_TOKEN", "LST", "A_TOKEN", "LENDING", "STAKING"},
    "TRANSFER": {"SPOT", "SPOT_PAIR", "SPOT_ASSET"},
    "BET": {"FIXED_ODDS", "EXCHANGE_ODDS", "SPREAD", "OVER_UNDER", "OUTRIGHT", "PROP"},
    "PREDICTION_BET": {"PREDICTION_MARKET"},
    "SPORTS_BET": {"FIXED_ODDS", "PROP"},
    "SPORTS_EXCHANGE_ORDER": {"EXCHANGE_ODDS"},
    "FUTURES_ROLL": {"FUTURE"},
    "OPTIONS_COMBO": {"OPTION"},
    "ADD_LIQUIDITY": {"POOL"},
    "REMOVE_LIQUIDITY": {"POOL"},
    "COLLECT_FEES": {"POOL"},
}

# Alpha Classification


class AlphaProfile(StrEnum):
    ZERO_ALPHA = "zero_alpha"
    ALPHA_SEEKING = "alpha_seeking"


VENUE_ALPHA_PROFILE: dict[str, AlphaProfile] = {
    BINANCE_SPOT: AlphaProfile.ALPHA_SEEKING,
    BINANCE_FUTURES: AlphaProfile.ALPHA_SEEKING,
    OKX_SPOT: AlphaProfile.ALPHA_SEEKING,
    OKX_FUTURES: AlphaProfile.ALPHA_SEEKING,
    BYBIT_SPOT: AlphaProfile.ALPHA_SEEKING,
    BYBIT_FUTURES: AlphaProfile.ALPHA_SEEKING,
    COINBASE_SPOT: AlphaProfile.ALPHA_SEEKING,
    DERIBIT: AlphaProfile.ALPHA_SEEKING,
    HYPERLIQUID: AlphaProfile.ALPHA_SEEKING,
    ASTER: AlphaProfile.ALPHA_SEEKING,
    UPBIT: AlphaProfile.ALPHA_SEEKING,
    NASDAQ: AlphaProfile.ALPHA_SEEKING,
    NYSE: AlphaProfile.ALPHA_SEEKING,
    CME: AlphaProfile.ALPHA_SEEKING,
    CBOT: AlphaProfile.ALPHA_SEEKING,
    NYMEX: AlphaProfile.ALPHA_SEEKING,
    COMEX: AlphaProfile.ALPHA_SEEKING,
    ICE: AlphaProfile.ALPHA_SEEKING,
    CBOE: AlphaProfile.ALPHA_SEEKING,
    UNISWAPV2_ETH: AlphaProfile.ALPHA_SEEKING,
    UNISWAPV3_ETH: AlphaProfile.ALPHA_SEEKING,
    UNISWAPV4_ETH: AlphaProfile.ALPHA_SEEKING,
    CURVE_ETH: AlphaProfile.ALPHA_SEEKING,
    AERODROME_BASE: AlphaProfile.ALPHA_SEEKING,
    AAVE_V3: AlphaProfile.ZERO_ALPHA,
    AAVE_V3_ETH: AlphaProfile.ZERO_ALPHA,
    MORPHO_ETHEREUM: AlphaProfile.ZERO_ALPHA,
    EULER_PLASMA: AlphaProfile.ZERO_ALPHA,
    FLUID_PLASMA: AlphaProfile.ZERO_ALPHA,
    AAVE_PLASMA: AlphaProfile.ZERO_ALPHA,
    LIDO: AlphaProfile.ZERO_ALPHA,
    ETHERFI: AlphaProfile.ZERO_ALPHA,
    ETHENA: AlphaProfile.ZERO_ALPHA,
}
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_EXCHANGE_VENUES, AlphaProfile.ALPHA_SEEKING))
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_PREDICTION_MARKET_VENUES, AlphaProfile.ALPHA_SEEKING))
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_BOOKMAKER_API_VENUES, AlphaProfile.ALPHA_SEEKING))
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_BOOKMAKER_WEB_VENUES, AlphaProfile.ZERO_ALPHA))
