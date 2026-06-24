"""TradFi ticker universe registry — canonical lists of equity tickers by category.

These lists are used by instruments-service config_reloaders to seed the ticker
cache for TickerUniverseConfig hot-reload and fallback. They represent the full
investable universe for each category.

These lists are the SSOT for which symbols the instruments-service will attempt to
fetch instrument definitions for when no cloud config is available.
"""

from __future__ import annotations

SP500_TICKERS: list[str] = [
    "AAPL",
    "MSFT",
    "AMZN",
    "NVDA",
    "GOOGL",
    "GOOG",
    "META",
    "BRK.B",
    "LLY",
    "AVGO",
    "TSLA",
    "JPM",
    "V",
    "UNH",
    "XOM",
    "MA",
    "COST",
    "HD",
    "PG",
    "JNJ",
    "WMT",
    "ABBV",
    "BAC",
    "MRK",
    "NFLX",
    "CRM",
    "CVX",
    "ORCL",
    "AMD",
    "PEP",
    "TMO",
    "KO",
    "ADBE",
    "WFC",
    "CSCO",
    "MCD",
    "ABT",
    "PM",
    "ACN",
    "DHR",
    "IBM",
    "TXN",
    "GE",
    "CAT",
    "QCOM",
    "INTU",
    "VZ",
    "AMGN",
    "GS",
    "SPGI",
    "ISRG",
    "BKNG",
    "RTX",
    "PLD",
    "HON",
    "AMAT",
    "LOW",
    "SYK",
    "T",
    "BLK",
    "VRTX",
    "MDLZ",
    "REGN",
    "C",
    "DE",
    "ADI",
    "SBUX",
    "AXP",
    "MMC",
    "CB",
    "MS",
    "PGR",
    "GILD",
    "MO",
    "ETN",
    "BSX",
    "ZTS",
    "UNP",
    "LRCX",
    "ELV",
    "CI",
    "SO",
    "FI",
    "KLAC",
    "CME",
    "DUK",
    "AON",
    "HCA",
    "EQIX",
    "SNPS",
    "MCK",
    "ICE",
    "TT",
    "MU",
    "CDNS",
    "NKE",
    "WELL",
    "CSX",
    "APH",
    "ITW",
    "EMR",
    "CL",
    "CVS",
    "FCX",
    "CTAS",
    "USB",
    "TGT",
    "ORLY",
    "ROP",
    "PCAR",
    "AZO",
    "GD",
    "MCO",
    "NOC",
    "AMP",
    "WM",
    "CARR",
    "NSC",
    "SHW",
    "AFL",
    "PSA",
    "GWW",
    "FTNT",
    "NXPI",
    "HLT",
    "TDG",
    "RSG",
    "MCHP",
    "MNST",
    "ECL",
    "ODFL",
    "COF",
    "DLR",
    "OXY",
    "ADSK",
    "HES",
    "ROST",
    "MTD",
    "A",
    "TEL",
    "PAYX",
    "KMB",
    "MSI",
    "CMG",
    "KR",
    "NEM",
    "EW",
    "PRU",
    "SPG",
    "CCI",
    "CPRT",
    "IDXX",
    "IQV",
    "FANG",
    "FAST",
    "BKR",
    "EXC",
    "VRSK",
    "WTW",
    "VMC",
    "YUM",
    "IR",
    "ED",
    "FIS",
    "EA",
    "DHI",
    "STZ",
    "ON",
    "XEL",
    "CTVA",
    "MLM",
    "PPG",
    "GEHC",
    "O",
    "ACGL",
    "ROK",
    "CBRE",
    "EXR",
    "AWK",
    "DAL",
    "ZBH",
    "HAL",
    "BAX",
    "CF",
    "DXCM",
    "KEYS",
    "CHD",
    "CINF",
    "DPZ",
    "DG",
    "AJG",
    "STE",
    "WST",
    "RMD",
    "MPWR",
    "TSCO",
    "LEN",
    "DLTR",
    "WRB",
    "VLTO",
]

NASDAQ_TICKERS: list[str] = [
    "AAPL",
    "MSFT",
    "AMZN",
    "NVDA",
    "META",
    "GOOGL",
    "GOOG",
    "TSLA",
    "AVGO",
    "COST",
    "NFLX",
    "AMD",
    "ADBE",
    "QCOM",
    "CSCO",
    "TXN",
    "INTU",
    "AMAT",
    "AMGN",
    "HON",
    "ISRG",
    "BKNG",
    "ADI",
    "LRCX",
    "KLAC",
    "SNPS",
    "CDNS",
    "REGN",
    "VRTX",
    "MU",
    "MRVL",
    "PANW",
    "INTC",
    "CRWD",
    "ABNB",
    "FTNT",
    "MCHP",
    "NXPI",
    "ON",
    "MNST",
    "DXCM",
    "IDXX",
    "ROST",
    "FAST",
    "CTAS",
    "CPRT",
    "BIIB",
    "ILMN",
    "MTCH",
    "ALGN",
    "DOCU",
    "SIRI",
    "WDAY",
    "ZM",
    "ZS",
    "OKTA",
    "TEAM",
    "DDOG",
    "SNOW",
    "RBLX",
    "HOOD",
    "SOFI",
    "RIVN",
    "LCID",
    "PINS",
    "SNAP",
    "UBER",
    "LYFT",
    "BYND",
    "ROKU",
    "TWLO",
    "VEEV",
    "NET",
    "BILL",
    "FIVN",
    "GTLB",
    # Binance TradFi-perp single stocks listed on NASDAQ (basis-arb superset,
    # 2026-06-24). Required so BINANCE-FUTURES PERPETUAL tradfi underlyings
    # each map to a captured/enumerated DBEQ.BASIC equity. NASDAQ listing →
    # the adapter routes canonical_venue=NASDAQ off this set.
    "ARM",  # Arm Holdings ADR
    "ASML",  # ASML ADR
    "AAOI",  # Applied Optoelectronics
    "ALAB",  # Astera Labs
    "ASTS",  # AST SpaceMobile
    "AXTI",  # AXT Inc
    "COIN",  # Coinbase
    "CRDO",  # Credo Technology
    "CRWV",  # CoreWeave
    "DKNG",  # DraftKings
    "EBAY",  # eBay
    "FLNC",  # Fluence Energy
    "IREN",  # IREN Limited
    "LITE",  # Lumentum
    "MSTR",  # Strategy (MicroStrategy)
    "NBIS",  # Nebius Group
    "ONDS",  # Ondas Holdings
    "PAYP",  # PayPay ADR
    "PLTR",  # Palantir
    "RKLB",  # Rocket Lab
    "SMCI",  # Super Micro
    "SNDK",  # Sandisk
    "SPCX",  # SpaceX-tracking vehicle
    "USAR",  # USA Rare Earth
    "WDC",  # Western Digital
]

# Binance TradFi-perp single stocks / ADRs listed on NYSE (basis-arb superset,
# 2026-06-24). NYSE listing → adapter default routes canonical_venue=NYSE, so
# these only need to be in the fetched symbol list (added via the universe dict
# below), not in NASDAQ_TICKERS. Kept as a discrete list for provenance.
NYSE_TRADFI_PERP_TICKERS: list[str] = [
    "BE",  # Bloom Energy
    "BMNR",  # BitMine Immersion
    "CFG",  # Citizens Financial
    "CIEN",  # Ciena
    "COHR",  # Coherent
    "CRCL",  # Circle Internet
    "DELL",  # Dell Technologies
    "DIS",  # Walt Disney
    "GLW",  # Corning
    "GME",  # GameStop
    "HIMS",  # Hims & Hers
    "HPE",  # Hewlett Packard Enterprise
    "NOW",  # ServiceNow
    "BABA",  # Alibaba ADR
    "NOK",  # Nokia ADR
    "NVO",  # Novo Nordisk ADR
    "SONY",  # Sony ADR
    "TSM",  # TSMC ADR
]

ETF_TICKERS: list[str] = [
    "SPY",
    "QQQ",
    "IWM",
    "VTI",
    "DIA",
    "EEM",
    "VEA",
    "VWO",
    "GLD",
    "SLV",
    "USO",
    "UNG",
    "TLT",
    "IEF",
    "SHY",
    "LQD",
    "HYG",
    "JNK",
    "XLF",
    "XLE",
    "XLK",
    "XLV",
    "XLI",
    "XLY",
    "XLP",
    "XLB",
    "XLU",
    "XLRE",
    "VNQ",
    "IBB",
    "SMH",
    "ARKK",
    "ARKG",
    "ARKW",
    "ARKF",
    "ARKQ",
    # BTC spot ETFs (all 10 US listings post-2024-01-11)
    "IBIT",
    "FBTC",
    "BITB",
    "ARKB",
    "BTCO",
    "BRRR",
    "HODL",
    "EZBC",
    "GBTC",
    "BITO",
    # ETH spot ETFs (all 8 US listings post-2024-07-23)
    "ETHA",
    "FETH",
    "ETHE",
    "ETHV",
    "ETHW",
    "CETH",
    "QETH",
    "EZET",
    "VIG",
    "VXUS",
    "AGG",
    "BND",
    "VCIT",
    "VCSH",
    "BSV",
    "BNDX",
    "EFA",
    "EWJ",
    "EWZ",
    "FXI",
    "ASHR",
    "MCHI",
    # Binance TradFi-perp index/sector ETFs (basis-arb superset, 2026-06-24).
    "EWT",  # iShares MSCI Taiwan
    "EWY",  # iShares MSCI South Korea
    "ROBO",  # ROBO Global Robotics & Automation
    "SLX",  # VanEck Steel
    "URNM",  # Sprott Uranium Miners
    "UVXY",  # ProShares Ultra VIX Short-Term Futures
    # Commodity/crypto REPRESENTATIVE ETFs for the Binance commodity/crypto perps
    # (operator 2026-06-24): the perp carry trade (short Binance perp + long
    # underlying) works via an ETF too (ETF ~ underlying), so these are valid
    # basis-arb underlyings alongside the CME futures roots. All DBEQ.BASIC-covered
    # (databento primary; verified ohlcv-1m). GLD/SLV/USO/UNG/IBIT/ETHA already
    # above; IAU/PPLT/PALL/CPER are the missing platinum-group + copper + alt-gold.
    "IAU",  # iShares Gold (XAU alt to GLD)
    "PPLT",  # abrdn Physical Platinum (XPT)
    "PALL",  # abrdn Physical Palladium (XPD)
    "CPER",  # United States Copper Index (COPPER)
]

TRADFI_FUTURES_PRODUCTS: list[str] = [
    # CME equity-index
    "ES",
    "MES",
    # CME crypto
    "BTC",
    "MBT",
    "ETH",
    "MET",
    # NYMEX energy
    "CL",
    "MCL",
    "NG",
    "QG",
    # COMEX metals
    "GC",
    "MGC",
    # COMEX platinum-group metals — Binance XPT/XPD perp coverage (2026-06-24).
    "PL",  # platinum (XPT)
    "PA",  # palladium (XPD)
]


TRADFI_TICKER_UNIVERSE: dict[str, list[str]] = {
    "sp500_tickers": SP500_TICKERS,
    "nasdaq_tickers": NASDAQ_TICKERS,
    "nyse_tradfi_perp_tickers": NYSE_TRADFI_PERP_TICKERS,
    "etf_tickers": ETF_TICKERS,
    "futures_products": TRADFI_FUTURES_PRODUCTS,
}

# ──────────────────────────────────────────────────────────────────────────
# TradFi equity/ETF MVP basis universe — the cash-equity twins of the Binance
# (BINANCE-FUTURES PERPETUAL) tradfi-perp underlyings (2026-06-24). These are
# the DBEQ.BASIC equities/ETFs that BACK a crypto-venue equity-perp, so they
# are the BASIS-REFERENCE leg of the equity-basis arb archetype and MUST be
# MVP-scoped (the cash leg the perp is measured against). Index-perps map to
# their ETF proxy (SPX/SPY→SPY, SOXL→SMH, …). Commodities are roots in
# TRADFI_FUTURES_PRODUCTS (PA/PL/GC/SI/HG/NG/CL), gated by the futures rule.
# KRX-only names (HYUNDAI 005380 / SAMSUNG 005930 / SKHYNIX 000660) are now
# UNBLOCKED (2026-06-24): sourced DIRECTLY via venue=KRX / source=yahoo (the
# ``.KS`` tickers in KRX_EQUITIES) — NOT a US-listed ADR twin. They join the
# basis universe by their canonical bare symbol (the KRX numeric code).
# Consumed by the tradfi MVP rule's equity carve-out (mvp_scope.is_mvp).
# Operator 2026-06-24: every Binance tradfi-perp underlying is captured — NOT LESS.
TRADFI_EQUITY_PERP_BASIS_UNIVERSE: frozenset[str] = frozenset(
    {
        "AAOI",
        "AAPL",
        "ADBE",
        "ALAB",
        "AMAT",
        "AMD",
        "AMZN",
        "ARM",
        "ASML",
        "ASTS",
        "AVGO",
        "AXTI",
        "BABA",
        "BE",
        "BMNR",
        "BRK.B",
        "BRKB",
        "CFG",
        "CIEN",
        "COHR",
        "COIN",
        "COST",
        "CRCL",
        "CRDO",
        "CRM",
        "CRWD",
        "CRWV",
        "CSCO",
        "DELL",
        "DIA",
        "DIS",
        "DKNG",
        "EBAY",
        "EWJ",
        "EWT",
        "EWY",
        "EWZ",
        "FLNC",
        "GLW",
        "GME",
        "GOOGL",
        "HD",
        "HIMS",
        "HOOD",
        "HPE",
        "IBM",
        "INTC",
        "IREN",
        "IWM",
        "JPM",
        "KLAC",
        "LITE",
        "LLY",
        "LRCX",
        "META",
        "MRVL",
        "MSFT",
        "MSTR",
        "MU",
        "NBIS",
        "NFLX",
        "NOK",
        "NOW",
        "NVDA",
        "NVO",
        "ONDS",
        "ORCL",
        "PAYP",
        "PLTR",
        "QCOM",
        "QQQ",
        "RIVN",
        "RKLB",
        "ROBO",
        "SLX",
        "SMCI",
        "SMH",
        "SNDK",
        "SONY",
        "SPCX",
        "SPY",
        "TSLA",
        "TSM",
        "UBER",
        "URNM",
        "USAR",
        "UVXY",
        "V",
        "WDC",
        "WMT",
        "XLE",
        "ZM",
        # Commodity/crypto representative ETFs (operator 2026-06-24) — the perp
        # carry trade also works long-ETF (ETF ~ underlying), so these are valid
        # basis-arb cash-leg underlyings for the Binance commodity/crypto perps:
        # XAU→GLD/IAU, XAG→SLV, XPT→PPLT, XPD→PALL, COPPER→CPER, CL→USO,
        # NATGAS→UNG, BTC→IBIT, ETH→ETHA. All DBEQ.BASIC-covered (databento primary).
        "GLD",
        "IAU",
        "SLV",
        "PPLT",
        "PALL",
        "CPER",
        "USO",
        "UNG",
        "IBIT",
        "ETHA",
        # KRX (Korea Exchange) single stocks — venue=KRX, source=yahoo (2026-06-24).
        # The Korean underliers of the Binance tradfi-perps, sourced via Yahoo
        # ``.KS`` tickers (see KRX_EQUITIES). Bare KRX numeric codes; → 103/103.
        "005380",  # Hyundai Motor (005380.KS)
        "005930",  # Samsung Electronics (005930.KS)
        "000660",  # SK Hynix (000660.KS)
    }
)
