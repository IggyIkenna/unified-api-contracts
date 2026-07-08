"""Ticker registry — human-readable underlying names + ticker→exchange mapping.

This module is the SSOT for two questions the canonical layer asks about
every raw TradFi ticker:

1. **What is the human-readable name of the underlying?** For example:
   ``ES`` → ``SP500``, ``CL`` → ``WTI``, ``6A`` → ``AUDUSD``, ``ZN`` →
   ``UST-10Y``. Canonical instrument IDs should always use the readable
   form so a glance at a GCS path tells you what instrument you are
   looking at.
2. **Which exchange does an equity/ETF ticker list on?** For example:
   ``AAPL`` → ``NASDAQ``, ``MMM`` → ``NYSE``, ``SPY`` → ``ARCA``.

Both mappings are **strict**: unknown inputs raise :class:`ValueError`.
No ``UNKNOWN`` sentinel, no fuzzy matching. The burden is on callers to
add missing tickers to the appropriate mapping rather than let
mis-classified rows flow downstream.

The underlying normalisation aligns with existing UAC
``EXCHANGE_CODE_TO_NAME`` (``registry/tradfi_symbology.py``) and the
CME/ICE/CBOE futures universe but uses **display-friendly** names
(``SP500``, ``UST-10Y``, ``AUDUSD``) rather than the legacy
``SP500``/``EUR``/``TNOTE10Y`` mix — this is the module that anchors the
convention going forward.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "EXCHANGE_BY_TICKER",
    "UNDERLYING_NORMALIZATION",
    "normalize_underlying",
    "resolve_exchange",
]


# ---------------------------------------------------------------------------
# Underlying normalisation — raw source code → human-readable canonical name
# ---------------------------------------------------------------------------

UNDERLYING_NORMALIZATION: Final[dict[str, str]] = {
    # --- CME Index Futures ---
    "ES": "SP500",
    "NQ": "NASDAQ100",
    "RTY": "RUSSELL2000",
    "YM": "DOW",
    "EMD": "SP400",  # S&P MidCap 400 e-mini
    # --- CME Energy ---
    "CL": "WTI",
    "NG": "NAT-GAS",
    "RB": "RBOB-GAS",
    "HO": "HEATING-OIL",
    # --- CME Metals ---
    "GC": "GOLD",
    "SI": "SILVER",
    "HG": "COPPER",
    "PL": "PLATINUM",
    "PA": "PALLADIUM",
    # --- CME Grains / Ags ---
    "ZC": "CORN",
    "ZW": "WHEAT",
    "KE": "KC-WHEAT",
    "ZS": "SOYBEAN",
    "ZM": "SOYMEAL",
    "ZL": "SOYOIL",
    # --- CME Interest Rates (Treasuries) ---
    "ZT": "UST-2Y",
    "ZF": "UST-5Y",
    "ZN": "UST-10Y",
    "TN": "UST-ULTRA10Y",
    "ZB": "UST-30Y",
    "UB": "UST-ULTRA30Y",
    # --- CME STIR / SOFR ---
    "SR1": "SOFR-1M",
    "SR3": "SOFR-3M",
    # --- CME FX Futures (6X shape) ---
    "6A": "AUDUSD",
    "6B": "GBPUSD",
    "6C": "CADUSD",
    "6E": "EURUSD",
    "6J": "JPYUSD",
    "6S": "CHFUSD",
    "6N": "NZDUSD",
    "6M": "MXNUSD",
    "6L": "BRLUSD",
    "6R": "RUBUSD",
    "6Z": "ZARUSD",
    # --- CME Livestock ---
    "LE": "LIVE-CATTLE",
    "GF": "FEEDER-CATTLE",
    "HE": "LEAN-HOG",
    # --- CBOE / CFE Volatility ---
    "VX": "VIX",
    # --- ICE Futures US ---
    "CT": "COTTON",
    "CC": "COCOA",
    "KC": "COFFEE",
    "SB": "SUGAR",
    "OJ": "ORANGE-JUICE",
    "DX": "DXY",
    # --- ICE Futures Europe ---
    "BRN": "BRENT",
    "G": "GASOIL",
    "T": "WTI-ICE",
}


# ---------------------------------------------------------------------------
# Exchange by ticker — equity / ETF ticker → listing exchange
# ---------------------------------------------------------------------------
# Canonical values: ``NASDAQ``, ``NYSE``, ``ARCA``, ``AMEX``, ``BATS``.
#
# Coverage goal: every ticker in ``TRADFI_TICKER_UNIVERSE`` (SP500, NASDAQ,
# ETF lists) must resolve. Tests assert full coverage — missing tickers MUST
# be added here, not routed to ``UNKNOWN``.

# NASDAQ-listed tickers (Nasdaq Composite / Nasdaq-100 / SP500-∩-NASDAQ members).
# Expanded 2026-07-08 alongside the SP500_TICKERS restoration (200 -> 503 real
# current S&P 500 constituents, tradfi_ticker_universe.py) — every NASDAQ-listed
# member of the real current S&P 500 is included here (source: the same
# Wikipedia "List of S&P 500 companies" live-page parse, cross-checked per-row
# against each ticker's Nasdaq/NYSE symbol-template link), plus the pre-existing
# NASDAQ_TICKERS / Binance TradFi-perp members. A ticker is **not** in
# ``_NYSE`` or ``_ARCA``: mutual exclusivity is asserted by
# :func:`_build_exchange_by_ticker` at import time.
_NASDAQ: Final[frozenset[str]] = frozenset(
    {
        "AAOI",
        "AAPL",
        "ABNB",
        "ACGL",
        "ADBE",
        "ADI",
        "ADP",
        "ADSK",
        "AEP",
        "AKAM",
        "ALAB",
        "ALGN",
        "AMAT",
        "AMD",
        "AMGN",
        "AMZN",
        "ANSS",
        "APA",
        "APP",
        "ARM",
        "ASML",
        "ASTS",
        "AVGO",
        "AXON",
        "AXTI",
        "BIIB",
        "BILL",
        "BKNG",
        "BKR",
        "BYND",
        "CASY",
        "CDNS",
        "CDW",
        "CEG",
        "CHRW",
        "CHTR",
        "CINF",
        "CME",
        "CMCSA",
        "COIN",
        "COO",
        "COST",
        "CPRT",
        "CRDO",
        "CRWD",
        "CRWV",
        "CSCO",
        "CSGP",
        "CSX",
        "CTAS",
        "CTSH",
        "DASH",
        "DDOG",
        "DKNG",
        "DLTR",
        "DOCU",
        "DXCM",
        "EA",
        "EBAY",
        "ECHO",
        "EQIX",
        "ERIE",
        "EXC",
        "EXE",
        "EXPD",
        "EXPE",
        "FANG",
        "FAST",
        "FFIV",
        "FISV",
        "FIVN",
        "FLEX",
        "FLNC",
        "FOX",
        "FOXA",
        "FSLR",
        "FTNT",
        "GEHC",
        "GEN",
        "GILD",
        "GOOG",
        "GOOGL",
        "GTLB",
        "HAS",
        "HBAN",
        "HON",
        "HONA",
        "HOOD",
        "HSIC",
        "HST",
        "IBKR",
        "IDXX",
        "ILMN",
        "INCY",
        "INTC",
        "INTU",
        "IREN",
        "ISRG",
        "JBHT",
        "JKHY",
        "KDP",
        "KHC",
        "KLAC",
        "KMB",
        "LCID",
        "LIN",
        "LITE",
        "LNT",
        "LRCX",
        "LULU",
        "LYFT",
        "MAR",
        "MCHP",
        "MDLZ",
        "META",
        "MNST",
        "MPWR",
        "MRNA",
        "MRVL",
        "MSFT",
        "MSTR",
        "MTCH",
        "MU",
        "NBIS",
        "NDAQ",
        "NDSN",
        "NET",
        "NFLX",
        "NTAP",
        "NTRS",
        "NVDA",
        "NWS",
        "NWSA",
        "NXPI",
        "ODFL",
        "OKTA",
        "ON",
        "ONDS",
        "ORLY",
        "PANW",
        "PAYP",
        "PAYX",
        "PCAR",
        "PEP",
        "PFG",
        "PINS",
        "PLTR",
        "PODD",
        "PSKY",
        "PTC",
        "PYPL",
        "QCOM",
        "RBLX",
        "REG",
        "REGN",
        "RIVN",
        "RKLB",
        "ROKU",
        "ROP",
        "ROST",
        "SBAC",
        "SBUX",
        "SIRI",
        "SMCI",
        "SNAP",
        "SNDK",
        "SNOW",
        "SNPS",
        "SOFI",
        "SPCX",
        "STLD",
        "STX",
        "SWKS",
        "TEAM",
        "TECH",
        "TER",
        "TMUS",
        "TRMB",
        "TROW",
        "TSCO",
        "TSLA",
        "TTD",
        "TTWO",
        "TWLO",
        "TXN",
        "UAL",
        "ULTA",
        "USAR",
        "VRSK",
        "VRSN",
        "VRTX",
        "VTRS",
        "WBD",
        "WDAY",
        "WDC",
        "WMT",
        "WTW",
        "WYNN",
        "XEL",
        "ZBRA",
        "ZM",
        "ZS",
    }
)

# NYSE-listed tickers = SP500 universe minus anything listed on NASDAQ/ARCA.
# Expanded 2026-07-08 alongside the SP500_TICKERS restoration (200 -> 503 real
# current S&P 500 constituents, tradfi_ticker_universe.py) — every NYSE-listed
# member of the real current S&P 500 is included here (source: the same
# Wikipedia "List of S&P 500 companies" live-page parse, cross-checked per-row
# against each ticker's NYSE/Nasdaq symbol-template link), plus the pre-existing
# NYSE_TRADFI_PERP_TICKERS members. Four tickers moved here FROM `_NASDAQ`
# (CMG, DPZ, UBER, VEEV — the live page shows them NYSE-listed, correcting the
# prior hand-curated mapping) and sixteen moved OUT to `_NASDAQ` (ACGL, ADSK,
# BKR, CINF, CME, EQIX, GEHC, KMB, MPWR, ORLY, PEP, ROP, SBUX, TSCO, WMT, WTW).
_NYSE: Final[frozenset[str]] = frozenset(
    {
        "A",
        "ABBV",
        "ABT",
        "ACN",
        "ADM",
        "AEE",
        "AES",
        "AFL",
        "AIG",
        "AIZ",
        "AJG",
        "ALB",
        "ALL",
        "ALLE",
        "AMCR",
        "AME",
        "AMT",
        "AMP",
        "ANET",
        "AON",
        "AOS",
        "APD",
        "APH",
        "APO",
        "APTV",
        "ARE",
        "ARES",
        "ATO",
        "AVB",
        "AVY",
        "AWK",
        "AXP",
        "AZO",
        "BA",
        "BABA",
        "BAC",
        "BALL",
        "BAX",
        "BBY",
        "BDX",
        "BE",
        "BEN",
        "BF.B",
        "BG",
        "BLDR",
        "BLK",
        "BMNR",
        "BMY",
        "BNY",
        "BR",
        "BRK.B",
        "BRO",
        "BSX",
        "BX",
        "BXP",
        "C",
        "CAH",
        "CARR",
        "CAT",
        "CB",
        "CBRE",
        "CCI",
        "CCL",
        "CF",
        "CFG",
        "CHD",
        "CI",
        "CIEN",
        "CL",
        "CLX",
        "CMG",
        "CMI",
        "CMS",
        "CNC",
        "CNP",
        "COF",
        "COHR",
        "COP",
        "COR",
        "CPAY",
        "CPT",
        "CRCL",
        "CRH",
        "CRL",
        "CRM",
        "CTVA",
        "CVNA",
        "CVS",
        "CVX",
        "D",
        "DAL",
        "DD",
        "DE",
        "DECK",
        "DELL",
        "DG",
        "DGX",
        "DHI",
        "DHR",
        "DIS",
        "DLR",
        "DOC",
        "DOV",
        "DOW",
        "DPZ",
        "DRI",
        "DTE",
        "DUK",
        "DVA",
        "DVN",
        "ECL",
        "ED",
        "EFX",
        "EG",
        "EIX",
        "EL",
        "ELV",
        "EME",
        "EMR",
        "EOG",
        "EQR",
        "EQT",
        "ES",
        "ESS",
        "ETN",
        "ETR",
        "EVRG",
        "EW",
        "EXR",
        "F",
        "FCX",
        "FDS",
        "FDX",
        "FDXF",
        "FE",
        "FICO",
        "FIS",
        "FITB",
        "FIX",
        "FRT",
        "FTV",
        "GD",
        "GDDY",
        "GE",
        "GEV",
        "GIS",
        "GL",
        "GLW",
        "GM",
        "GME",
        "GNRC",
        "GPC",
        "GPN",
        "GRMN",
        "GS",
        "GWW",
        "HAL",
        "HCA",
        "HD",
        "HIG",
        "HII",
        "HIMS",
        "HLT",
        "HPE",
        "HPQ",
        "HRL",
        "HSY",
        "HUBB",
        "HUM",
        "HWM",
        "IBM",
        "ICE",
        "IEX",
        "IFF",
        "INVH",
        "IP",
        "IQV",
        "IR",
        "IRM",
        "IT",
        "ITW",
        "IVZ",
        "J",
        "JBL",
        "JCI",
        "JNJ",
        "JPM",
        "KEY",
        "KEYS",
        "KIM",
        "KKR",
        "KMI",
        "KO",
        "KR",
        "KVUE",
        "L",
        "LDOS",
        "LEN",
        "LH",
        "LHX",
        "LII",
        "LLY",
        "LMT",
        "LOW",
        "LUV",
        "LVS",
        "LYB",
        "LYV",
        "MA",
        "MAA",
        "MAS",
        "MCD",
        "MCK",
        "MCO",
        "MDT",
        "MET",
        "MGM",
        "MKC",
        "MLM",
        "MMM",
        "MO",
        "MOS",
        "MPC",
        "MRK",
        "MRSH",
        "MS",
        "MSCI",
        "MSI",
        "MTB",
        "MTD",
        "NCLH",
        "NEE",
        "NEM",
        "NI",
        "NKE",
        "NOC",
        "NOK",
        "NOW",
        "NRG",
        "NSC",
        "NUE",
        "NVO",
        "NVR",
        "O",
        "OKE",
        "OMC",
        "ORCL",
        "OTIS",
        "OXY",
        "PCG",
        "PEG",
        "PFE",
        "PG",
        "PGR",
        "PH",
        "PHM",
        "PKG",
        "PLD",
        "PM",
        "PNC",
        "PNR",
        "PNW",
        "PPG",
        "PPL",
        "PRU",
        "PSA",
        "PSX",
        "PWR",
        "Q",
        "RCL",
        "RF",
        "RJF",
        "RL",
        "RMD",
        "ROK",
        "ROL",
        "RSG",
        "RTX",
        "RVTY",
        "SCHW",
        "SHW",
        "SJM",
        "SLB",
        "SNA",
        "SO",
        "SOLV",
        "SONY",
        "SPG",
        "SPGI",
        "SRE",
        "STE",
        "STT",
        "STZ",
        "SW",
        "SWK",
        "SYF",
        "SYK",
        "SYY",
        "T",
        "TAP",
        "TDG",
        "TDY",
        "TEL",
        "TFC",
        "TGT",
        "TJX",
        "TKO",
        "TMO",
        "TPL",
        "TPR",
        "TRGP",
        "TRV",
        "TSM",
        "TSN",
        "TT",
        "TXT",
        "TYL",
        "UBER",
        "UDR",
        "UHS",
        "UNH",
        "UNP",
        "UPS",
        "URI",
        "USB",
        "V",
        "VEEV",
        "VICI",
        "VLO",
        "VLTO",
        "VMC",
        "VRT",
        "VST",
        "VTR",
        "VZ",
        "WAB",
        "WAT",
        "WEC",
        "WELL",
        "WFC",
        "WM",
        "WMB",
        "WRB",
        "WSM",
        "WST",
        "WY",
        "XOM",
        "XYL",
        "XYZ",
        "YUM",
        "ZBH",
        "ZTS",
    }
)

# ARCA-listed ETFs and ETPs (NYSE Arca is the primary US ETF venue).
_ARCA: Final[frozenset[str]] = frozenset(
    {
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
        "IVV",
        "VOO",
        # Binance TradFi-perp index/sector ETFs (basis-arb superset, 2026-06-24)
        "EWT",
        "EWY",
        "ROBO",
        "SLX",
        "URNM",
        "UVXY",
        # Commodity/crypto representative ETFs (basis-arb cash leg, 2026-06-24)
        "IAU",
        "PPLT",
        "PALL",
        "CPER",
    }
)

# AMEX-listed (legacy NYSE American) — small set today.
_AMEX: Final[frozenset[str]] = frozenset(set())

# BATS-listed (Cboe BZX Exchange, the modern name for the exchange formerly
# branded "BATS" after Cboe's 2017 acquisition of BATS Global Markets).
# CBOE (Cboe Global Markets Inc — the S&P 500 member) added 2026-07-08: its
# own stock lists on its own Cboe BZX exchange, not NYSE/Nasdaq (confirmed via
# the Wikipedia S&P 500 live-page parse — the one non-NYSE/Nasdaq row).
_BATS: Final[frozenset[str]] = frozenset({"CBOE"})


def _build_exchange_by_ticker() -> dict[str, str]:
    """Compose the ticker→exchange mapping from the per-venue frozensets.

    A ticker appearing in more than one set raises ``ValueError`` when
    the module is first loaded — enforces the SSOT: every ticker
    resolves to exactly one exchange.
    """
    mapping: dict[str, str] = {}
    for venue, tickers in (
        ("NASDAQ", _NASDAQ),
        ("NYSE", _NYSE),
        ("ARCA", _ARCA),
        ("AMEX", _AMEX),
        ("BATS", _BATS),
    ):
        for ticker in tickers:
            if ticker in mapping:
                msg = (
                    f"Duplicate ticker {ticker!r} in ticker_registry: "
                    f"already mapped to {mapping[ticker]!r}, cannot re-map to {venue!r}"
                )
                raise ValueError(msg)
            mapping[ticker] = venue
    return mapping


EXCHANGE_BY_TICKER: Final[dict[str, str]] = _build_exchange_by_ticker()


# ---------------------------------------------------------------------------
# Resolvers — strict, fail-loud
# ---------------------------------------------------------------------------


def normalize_underlying(raw_code: str) -> str:
    """Return the human-readable canonical name for a raw underlying code.

    Examples
    --------
    ``normalize_underlying("ES") == "SP500"``
    ``normalize_underlying("6E") == "EURUSD"``
    ``normalize_underlying("ZN") == "UST-10Y"``

    Parameters
    ----------
    raw_code:
        The exchange/source code (upper-case by convention; we upper-case
        internally so callers don't have to).

    Raises
    ------
    ValueError
        If ``raw_code`` is empty or not present in
        :data:`UNDERLYING_NORMALIZATION`. Add the missing code to the
        mapping rather than catch this exception.
    """
    if not raw_code:
        msg = "normalize_underlying: raw_code must be a non-empty string"
        raise ValueError(msg)
    key = raw_code.strip().upper()
    if key not in UNDERLYING_NORMALIZATION:
        msg = (
            f"normalize_underlying: unknown underlying code {raw_code!r}. "
            "Add it to UNDERLYING_NORMALIZATION in ticker_registry.py."
        )
        raise ValueError(msg)
    return UNDERLYING_NORMALIZATION[key]


def resolve_exchange(ticker: str) -> str:
    """Return the listing exchange for an equity/ETF ticker.

    Examples
    --------
    ``resolve_exchange("AAPL") == "NASDAQ"``
    ``resolve_exchange("SPY")  == "ARCA"``
    ``resolve_exchange("MMM")  == "NYSE"``

    Parameters
    ----------
    ticker:
        The equity/ETF ticker (upper-case by convention; we upper-case
        internally). Class suffixes such as ``BRK.B`` are preserved.

    Raises
    ------
    ValueError
        If ``ticker`` is empty or not registered in
        :data:`EXCHANGE_BY_TICKER`. Add the missing ticker to the
        appropriate venue frozenset rather than catch this exception.
    """
    if not ticker:
        msg = "resolve_exchange: ticker must be a non-empty string"
        raise ValueError(msg)
    key = ticker.strip().upper()
    if key not in EXCHANGE_BY_TICKER:
        msg = (
            f"resolve_exchange: unknown ticker {ticker!r}. "
            "Add it to _NASDAQ/_NYSE/_ARCA/_AMEX/_BATS in ticker_registry.py."
        )
        raise ValueError(msg)
    return EXCHANGE_BY_TICKER[key]
