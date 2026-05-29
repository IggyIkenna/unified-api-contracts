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
# Built from ``TRADFI_TICKER_UNIVERSE["nasdaq_tickers"]`` — every ticker in
# that universe lists on NASDAQ by construction. A ticker is **not** in
# ``_NYSE`` or ``_ARCA``: mutual exclusivity is asserted by
# :func:`_build_exchange_by_ticker` at import time.
_NASDAQ: Final[frozenset[str]] = frozenset(
    {
        "AAPL",
        "ABNB",
        "ADBE",
        "ADI",
        "AEP",
        "ALGN",
        "AMAT",
        "AMD",
        "AMGN",
        "AMZN",
        "ANSS",
        "ASML",
        "AVGO",
        "BIIB",
        "BILL",
        "BKNG",
        "BYND",
        "CDNS",
        "CEG",
        "CHTR",
        "CMG",
        "COST",
        "CPRT",
        "CRWD",
        "CSCO",
        "CSX",
        "CTAS",
        "DDOG",
        "DLTR",
        "DOCU",
        "DPZ",
        "DXCM",
        "EA",
        "EXC",
        "FANG",
        "FAST",
        "FI",
        "FIVN",
        "FTNT",
        "GILD",
        "GOOG",
        "GOOGL",
        "GTLB",
        "HON",
        "HOOD",
        "IDXX",
        "ILMN",
        "INTC",
        "INTU",
        "ISRG",
        "KLAC",
        "LCID",
        "LRCX",
        "LYFT",
        "MCHP",
        "MDLZ",
        "META",
        "MNST",
        "MRNA",
        "MRVL",
        "MSFT",
        "MTCH",
        "MU",
        "NET",
        "NFLX",
        "NVDA",
        "NXPI",
        "ODFL",
        "OKTA",
        "ON",
        "PANW",
        "PAYX",
        "PCAR",
        "PINS",
        "QCOM",
        "RBLX",
        "REGN",
        "RIVN",
        "ROKU",
        "ROST",
        "SIRI",
        "SNAP",
        "SNOW",
        "SNPS",
        "SOFI",
        "STX",
        "TEAM",
        "TMUS",
        "TSLA",
        "TWLO",
        "TXN",
        "UBER",
        "VEEV",
        "VRSK",
        "VRTX",
        "WDAY",
        "WDC",
        "XEL",
        "ZM",
        "ZS",
    }
)

# NYSE-listed tickers = SP500 universe minus anything listed on NASDAQ/ARCA.
# Derived mechanically from ``TRADFI_TICKER_UNIVERSE["sp500_tickers"]`` —
# the full SP500 list minus known NASDAQ and ARCA members.
_NYSE: Final[frozenset[str]] = frozenset(
    {
        "A",
        "ABBV",
        "ABT",
        "ACGL",
        "ACN",
        "ADSK",
        "AFL",
        "AIG",
        "AJG",
        "AMP",
        "AON",
        "APH",
        "AWK",
        "AXP",
        "AZO",
        "BA",
        "BAC",
        "BAX",
        "BKR",
        "BLK",
        "BRK.B",
        "BSX",
        "C",
        "CARR",
        "CAT",
        "CB",
        "CBRE",
        "CCI",
        "CF",
        "CHD",
        "CI",
        "CINF",
        "CL",
        "CME",
        "COF",
        "CRM",
        "CTVA",
        "CVS",
        "CVX",
        "DAL",
        "DE",
        "DELL",
        "DG",
        "DHI",
        "DHR",
        "DIS",
        "DLR",
        "DUK",
        "ECL",
        "ED",
        "ELV",
        "EMR",
        "EQIX",
        "ETN",
        "EW",
        "EXR",
        "F",
        "FCX",
        "FIS",
        "GD",
        "GE",
        "GEHC",
        "GM",
        "GS",
        "GWW",
        "HAL",
        "HCA",
        "HD",
        "HES",
        "HLT",
        "HPQ",
        "IBM",
        "ICE",
        "IQV",
        "IR",
        "ITW",
        "JNJ",
        "JPM",
        "KEYS",
        "KMB",
        "KO",
        "KR",
        "LEN",
        "LLY",
        "LOW",
        "MA",
        "MCD",
        "MCK",
        "MCO",
        "MLM",
        "MMC",
        "MMM",
        "MO",
        "MPWR",
        "MRK",
        "MS",
        "MSI",
        "MTD",
        "NEM",
        "NKE",
        "NOC",
        "NSC",
        "O",
        "ORCL",
        "ORLY",
        "OXY",
        "PEP",
        "PFE",
        "PG",
        "PGR",
        "PLD",
        "PM",
        "PPG",
        "PRU",
        "PSA",
        "RMD",
        "ROK",
        "ROP",
        "RSG",
        "RTX",
        "SBUX",
        "SHW",
        "SLB",
        "SO",
        "SPG",
        "SPGI",
        "STE",
        "STZ",
        "SYK",
        "T",
        "TDG",
        "TEL",
        "TGT",
        "TMO",
        "TSCO",
        "TT",
        "UNH",
        "UNP",
        "UPS",
        "USB",
        "V",
        "VLTO",
        "VMC",
        "VZ",
        "WELL",
        "WFC",
        "WM",
        "WMT",
        "WRB",
        "WST",
        "WTW",
        "XOM",
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
    }
)

# AMEX-listed (legacy NYSE American) — small set today.
_AMEX: Final[frozenset[str]] = frozenset(set())

# BATS-listed.
_BATS: Final[frozenset[str]] = frozenset(set())


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
