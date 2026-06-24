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
    "KAT", "KAVA", "KCS", "KDA", "KGEN", "KING", "KITE", "KMD",
    "KNC", "KOMA", "KSM", "LAB", "LAYER", "LDO", "LEO", "LIGHT",
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
_CEFI_VENUE_QUOTE_EXTENSIONS: dict[str, frozenset[str]] = {
    "UPBIT": frozenset({"KRW"}),
}


def accepted_quotes_for_venue(venue: str | None) -> frozenset[str]:
    """Return the accepted quote-asset set for ``venue`` (entity-normalized).

    The fleet default is :data:`CEFI_ACCEPTED_QUOTE_ASSETS` (USDT/USDC/USD).
    A venue whose ENTITY prefix is in :data:`_CEFI_VENUE_QUOTE_EXTENSIONS` (today
    only ``UPBIT`` → ``KRW``) gets that extension UNIONED in — so an UPBIT KRW
    spot pair passes the quote gate while KRW stays rejected on every other venue
    (operator 2026-06-23, cefi_universe_capture_rule).
    """
    if not venue:
        return CEFI_ACCEPTED_QUOTE_ASSETS
    entity = venue.strip().upper().split("-", 1)[0]
    extra = _CEFI_VENUE_QUOTE_EXTENSIONS.get(entity)
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
# names (HYUNDAI/SAMSUNG/SKHYNIX, or the OKX KRX codes below) are perp-side MVP
# but their tradfi UNDERLYING is BLOCKED-DATA (no US-listed cash twin).
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
    "AMC",      # AMC Entertainment
    "MARA",     # Marathon Digital
    # --- Korean equities (OKX confirmed) ---
    "005930",   # Samsung Electronics (KRX code)
    "000660",   # SK Hynix (KRX code)
    "005380",   # Hyundai Motor (KRX code)
    # --- Binance tradfi-perp single stocks / ADRs (2026-06-24 symmetry) ---
    "AAOI", "ADBE", "ALAB", "AMAT", "ARM", "ASML", "ASTS", "AVGO", "AXTI",
    "BE", "BMNR", "BRKB", "CFG", "CIEN", "COHR", "COST", "CRCL", "CRDO", "CRM",
    "CRWD", "CRWV", "CSCO", "DELL", "DIS", "DKNG", "EBAY", "FLNC", "GLW", "HD",
    "HIMS", "HOOD", "HPE", "IBM", "IREN", "JPM", "KLAC", "LITE", "LLY", "LRCX",
    "MRVL", "MU", "NBIS", "NOK", "NOW", "NVO", "ONDS", "ORCL", "PAYP", "QCOM",
    "RIVN", "RKLB", "SMCI", "SNDK", "SONY", "SPCX", "TSM", "UBER", "USAR",
    "WDC", "WMT", "V", "ZM",
    # --- Binance tradfi-perp commodities (RAW base_asset form) ---
    "XAU", "XAG", "XPT", "XPD", "NATGAS", "COPPER", "CL",
    # --- Binance tradfi-perp indices / sector + commodity ETFs ---
    "SPX", "SPY", "QQQ", "IWM", "DIA", "SOXL", "XLE", "EWJ", "EWZ", "EWT",
    "EWY", "ROBO", "SLX", "URNM", "UVXY", "INX",
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
