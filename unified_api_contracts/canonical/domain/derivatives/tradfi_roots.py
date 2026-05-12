"""TradFi futures-root canonical SSOT — Phase 5B (cross_asset_group_catalogue_audit TF-2).

Consolidates 3 fragmented futures-root sources into one canonical dict:
- ``TRADFI_INSTRUMENTS`` in ``tradfi_symbology.py`` (provider-agnostic instrument list)
- ``TRADFI_DATABENTO_INSTRUMENTS`` in ``tradfi_instrument_universe.py`` (Databento-specific)
- ``SUPPORTED_UNDERLYINGS`` in ``databento_cme_converter.py`` (5-root converter scope)

SSOT for root-product classification, exchange/dataset routing, micro-contract
relationships, options availability, and converter scope flags.
Migration of consumers from the 3 source files to this module: Phase 6 scope.

SSOT: cross_asset_group_catalogue_audit_2026_05_10.md Phase 5B (TF-2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RootMetadata:
    """Canonical metadata for a TradFi futures/options root product.

    Attributes:
        root: Root symbol (ES, NQ, BTC, VX, …).
        category: Product category (see CATEGORY_* constants below).
        underlying: Human-readable underlying name (SP500, CRUDE, BTC, …).
        exchange: Primary exchange (CME, ICE, CFE, CBOE).
        dataset: Databento dataset ID; None for non-Databento sources (VIX spot).
        asset_group: Asset-group vocab key (equity/commodity/fx/fixed_income/crypto).
        has_options: Whether an options chain exists for this root.
        parent_root: For micro contracts: the full-size parent (MES→ES, MBT→BTC).
        micro_root: For full-size contracts: the micro variant (ES→MES, BTC→MBT).
        options_parent: For ES options sub-series: the parent futures root (EW→ES).
        expiry_series: For options sub-series: human description of expiry schedule.
        listing_date: First Databento-available date; None = pre-2003 floor applies.
        in_supported_underlyings: In ``SUPPORTED_UNDERLYINGS`` options-converter set.
    """

    root: str
    category: str
    underlying: str
    exchange: str
    dataset: str | None
    asset_group: str
    has_options: bool = False
    parent_root: str | None = None
    micro_root: str | None = None
    options_parent: str | None = None
    expiry_series: str | None = None
    listing_date: date | None = None
    in_supported_underlyings: bool = False


# Category constants
CATEGORY_INDEX_FUTURES = "index_futures"
CATEGORY_ENERGY_FUTURES = "energy_futures"
CATEGORY_METALS_FUTURES = "metals_futures"
CATEGORY_GRAINS_FUTURES = "grains_futures"
CATEGORY_FIXED_INCOME_FUTURES = "fixed_income_futures"
CATEGORY_FX_FUTURES = "fx_futures"
CATEGORY_LIVESTOCK_FUTURES = "livestock_futures"
CATEGORY_SECTOR_FUTURES = "sector_futures"
CATEGORY_CRYPTO_FUTURES = "crypto_futures"
CATEGORY_ICE_FUTURES = "ice_futures"
CATEGORY_VOLATILITY_FUTURES = "volatility_futures"
CATEGORY_VOLATILITY_INDEX = "volatility_index"
CATEGORY_OPTIONS_CLUSTER = "options_cluster"
CATEGORY_EVENT_CONTRACT = "event_contract"

# Databento dataset constants
DATASET_CME = "GLBX.MDP3"
DATASET_ICE_EUROPE = "IFEU.IMPACT"
DATASET_ICE_US = "IFUS.IMPACT"
DATASET_CBOE_CFE = "XCBF.PITCH"


TRADFI_ROOTS: dict[str, RootMetadata] = {
    # ── CME Index Futures ──────────────────────────────────────────────────
    "ES": RootMetadata(
        "ES", CATEGORY_INDEX_FUTURES, "SP500", "CME", DATASET_CME, "equity",
        has_options=True, micro_root="MES", in_supported_underlyings=True,
    ),
    "NQ": RootMetadata(
        "NQ", CATEGORY_INDEX_FUTURES, "NASDAQ100", "CME", DATASET_CME, "equity",
        has_options=True, in_supported_underlyings=True,
    ),
    "RTY": RootMetadata("RTY", CATEGORY_INDEX_FUTURES, "RUSSELL2000", "CME", DATASET_CME, "equity"),
    "YM": RootMetadata("YM", CATEGORY_INDEX_FUTURES, "DOW", "CME", DATASET_CME, "equity"),
    "NKD": RootMetadata("NKD", CATEGORY_INDEX_FUTURES, "NIKKEI225", "CME", DATASET_CME, "equity"),
    # Micro E-mini S&P 500 (1/10 notional; same monthly expiry + dataset)
    "MES": RootMetadata(
        "MES", CATEGORY_INDEX_FUTURES, "SP500", "CME", DATASET_CME, "equity",
        parent_root="ES", listing_date=date(2019, 5, 6),
    ),
    # ── CME Energy Futures ─────────────────────────────────────────────────
    "CL": RootMetadata(
        "CL", CATEGORY_ENERGY_FUTURES, "CRUDE", "CME", DATASET_CME, "commodity",
        has_options=True, in_supported_underlyings=True,
    ),
    "NG": RootMetadata(
        "NG", CATEGORY_ENERGY_FUTURES, "NATGAS", "CME", DATASET_CME, "commodity",
        has_options=True, in_supported_underlyings=True,
    ),
    "HO": RootMetadata("HO", CATEGORY_ENERGY_FUTURES, "HEATING_OIL", "CME", DATASET_CME, "commodity"),
    "RB": RootMetadata("RB", CATEGORY_ENERGY_FUTURES, "GASOLINE", "CME", DATASET_CME, "commodity"),
    # ── CME Metals Futures ─────────────────────────────────────────────────
    "GC": RootMetadata(
        "GC", CATEGORY_METALS_FUTURES, "GOLD", "CME", DATASET_CME, "commodity",
        has_options=True, in_supported_underlyings=True,
    ),
    "SI": RootMetadata("SI", CATEGORY_METALS_FUTURES, "SILVER", "CME", DATASET_CME, "commodity"),
    "HG": RootMetadata("HG", CATEGORY_METALS_FUTURES, "COPPER", "CME", DATASET_CME, "commodity"),
    "PL": RootMetadata("PL", CATEGORY_METALS_FUTURES, "PLATINUM", "CME", DATASET_CME, "commodity"),
    # ── CME Grains Futures ─────────────────────────────────────────────────
    "ZC": RootMetadata("ZC", CATEGORY_GRAINS_FUTURES, "CORN", "CME", DATASET_CME, "commodity"),
    "ZW": RootMetadata("ZW", CATEGORY_GRAINS_FUTURES, "WHEAT", "CME", DATASET_CME, "commodity"),
    "ZS": RootMetadata("ZS", CATEGORY_GRAINS_FUTURES, "SOYBEANS", "CME", DATASET_CME, "commodity"),
    "ZL": RootMetadata("ZL", CATEGORY_GRAINS_FUTURES, "SOYBEAN_OIL", "CME", DATASET_CME, "commodity"),
    "ZM": RootMetadata("ZM", CATEGORY_GRAINS_FUTURES, "SOYBEAN_MEAL", "CME", DATASET_CME, "commodity"),
    # ── CME Fixed Income Futures ───────────────────────────────────────────
    "ZB": RootMetadata("ZB", CATEGORY_FIXED_INCOME_FUTURES, "TREASURY_30Y", "CME", DATASET_CME, "fixed_income"),
    "ZN": RootMetadata("ZN", CATEGORY_FIXED_INCOME_FUTURES, "TREASURY_10Y", "CME", DATASET_CME, "fixed_income"),
    "ZF": RootMetadata("ZF", CATEGORY_FIXED_INCOME_FUTURES, "TREASURY_5Y", "CME", DATASET_CME, "fixed_income"),
    "ZT": RootMetadata("ZT", CATEGORY_FIXED_INCOME_FUTURES, "TREASURY_2Y", "CME", DATASET_CME, "fixed_income"),
    # ── CME FX Futures ─────────────────────────────────────────────────────
    "6E": RootMetadata("6E", CATEGORY_FX_FUTURES, "EUR", "CME", DATASET_CME, "fx"),
    "6B": RootMetadata("6B", CATEGORY_FX_FUTURES, "GBP", "CME", DATASET_CME, "fx"),
    "6J": RootMetadata("6J", CATEGORY_FX_FUTURES, "JPY", "CME", DATASET_CME, "fx"),
    "6A": RootMetadata("6A", CATEGORY_FX_FUTURES, "AUD", "CME", DATASET_CME, "fx"),
    "6C": RootMetadata("6C", CATEGORY_FX_FUTURES, "CAD", "CME", DATASET_CME, "fx"),
    "6S": RootMetadata("6S", CATEGORY_FX_FUTURES, "CHF", "CME", DATASET_CME, "fx"),
    "6N": RootMetadata("6N", CATEGORY_FX_FUTURES, "NZD", "CME", DATASET_CME, "fx"),
    "6L": RootMetadata("6L", CATEGORY_FX_FUTURES, "BRL", "CME", DATASET_CME, "fx"),
    "6Z": RootMetadata("6Z", CATEGORY_FX_FUTURES, "ZAR", "CME", DATASET_CME, "fx"),
    "6M": RootMetadata("6M", CATEGORY_FX_FUTURES, "MXN", "CME", DATASET_CME, "fx"),
    # ── CME Livestock Futures ──────────────────────────────────────────────
    "LE": RootMetadata("LE", CATEGORY_LIVESTOCK_FUTURES, "LIVECATTLE", "CME", DATASET_CME, "commodity"),
    "HE": RootMetadata("HE", CATEGORY_LIVESTOCK_FUTURES, "LEANHOGS", "CME", DATASET_CME, "commodity"),
    # ── CME Sector Futures (E-mini Select Sector) ──────────────────────────
    "XAF": RootMetadata("XAF", CATEGORY_SECTOR_FUTURES, "ENERGY_SECTOR", "CME", DATASET_CME, "equity"),
    "XAK": RootMetadata("XAK", CATEGORY_SECTOR_FUTURES, "TECH_SECTOR", "CME", DATASET_CME, "equity"),
    "XAY": RootMetadata("XAY", CATEGORY_SECTOR_FUTURES, "CONSUMER_DISC_SECTOR", "CME", DATASET_CME, "equity"),
    "XAP": RootMetadata("XAP", CATEGORY_SECTOR_FUTURES, "CONSUMER_STAPLES_SECTOR", "CME", DATASET_CME, "equity"),
    "XAV": RootMetadata("XAV", CATEGORY_SECTOR_FUTURES, "HEALTHCARE_SECTOR", "CME", DATASET_CME, "equity"),
    "XAI": RootMetadata("XAI", CATEGORY_SECTOR_FUTURES, "INDUSTRIALS_SECTOR", "CME", DATASET_CME, "equity"),
    "XAB": RootMetadata("XAB", CATEGORY_SECTOR_FUTURES, "MATERIALS_SECTOR", "CME", DATASET_CME, "equity"),
    "XAU": RootMetadata("XAU", CATEGORY_SECTOR_FUTURES, "UTILITIES_SECTOR", "CME", DATASET_CME, "equity"),
    # ── CME Crypto Futures ─────────────────────────────────────────────────
    "BTC": RootMetadata(
        "BTC", CATEGORY_CRYPTO_FUTURES, "BTC", "CME", DATASET_CME, "crypto",
        micro_root="MBT", listing_date=date(2017, 12, 18),
    ),
    "ETH": RootMetadata(
        "ETH", CATEGORY_CRYPTO_FUTURES, "ETH", "CME", DATASET_CME, "crypto",
        micro_root="MET", listing_date=date(2021, 2, 8),
    ),
    # Micro CME crypto futures (1/10 notional; same monthly expiry calendar)
    "MBT": RootMetadata(
        "MBT", CATEGORY_CRYPTO_FUTURES, "BTC", "CME", DATASET_CME, "crypto",
        parent_root="BTC", listing_date=date(2021, 5, 3),
    ),
    "MET": RootMetadata(
        "MET", CATEGORY_CRYPTO_FUTURES, "ETH", "CME", DATASET_CME, "crypto",
        parent_root="ETH", listing_date=date(2021, 10, 4),
    ),
    # ── ICE Futures Europe ─────────────────────────────────────────────────
    "BRN": RootMetadata("BRN", CATEGORY_ICE_FUTURES, "BRENT", "ICE", DATASET_ICE_EUROPE, "commodity"),
    "G": RootMetadata("G", CATEGORY_ICE_FUTURES, "GASOIL", "ICE", DATASET_ICE_EUROPE, "commodity"),
    # ── CBOE / CFE Volatility ──────────────────────────────────────────────
    # VX: VIX futures on CBOE Futures Exchange (CFE). XCBF.PITCH supports only
    # raw_symbol stype_in (explicit contract codes like VXH6); parent symbology
    # not available. Front-month symbols must be generated from target date.
    "VX": RootMetadata(
        "VX", CATEGORY_VOLATILITY_FUTURES, "VIX", "CFE", DATASET_CBOE_CFE, "equity",
    ),
    # VIX spot index — calculated by CBOE, sourced via yahoo_finance (not Databento).
    "VIX": RootMetadata("VIX", CATEGORY_VOLATILITY_INDEX, "VIX", "CBOE", None, "equity"),
    # ── CME ES Options Sub-Series ──────────────────────────────────────────
    # ES quarterly options (3rd Friday of Mar/Jun/Sep/Dec)
    "EW": RootMetadata(
        "EW", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="weekly_friday",
    ),
    "EW1": RootMetadata(
        "EW1", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="weekly_monday",
    ),
    "EW2": RootMetadata(
        "EW2", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="weekly_wednesday",
    ),
    "EW4": RootMetadata(
        "EW4", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="weekly_tuesday",
    ),
    "E1A": RootMetadata(
        "E1A", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="daily_monday_0dte",
    ),
    "E2A": RootMetadata(
        "E2A", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="daily_tuesday_0dte",
    ),
    "E3A": RootMetadata(
        "E3A", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="daily_wednesday_0dte",
    ),
    "E4A": RootMetadata(
        "E4A", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="daily_thursday_0dte",
    ),
    "E5A": RootMetadata(
        "E5A", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="daily_friday_0dte",
    ),
    "EOM": RootMetadata(
        "EOM", CATEGORY_OPTIONS_CLUSTER, "SP500", "CME", DATASET_CME, "equity",
        options_parent="ES", expiry_series="end_of_month",
    ),
    # ── CME Event Contracts ────────────────────────────────────────────────
    # Binary YES/NO settlement; classified as OPTIONS by Databento (parent stype).
    # Databento coverage starts 2025-09-28.
    "ECES": RootMetadata(
        "ECES", CATEGORY_EVENT_CONTRACT, "SP500", "CME", DATASET_CME, "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECNQ": RootMetadata(
        "ECNQ", CATEGORY_EVENT_CONTRACT, "NASDAQ100", "CME", DATASET_CME, "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECRTY": RootMetadata(
        "ECRTY", CATEGORY_EVENT_CONTRACT, "RUSSELL2000", "CME", DATASET_CME, "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECYM": RootMetadata(
        "ECYM", CATEGORY_EVENT_CONTRACT, "DOW", "CME", DATASET_CME, "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECGC": RootMetadata(
        "ECGC", CATEGORY_EVENT_CONTRACT, "GOLD", "CME", DATASET_CME, "commodity",
        listing_date=date(2025, 9, 28),
    ),
    "ECCL": RootMetadata(
        "ECCL", CATEGORY_EVENT_CONTRACT, "CRUDE", "CME", DATASET_CME, "commodity",
        listing_date=date(2025, 9, 28),
    ),
    "ECNG": RootMetadata(
        "ECNG", CATEGORY_EVENT_CONTRACT, "NATGAS", "CME", DATASET_CME, "commodity",
        listing_date=date(2025, 9, 28),
    ),
    "EC6E": RootMetadata(
        "EC6E", CATEGORY_EVENT_CONTRACT, "EUR", "CME", DATASET_CME, "fx",
        listing_date=date(2025, 9, 28),
    ),
    "ECBTC": RootMetadata(
        "ECBTC", CATEGORY_EVENT_CONTRACT, "BTC", "CME", DATASET_CME, "crypto",
        listing_date=date(2025, 9, 28),
    ),
}


# ---------------------------------------------------------------------------
# Derived sets — consumers should use these rather than re-deriving
# ---------------------------------------------------------------------------

ALL_ROOT_SYMBOLS: frozenset[str] = frozenset(TRADFI_ROOTS)

CME_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.exchange == "CME"
)

ICE_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.exchange == "ICE"
)

OPTIONS_ENABLED_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.has_options
)

# Roots currently supported by the Databento CME options converter
# (SUPPORTED_UNDERLYINGS in databento_cme_converter.py).
SUPPORTED_CONVERTER_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.in_supported_underlyings
)

CRYPTO_FUTURE_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.category == CATEGORY_CRYPTO_FUTURES
)

MICRO_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.parent_root is not None
)

ES_OPTIONS_CLUSTER_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items()
    if m.category == CATEGORY_OPTIONS_CLUSTER and m.options_parent == "ES"
)

EVENT_CONTRACT_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.category == CATEGORY_EVENT_CONTRACT
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_tradfi_root(root: str) -> bool:
    """Return True if ``root`` is a known TradFi futures/options root."""
    return root in TRADFI_ROOTS


def get_root_category(root: str) -> str | None:
    """Return the category string for ``root``, or None if unknown."""
    meta = TRADFI_ROOTS.get(root)
    return meta.category if meta is not None else None


def get_roots_by_category(category: str) -> list[str]:
    """Return all root symbols matching ``category``."""
    return [r for r, m in TRADFI_ROOTS.items() if m.category == category]


__all__ = [
    "ALL_ROOT_SYMBOLS",
    "CATEGORY_CRYPTO_FUTURES",
    "CATEGORY_ENERGY_FUTURES",
    "CATEGORY_EVENT_CONTRACT",
    "CATEGORY_FIXED_INCOME_FUTURES",
    "CATEGORY_FX_FUTURES",
    "CATEGORY_GRAINS_FUTURES",
    "CATEGORY_ICE_FUTURES",
    "CATEGORY_INDEX_FUTURES",
    "CATEGORY_LIVESTOCK_FUTURES",
    "CATEGORY_METALS_FUTURES",
    "CATEGORY_OPTIONS_CLUSTER",
    "CATEGORY_SECTOR_FUTURES",
    "CATEGORY_VOLATILITY_FUTURES",
    "CATEGORY_VOLATILITY_INDEX",
    "CME_ROOTS",
    "CRYPTO_FUTURE_ROOTS",
    "DATASET_CBOE_CFE",
    "DATASET_CME",
    "DATASET_ICE_EUROPE",
    "DATASET_ICE_US",
    "ES_OPTIONS_CLUSTER_ROOTS",
    "EVENT_CONTRACT_ROOTS",
    "ICE_ROOTS",
    "MICRO_ROOTS",
    "OPTIONS_ENABLED_ROOTS",
    "SUPPORTED_CONVERTER_ROOTS",
    "TRADFI_ROOTS",
    "RootMetadata",
    "get_root_category",
    "get_roots_by_category",
    "is_tradfi_root",
]
