"""CeFi instrument universe — curated, survivorship-bias-free base-asset capture set.

SSOT for which crypto assets the instruments-service tracks (and MTDS captures)
across the Tardis CEX venues (binance-futures / bybit / okx / deribit / kraken /
coinbase / bitget / bitfinex / …). The CeFi adapters' ``_passes_asset_filter``
gate returns only instruments whose base asset is in this set — so it deliberately
KEEPS gating (NOT "everything the venue lists" — that admits thousands of junk /
wash pairs), but with a much wider, principled universe than the former 44-coin
MVP cap.

``CEFI_BASE_ASSET_UNIVERSE`` is the UNION of three sources (operator decision
2026-06-23):

1. **Legacy 44** — the prior MVP subset (top-cap majors + operator-requested
   coverage incl. EigenLayer dust + FTT/LUNA delisting-test coins). All kept.

2. **Top-100-by-market-cap aggregated across TIME since 2019** — the UNION of the
   coins that were top-100 by market cap at each year-end / cycle-peak snapshot
   2019 → today. Because top-100 membership churns hard over a cycle, the union is
   a few hundred unique base assets, and — by construction — it DELIBERATELY
   captures coins that WERE top-100 but later declined or were delisted (LUNA /
   LUNC / UST / FTT / SRM / CEL / WAVES / HT / OKB / OMG / …). This is what makes
   the set **survivorship-bias-free**: a backtest over 2021 must see the assets
   that mattered in 2021, not just today's survivors. We have NO live market-cap
   API, so this tranche is CURATED as a checked-in frozenset from well-known
   historical top-100 rankings rather than fetched.

3. **All HYPERLIQUID + ASTER perp base assets** — the deduped base asset of every
   perp listed on HL / ASTER (read from the rebuilt instruments catalogue
   ``prod/catalog.parquet``, venue ∈ {HYPERLIQUID, ASTER}, instrument_type =
   PERPETUAL; equity / tokenized-stock / macro tickers — tracked separately via
   ``CEFI_EQUITY_PERP_BASE_UNIVERSE`` + ``crypto_equity_link`` — excluded). HL /
   ASTER themselves bypass this filter; the point is that a coin tradable as a
   perp on HL / ASTER is ALSO captured on the CEX venues, so cross-venue price /
   funding dispersion has both legs.

Curated, not fetched: there is no live market-cap source, so the set is checked
in and SORTED for deterministic diffs. Bias toward over-inclusion — small-coin
tick data is cheap and the goal is "set once, stop editing". Quote assets
(USDT / USDC / USD / BTC / ETH) are NOT filtered by this set — any canonical
quote is fine as long as the base is here (see ``CEFI_ACCEPTED_QUOTE_ASSETS``).

FTT and LUNA (delisted) remain included so the system's delisting handling is
exercised — they appear with ``is_active=False`` and ``available_to`` set.
"""

from __future__ import annotations

# fmt: off

# Curated union — legacy-44 + top-100-mcap-aggregated-since-2019 + HL/ASTER perp
# bases. Survivorship-bias-free (retired top-100 coins kept). Sorted for
# deterministic diffs; see module docstring for the rationale + provenance of
# each tranche. ~540 base assets (incl. the staking/restaking/LST spot-exception
# set ``STAKING_SPOT_EXCEPTION`` below).
CEFI_BASE_ASSET_UNIVERSE: frozenset[str] = frozenset({
    "0G", "1INCH", "2Z", "AAVE", "ABBC", "ACE", "ACH", "ACU",
    "ACX", "ADA", "AERGO", "AERO", "AEVO", "AGIX", "AGLD", "AI16Z",
    "AIA", "AIGENSYN", "AIO", "AIOT", "AIXBT", "AKT", "ALCH", "ALGO",
    "ALICE", "ALLO", "ALT", "ANIME", "ANKR", "ANKRETH", "APE", "APEX", "API3",
    "APR", "APT", "AR", "ARB", "ARC", "ARDR", "ARIA", "ARK",
    "ARKM", "ARPA", "ARX", "ASTER", "ASTEROID", "ASTR", "ATH", "ATOM",
    "AUCTION", "AVAAI", "AVAX", "AVL", "AVNT", "AWE", "AXL", "AXS",
    "AZTEC", "B2", "B3", "BABY", "BAL", "BAN", "BANANA", "BANANAS31",
    "BAND", "BANK", "BASED", "BAT", "BB", "BBX", "BCH", "BEAT",
    "BEL", "BERA", "BGB", "BICO", "BIGTIME", "BIO", "BIRB", "BLAST",
    "BLEND", "BLESS", "BLUAI", "BLUR", "BMT", "BNB", "BNT", "BOBA",
    "BOME", "BONK", "BR", "BRETT", "BREV", "BROCCOLI714", "BSB", "BSV",
    "BTC", "BTCDOM", "BTG", "BTM", "BTR", "BTS", "BTT", "BTW",
    "BSOL", "BULLA", "BUSD", "BZ", "CAKE", "CARDS", "CBETH", "CBRS",
    "CEL",
    "CELO", "CELR", "CFG", "CFX", "CHEEMS", "CHILLGUY", "CHIP", "CHR",
    "CHZ", "CLANKER", "CLO", "COAI", "COLLECT", "COMP", "CORE", "COTI",
    "COW", "CRO", "CRV", "CTR", "CTSI", "CVC", "CVX", "CYBER",
    "CYS", "DAI", "DASH", "DCR", "DENT", "DEXE", "DGB", "DOGE",
    "DOGS", "DOLO", "DOOD", "DOT", "DRGN", "DRIFT", "DUSK", "DYDX",
    "DYM", "EDEN", "EDGE", "EDU", "EETH", "EGLD", "EIGEN", "ELF",
    "ENA",
    "ENJ", "ENS", "ENSO", "EOS", "ESP", "ESPORTS", "ETC", "ETH",
    "ETHFI", "ETHX", "EUL", "EVAA", "EZETH", "FARTCOIN", "FET", "FF", "FHE", "FIDA",
    "FIGHT", "FIL", "FLOCK", "FLOKI", "FLOW", "FLUX", "FOGO", "FOLKS",
    "FORM", "FRAX", "FRXETH", "FTT", "FUN", "FXS", "G", "GALA", "GAS",
    "GENIUS", "GIGGLE", "GLM", "GMT", "GMX", "GNT", "GOAT", "GRASS",
    "GRIFFAIN", "GRT", "GT", "GTC", "GUN", "GUSD", "GWEI", "HANA",
    "HBAR", "HBTC", "HEDG", "HEMI", "HFT", "HMSTR", "HNT", "HOLO",
    "HOME", "HOT", "HT", "HUMA", "HYPE", "HYPER", "ICP", "ICX",
    "ILV", "IMX", "INF", "INIT", "INJ", "IO", "IOTA", "IOTX", "IP",
    "IRYS", "JASMY", "JCT", "JELLYJELLY", "JITOSOL", "JSOL", "JTO", "JUP", "KAITO",
    "KAS",
    "KAT", "KAVA", "KBONK", "KCS", "KDA", "KFLOKI", "KGEN", "KING", "KITE", "KLUNC", "KMD",
    "KNC", "KNEIRO", "KOMA", "KPEPE", "KSHIB", "KSM", "LAB", "LAYER", "LDO", "LEO", "LIGHT",
    "LINEA", "LINK", "LISTA", "LIT", "LITE", "LPT", "LQTY", "LRC",
    "LTC", "LUMIA", "LUNA", "LUNA2", "LUNC", "LYN", "MAGIC", "MAGMA",
    "MANA", "MANTA", "MANTRA", "MASK", "MATIC", "ME", "MEGA", "MELANIA",
    "MEME", "MERL", "METH", "METIS", "MEW", "MINA", "MITH", "MITO", "MKR",
    "MMT", "MNT", "MOG", "MON", "MOODENG", "MORPHO", "MOVE", "MOVR",
    "MSOL", "MX", "MYX", "NANO", "NAORIS", "NEAR", "NEIRO", "NEO",
    "NEX",
    "NEXO", "NIGHT", "NIL", "NMR", "NOM", "NOT", "NOW", "NULS",
    "NXPC", "OCEAN", "OGN", "OKB", "OMG", "ONDO", "ONDS", "ONE",
    "ONT", "OP", "OPEN", "OPG", "OPN", "ORCA", "ORDI", "OSETH", "OXT",
    "PARTI", "PAXG", "PAY", "PENDLE", "PENGU", "PENGUIN", "PEOPLE", "PEPE",
    "PHA", "PIEVERSE", "PIPPIN", "PIXEL", "PLAY", "PLUME", "PNUT", "POL",
    "POLYX", "POPCAT", "POPMART", "PORTAL", "POWER", "POWR", "PRL", "PROM",
    "PROMPT", "PROS", "PROVE", "PTB", "PUFETH", "PUMP", "PUMPBTC", "PUNDIAI", "PURR",
    "PYTH", "QNT", "QNTX", "QTUM", "RAD", "RAIL", "RARE", "RAVE",
    "RAY", "RECALL", "RED", "REN", "RENDER", "REP", "RESOLV", "RETH",
    "REZ",
    "RIF", "RLC", "RNDR", "RONIN", "ROSE", "RPL", "RSETH", "RSR", "RSTETH", "RSWETH", "RUNE",
    "RVN", "S", "SAGA", "SAHARA", "SAND", "SAPIEN", "SATS", "SC",
    "SCNSOL", "SEI", "SENT", "SFRXETH", "SHELL", "SHIB", "SIGN", "SIREN", "SKL", "SKR",
    "SKY", "SKYAI", "SNT", "SNX", "SOL", "SOLV", "SOMI", "SOON",
    "SOPH", "SPELL", "SPK", "SPX", "SQD", "SRM", "SSV", "STABLE",
    "STAR", "STBL", "STEEM", "STETH", "STG", "STORJ", "STRAT", "STRK",
    "STX", "SUI", "SUPER", "SUSHI", "SWARMS", "SWETH", "SYN", "SYRUP", "SYS",
    "T", "TAC", "TAG", "TAKE", "TAO", "TFUEL", "THETA", "TIA",
    "TNSR", "TON", "TOSHI", "TOWNS", "TRADOOR", "TRB", "TREE", "TRIA",
    "TROLL", "TRUMP", "TRUST", "TRUTH", "TRX", "TST", "TURBO", "TURTLE",
    "TUSD", "TWT", "UAI", "UMA", "UNI", "USAR", "USD1", "USDC",
    "USDD", "USDP", "USDT", "USELESS", "UST", "USTC", "USUAL", "VANA",
    "VELO", "VELVET", "VET", "VINE", "VIRTUAL", "VVV", "W", "WAVES",
    "WBTC", "WCT", "WEETH", "WET", "WIF", "WLD", "WLFI", "WOJAK",
    "WOO", "WSTETH", "WTC", "XAI", "XAN", "XCN", "XEM", "XLM",
    "XMR", "XPIN",
    "XPL", "XRP", "XTZ", "XVG", "YB", "YFI", "YGG", "ZAMA",
    "ZBT", "ZEC", "ZEN", "ZEREBRO", "ZEST", "ZETA", "ZIL", "ZK",
    "ZKC", "ZKP", "ZM", "ZORA", "ZRO", "ZRX",
})

# Quote assets we accept. Only USD and major stablecoins — no cross pairs.
CEFI_ACCEPTED_QUOTE_ASSETS: frozenset[str] = frozenset({
    "USDT", "USDC", "USD",
})

# Per-venue accepted-quote EXTENSIONS (operator 2026-06-23, cefi_universe_capture_rule).
# The default accepted quotes are USDT/USDC/USD fleet-wide. UPBIT is the Korean
# venue we track for the kimchi premium + cross-currency dispersion; the operator
# wants "all the KRW pairs that actually exist on Upbit", so KRW is accepted ONLY
# for the UPBIT entity. KRW is NOT globally added (it would admit thousands of
# cross pairs on other venues). Keyed on the venue ENTITY prefix (split on '-')
# so UPBIT / UPBIT-SPOT both resolve.
#
# BITFINEX-FUTURES -> BTC (bug fix, 2026-07-08): Bitfinex's OWN derivatives
# symbol parser (the ``bitfinex-derivatives`` branch of ``_resolve_base_quote``
# above) extracts a REAL quote for Bitfinex's BTC-margined inverse perps —
# ``ETHF0:BTCF0`` -> base=ETH, quote=BTC (confirmed live via
# api-pub.bitfinex.com/v2/tickers: ~2,000+ ETH/day, ~$6-7M/day). The same family
# includes ``LTCF0:BTCF0``, ``XRPF0:BTCF0``, ``XAUTF0:BTCF0``. These are genuine
# derivatives, not exotic spot cross-pairs, so BTC was wrongly rejected by the
# fleet-default quote gate. Keyed on the FULL canonical venue string
# ``BITFINEX-FUTURES`` (NOT the bare ``BITFINEX`` entity) so the extension does
# NOT leak into ``BITFINEX-SPOT`` — a genuine BASE/BTC SPOT cross-pair (e.g.
# ``ETHBTC``) must stay rejected as an exotic cross pair; only the derivatives
# leg gets the BTC allowance.
_CEFI_VENUE_QUOTE_EXTENSIONS: dict[str, frozenset[str]] = {
    "UPBIT": frozenset({"KRW"}),
    "BITFINEX-FUTURES": frozenset({"BTC"}),
}


def accepted_quotes_for_venue(venue: str | None) -> frozenset[str]:
    """Return the accepted quote-asset set for ``venue``.

    The fleet default is :data:`CEFI_ACCEPTED_QUOTE_ASSETS` (USDT/USDC/USD).
    ``venue`` is checked against :data:`_CEFI_VENUE_QUOTE_EXTENSIONS` two ways:
    first by its FULL canonical string (e.g. ``BITFINEX-FUTURES`` -> ``BTC``, so
    the extension does not leak into the sibling ``BITFINEX-SPOT``), then by its
    ENTITY prefix — split on ``-`` — (e.g. ``UPBIT`` -> ``KRW``, so both
    ``UPBIT`` and ``UPBIT-SPOT`` resolve). Either match is UNIONED into the
    fleet default (operator 2026-06-23, cefi_universe_capture_rule).
    """
    if not venue:
        return CEFI_ACCEPTED_QUOTE_ASSETS
    venue_upper = venue.strip().upper()
    entity = venue_upper.split("-", 1)[0]
    extra = _CEFI_VENUE_QUOTE_EXTENSIONS.get(venue_upper) or _CEFI_VENUE_QUOTE_EXTENSIONS.get(entity)
    if extra is None:
        return CEFI_ACCEPTED_QUOTE_ASSETS
    return CEFI_ACCEPTED_QUOTE_ASSETS | extra

# Options are only tracked for these underlyings. Everything else (SOL, USDC,
# BNB options on Deribit etc.) is filtered out to keep data volume manageable.
CEFI_OPTIONS_UNDERLYINGS: frozenset[str] = frozenset({
    "BTC",
    "ETH",
})

# Equity base assets for crypto-venue single-stock perps + tokenized stocks.
# These are the UNDERLYING real-equity tickers (as used by Databento DBEQ.BASIC),
# NOT the full crypto-venue symbol (e.g. META not METAUSDT). Each entry here
# indicates a family of crypto-venue instruments (e.g. Binance METAUSDT,
# OKX META-USDT-SWAP, Bybit METAUSDT) that track the real equity.
# Pre-IPO / no-real-twin symbols (SPACEX, etc.) are tracked separately in the
# crypto_equity_link module (STANDALONE_EQUITY_PERP_SYMBOLS).
# Operator-seeded 2026-06-20: OKX 17 US equity perps + Binance/Bybit reps.
#
# FULL BINANCE TRADFI-PERP SYMMETRY (2026-06-24): expanded to cover EVERY
# BINANCE-FUTURES PERPETUAL tradfi underlying so each Binance tradfi PERP is
# cefi-MVP, SYMMETRIC with the tradfi MVP list covering the captured UNDERLYING
# (`TRADFI_EQUITY_PERP_BASIS_UNIVERSE`). The base_asset here is the RAW Binance
# form (XAU/XAG/NATGAS/COPPER/CL/XPT/XPD for commodities; the ticker for
# equities/ETFs/indices) — that is the cefi perp's base_ccy axis. This is the
# CEFI-SIDE of the equity/commodity-basis arc: each Binance tradfi PERP (cefi
# MVP) <-> its captured tradfi UNDERLYING (tradfi MVP), both MVP. Crypto perps
# (BTC/ETH/SOL/…) are NOT here — only the tradfi-underlying perps. The 3 KRX
# names (HYUNDAI/SAMSUNG/SKHYNIX) are perp-side MVP but their tradfi UNDERLYING
# is BLOCKED-DATA (no US-listed cash twin).
#
# RE-SYNCED 2026-07-08 against the live Binance ``fapi/v1/exchangeInfo``
# (``contractType=TRADIFI_PERPETUAL``, 118 symbols live today, all
# ``status=TRADING``; underlyingType in {EQUITY, COMMODITY, PREMARKET,
# KR_EQUITY}). Changes from the 105-entry 2026-06-24 snapshot:
#   - ADDED 21 tickers live on Binance today but missing from the 2026-06-24
#     capture: ANTHROPIC / OPENAI (underlyingType=PREMARKET, pre-IPO share
#     perps), BBX, BSP, BX, BZ (underlyingType=COMMODITY), CAT, CBRS, DRAM,
#     FLEX, KORU, KSTR, MVLL, QNTX, SQQQ, STRC, STXX, TER, TQQQ, TTWO, TXN.
#   - RENAMED the 3 KRX entries from the KRX numeric code to Binance's (and
#     OKX's / Bybit's — confirmed on all 3 venues) actual live ``baseAsset``
#     string: 005930->SAMSUNG, 000660->SKHYNIX, 005380->HYUNDAI. The numeric
#     KRX code never matched any live venue's real base_ccy for THIS
#     (cefi-perp) universe — it is the correct identifier for the SEPARATE
#     TradFi-side Yahoo/Databento universe (``TRADFI_EQUITY_PERP_BASIS_UNIVERSE``
#     / ``KRX_EQUITIES``), which is an independent identifier namespace and is
#     intentionally left unchanged.
#   - REMOVED AMC, MARA: verified genuinely delisted — absent from Binance
#     ``fapi/v1/exchangeInfo`` (no symbol at all, any contractType/status),
#     absent from OKX (``/api/v5/public/instruments`` across SWAP/FUTURES/
#     SPOT/MARGIN, and ``AMC-USDT-SWAP``/``MARA-USDT-SWAP`` return OKX error
#     51001 "doesn't exist"), and absent from Bybit
#     (``/v5/market/instruments-info?category=linear``). Neither symbol is in
#     ``TRADFI_EQUITY_PERP_BASIS_UNIVERSE`` so no cross-file symmetry breaks.
#   - KEPT (not removed) despite no longer appearing under
#     ``contractType=TRADIFI_PERPETUAL`` on Binance today: CFG, DIA, INX, ROBO,
#     SLX, SPX. These tickers are still LIVE on Binance/OKX/Bybit, but Binance
#     now tags them ``underlyingType=COIN`` with subtypes Meme/Infrastructure/
#     RWA/Alpha — the ticker has been reused by an unrelated crypto token
#     (e.g. SPX = the "SPX6900" meme coin, not the S&P 500), not "delisted" in
#     the simple sense. All 6 also have live symmetric entries in
#     ``TRADFI_EQUITY_PERP_BASIS_UNIVERSE`` (real DIA/CFG/ROBO/SLX ETFs/stocks)
#     and in ``crypto_equity_link.CRYPTO_EQUITY_PERP_TO_REAL_EQUITY`` cross-refs
#     — resolving this correctly needs a dedicated cross-venue + cross-file
#     audit (does OKX/Bybit's same-ticker perp reuse the SAME crypto token, or
#     a genuine surviving equity-basis product?) rather than a unilateral
#     removal here. FLAGGED for follow-up, not silently dropped.
#
# WIDENED 2026-07-18 (operator: "get all the Binance listings, it's recent data
# so not that much, we can curate it our end") — full live pull of EVERY
# ``contractType=TRADIFI_PERPETUAL`` from ``fapi/v1/exchangeInfo`` (139 contracts
# / 138 distinct bases; underlyingType ∈ {EQUITY, COMMODITY, HK_EQUITY,
# KR_EQUITY, PREMARKET}, underlyingSubType=["TradFi"]). 20 NEW bases added below
# (was 124 → now 144) grouped under the dated comment inside the frozenset. NEW
# ``HK_EQUITY`` category (Tencent / Xiaomi / Zhipu / MiniMax). NOTHING excluded
# as non-equity: ``contractType=TRADIFI_PERPETUAL`` already partitions equity
# perps from crypto (crypto = ``contractType=PERPETUAL``, ``underlyingType=COIN``)
# — the 3 crypto INDEX perps live today (DEFI / BTCDOM / ALL, all
# ``contractType=PERPETUAL``) are correctly NOT here. Bases stay in the RAW
# Binance ``baseAsset`` form (matching the existing entries); the Databento
# real-equity twin (``tracks_equity``) is left UNWIRED for the new bases (they
# tag ``is_equity_perp=True`` / ``tracks_equity=""`` like SPCX/OPENAI/ANTHROPIC)
# until the tradfi DBEQ.BASIC leg is added in Phase 1b — honest, not a regression.
CEFI_EQUITY_PERP_BASE_UNIVERSE: frozenset[str] = frozenset({
    # --- US equities (OKX 17-perp universe + Binance/Bybit verified coverage) ---
    "AAPL",     # Apple
    "TSLA",     # Tesla
    "AMZN",     # Amazon
    "MSFT",     # Microsoft
    "GOOGL",    # Alphabet (Google)
    "META",     # Meta Platforms (Facebook)
    "NVDA",     # NVIDIA
    "NFLX",     # Netflix
    "AMD",      # AMD
    "INTC",     # Intel
    "BABA",     # Alibaba
    "COIN",     # Coinbase
    "MSTR",     # MicroStrategy
    "PLTR",     # Palantir
    "GME",      # GameStop
    # --- Korean equities (Binance/OKX/Bybit confirmed live 2026-07-08) ---
    "SAMSUNG",  # Samsung Electronics (Binance/OKX/Bybit baseAsset string)
    "SKHYNIX",  # SK Hynix (Binance/OKX/Bybit baseAsset string)
    "HYUNDAI",  # Hyundai Motor (Binance/OKX/Bybit baseAsset string)
    # --- Binance tradfi-perp single stocks / ADRs (2026-06-24 symmetry) ---
    "AAOI", "ADBE", "ALAB", "AMAT", "ARM", "ASML", "ASTS", "AVGO", "AXTI",
    "BE", "BMNR", "BRKB", "CFG", "CIEN", "COHR", "COST", "CRCL", "CRDO", "CRM",
    "CRWD", "CRWV", "CSCO", "DELL", "DIS", "DKNG", "EBAY", "FLNC", "GLW", "HD",
    "HIMS", "HOOD", "HPE", "IBM", "IREN", "JPM", "KLAC", "LITE", "LLY", "LRCX",
    "MRVL", "MU", "NBIS", "NOK", "NOW", "NVO", "ONDS", "ORCL", "PAYP", "QCOM",
    "RIVN", "RKLB", "SMCI", "SNDK", "SONY", "SPCX", "TSM", "UBER", "USAR",
    "WDC", "WMT", "V", "ZM",
    # --- Binance tradfi-perp single stocks / ADRs (2026-07-08 re-sync additions) ---
    "BBX", "BSP", "BX", "CAT", "CBRS", "DRAM", "FLEX", "KORU", "KSTR", "MVLL",
    "QNTX", "STRC", "STXX", "TER", "TTWO", "TXN",
    # --- Binance tradfi-perp pre-IPO / premarket share perps (2026-07-08) ---
    "ANTHROPIC",  # Anthropic (underlyingType=PREMARKET, pre-IPO)
    "OPENAI",     # OpenAI (underlyingType=PREMARKET, pre-IPO)
    # --- Binance tradfi-perp commodities (RAW base_asset form) ---
    "XAU", "XAG", "XPT", "XPD", "NATGAS", "COPPER", "CL",
    "BZ",  # 2026-07-08 re-sync addition (underlyingType=COMMODITY)
    # --- Binance tradfi-perp indices / sector + commodity ETFs ---
    "SPX", "SPY", "QQQ", "IWM", "DIA", "SOXL", "XLE", "EWJ", "EWZ", "EWT",
    "EWY", "ROBO", "SLX", "URNM", "UVXY", "INX",
    "SQQQ", "TQQQ",  # 2026-07-08 re-sync additions (leveraged QQQ ETFs)
    # --- Binance 2026-07-18 full-listing widen (ALL live TRADIFI_PERPETUAL) ---
    # US equities / ETFs (underlyingType=EQUITY). Clear real twins: APP=AppLovin,
    # GEV=GE Vernova, SNOW=Snowflake, VRT=Vertiv, WEN=Wendy's; SOXS/TZA=Direxion
    # daily 3x bear ETFs (SOXS = bear pair of SOXL, already above), XBI=SPDR S&P
    # Biotech ETF. Binance collision-avoidance / mangled tickers whose real twin
    # is unresolved (kept per "get all, curate our end" — tracks_equity stays ""):
    # BNC, BOT, FWDI, INTW, MUU, SKHY, SNXX.
    "APP", "BNC", "BOT", "FWDI", "GEV", "INTW", "MUU", "SKHY", "SNOW", "SNXX",
    "SOXS", "TZA", "VRT", "WEN", "XBI",
    # Hong Kong equities (underlyingType=HK_EQUITY — NEW category 2026-07-18):
    # HK0700=Tencent (HKEX 0700), HK1810=Xiaomi (HKEX 1810), TENCENT=Tencent
    # (named baseAsset variant), MINIMAX + ZHIPU = Chinese-AI listings.
    "HK0700", "HK1810", "MINIMAX", "TENCENT", "ZHIPU",
})

# Staking / restaking / liquid-staking (LST) / liquid-restaking (LRT) tokens
# whose SPOT we capture EVEN WHEN NO PERP exists for them on the venue — the ONLY
# spot-without-perp carve-out (operator 2026-06-23, cefi_universe_capture_rule).
# These are the ``carry_staked_basis`` / DeFi-seasonal-rewards legs: we want their
# spot liquidity and they often have no perp anywhere. The ordinary CeFi rule
# (SPOT captured only where the venue also lists a perp for the base) does NOT
# apply to a base in this set — its SPOT is mvp=true on ANY venue that lists it,
# regardless of perp existence. Adding a new staking token is a manual UAC edit
# (like the base universe). Every member is ALSO present in
# ``CEFI_BASE_ASSET_UNIVERSE`` so the base-membership leg of the predicate passes.
# Forward-looking allow-list (operator 2026-06-23): ALL wrapped + unwrapped LST/LRT
# equivalents are included even if no CEX currently lists them (harmless extras —
# the carve-out only MATTERS for a base a venue actually lists).
#   Restaking:   EIGEN, KING, ETHFI
#   ETH LSTs/LRTs: STETH, WSTETH, RETH, WEETH, EETH, CBETH, FRXETH, SFRXETH (Frax),
#                  ANKRETH (Ankr), OSETH (StakeWise), SWETH, RSWETH (Swell),
#                  ETHX (Stader), METH (Mantle), RSETH (Kelp), EZETH (Renzo),
#                  PUFETH (Puffer), RSTETH
#   SOL LSTs:    MSOL (Marinade), JITOSOL + JTO (Jito), BSOL, JSOL, SCNSOL,
#                INF (Sanctum)
STAKING_SPOT_EXCEPTION: frozenset[str] = frozenset({
    "ANKRETH", "BSOL", "CBETH", "EETH", "EIGEN", "ETHFI", "ETHX", "EZETH",
    "FRXETH", "INF", "JITOSOL", "JSOL", "JTO", "KING", "METH", "MSOL",
    "OSETH", "PUFETH", "RETH", "RSETH", "RSTETH", "RSWETH", "SCNSOL", "SFRXETH",
    "STETH", "SWETH", "WEETH", "WSTETH",
})
# fmt: on
