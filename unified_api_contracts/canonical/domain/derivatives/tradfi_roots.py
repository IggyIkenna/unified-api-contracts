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
# CFE = Cboe Futures Exchange — the third subscribed feed (operator 2026-06-18),
# carrying VX/VIX futures. Databento's dataset CODE for the Cboe Futures Exchange
# is ``XCBF.PITCH`` (verified live 2026-06-19 via metadata.get_dataset_range — a
# bare ``CFE`` is rejected by the Databento API with 400 validation_failed; the
# operator's "CFE subscription" is the entitlement to XCBF.PITCH, which covers
# 2018-11-04→now and exposes definition/ohlcv-1s/ohlcv-1m). The constant name keeps
# the CFE label (the exchange) while the value is the Databento dataset id.
DATASET_CBOE_CFE = "XCBF.PITCH"


TRADFI_ROOTS: dict[str, RootMetadata] = {
    # ── CME Index Futures ──────────────────────────────────────────────────
    "ES": RootMetadata(
        "ES",
        CATEGORY_INDEX_FUTURES,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        has_options=True,
        micro_root="MES",
        in_supported_underlyings=True,
    ),
    "NQ": RootMetadata(
        "NQ",
        CATEGORY_INDEX_FUTURES,
        "NASDAQ100",
        "CME",
        DATASET_CME,
        "equity",
        has_options=True,
        in_supported_underlyings=True,
    ),
    "RTY": RootMetadata("RTY", CATEGORY_INDEX_FUTURES, "RUSSELL2000", "CME", DATASET_CME, "equity"),
    "YM": RootMetadata("YM", CATEGORY_INDEX_FUTURES, "DOW", "CME", DATASET_CME, "equity"),
    "NKD": RootMetadata("NKD", CATEGORY_INDEX_FUTURES, "NIKKEI225", "CME", DATASET_CME, "equity"),
    # Micro E-mini S&P 500 (1/10 notional; same monthly expiry + dataset)
    "MES": RootMetadata(
        "MES",
        CATEGORY_INDEX_FUTURES,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        parent_root="ES",
        listing_date=date(2019, 5, 6),
    ),
    # ── CME Energy Futures ─────────────────────────────────────────────────
    "CL": RootMetadata(
        "CL",
        CATEGORY_ENERGY_FUTURES,
        "CRUDE",
        "CME",
        DATASET_CME,
        "commodity",
        has_options=True,
        in_supported_underlyings=True,
    ),
    "NG": RootMetadata(
        "NG",
        CATEGORY_ENERGY_FUTURES,
        "NATGAS",
        "CME",
        DATASET_CME,
        "commodity",
        has_options=True,
        in_supported_underlyings=True,
    ),
    "HO": RootMetadata("HO", CATEGORY_ENERGY_FUTURES, "HEATING_OIL", "CME", DATASET_CME, "commodity"),
    "RB": RootMetadata("RB", CATEGORY_ENERGY_FUTURES, "GASOLINE", "CME", DATASET_CME, "commodity"),
    # ── CME Metals Futures ─────────────────────────────────────────────────
    "GC": RootMetadata(
        "GC",
        CATEGORY_METALS_FUTURES,
        "GOLD",
        "CME",
        DATASET_CME,
        "commodity",
        has_options=True,
        in_supported_underlyings=True,
    ),
    "SI": RootMetadata("SI", CATEGORY_METALS_FUTURES, "SILVER", "CME", DATASET_CME, "commodity"),
    "HG": RootMetadata("HG", CATEGORY_METALS_FUTURES, "COPPER", "CME", DATASET_CME, "commodity"),
    "PL": RootMetadata("PL", CATEGORY_METALS_FUTURES, "PLATINUM", "CME", DATASET_CME, "commodity"),
    "PA": RootMetadata("PA", CATEGORY_METALS_FUTURES, "PALLADIUM", "CME", DATASET_CME, "commodity"),
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
        "BTC",
        CATEGORY_CRYPTO_FUTURES,
        "BTC",
        "CME",
        DATASET_CME,
        "crypto",
        micro_root="MBT",
        listing_date=date(2017, 12, 18),
    ),
    "ETH": RootMetadata(
        "ETH",
        CATEGORY_CRYPTO_FUTURES,
        "ETH",
        "CME",
        DATASET_CME,
        "crypto",
        micro_root="MET",
        listing_date=date(2021, 2, 8),
    ),
    # Micro CME crypto futures (1/10 notional; same monthly expiry calendar)
    "MBT": RootMetadata(
        "MBT",
        CATEGORY_CRYPTO_FUTURES,
        "BTC",
        "CME",
        DATASET_CME,
        "crypto",
        parent_root="BTC",
        listing_date=date(2021, 5, 3),
    ),
    "MET": RootMetadata(
        "MET",
        CATEGORY_CRYPTO_FUTURES,
        "ETH",
        "CME",
        DATASET_CME,
        "crypto",
        parent_root="ETH",
        listing_date=date(2021, 10, 4),
    ),
    # ── ICE Futures Europe ─────────────────────────────────────────────────
    "BRN": RootMetadata("BRN", CATEGORY_ICE_FUTURES, "BRENT", "ICE", DATASET_ICE_EUROPE, "commodity"),
    "G": RootMetadata("G", CATEGORY_ICE_FUTURES, "GASOIL", "ICE", DATASET_ICE_EUROPE, "commodity"),
    # T = WTI Crude Oil Futures on ICE Europe (separate from CME's CL light-sweet
    # crude). Same dataset/stype pattern as BRN/G — IFEU.IMPACT parent symbology.
    # Legacy presence: tradfi_symbology.py TRADFI_INSTRUMENTS+TRADFI_DATA_BINDINGS;
    # NOT in tradfi_instrument_universe.py (omission, not ambiguity).
    "T": RootMetadata("T", CATEGORY_ICE_FUTURES, "WTI", "ICE", DATASET_ICE_EUROPE, "commodity"),
    # ── ICE Futures US (Softs) ────────────────────────────────────────────────
    # All 6 trade on ICE Futures US (IFUS.IMPACT). Disambiguation: CT is ICE, NOT
    # CME — tradfi_instrument_universe.py had a data-entry error (CME/GLBX.MDP3).
    # DX (US Dollar Index) is classified as fx despite trading as a futures contract
    # because its underlying is a currency basket, not a commodity.
    "CT": RootMetadata("CT", CATEGORY_ICE_FUTURES, "COTTON", "ICE", DATASET_ICE_US, "commodity"),
    "CC": RootMetadata("CC", CATEGORY_ICE_FUTURES, "COCOA", "ICE", DATASET_ICE_US, "commodity"),
    "KC": RootMetadata("KC", CATEGORY_ICE_FUTURES, "COFFEE", "ICE", DATASET_ICE_US, "commodity"),
    "SB": RootMetadata("SB", CATEGORY_ICE_FUTURES, "SUGAR", "ICE", DATASET_ICE_US, "commodity"),
    "OJ": RootMetadata("OJ", CATEGORY_ICE_FUTURES, "OJ", "ICE", DATASET_ICE_US, "commodity"),
    "DX": RootMetadata("DX", CATEGORY_ICE_FUTURES, "DOLLARINDEX", "ICE", DATASET_ICE_US, "fx"),
    # ── CBOE / CFE Volatility ──────────────────────────────────────────────
    # VX: VIX futures on CBOE Futures Exchange (CFE dataset, the subscribed feed).
    "VX": RootMetadata(
        "VX",
        CATEGORY_VOLATILITY_FUTURES,
        "VIX",
        "CFE",
        DATASET_CBOE_CFE,
        "equity",
    ),
    # VIX spot index — calculated by CBOE, sourced via yahoo_finance (not Databento).
    "VIX": RootMetadata("VIX", CATEGORY_VOLATILITY_INDEX, "VIX", "CBOE", None, "equity"),
    # ── CME ES Options Sub-Series ──────────────────────────────────────────
    # ES quarterly options (3rd Friday of Mar/Jun/Sep/Dec)
    "EW": RootMetadata(
        "EW",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="weekly_friday",
    ),
    "EW1": RootMetadata(
        "EW1",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="weekly_monday",
    ),
    "EW2": RootMetadata(
        "EW2",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="weekly_wednesday",
    ),
    "EW4": RootMetadata(
        "EW4",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="weekly_tuesday",
    ),
    "E1A": RootMetadata(
        "E1A",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="daily_monday_0dte",
    ),
    "E2A": RootMetadata(
        "E2A",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="daily_tuesday_0dte",
    ),
    "E3A": RootMetadata(
        "E3A",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="daily_wednesday_0dte",
    ),
    "E4A": RootMetadata(
        "E4A",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="daily_thursday_0dte",
    ),
    "E5A": RootMetadata(
        "E5A",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="daily_friday_0dte",
    ),
    "EOM": RootMetadata(
        "EOM",
        CATEGORY_OPTIONS_CLUSTER,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        options_parent="ES",
        expiry_series="end_of_month",
    ),
    # ── CME Event Contracts ────────────────────────────────────────────────
    # Binary YES/NO settlement; classified as OPTIONS by Databento (parent stype).
    # Databento coverage starts 2025-09-28.
    "ECES": RootMetadata(
        "ECES",
        CATEGORY_EVENT_CONTRACT,
        "SP500",
        "CME",
        DATASET_CME,
        "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECNQ": RootMetadata(
        "ECNQ",
        CATEGORY_EVENT_CONTRACT,
        "NASDAQ100",
        "CME",
        DATASET_CME,
        "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECRTY": RootMetadata(
        "ECRTY",
        CATEGORY_EVENT_CONTRACT,
        "RUSSELL2000",
        "CME",
        DATASET_CME,
        "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECYM": RootMetadata(
        "ECYM",
        CATEGORY_EVENT_CONTRACT,
        "DOW",
        "CME",
        DATASET_CME,
        "equity",
        listing_date=date(2025, 9, 28),
    ),
    "ECGC": RootMetadata(
        "ECGC",
        CATEGORY_EVENT_CONTRACT,
        "GOLD",
        "CME",
        DATASET_CME,
        "commodity",
        listing_date=date(2025, 9, 28),
    ),
    "ECCL": RootMetadata(
        "ECCL",
        CATEGORY_EVENT_CONTRACT,
        "CRUDE",
        "CME",
        DATASET_CME,
        "commodity",
        listing_date=date(2025, 9, 28),
    ),
    "ECNG": RootMetadata(
        "ECNG",
        CATEGORY_EVENT_CONTRACT,
        "NATGAS",
        "CME",
        DATASET_CME,
        "commodity",
        listing_date=date(2025, 9, 28),
    ),
    "EC6E": RootMetadata(
        "EC6E",
        CATEGORY_EVENT_CONTRACT,
        "EUR",
        "CME",
        DATASET_CME,
        "fx",
        listing_date=date(2025, 9, 28),
    ),
    "ECBTC": RootMetadata(
        "ECBTC",
        CATEGORY_EVENT_CONTRACT,
        "BTC",
        "CME",
        DATASET_CME,
        "crypto",
        listing_date=date(2025, 9, 28),
    ),
}


# ---------------------------------------------------------------------------
# Derived sets — consumers should use these rather than re-deriving
# ---------------------------------------------------------------------------

ALL_ROOT_SYMBOLS: frozenset[str] = frozenset(TRADFI_ROOTS)

CME_ROOTS: frozenset[str] = frozenset(r for r, m in TRADFI_ROOTS.items() if m.exchange == "CME")

ICE_ROOTS: frozenset[str] = frozenset(r for r, m in TRADFI_ROOTS.items() if m.exchange == "ICE")

OPTIONS_ENABLED_ROOTS: frozenset[str] = frozenset(r for r, m in TRADFI_ROOTS.items() if m.has_options)

# Roots currently supported by the Databento CME options converter
# (SUPPORTED_UNDERLYINGS in databento_cme_converter.py).
SUPPORTED_CONVERTER_ROOTS: frozenset[str] = frozenset(r for r, m in TRADFI_ROOTS.items() if m.in_supported_underlyings)

CRYPTO_FUTURE_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.category == CATEGORY_CRYPTO_FUTURES
)

MICRO_ROOTS: frozenset[str] = frozenset(r for r, m in TRADFI_ROOTS.items() if m.parent_root is not None)

ES_OPTIONS_CLUSTER_ROOTS: frozenset[str] = frozenset(
    r for r, m in TRADFI_ROOTS.items() if m.category == CATEGORY_OPTIONS_CLUSTER and m.options_parent == "ES"
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


# ---------------------------------------------------------------------------
# Reverse lookup: manifest-captured spelled-out underlying name -> short root
# code (issue: tradfi_combo_underlying_naming_mismatch_blocks_g1_enum_present_
# rollup_2026_07_28.md). TradFi COMBO/futures_chain/options_chain captures in
# the market-tick-data manifest sometimes carry a SPELLED-OUT underlying value
# ("HEATING-OIL", "PLATINUM") instead of the catalog's short root-code
# convention ("HO", "PL") this registry uses. This is the query-time
# reconciliation half (direction 2 of the issue's two candidate directions);
# the writer-side normalization (direction 1, MTDS `venue_fetch.py`/
# `manifest_finalize.py`) is a separate follow-up.
# ---------------------------------------------------------------------------


def _normalize_underlying_name(name: str) -> str:
    """Fold a spelled-out underlying string to one comparable form.

    Uppercases and collapses hyphens/spaces/underscores to a single ``_``
    separator so ``"HEATING-OIL"``, ``"HEATING_OIL"``, and ``"Heating Oil"``
    all fold to the same key. No fuzzy matching — this is a pure, deterministic
    string fold; anything it doesn't line up with is a real near-miss handled
    (or knowingly left unresolved) via ``_MANIFEST_UNDERLYING_ALIASES`` below.
    """
    folded = name.strip().upper()
    for sep in ("-", " "):
        folded = folded.replace(sep, "_")
    while "__" in folded:
        folded = folded.replace("__", "_")
    return folded.strip("_")


def _build_underlying_name_to_root_index() -> dict[str, str]:
    """Build the ``RootMetadata.underlying`` (normalized) -> ``root`` index.

    Built once at import time — never rebuilt per call.

    Only "primary" roots participate as index VALUES (a name should reverse-
    resolve to the one product root a combo/futures_chain/options_chain
    capture actually means, not to an arbitrary variant sharing the same
    underlying):

    - micro contracts (``parent_root is not None``, e.g. MES/MBT/MET) are
      skipped — a spelled underlying name resolves to the full-size root.
    - options sub-series (``options_parent is not None``, e.g. EW/EW1/E1A)
      are skipped — resolves to the underlying future root, not the option
      cluster root.
    - event contracts (``CATEGORY_EVENT_CONTRACT``, e.g. ECGC/ECCL) are
      skipped — same underlying as the plain future root; resolves there.

    Where a genuine ambiguity survives this filter (e.g. "VIX" is the
    ``underlying`` of both the VX future and the VIX spot-index root), the
    first-declared root in ``TRADFI_ROOTS`` insertion order wins and later
    duplicates are dropped — deterministic, not arbitrary.
    """
    index: dict[str, str] = {}
    for root, meta in TRADFI_ROOTS.items():
        if meta.parent_root is not None:
            continue
        if meta.options_parent is not None:
            continue
        if meta.category == CATEGORY_EVENT_CONTRACT:
            continue
        key = _normalize_underlying_name(meta.underlying)
        if key not in index:
            index[key] = root
    return index


_UNDERLYING_NAME_TO_ROOT: dict[str, str] = _build_underlying_name_to_root_index()


# Real manifest `underlying` spellings that do NOT fold cleanly onto a
# TRADFI_ROOTS `underlying` value even after normalization — each verified via
# a direct probe of the live prod market-data-tick-tradfi manifest's
# `_index/availability_index.parquet` (bucket via resolve_bucket_name()),
# `instrument_type` in {COMBO, combo}, 2026-07-28; row counts are the
# distinct-value counts seen in that probe, not estimates). Exact + documented,
# not fuzzy-derived — this is a data-correctness-sensitive lookup.
#
# NOT included here (left to correctly resolve to None — honest absence, not
# a single-root concept): composite/spread values that name TWO roots at once
# (e.g. "WTI-BZ", "WTI-MCL", "NKD-NIY", "LIVE-CATTLE-LEAN-HOG", "WHEAT-CORN",
# "RBOB-GAS-HEATING-OIL") and the ~1,200 distinct calendar/butterfly spread
# *type* codes ("GN", "VT", "12", "3W", "CFO", "IB", ...) and raw composite
# ICE instrument-id strings (e.g. "ICE:COMBO:G   FMV0025_Z") that leak into
# the manifest's `underlying` column for a subset of ICE combo rows — these
# are a distinct writer-side data-quality residual, not a naming-convention
# near-miss this alias table can honestly resolve to one root.
_MANIFEST_UNDERLYING_ALIASES: dict[str, str] = {
    # NatGas family: registry key "NG" has underlying="NATGAS"; the manifest
    # carries the Henry-Hub hub/contract-type qualifier as a suffix.
    "NAT-GAS": "NG",  # 3,291 rows
    "NAT-GAS-HH": "NG",  # 3,288 rows (Henry Hub)
    "NAT-GAS-MNG": "NG",  # 1,354 rows (Henry Hub Last-Day Financial "MNG")
    "NAT-GAS-QG": "NG",  # 1,252 rows (Henry Hub Penultimate "QG")
    "NAT-GAS-NN": "NG",  # 16 rows
    # RBOB gasoline: registry "RB" underlying="GASOLINE"; manifest uses the
    # RBOB acronym instead.
    "RBOB-GAS": "RB",  # 3,189 rows
    # Livestock: registry underlying values are single-word/no-separator
    # ("LIVECATTLE", "LEANHOGS"); manifest hyphenates and (for hogs) drops the
    # plural "S".
    "LIVE-CATTLE": "LE",  # 3,247 rows
    "LEAN-HOG": "HE",  # 3,245 rows
    # Soy family: registry underlying values are full compound words
    # ("SOYBEANS", "SOYBEAN_OIL", "SOYBEAN_MEAL"); manifest abbreviates.
    "SOYBEAN": "ZS",  # 2,931 rows (registry: "SOYBEANS", plural)
    "SOYOIL": "ZL",  # 3,049 rows (registry: "SOYBEAN_OIL")
    "SOYMEAL": "ZM",  # 3,052 rows (registry: "SOYBEAN_MEAL")
    # US Treasuries: registry underlying values are "TREASURY_<tenor>"; the
    # manifest uses the "UST-<tenor>" convention instead.
    "UST-10Y": "ZN",  # 2,993 rows
    "UST-30Y": "ZB",  # 2,922 rows
    "UST-5Y": "ZF",  # 2,730 rows
    "UST-2Y": "ZT",  # 2,618 rows
    # FX futures: registry underlying values are the bare currency code
    # ("EUR", "GBP", ...); the manifest uses the currency-PAIR convention
    # against USD instead.
    "EURUSD": "6E",  # 3,249 rows
    "GBPUSD": "6B",  # 3,239 rows
    "JPYUSD": "6J",  # 3,212 rows
    "AUDUSD": "6A",  # 3,207 rows
    "CADUSD": "6C",  # 3,238 rows
    "CHFUSD": "6S",  # 2,255 rows
    "BRLUSD": "6L",  # 3,087 rows
    "MXNUSD": "6M",  # 1,761 rows
    "NZDUSD": "6N",  # 1,188 rows
}

_NORMALIZED_MANIFEST_ALIASES: dict[str, str] = {
    _normalize_underlying_name(raw): root for raw, root in _MANIFEST_UNDERLYING_ALIASES.items()
}


def root_for_underlying_name(name: str) -> str | None:
    """Reverse-lookup: a captured ``underlying`` string -> its short root code.

    Honest-absence, never a guess: returns ``None`` for anything not
    recognized rather than a fuzzy best-effort match. Resolves, in order:

    1. Exact root code (case-insensitive) — some real manifest rows already
       carry the correct short root code (e.g. "CL", "NG", "HO", "MES") as
       their ``underlying`` value; that is already the answer.
    2. A known alias for a real manifest spelling that does not fold onto the
       registry's ``underlying`` convention even after normalization (see
       ``_MANIFEST_UNDERLYING_ALIASES``).
    3. The registry's own ``underlying`` value, normalized the same way as
       the input (handles "HEATING-OIL"/"HEATING_OIL"/"Heating Oil" all
       resolving to "HO" via ``RootMetadata.underlying == "HEATING_OIL"``).

    Args:
        name: The captured/spelled underlying string to resolve (e.g. from a
            manifest row's ``underlying`` column).

    Returns:
        The short TradFi root code (a ``TRADFI_ROOTS`` key), or ``None`` if
        ``name`` does not resolve to a known root.
    """
    normalized = _normalize_underlying_name(name)
    if not normalized:
        return None
    if normalized in TRADFI_ROOTS:
        return normalized
    if normalized in _NORMALIZED_MANIFEST_ALIASES:
        return _NORMALIZED_MANIFEST_ALIASES[normalized]
    return _UNDERLYING_NAME_TO_ROOT.get(normalized)


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
    "root_for_underlying_name",
]
