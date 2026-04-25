"""TradFi instrument universe registry — curated list of Databento symbols to track.

This is the SSOT for which TradFi futures, options, and derivatives the
instruments-service fetches from Databento. Equities/ETFs come from the
tradfi_ticker_universe.py (SP500_TICKERS, ETF_TICKERS etc.) instead.

Each entry specifies the Databento parent symbol, dataset, and stype_in so the
URDI Databento adapter can fetch only these instruments (not the entire dataset
dump, which returns millions of rows).

FX spot pairs are also declared here — they are static definitions fetched via
Yahoo Finance (not Databento).  The ``FX_SPOT_PAIRS`` list tells the adapter
which pairs to create.

Architecture
------------
- UAC owns the registry (this file).
- URDI Databento adapter reads ``TRADFI_DATABENTO_INSTRUMENTS`` and
  ``FX_SPOT_PAIRS`` at import time.
- instruments-service config_reloaders can override via cloud ConfigStore
  (hot-reloadable), but the registry here is the default.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DatabentoInstrumentDef:
    """A single curated Databento instrument definition.

    Attributes:
        symbol: Databento symbol (e.g. ``ES.FUT``, ``SPY``).
        venue: Canonical venue name (``CME``, ``NASDAQ``, ``ICE``, ``CBOE``).
        instrument_type: ``FUTURE``, ``OPTION``, ``ETF``, ``INDEX``.
        dataset: Databento dataset ID (``GLBX.MDP3``, ``DBEQ.BASIC``, …).
        stype_in: ``parent`` for futures/options, ``raw_symbol`` for equities.
        base_asset: Human-readable underlying name (``SP500``, ``CRUDE``, …).
        exchange_code: Short Databento exchange code (``ES``, ``CL``, …).
        underlying: Underlying asset when different from base (e.g. ``BTC``
            for Bitcoin ETFs).
    """

    symbol: str
    venue: str
    instrument_type: str
    dataset: str
    stype_in: str
    base_asset: str
    asset_group: str = "commodity"
    exchange_code: str | None = None
    underlying: str | None = None


@dataclass(frozen=True, slots=True)
class FxSpotPairDef:
    """A static FX spot pair definition (fetched via Yahoo Finance, not Databento).

    Attributes:
        base: Base currency (e.g. ``KRW``).
        quote: Quote currency (e.g. ``USD``).
        yahoo_ticker: Yahoo Finance ticker (e.g. ``KRWUSD=X``).
    """

    base: str
    quote: str
    yahoo_ticker: str


# ---------------------------------------------------------------------------
# CME futures — index, commodity, fixed-income, FX futures
# ---------------------------------------------------------------------------
_CME_INDEX_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("ES.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SP500", "equity", "ES"),
    DatabentoInstrumentDef("NQ.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "NASDAQ100", "equity", "NQ"),
    DatabentoInstrumentDef("RTY.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "RUSSELL2000", "equity", "RTY"),
    DatabentoInstrumentDef("YM.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "DOW", "equity", "YM"),
    DatabentoInstrumentDef("NKD.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "NIKKEI225", "equity", "NKD"),
]

_CME_SECTOR_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("XAF.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "ENERGY_SECTOR", "equity", "XAF"),
    DatabentoInstrumentDef("XAK.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "TECH_SECTOR", "equity", "XAK"),
    DatabentoInstrumentDef("XAY.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CONSUMER_DISC_SECTOR", "equity", "XAY"),
    DatabentoInstrumentDef(
        "XAP.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CONSUMER_STAPLES_SECTOR", "equity", "XAP"
    ),
    DatabentoInstrumentDef("XAV.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "HEALTHCARE_SECTOR", "equity", "XAV"),
    DatabentoInstrumentDef("XAI.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "INDUSTRIALS_SECTOR", "equity", "XAI"),
    DatabentoInstrumentDef("XAB.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "MATERIALS_SECTOR", "equity", "XAB"),
    DatabentoInstrumentDef("XAU.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "UTILITIES_SECTOR", "equity", "XAU"),
]

_CME_TREASURY_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("ZT.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "TREASURY_2Y", "fixed_income", "ZT"),
    DatabentoInstrumentDef("ZF.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "TREASURY_5Y", "fixed_income", "ZF"),
    DatabentoInstrumentDef("ZN.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "TREASURY_10Y", "fixed_income", "ZN"),
    DatabentoInstrumentDef("ZB.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "TREASURY_30Y", "fixed_income", "ZB"),
]

_CME_COMMODITY_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("GC.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "GOLD", "commodity", "GC"),
    DatabentoInstrumentDef("CL.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CRUDE", "commodity", "CL"),
    DatabentoInstrumentDef("NG.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "NATGAS", "commodity", "NG"),
    DatabentoInstrumentDef("HO.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "HEATING_OIL", "commodity", "HO"),
    DatabentoInstrumentDef("RB.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "GASOLINE", "commodity", "RB"),
    DatabentoInstrumentDef("SI.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SILVER", "commodity", "SI"),
    DatabentoInstrumentDef("HG.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "COPPER", "commodity", "HG"),
    DatabentoInstrumentDef("CT.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "COTTON", "commodity", "CT"),
    DatabentoInstrumentDef("ZS.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SOYBEANS", "commodity", "ZS"),
    DatabentoInstrumentDef("ZC.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CORN", "commodity", "ZC"),
    DatabentoInstrumentDef("ZW.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "WHEAT", "commodity", "ZW"),
    DatabentoInstrumentDef("ZL.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SOYBEAN_OIL", "commodity", "ZL"),
    DatabentoInstrumentDef("ZM.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SOYBEAN_MEAL", "commodity", "ZM"),
    DatabentoInstrumentDef("LE.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "LIVECATTLE", "commodity", "LE"),
    DatabentoInstrumentDef("HE.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "LEANHOGS", "commodity", "HE"),
]

_CME_FX_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("6E.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "EUR", "fx", "6E"),
    DatabentoInstrumentDef("6B.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "GBP", "fx", "6B"),
    DatabentoInstrumentDef("6J.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "JPY", "fx", "6J"),
    DatabentoInstrumentDef("6A.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "AUD", "fx", "6A"),
    DatabentoInstrumentDef("6C.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CAD", "fx", "6C"),
    DatabentoInstrumentDef("6N.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "NZD", "fx", "6N"),
    DatabentoInstrumentDef("6S.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CHF", "fx", "6S"),
    DatabentoInstrumentDef("6M.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "MXN", "fx", "6M"),
    DatabentoInstrumentDef("6Z.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "ZAR", "fx", "6Z"),
    DatabentoInstrumentDef("6L.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "BRL", "fx", "6L"),
]

_CME_CRYPTO_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("BTC.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "BTC", "crypto", "BTC"),
    DatabentoInstrumentDef("ETH.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "ETH", "crypto", "ETH"),
]

# CME ES options — full E-mini S&P 500 options surface.
# Databento parent symbology: [ROOT].OPT fetches all strikes/expiries for that product.
#
# Product codes (CME Group / Databento asset field):
#   ES   = Quarterly options (3rd Friday of quarter month)
#   EW   = Weekly options (Friday expiry, end-of-week)
#   EW1  = Monday weekly options
#   EW2  = Wednesday weekly options
#   EW4  = Tuesday weekly options
#   E1A  = Monday daily (0DTE)
#   E2A  = Tuesday daily
#   E3A  = Wednesday daily
#   E4A  = Thursday daily
#   E5A  = Friday daily
#   EOM  = End-of-month options (last business day)
#
# Together these give 2+ full volatility surfaces (quarterly + weekly/daily).
_CME_ES_OPTIONS: list[DatabentoInstrumentDef] = [
    # Quarterly (standard monthly/quarterly — 3rd Friday)
    DatabentoInstrumentDef("ES.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "ES"),
    # Weekly options (Mon/Tue/Wed/Fri expiries)
    DatabentoInstrumentDef("EW.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "EW"),
    DatabentoInstrumentDef("EW1.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "EW1"),
    DatabentoInstrumentDef("EW2.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "EW2"),
    DatabentoInstrumentDef("EW4.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "EW4"),
    # Daily options (0DTE — Mon through Fri)
    DatabentoInstrumentDef("E1A.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "E1A"),
    DatabentoInstrumentDef("E2A.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "E2A"),
    DatabentoInstrumentDef("E3A.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "E3A"),
    DatabentoInstrumentDef("E4A.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "E4A"),
    DatabentoInstrumentDef("E5A.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "E5A"),
    # End-of-month options (last business day)
    DatabentoInstrumentDef("EOM.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "EOM"),
]

# ---------------------------------------------------------------------------
# ICE futures
# ---------------------------------------------------------------------------
_ICE_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("BRN.FUT", "ICE", "FUTURE", "IFEU.IMPACT", "parent", "BRENT", "commodity", "BRN"),
    DatabentoInstrumentDef("G.FUT", "ICE", "FUTURE", "IFEU.IMPACT", "parent", "GASOIL", "commodity", "G"),
]

# ---------------------------------------------------------------------------
# CBOE / CFE
# ---------------------------------------------------------------------------
# CBOE VX futures: XCBF.PITCH only supports stype_in=raw_symbol with explicit
# contract codes (e.g. "VXH6" for March 2026). Parent/continuous symbology not
# supported.  TODO: generate front-month VX symbols dynamically from target date.
_CBOE_INSTRUMENTS: list[DatabentoInstrumentDef] = []

# ---------------------------------------------------------------------------
# Aggregate: all Databento instruments
# ---------------------------------------------------------------------------
TRADFI_DATABENTO_INSTRUMENTS: list[DatabentoInstrumentDef] = [
    *_CME_INDEX_FUTURES,
    *_CME_SECTOR_FUTURES,
    *_CME_TREASURY_FUTURES,
    *_CME_COMMODITY_FUTURES,
    *_CME_FX_FUTURES,
    *_CME_CRYPTO_FUTURES,
    *_CME_ES_OPTIONS,
    *_ICE_FUTURES,
    *_CBOE_INSTRUMENTS,
]

# ---------------------------------------------------------------------------
# FX spot pairs (Yahoo Finance — static definitions, not Databento)
# ---------------------------------------------------------------------------
FX_SPOT_PAIRS: list[FxSpotPairDef] = [
    FxSpotPairDef("KRW", "USD", "KRWUSD=X"),
]


@dataclass(frozen=True, slots=True)
class YahooIndexDef:
    """A static index definition fetched via Yahoo Finance (daily close).

    Used for indices that aren't directly tradeable via Databento
    but are needed for features (VIX, DXY, etc.).
    """

    symbol: str
    venue: str
    base_asset: str
    yahoo_ticker: str
    asset_group: str = "equity"


YAHOO_INDICES: list[YahooIndexDef] = [
    YahooIndexDef("VIX", "CBOE", "VIX", "^VIX", "equity"),
]

# ---------------------------------------------------------------------------
# Exchange code → human-readable name (for display / grouping)
# ---------------------------------------------------------------------------
EXCHANGE_CODE_TO_NAME: dict[str, str] = {
    # FX futures (including micro)
    "6A": "AUD",
    "M6A": "AUD",
    "6B": "GBP",
    "M6B": "GBP",
    "6E": "EUR",
    "M6E": "EUR",
    "6J": "JPY",
    "M6J": "JPY",
    "6C": "CAD",
    "M6C": "CAD",
    "6N": "NZD",
    "M6N": "NZD",
    "6S": "CHF",
    "M6S": "CHF",
    "6M": "MXN",
    "6Z": "ZAR",
    "6L": "BRL",
    # Energy + metals
    "CL": "CRUDE",
    "MCL": "CRUDE",
    "GC": "GOLD",
    "MGC": "GOLD",
    "NG": "NATGAS",
    "MNG": "NATGAS",
    "HO": "HEATING_OIL",
    "RB": "GASOLINE",
    "SI": "SILVER",
    "MSI": "SILVER",
    "HG": "COPPER",
    "MHG": "COPPER",
    # Agriculture
    "CT": "COTTON",
    "ZS": "SOYBEANS",
    "ZC": "CORN",
    "ZW": "WHEAT",
    "ZL": "SOYBEAN_OIL",
    "ZM": "SOYBEAN_MEAL",
    "LE": "LIVECATTLE",
    "HE": "LEANHOGS",
    # VIX
    "VX": "VIX",
    # ICE energy
    "BRN": "BRENT",
    "G": "GASOIL",
    # Crypto
    "BTC": "BTC",
    "ETH": "ETH",
    # Index futures (including micro)
    "ES": "SP500",
    "MES": "SP500",
    "NQ": "NASDAQ100",
    "MNQ": "NASDAQ100",
    "RTY": "RUSSELL2000",
    "M2K": "RUSSELL2000",
    "YM": "DOW",
    "MYM": "DOW",
    "NKD": "NIKKEI225",
    # Sector futures
    "XAF": "ENERGY_SECTOR",
    "XAK": "TECH_SECTOR",
    "XAY": "CONSUMER_DISC_SECTOR",
    "XAP": "CONSUMER_STAPLES_SECTOR",
    "XAV": "HEALTHCARE_SECTOR",
    "XAI": "INDUSTRIALS_SECTOR",
    "XAB": "MATERIALS_SECTOR",
    "XAU": "UTILITIES_SECTOR",
    # Treasuries
    "ZT": "TREASURY_2Y",
    "ZF": "TREASURY_5Y",
    "ZN": "TREASURY_10Y",
    "ZB": "TREASURY_30Y",
    # Options on ES
    "EW1": "SP500",
    "EW2": "SP500",
    "EW3": "SP500",
    "EW4": "SP500",
    "EW5": "SP500",
    # ETFs (crypto)
    "IBIT": "BTC_ETF",
    "FBTC": "BTC_ETF",
    "ARKB": "BTC_ETF",
    # S&P 500 index
    "SPX": "SP500",
}


def get_databento_symbols_for_dataset(dataset: str) -> list[DatabentoInstrumentDef]:
    """Return all curated instruments for a specific Databento dataset."""
    return [i for i in TRADFI_DATABENTO_INSTRUMENTS if i.dataset == dataset]


def get_databento_symbols_for_venue(venue: str) -> list[DatabentoInstrumentDef]:
    """Return all curated instruments for a canonical venue."""
    return [i for i in TRADFI_DATABENTO_INSTRUMENTS if i.venue == venue.upper()]


def get_required_datasets() -> list[str]:
    """Return the unique set of Databento datasets needed for the curated universe."""
    return sorted({i.dataset for i in TRADFI_DATABENTO_INSTRUMENTS})


# ---------------------------------------------------------------------------
# MVP CME exchange codes — only these parent symbols are downloaded in MVP mode.
# Full TRADFI_TICKER_UNIVERSE is kept for later expansion.
# ES covers: ES.FUT (quarterly futures), ES.OPT (quarterly options),
# EW.OPT (weekly), EW1-4.OPT (weekly), E1A-E5A.OPT (daily/0DTE), EOM.OPT (end-of-month)
# ---------------------------------------------------------------------------
MVP_CME_EXCHANGE_CODES: frozenset[str] = frozenset(
    {
        "ES",
        "EW",
        "EW1",
        "EW2",
        "EW4",
        "E1A",
        "E2A",
        "E3A",
        "E4A",
        "E5A",
        "EOM",
    }
)


def get_mvp_databento_symbols_for_venue(venue: str) -> list[DatabentoInstrumentDef]:
    """Return MVP-filtered instruments for a venue (ES-only for CME)."""
    all_defs = get_databento_symbols_for_venue(venue)
    if venue.upper() == "CME":
        return [d for d in all_defs if d.exchange_code in MVP_CME_EXCHANGE_CODES]
    return all_defs
