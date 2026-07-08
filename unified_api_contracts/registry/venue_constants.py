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
KRAKEN_SPOT = "KRAKEN-SPOT"
KRAKEN_FUTURES = "KRAKEN-FUTURES"

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
UNISWAP_V2_ETH = "UNISWAP_V2-ETHEREUM"
UNISWAP_V3_ETH = "UNISWAP_V3-ETHEREUM"
UNISWAP_V4_ETH = "UNISWAP_V4-ETHEREUM"
CURVE_ETH = "CURVE-ETHEREUM"
AERODROME_BASE = "AERODROME-BASE"

# DeFi Lending/Staking Constants
AAVE_V3 = "AAVE_V3"
AAVE_V3_ETH = "AAVE_V3-ETHEREUM"
MORPHO_ETHEREUM = "MORPHO-ETHEREUM"
FLUID_PLASMA = "FLUID-PLASMA"
AAVE_PLASMA = "AAVE-PLASMA"
LIDO = "LIDO"
ETHERFI = "ETHERFI"
ETHENA = "ETHENA"

# Sports Betting Exchanges — two-sided markets with API access
BETFAIR = "BETFAIR"
BETFAIR_SB_UK = "BETFAIR_SB_UK"  # Betfair Sportsbook (UK)
BETFAIR_EX_UK = "BETFAIR_EX_UK"  # Betfair Exchange (UK)
BETFAIR_EX_EU = "BETFAIR_EX_EU"  # Betfair Exchange (EU)
MATCHBOOK = "MATCHBOOK"

# Prediction Markets — crypto/blockchain-based prediction exchanges
POLYMARKET = "POLYMARKET"
KALSHI = "KALSHI"
NOVIG = "NOVIG"
BETOPENLY = "BETOPENLY"
PROPHETX = "PROPHETX"

# Prediction-platform PERPETUAL FUTURES — crypto perps with funding launched by
# Kalshi (CFTC-approved, 2026-05-29, 13 BTC+alt contracts) and Polymarket
# (beta 2026-04-21, crypto+stocks, 10-20x leverage). These are CFTC-regulated
# crypto perpetual futures, NOT prediction YES/NO markets — they share the
# canonical perp instrument universe (BTC-PERP, ETH-PERP, …) alongside CeFi
# perp venues. Distinct venue tokens from KALSHI/POLYMARKET (prediction Q&A).
# SSOT: plans/active/prediction_venue_perps_and_live_clob_depth_2026_06_20.md
KALSHI_PERP = "KALSHI-PERP"
POLYMARKET_PERP = "POLYMARKET-PERP"

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

# Sports Venue Sub-Sets — grouped by execution semantics
SPORTS_EXCHANGE_VENUES: set[str] = {BETFAIR, MATCHBOOK, BETFAIR_SB_UK, BETFAIR_EX_UK, BETFAIR_EX_EU}

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
}

SPORTS_BET_PLACEMENT_VENUES: set[str] = (
    SPORTS_EXCHANGE_VENUES | SPORTS_PREDICTION_MARKET_VENUES | SPORTS_BOOKMAKER_API_VENUES | SPORTS_BOOKMAKER_WEB_VENUES
)

SPORTS_VENUES: set[str] = SPORTS_BET_PLACEMENT_VENUES | SPORTS_DFS_VENUES | SPORTS_DATA_VENUES

# Venue Sets — grouped by execution semantics (non-sports)

DEX_VENUES: set[str] = {
    UNISWAP_V2_ETH,
    UNISWAP_V3_ETH,
    UNISWAP_V4_ETH,
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
    KRAKEN_SPOT,
    KRAKEN_FUTURES,
    "OKX",
    "BYBIT",
    NASDAQ,
    NYSE,
    CME,
    ICE,
    CBOE,
    # Prediction-platform perp CLOBs (crypto perpetuals, not YES/NO markets)
    KALSHI_PERP,
    POLYMARKET_PERP,
}

ZERO_ALPHA_VENUES: set[str] = {
    AAVE_V3,
    AAVE_V3_ETH,
    MORPHO_ETHEREUM,
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
    UNISWAP_V2_ETH: "defi",
    UNISWAP_V3_ETH: "defi",
    UNISWAP_V4_ETH: "defi",
    CURVE_ETH: "defi",
    AERODROME_BASE: "defi",
    AAVE_V3: "defi",
    AAVE_V3_ETH: "defi",
    MORPHO_ETHEREUM: "defi",
    FLUID_PLASMA: "defi",
    AAVE_PLASMA: "defi",
    LIDO: "defi",
    ETHERFI: "defi",
    ETHENA: "defi",
    # Prediction-platform perp CLOBs — treated as cefi (CFTC-regulated crypto perps)
    KALSHI_PERP: "cefi",
    POLYMARKET_PERP: "cefi",
}
VENUE_CATEGORY_MAP.update(dict.fromkeys(SPORTS_VENUES, "sports"))

INSTRUMENT_TYPES_BY_VENUE: dict[str, set[str]] = {
    BINANCE_SPOT: {"SPOT_PAIR"},
    COINBASE_SPOT: {"SPOT_PAIR"},
    # VENUES_BY_ASSET_GROUP["cefi"] (market_data_categories.py) declares the
    # BARE "COINBASE" token (not "COINBASE-SPOT") as the canonical cefi spot
    # venue; the writer stamps "COINBASE-SPOT" (folded back to "COINBASE" by
    # the Layer-1 checker's _CEFI_VENUE_FOLD for the EXPECTED/ENUMERATED
    # comparison — check_enumeration_completeness.py). The EXPECTED-side
    # lookup is keyed by the VENUES_BY_ASSET_GROUP token, i.e. bare
    # "COINBASE", so it needs its OWN key here too (D2a naming reconciliation,
    # 2026-07-06) — without it the itype-gate authority switch silently zeroes
    # COINBASE's entire EXPECTED set.
    "COINBASE": {"SPOT_PAIR"},
    OKX_SPOT: {"SPOT_PAIR"},
    OKX_FUTURES: {"PERPETUAL", "FUTURE", "OPTION"},
    # bare "OKX" keeps SPOT_PAIR (reverted 2026-07-08, commit 23fa3a99 had
    # dropped it as "phantom"): VENUES_BY_ASSET_GROUP["cefi"] never declares
    # "OKX-SPOT" as a distinct cefi venue (only bare "OKX" is registered) —
    # OKX was never split like BINANCE-SPOT/BINANCE-FUTURES or BYBIT/
    # BYBIT-SPOT, so bare "OKX" is the ONLY cefi venue token that can carry
    # OKX spot_pair capability in the EXPECTED denominator. Removing it left
    # OKX spot_pair permanently unenumerable, dropping build_expected('cefi')
    # 75→71 tuples and failing the golden-byte-identical test (blocked ALL
    # instruments-service shipping). See
    # plans/active/issues/instruments_service_cefi_qg_red_on_ldr_head_2026_07_08.md.
    "OKX": {"SPOT_PAIR", "PERPETUAL", "FUTURE", "OPTION"},
    BYBIT_SPOT: {"SPOT_PAIR"},
    BYBIT_FUTURES: {"PERPETUAL", "FUTURE"},
    # bare "BYBIT" keeps SPOT_PAIR too (same 2026-07-08 revert) — unlike OKX,
    # BYBIT-SPOT IS a separately declared cefi venue, but the checked-in
    # golden (tests/unit/scripts/goldens/expected_universe/cefi.json) expects
    # BOTH ('BYBIT', 'spot_pair', ...) and ('BYBIT-SPOT', 'spot_pair', ...) as
    # distinct EXPECTED cells; per the golden test's own docstring, a real
    # coverage regression must not be laundered into a fixture update, so the
    # source-of-truth capability declaration is restored to match instead.
    "BYBIT": {"SPOT_PAIR", "PERPETUAL", "FUTURE"},
    UPBIT: {"SPOT_PAIR"},
    BINANCE_FUTURES: {"PERPETUAL", "FUTURE"},
    # SPOT_PAIR added 2026-07-06 (D2a regression fix): the OLD tardis-routing
    # authority (VenueMapping.venue_instrument_type_to_tardis) already declared
    # ("DERIBIT", "SPOT_PAIR"): "deribit" (Tardis's deribit endpoint serves
    # spot). Missing it here would have made the D2a authority switch silently
    # DROP a real, previously-EXPECTED (DERIBIT, spot_pair, {trades,
    # book_snapshot_5}) pair — a regression the itype-gate switch must not
    # introduce (VENUE_DATA_TYPE_CAPABILITIES["DERIBIT"] already carries trades
    # / book_snapshot_5 since 2019-03-30, confirming this is real capability,
    # not a stale routing artifact).
    DERIBIT: {"SPOT_PAIR", "PERPETUAL", "FUTURE", "OPTION"},
    KRAKEN_SPOT: {"SPOT_PAIR"},
    KRAKEN_FUTURES: {"PERPETUAL", "FUTURE"},
    HYPERLIQUID: {"PERPETUAL"},
    ASTER: {"PERPETUAL"},
    # D2a (cefi Layer-1 gate-authority fix, honest_coverage_v2, 2026-07-06):
    # these 10 declared cefi venues (VENUES_BY_ASSET_GROUP["cefi"]) had NO
    # entry here. check_enumeration_completeness.py's itype-gate authority is
    # switching FROM VenueMapping.venue_instrument_type_to_tardis (a
    # tardis-fetch ROUTING table — sourcing) TO this dict (a declarative
    # existence authority). A declared venue absent from the routing table is
    # NOT the same as "does not exist"; completing this dict is the fix.
    # Itypes below are the operator-decided universe (verified against
    # tardis_exchange_instrument_types / venue_instrument_config.py /
    # data_type_capability.py DataTypeCapability entries where available; see
    # honest_coverage_uac_writer_matrix_reconciliation). None of these 10 has
    # a dedicated module constant (grepped) — string literals match the style
    # of the other unconstant-ed cefi entries above ("OKX", "BYBIT").
    "BINANCE-DELIVERY": {"PERPETUAL", "FUTURE"},  # COIN-M inverse perps + dated delivery futures
    "COINBASE-FUTURES": {"PERPETUAL", "FUTURE"},  # Coinbase Derivatives via Tardis coinbase-international
    "BITFINEX-FUTURES": {"PERPETUAL", "FUTURE"},
    "BITGET-FUTURES": {"PERPETUAL", "FUTURE"},
    "BITFINEX-SPOT": {"SPOT_PAIR"},
    "BITGET-SPOT": {"SPOT_PAIR"},
    "PACIFICA-SOLANA": {"PERPETUAL"},  # Solana perp DEX — native pacifica_api, not Tardis
    "EXTENDED-STARKNET": {"PERPETUAL"},  # Starknet perp DEX — native extended_api, not Tardis
    "LIGHTER-ZKSYNC": {"PERPETUAL"},  # zkSync perp DEX — Tardis post-2026-04-17, native lighter_api before
    # DERIBIT-COMBO: multi-leg combo/spread instruments from Deribit's
    # get_instruments (future_combo + option_combo kinds). Ikenna 2026-07-06:
    # future_combo is NOT in MVP — only the option_combo kind counts, so this
    # venue is OPTION-ONLY (it rolls up to the options_chain bundle via
    # bundle_instrument_type_for_leaf, same universal cefi option roll-up
    # DERIBIT's own OPTION leaf uses). Do NOT add FUTURE without a new,
    # explicit operator decision superseding this one.
    "DERIBIT-COMBO": {"OPTION"},
    NASDAQ: {"EQUITY", "ETF", "INDEX"},
    NYSE: {"EQUITY", "ETF", "INDEX"},
    CME: {"FUTURE", "OPTION", "INDEX", "BOND", "EVENT_CONTRACT"},
    CBOT: {"FUTURE", "OPTION", "BOND"},
    NYMEX: {"FUTURE", "OPTION", "COMMODITY"},
    COMEX: {"FUTURE", "OPTION", "COMMODITY"},
    ICE: {"FUTURE", "OPTION", "COMMODITY"},
    CBOE: {"EQUITY", "ETF", "OPTION", "INDEX"},
    XNAS: {"EQUITY", "ETF"},
    XNYS: {"EQUITY", "ETF"},
    UNISWAP_V2_ETH: {"POOL"},
    UNISWAP_V3_ETH: {"POOL"},
    UNISWAP_V4_ETH: {"POOL"},
    CURVE_ETH: {"POOL"},
    AERODROME_BASE: {"POOL"},
    AAVE_V3: {"LENDING"},
    AAVE_V3_ETH: {"LENDING"},
    MORPHO_ETHEREUM: {"LENDING"},
    FLUID_PLASMA: {"LENDING"},
    AAVE_PLASMA: {"LENDING"},
    LIDO: {"STAKING"},
    ETHERFI: {"STAKING"},
    ETHENA: {"STAKING"},
    # Prediction-platform perp CLOBs — CFTC-regulated crypto perpetual futures
    KALSHI_PERP: {"PERPETUAL"},
    POLYMARKET_PERP: {"PERPETUAL"},
}
INSTRUMENT_TYPES_BY_VENUE.update({v: {"EXCHANGE_ODDS"} for v in SPORTS_EXCHANGE_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"PREDICTION_MARKET"} for v in SPORTS_PREDICTION_MARKET_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"FIXED_ODDS"} for v in SPORTS_BOOKMAKER_API_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"FIXED_ODDS"} for v in SPORTS_BOOKMAKER_WEB_VENUES})
INSTRUMENT_TYPES_BY_VENUE.update({v: {"PROP"} for v in SPORTS_DFS_VENUES})

INSTRUMENT_TYPE_FOLDER_MAP: dict[str, str] = {
    "PERPETUAL": "perpetuals",
    "EQUITY_PERP": "equity_perps",
    "TOKENIZED_EQUITY": "tokenized_equities",
    "SPOT_PAIR": "spot_pairs",
    "ETF": "etf",
    "EQUITY": "equities",
    "INDEX": "indices",
    "FUTURE": "futures_chain",
    "OPTION": "options_chain",
    "POOL": "pools",
    "DEX_POOL": "dex_pool_state",
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
    "COMBO": "combos",
    "EVENT_CONTRACT": "event_contracts",
    "SOLANA_LENDING": "solana_lending",
    "SOLANA_VAULT": "solana_vaults",
    "SOLANA_AMM_POOL": "solana_amm_pools",
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
    UNISWAP_V2_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    UNISWAP_V3_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    UNISWAP_V4_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    CURVE_ETH: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    AERODROME_BASE: {VenueCapability.SWAP, VenueCapability.PROVIDE_LIQUIDITY},
    AAVE_V3: {VenueCapability.LEND, VenueCapability.BORROW, VenueCapability.FLASH_LOAN},
    AAVE_V3_ETH: {VenueCapability.LEND, VenueCapability.BORROW, VenueCapability.FLASH_LOAN},
    MORPHO_ETHEREUM: {VenueCapability.LEND, VenueCapability.BORROW, VenueCapability.FLASH_LOAN},
    FLUID_PLASMA: {VenueCapability.LEND, VenueCapability.BORROW},
    AAVE_PLASMA: {VenueCapability.LEND, VenueCapability.BORROW},
    LIDO: {VenueCapability.STAKE, VenueCapability.UNSTAKE},
    ETHERFI: {VenueCapability.STAKE, VenueCapability.UNSTAKE},
    ETHENA: {VenueCapability.STAKE, VenueCapability.UNSTAKE},
    # Prediction-platform perp CLOBs — CFTC-regulated crypto perpetual futures
    KALSHI_PERP: {VenueCapability.PERP_TRADE},
    POLYMARKET_PERP: {VenueCapability.PERP_TRADE},
}
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_EXCHANGE} for v in SPORTS_EXCHANGE_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.PREDICTION_MARKET} for v in SPORTS_PREDICTION_MARKET_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_BOOKMAKER_API} for v in SPORTS_BOOKMAKER_API_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_BOOKMAKER_WEB} for v in SPORTS_BOOKMAKER_WEB_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_DFS} for v in SPORTS_DFS_VENUES})
VENUE_CAPABILITIES.update({v: {VenueCapability.SPORTS_DATA} for v in SPORTS_DATA_VENUES})


def get_perp_venues() -> frozenset[str]:
    """Return the canonical set of venues with PERP_TRADE capability.

    Filters ``VENUE_CAPABILITIES`` by ``VenueCapability.PERP_TRADE``. Used by
    strategy-service / execution-service to validate
    ``perp_venue`` config fields (e.g. ``CARRY_BASIS_PERP_INV``)
    without introducing a per-archetype ``PerpVenue`` StrEnum.
    """
    return frozenset(venue for venue, caps in VENUE_CAPABILITIES.items() if VenueCapability.PERP_TRADE in caps)


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
    UNISWAP_V2_ETH: _DEX_AMM,
    UNISWAP_V3_ETH: _DEX_AMM,
    UNISWAP_V4_ETH: _DEX_AMM,
    CURVE_ETH: _DEX_AMM,
    AERODROME_BASE: _DEX_AMM,
    # DeFi lending
    AAVE_V3: _DEFI_LENDING,
    AAVE_V3_ETH: _DEFI_LENDING,
    MORPHO_ETHEREUM: _DEFI_LENDING,
    FLUID_PLASMA: _DEFI_LENDING,
    AAVE_PLASMA: _DEFI_LENDING,
    # DeFi staking
    LIDO: _DEFI_STAKING,
    ETHERFI: _DEFI_STAKING,
    ETHENA: _DEFI_STAKING,
    # Prediction-platform perp CLOBs — basic order caps pending live API verification
    KALSHI_PERP: _CEFI_BASIC,
    POLYMARKET_PERP: _CEFI_BASIC,
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
    UNISWAP_V2_ETH: DefiProtocolType.DEX_AMM,
    UNISWAP_V3_ETH: DefiProtocolType.DEX_AMM,
    UNISWAP_V4_ETH: DefiProtocolType.DEX_AMM,
    CURVE_ETH: DefiProtocolType.DEX_AMM,
    AERODROME_BASE: DefiProtocolType.DEX_AMM,
    AAVE_V3: DefiProtocolType.LENDING,
    AAVE_V3_ETH: DefiProtocolType.LENDING,
    MORPHO_ETHEREUM: DefiProtocolType.LENDING,
    FLUID_PLASMA: DefiProtocolType.LENDING,
    AAVE_PLASMA: DefiProtocolType.LENDING,
    LIDO: DefiProtocolType.LIQUID_STAKING,
    ETHERFI: DefiProtocolType.LIQUID_STAKING,
    ETHENA: DefiProtocolType.YIELD,
}

# Venue -> Blockchain (DeFi smart order routing: shared wallet)
VENUE_CHAIN_MAP: dict[str, str] = {
    UNISWAP_V2_ETH: "ethereum",
    UNISWAP_V3_ETH: "ethereum",
    UNISWAP_V4_ETH: "ethereum",
    CURVE_ETH: "ethereum",
    AERODROME_BASE: "base",
    AAVE_V3: "ethereum",
    AAVE_V3_ETH: "ethereum",
    MORPHO_ETHEREUM: "ethereum",
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
    UNISWAP_V2_ETH: [30],
    UNISWAP_V3_ETH: [1, 5, 30, 100],
    UNISWAP_V4_ETH: [1, 5, 30, 100],
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
    UNISWAP_V2_ETH: VenueFeeModel.POOL_FEE,
    UNISWAP_V3_ETH: VenueFeeModel.POOL_FEE,
    UNISWAP_V4_ETH: VenueFeeModel.POOL_FEE,
    CURVE_ETH: VenueFeeModel.POOL_FEE,
    AERODROME_BASE: VenueFeeModel.POOL_FEE,
    AAVE_V3: VenueFeeModel.RATE_BASED,
    AAVE_V3_ETH: VenueFeeModel.RATE_BASED,
    MORPHO_ETHEREUM: VenueFeeModel.RATE_BASED,
    FLUID_PLASMA: VenueFeeModel.RATE_BASED,
    AAVE_PLASMA: VenueFeeModel.RATE_BASED,
    LIDO: VenueFeeModel.RATE_BASED,
    ETHERFI: VenueFeeModel.RATE_BASED,
    ETHENA: VenueFeeModel.RATE_BASED,
    # Prediction-platform perp CLOBs — maker/taker fee model (crypto perps)
    KALSHI_PERP: VenueFeeModel.MAKER_TAKER,
    POLYMARKET_PERP: VenueFeeModel.MAKER_TAKER,
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
    "TRANSFER": {"SPOT_PAIR", "SPOT_ASSET"},
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
    UNISWAP_V2_ETH: AlphaProfile.ALPHA_SEEKING,
    UNISWAP_V3_ETH: AlphaProfile.ALPHA_SEEKING,
    UNISWAP_V4_ETH: AlphaProfile.ALPHA_SEEKING,
    CURVE_ETH: AlphaProfile.ALPHA_SEEKING,
    AERODROME_BASE: AlphaProfile.ALPHA_SEEKING,
    AAVE_V3: AlphaProfile.ZERO_ALPHA,
    AAVE_V3_ETH: AlphaProfile.ZERO_ALPHA,
    MORPHO_ETHEREUM: AlphaProfile.ZERO_ALPHA,
    FLUID_PLASMA: AlphaProfile.ZERO_ALPHA,
    AAVE_PLASMA: AlphaProfile.ZERO_ALPHA,
    LIDO: AlphaProfile.ZERO_ALPHA,
    ETHERFI: AlphaProfile.ZERO_ALPHA,
    ETHENA: AlphaProfile.ZERO_ALPHA,
    # Prediction-platform perp CLOBs — alpha-seeking (funding arb / dispersion)
    KALSHI_PERP: AlphaProfile.ALPHA_SEEKING,
    POLYMARKET_PERP: AlphaProfile.ALPHA_SEEKING,
}
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_EXCHANGE_VENUES, AlphaProfile.ALPHA_SEEKING))
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_PREDICTION_MARKET_VENUES, AlphaProfile.ALPHA_SEEKING))
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_BOOKMAKER_API_VENUES, AlphaProfile.ALPHA_SEEKING))
VENUE_ALPHA_PROFILE.update(dict.fromkeys(SPORTS_BOOKMAKER_WEB_VENUES, AlphaProfile.ZERO_ALPHA))
