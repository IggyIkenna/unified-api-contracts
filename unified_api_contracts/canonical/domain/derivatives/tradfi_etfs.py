"""TradFi ETF canonical SSOT — Phase 5A (cross_asset_group_catalogue_audit TF-1).

Consolidates 4 fragmented ETF sources into one canonical dict:
- ``KNOWN_ETFS`` in ``tradfi_symbology.py`` (~43 tickers — ETF classifier)
- ``ETF_TICKERS`` in ``tradfi_ticker_universe.py`` (~59 tickers — superset)
- ``_BTC_SPOT_ETFS`` / ``_ETH_SPOT_ETFS`` in ``tradfi_instrument_universe.py``
- ``TRADFI_TICKER_COVERAGE_START`` ETF subset in ``coverage_starts.py``

SSOT for ETF classification, coverage start dates, and crypto-underlying metadata.
Migration of consumers from the 4 source files to this module: Phase 6 scope.

SSOT: cross_asset_group_catalogue_audit_2026_05_10.md Phase 5A (TF-1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ETFMetadata:
    """Canonical metadata for a TradFi ETF instrument.

    Attributes:
        ticker: Primary exchange ticker (SPY, IBIT, etc.).
        category: Instrument category (see CATEGORY_* constants below).
        underlying: Human-readable underlying asset/index name.
        listing_date: Earliest data available (None = pre-2003 Databento floor).
            Only populated for ETFs with explicit coverage-start overrides (mostly
            newer crypto ETFs where data pre-dates the Databento universal floor).
        issuer: Fund issuer (None if not catalogued).
        in_known_etfs: Whether ticker appears in legacy ``KNOWN_ETFS`` classifier set.
        crypto_underlying: For crypto ETFs: "BTC" or "ETH"; None otherwise.
    """

    ticker: str
    category: str
    underlying: str
    listing_date: date | None = None
    issuer: str | None = None
    in_known_etfs: bool = True
    crypto_underlying: str | None = None


# Category constants
CATEGORY_EQUITY = "equity"
CATEGORY_INTERNATIONAL = "international"
CATEGORY_FIXED_INCOME = "fixed_income"
CATEGORY_COMMODITY = "commodity"
CATEGORY_SECTOR = "sector"
CATEGORY_CRYPTO_SPOT = "crypto_spot"
CATEGORY_CRYPTO_FUTURES = "crypto_futures"


TRADFI_ETFS: dict[str, ETFMetadata] = {
    # ── US broad-market equity ──────────────────────────────────────────────
    "SPY": ETFMetadata("SPY", CATEGORY_EQUITY, "SP500", issuer="SPDR"),
    "QQQ": ETFMetadata("QQQ", CATEGORY_EQUITY, "NASDAQ100", issuer="Invesco"),
    "IVV": ETFMetadata("IVV", CATEGORY_EQUITY, "SP500", issuer="iShares"),
    "VOO": ETFMetadata("VOO", CATEGORY_EQUITY, "SP500", issuer="Vanguard"),
    "VTI": ETFMetadata("VTI", CATEGORY_EQUITY, "US_TOTAL_MARKET", issuer="Vanguard"),
    "DIA": ETFMetadata("DIA", CATEGORY_EQUITY, "DOW", issuer="SPDR"),
    "IWM": ETFMetadata("IWM", CATEGORY_EQUITY, "RUSSELL2000", issuer="iShares"),
    # Active (ARK)
    "ARKK": ETFMetadata("ARKK", CATEGORY_EQUITY, "ARK_INNOVATION", issuer="ARK"),
    "ARKG": ETFMetadata("ARKG", CATEGORY_EQUITY, "ARK_GENOMICS", issuer="ARK"),
    "ARKW": ETFMetadata("ARKW", CATEGORY_EQUITY, "ARK_NEXT_GEN_INTERNET", issuer="ARK"),
    "ARKF": ETFMetadata("ARKF", CATEGORY_EQUITY, "ARK_FINTECH", issuer="ARK"),
    "ARKQ": ETFMetadata("ARKQ", CATEGORY_EQUITY, "ARK_AUTONOMOUS_TECH", issuer="ARK"),
    # Dividend growth (in ETF_TICKERS, not KNOWN_ETFS)
    "VIG": ETFMetadata("VIG", CATEGORY_EQUITY, "US_DIVIDEND_GROWTH", issuer="Vanguard", in_known_etfs=False),
    # ── International / Emerging Markets ───────────────────────────────────
    "EEM": ETFMetadata("EEM", CATEGORY_INTERNATIONAL, "EMERGING_MARKETS", issuer="iShares"),
    "VEA": ETFMetadata("VEA", CATEGORY_INTERNATIONAL, "DEVELOPED_EX_US", issuer="Vanguard"),
    "VWO": ETFMetadata("VWO", CATEGORY_INTERNATIONAL, "EMERGING_MARKETS", issuer="Vanguard"),
    "VXUS": ETFMetadata("VXUS", CATEGORY_INTERNATIONAL, "EX_US_TOTAL_MARKET", issuer="Vanguard", in_known_etfs=False),
    "EFA": ETFMetadata("EFA", CATEGORY_INTERNATIONAL, "MSCI_EAFE", issuer="iShares", in_known_etfs=False),
    "EWJ": ETFMetadata("EWJ", CATEGORY_INTERNATIONAL, "JAPAN", issuer="iShares", in_known_etfs=False),
    "EWZ": ETFMetadata("EWZ", CATEGORY_INTERNATIONAL, "BRAZIL", issuer="iShares", in_known_etfs=False),
    "FXI": ETFMetadata("FXI", CATEGORY_INTERNATIONAL, "CHINA_LARGE_CAP", issuer="iShares", in_known_etfs=False),
    "ASHR": ETFMetadata("ASHR", CATEGORY_INTERNATIONAL, "CHINA_A_SHARES", issuer="Xtrackers", in_known_etfs=False),
    "MCHI": ETFMetadata("MCHI", CATEGORY_INTERNATIONAL, "CHINA_MIDCAP", issuer="iShares", in_known_etfs=False),
    # ── Commodity ──────────────────────────────────────────────────────────
    "GLD": ETFMetadata("GLD", CATEGORY_COMMODITY, "GOLD", issuer="SPDR"),
    "SLV": ETFMetadata("SLV", CATEGORY_COMMODITY, "SILVER", issuer="iShares"),
    "USO": ETFMetadata("USO", CATEGORY_COMMODITY, "CRUDE_OIL", issuer="USCF"),
    "UNG": ETFMetadata("UNG", CATEGORY_COMMODITY, "NATURAL_GAS", issuer="USCF"),
    # ── Fixed income ───────────────────────────────────────────────────────
    "TLT": ETFMetadata("TLT", CATEGORY_FIXED_INCOME, "US_TREASURY_20Y", issuer="iShares"),
    "IEF": ETFMetadata("IEF", CATEGORY_FIXED_INCOME, "US_TREASURY_10Y", issuer="iShares"),
    "SHY": ETFMetadata("SHY", CATEGORY_FIXED_INCOME, "US_TREASURY_1_3Y", issuer="iShares"),
    "LQD": ETFMetadata("LQD", CATEGORY_FIXED_INCOME, "US_CORP_INVESTMENT_GRADE", issuer="iShares"),
    "HYG": ETFMetadata("HYG", CATEGORY_FIXED_INCOME, "US_HIGH_YIELD", issuer="iShares"),
    "JNK": ETFMetadata("JNK", CATEGORY_FIXED_INCOME, "US_HIGH_YIELD", issuer="SPDR"),
    "AGG": ETFMetadata("AGG", CATEGORY_FIXED_INCOME, "US_AGGREGATE_BOND", issuer="iShares", in_known_etfs=False),
    "BND": ETFMetadata("BND", CATEGORY_FIXED_INCOME, "US_TOTAL_BOND", issuer="Vanguard", in_known_etfs=False),
    "VCIT": ETFMetadata("VCIT", CATEGORY_FIXED_INCOME, "US_CORP_INTERMEDIATE", issuer="Vanguard", in_known_etfs=False),
    "VCSH": ETFMetadata("VCSH", CATEGORY_FIXED_INCOME, "US_CORP_SHORT", issuer="Vanguard", in_known_etfs=False),
    "BSV": ETFMetadata("BSV", CATEGORY_FIXED_INCOME, "US_SHORT_TERM_BOND", issuer="Vanguard", in_known_etfs=False),
    "BNDX": ETFMetadata("BNDX", CATEGORY_FIXED_INCOME, "INTL_BOND", issuer="Vanguard", in_known_etfs=False),
    # ── Sector (SPDR + niche) ───────────────────────────────────────────────
    "XLF": ETFMetadata("XLF", CATEGORY_SECTOR, "FINANCIALS", issuer="SPDR"),
    "XLE": ETFMetadata("XLE", CATEGORY_SECTOR, "ENERGY", issuer="SPDR"),
    "XLK": ETFMetadata("XLK", CATEGORY_SECTOR, "TECHNOLOGY", issuer="SPDR"),
    "XLV": ETFMetadata("XLV", CATEGORY_SECTOR, "HEALTHCARE", issuer="SPDR"),
    "XLI": ETFMetadata("XLI", CATEGORY_SECTOR, "INDUSTRIALS", issuer="SPDR"),
    "XLY": ETFMetadata("XLY", CATEGORY_SECTOR, "CONSUMER_DISCRETIONARY", issuer="SPDR"),
    "XLP": ETFMetadata("XLP", CATEGORY_SECTOR, "CONSUMER_STAPLES", issuer="SPDR"),
    "XLB": ETFMetadata("XLB", CATEGORY_SECTOR, "MATERIALS", issuer="SPDR"),
    "XLU": ETFMetadata("XLU", CATEGORY_SECTOR, "UTILITIES", issuer="SPDR"),
    "XLRE": ETFMetadata("XLRE", CATEGORY_SECTOR, "REAL_ESTATE", issuer="SPDR"),
    "VNQ": ETFMetadata("VNQ", CATEGORY_SECTOR, "REAL_ESTATE", issuer="Vanguard"),
    "IBB": ETFMetadata("IBB", CATEGORY_SECTOR, "BIOTECH", issuer="iShares"),
    "SMH": ETFMetadata("SMH", CATEGORY_SECTOR, "SEMICONDUCTORS", issuer="VanEck"),
    # ── Crypto spot ETFs (BTC) — listing-date overrides required ───────────
    # Listing date = 2024-01-11 (SEC approval + first trading day for BTC spot ETFs).
    # GBTC converted from trust to ETF on the same date.
    "IBIT": ETFMetadata(
        "IBIT", CATEGORY_CRYPTO_SPOT, "BTC",
        listing_date=date(2024, 1, 11), issuer="iShares", crypto_underlying="BTC",
    ),
    "FBTC": ETFMetadata(
        "FBTC", CATEGORY_CRYPTO_SPOT, "BTC",
        listing_date=date(2024, 1, 11), issuer="Fidelity", crypto_underlying="BTC",
    ),
    "ARKB": ETFMetadata(
        "ARKB", CATEGORY_CRYPTO_SPOT, "BTC",
        listing_date=date(2024, 1, 11), issuer="ARK/21Shares", crypto_underlying="BTC",
    ),
    "GBTC": ETFMetadata(
        "GBTC", CATEGORY_CRYPTO_SPOT, "BTC",
        listing_date=date(2024, 1, 11), issuer="Grayscale", crypto_underlying="BTC",
    ),
    # ── Crypto spot ETFs (ETH) ─────────────────────────────────────────────
    # Listing date = 2024-07-23 (SEC approval for ETH spot ETFs).
    # NOT in KNOWN_ETFS (legacy classifier set predates ETH ETF approval).
    "ETHA": ETFMetadata(
        "ETHA", CATEGORY_CRYPTO_SPOT, "ETH",
        listing_date=date(2024, 7, 23), issuer="iShares", in_known_etfs=False, crypto_underlying="ETH",
    ),
    "FETH": ETFMetadata(
        "FETH", CATEGORY_CRYPTO_SPOT, "ETH",
        listing_date=date(2024, 7, 23), issuer="Fidelity", in_known_etfs=False, crypto_underlying="ETH",
    ),
    "ETHE": ETFMetadata(
        "ETHE", CATEGORY_CRYPTO_SPOT, "ETH",
        listing_date=date(2024, 7, 23), issuer="Grayscale", in_known_etfs=False, crypto_underlying="ETH",
    ),
    # ── Crypto futures ETF ─────────────────────────────────────────────────
    "BITO": ETFMetadata(
        "BITO", CATEGORY_CRYPTO_FUTURES, "BTC_FUTURES",
        listing_date=date(2021, 10, 19), issuer="ProShares", crypto_underlying="BTC",
    ),
}


# ---------------------------------------------------------------------------
# Derived sets — consumers should use these rather than re-deriving from TRADFI_ETFS
# ---------------------------------------------------------------------------

ALL_ETF_TICKERS: frozenset[str] = frozenset(TRADFI_ETFS)

KNOWN_ETFS_TICKERS: frozenset[str] = frozenset(
    t for t, m in TRADFI_ETFS.items() if m.in_known_etfs
)

CRYPTO_ETF_TICKERS: frozenset[str] = frozenset(
    t for t, m in TRADFI_ETFS.items()
    if m.category in (CATEGORY_CRYPTO_SPOT, CATEGORY_CRYPTO_FUTURES)
)

BTC_ETF_TICKERS: frozenset[str] = frozenset(
    t for t, m in TRADFI_ETFS.items() if m.crypto_underlying == "BTC"
)

ETH_ETF_TICKERS: frozenset[str] = frozenset(
    t for t, m in TRADFI_ETFS.items() if m.crypto_underlying == "ETH"
)

ETF_LISTING_DATES: dict[str, date] = {
    t: m.listing_date
    for t, m in TRADFI_ETFS.items()
    if m.listing_date is not None
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_etf(ticker: str) -> bool:
    """Return True if ``ticker`` is a known TradFi ETF."""
    return ticker in TRADFI_ETFS


def get_etf_category(ticker: str) -> str | None:
    """Return the category string for ``ticker``, or None if not an ETF."""
    meta = TRADFI_ETFS.get(ticker)
    return meta.category if meta is not None else None


def get_etf_listing_date(ticker: str) -> date | None:
    """Return the listing/coverage-start date for ``ticker``, or None."""
    meta = TRADFI_ETFS.get(ticker)
    return meta.listing_date if meta is not None else None


def get_crypto_etfs(underlying: str | None = None) -> list[str]:
    """Return crypto ETF tickers, optionally filtered by underlying ("BTC" or "ETH")."""
    return [
        t for t, m in TRADFI_ETFS.items()
        if m.category in (CATEGORY_CRYPTO_SPOT, CATEGORY_CRYPTO_FUTURES)
        and (underlying is None or m.crypto_underlying == underlying)
    ]


__all__ = [
    "ALL_ETF_TICKERS",
    "BTC_ETF_TICKERS",
    "CATEGORY_COMMODITY",
    "CATEGORY_CRYPTO_FUTURES",
    "CATEGORY_CRYPTO_SPOT",
    "CATEGORY_EQUITY",
    "CATEGORY_FIXED_INCOME",
    "CATEGORY_INTERNATIONAL",
    "CATEGORY_SECTOR",
    "CRYPTO_ETF_TICKERS",
    "ETF_LISTING_DATES",
    "ETH_ETF_TICKERS",
    "KNOWN_ETFS_TICKERS",
    "TRADFI_ETFS",
    "ETFMetadata",
    "get_crypto_etfs",
    "get_etf_category",
    "get_etf_listing_date",
    "is_etf",
]
