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
    asset_class: str = "commodity"
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
    DatabentoInstrumentDef("GC.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "GOLD", "GC"),
    DatabentoInstrumentDef("CL.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CRUDE", "CL"),
    DatabentoInstrumentDef("NG.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "NATGAS", "NG"),
    DatabentoInstrumentDef("HO.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "HEATING_OIL", "HO"),
    DatabentoInstrumentDef("RB.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "GASOLINE", "RB"),
    DatabentoInstrumentDef("SI.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SILVER", "SI"),
    DatabentoInstrumentDef("HG.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "COPPER", "HG"),
    DatabentoInstrumentDef("CT.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "COTTON", "CT"),
    DatabentoInstrumentDef("ZS.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SOYBEANS", "ZS"),
    DatabentoInstrumentDef("ZC.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "CORN", "ZC"),
    DatabentoInstrumentDef("ZW.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "WHEAT", "ZW"),
    DatabentoInstrumentDef("ZL.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SOYBEAN_OIL", "ZL"),
    DatabentoInstrumentDef("ZM.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SOYBEAN_MEAL", "ZM"),
    DatabentoInstrumentDef("LE.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "LIVECATTLE", "LE"),
    DatabentoInstrumentDef("HE.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "LEANHOGS", "HE"),
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

# CME options — disabled for now (5,990 instruments per day, too much data).
# Revisit when options strategy is implemented.
# _CME_SP500_OPTIONS: list[DatabentoInstrumentDef] = [
#     DatabentoInstrumentDef("ES.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "ES"),
#     DatabentoInstrumentDef("EW1.OPT", ... "EW5.OPT"),
# ]
_CME_SP500_OPTIONS: list[DatabentoInstrumentDef] = []

# ---------------------------------------------------------------------------
# ICE futures
# ---------------------------------------------------------------------------
_ICE_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("BRN.FUT", "ICE", "FUTURE", "IFEU.IMPACT", "parent", "BRENT", "BRN"),
    DatabentoInstrumentDef("G.FUT", "ICE", "FUTURE", "IFEU.IMPACT", "parent", "GASOIL", "G"),
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
    *_CME_SP500_OPTIONS,
    *_ICE_FUTURES,
    *_CBOE_INSTRUMENTS,
]

# ---------------------------------------------------------------------------
# FX spot pairs (Yahoo Finance — static definitions, not Databento)
# ---------------------------------------------------------------------------
FX_SPOT_PAIRS: list[FxSpotPairDef] = [
    FxSpotPairDef("KRW", "USD", "KRWUSD=X"),
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
