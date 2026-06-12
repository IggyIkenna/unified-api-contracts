# Venue Coverage Report (F39)

#

# Cross-reference: VENUE_CATEGORY_MAP + INSTRUMENT_TYPES_BY_VENUE

# x ENDPOINT_REGISTRY x execution-service adapter inventory

# x ARCHETYPE_LEG_STRUCTURES eligible_venue_ids

#

# Verdict definitions:

# wired: execution adapter exists + venue appears in >= 1 archetype leg eligible_venue_ids

# adapter-no-eligibility: execution adapter exists but venue NOT in any archetype leg eligible_venue_ids

# registered-no-adapter: venue in ENDPOINT_REGISTRY (data/API access) but NO execution adapter

# orphan: venue in manifest/registry but NO execution adapter AND not in ENDPOINT_REGISTRY

#

# Total venues: 145

# wired: 22

# adapter-no-eligibility: 6

# registered-no-adapter: 15

# orphan: 102

## WIRED (22)

# execution adapter exists + venue appears in >= 1 archetype leg eligible_venue_ids

BINANCE category=cefi adapter=binance_ccxt.py, binance_native.py endpoint_registry=yes leg_eligible=yes
BINANCE-FUTURES category=cefi adapter=binance_ccxt.py, binance_native.py endpoint_registry=no leg_eligible=yes
BINANCE-SPOT category=cefi adapter=binance_ccxt.py, binance_native.py endpoint_registry=no leg_eligible=yes
BITGET category=(unknown) adapter=bitget_native.py endpoint_registry=yes leg_eligible=yes
BITGET-FUTURES category=(unknown) adapter=bitget_native.py endpoint_registry=no leg_eligible=yes
BITGET-SPOT category=(unknown) adapter=bitget_native.py endpoint_registry=no leg_eligible=yes
BYBIT category=cefi adapter=bybit_ccxt.py, bybit_native.py endpoint_registry=yes leg_eligible=yes
BYBIT-FUTURES category=cefi adapter=bybit_ccxt.py, bybit_native.py endpoint_registry=no leg_eligible=yes
BYBIT-SPOT category=cefi adapter=bybit_ccxt.py, bybit_native.py endpoint_registry=no leg_eligible=yes
CBOE category=tradfi adapter=cboe_adapter.py endpoint_registry=no leg_eligible=yes
CME category=tradfi adapter=cme_adapter.py endpoint_registry=no leg_eligible=yes
COINBASE category=(unknown) adapter=coinbase_ccxt.py endpoint_registry=yes leg_eligible=yes
COINBASE-SPOT category=cefi adapter=coinbase_ccxt.py endpoint_registry=no leg_eligible=yes
DERIBIT category=cefi adapter=deribit_ccxt.py endpoint_registry=yes leg_eligible=yes
HYPERLIQUID category=cefi adapter=hyperliquid_ccxt.py endpoint_registry=yes leg_eligible=yes
ICE category=tradfi adapter=ice_adapter.py endpoint_registry=no leg_eligible=yes
KRAKEN-FUTURES category=(unknown) adapter=kraken_rest_adapter.py endpoint_registry=no leg_eligible=yes
KRAKEN-SPOT category=(unknown) adapter=kraken_rest_adapter.py endpoint_registry=no leg_eligible=yes
OKX category=cefi adapter=okx_ccxt.py, okx_native.py endpoint_registry=yes leg_eligible=yes
OKX-FUTURES category=cefi adapter=okx_ccxt.py, okx_native.py endpoint_registry=no leg_eligible=yes
OKX-SPOT category=cefi adapter=okx_ccxt.py, okx_native.py endpoint_registry=no leg_eligible=yes
POLYMARKET category=sports adapter=polymarket_adapter.py endpoint_registry=yes leg_eligible=yes

## ADAPTER-NO-ELIGIBILITY (6)

# execution adapter exists but venue NOT in any archetype leg eligible_venue_ids

BETFAIR category=sports adapter=sports_adapter.py endpoint_registry=yes leg_eligible=no
BITFINEX-SPOT category=(unknown) adapter=bitfinex_native.py endpoint_registry=no leg_eligible=no
FX category=(unknown) adapter=fx_adapter.py endpoint_registry=no leg_eligible=no
NASDAQ category=tradfi adapter=nasdaq_adapter.py endpoint_registry=no leg_eligible=no
NYSE category=tradfi adapter=nyse_adapter.py endpoint_registry=no leg_eligible=no
UPBIT category=cefi adapter=upbit_ccxt.py endpoint_registry=yes leg_eligible=no

## REGISTERED-NO-ADAPTER (15)

# venue in ENDPOINT_REGISTRY (data/API access) but NO execution adapter

API_FOOTBALL category=sports adapter=(none) endpoint_registry=yes leg_eligible=no
BARCHART category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
BITSTAMP category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
DATABENTO category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
DEFILLAMA category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
HUOBI category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
IBKR category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=yes
KALSHI category=sports adapter=(none) endpoint_registry=yes leg_eligible=yes
KUCOIN category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
MEXC category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
ODDS_API category=sports adapter=(none) endpoint_registry=yes leg_eligible=no
OPEN_METEO category=sports adapter=(none) endpoint_registry=yes leg_eligible=no
PINNACLE category=sports adapter=(none) endpoint_registry=yes leg_eligible=no
TARDIS category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no
THEGRAPH category=(unknown) adapter=(none) endpoint_registry=yes leg_eligible=no

## ORPHAN (102)

# venue in manifest/registry but NO execution adapter AND not in ENDPOINT_REGISTRY

AAVE-PLASMA category=defi adapter=(none) endpoint_registry=no leg_eligible=no
AAVE_V3 category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
AAVE_V3-ETHEREUM category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
AERODROME-BASE category=defi adapter=(none) endpoint_registry=no leg_eligible=no
ASTER category=cefi adapter=(none) endpoint_registry=no leg_eligible=no
ATG category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BALLYBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BET365 category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BET888SPORT category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETANYSPORTS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETCLIC category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETFAIR_EX_EU category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETFAIR_EX_UK category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETFAIR_SB_UK category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETFRED category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETMGM category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETONLINEAG category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETOPENLY category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETPARX category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETRIGHT category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETRIVERS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETR_AU category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETR_DFS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETSSON category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETUS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETVICTOR category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BETWAY category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BOVADA category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BOYLESPORTS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
BWIN category=sports adapter=(none) endpoint_registry=no leg_eligible=no
CAESARS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
CASUMO category=sports adapter=(none) endpoint_registry=no leg_eligible=no
CBOT category=tradfi adapter=(none) endpoint_registry=no leg_eligible=no
CODERE category=sports adapter=(none) endpoint_registry=no leg_eligible=no
COMEX category=tradfi adapter=(none) endpoint_registry=no leg_eligible=no
COOLBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
CORAL category=sports adapter=(none) endpoint_registry=no leg_eligible=no
CURVE-ETHEREUM category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
DABBLE category=sports adapter=(none) endpoint_registry=no leg_eligible=no
DRAFTKINGS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
DRAFTKINGS_PICK6 category=sports adapter=(none) endpoint_registry=no leg_eligible=no
ESPNBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
ETHENA category=defi adapter=(none) endpoint_registry=no leg_eligible=no
ETHERFI category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
EVERYGAME category=sports adapter=(none) endpoint_registry=no leg_eligible=no
FANATICS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
FANDUEL category=sports adapter=(none) endpoint_registry=no leg_eligible=no
FLIFF category=sports adapter=(none) endpoint_registry=no leg_eligible=no
FLUID-PLASMA category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
FOOTYSTATS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
GROSVENOR category=sports adapter=(none) endpoint_registry=no leg_eligible=no
GTBETS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
HARDROCKBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
LADBROKES category=sports adapter=(none) endpoint_registry=no leg_eligible=no
LEOVEGAS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
LIDO category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
LIVESCOREBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
LOWVIG category=sports adapter=(none) endpoint_registry=no leg_eligible=no
MARATHONBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
MATCHBOOK category=sports adapter=(none) endpoint_registry=no leg_eligible=no
METABET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
MORPHO-ETHEREUM category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
MRGREEN category=sports adapter=(none) endpoint_registry=no leg_eligible=no
MYBOOKIEAG category=sports adapter=(none) endpoint_registry=no leg_eligible=no
NEDS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
NETBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
NORDICBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
NOVIG category=sports adapter=(none) endpoint_registry=no leg_eligible=no
NYMEX category=tradfi adapter=(none) endpoint_registry=no leg_eligible=no
ODDS_ENGINE category=sports adapter=(none) endpoint_registry=no leg_eligible=no
ONEXBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
OPTICODDS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
PADDYPOWER category=sports adapter=(none) endpoint_registry=no leg_eligible=no
PARIONSSPORT category=sports adapter=(none) endpoint_registry=no leg_eligible=no
PLAYUP category=sports adapter=(none) endpoint_registry=no leg_eligible=no
PMU category=sports adapter=(none) endpoint_registry=no leg_eligible=no
POINTSBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
PRIZEPICKS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
PROPHETX category=sports adapter=(none) endpoint_registry=no leg_eligible=no
REBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
SBOBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
SHARPAPI category=sports adapter=(none) endpoint_registry=no leg_eligible=no
SKYBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
SOCCER_FOOTBALL_INFO category=sports adapter=(none) endpoint_registry=no leg_eligible=no
SPORTSBET_AU category=sports adapter=(none) endpoint_registry=no leg_eligible=no
SUPRABETS category=sports adapter=(none) endpoint_registry=no leg_eligible=no
SVENSKASPEL category=sports adapter=(none) endpoint_registry=no leg_eligible=no
TAB category=sports adapter=(none) endpoint_registry=no leg_eligible=no
TABTOUCH category=sports adapter=(none) endpoint_registry=no leg_eligible=no
TIPICO category=sports adapter=(none) endpoint_registry=no leg_eligible=no
TRANSFERMARKT category=sports adapter=(none) endpoint_registry=no leg_eligible=no
UNDERDOG category=sports adapter=(none) endpoint_registry=no leg_eligible=no
UNDERSTAT category=sports adapter=(none) endpoint_registry=no leg_eligible=no
UNIBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
UNISWAP_V2-ETHEREUM category=defi adapter=(none) endpoint_registry=no leg_eligible=no
UNISWAP_V3-ETHEREUM category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
UNISWAP_V4-ETHEREUM category=defi adapter=(none) endpoint_registry=no leg_eligible=yes
VIRGINBET category=sports adapter=(none) endpoint_registry=no leg_eligible=no
WILLIAMHILL category=sports adapter=(none) endpoint_registry=no leg_eligible=no
WINAMAX category=sports adapter=(none) endpoint_registry=no leg_eligible=no
XNAS category=tradfi adapter=(none) endpoint_registry=no leg_eligible=no
XNYS category=tradfi adapter=(none) endpoint_registry=no leg_eligible=no
