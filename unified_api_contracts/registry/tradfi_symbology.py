"""TradFi symbology reference data (SSOT).

Databento parent/options symbol validation, exchange code mappings,
ETF classification, and TradFi venue instrument definitions.

Instrument identity is separated from data-source-specific bindings:
- TRADFI_INSTRUMENTS: provider-agnostic identity (what the instrument IS)
- TRADFI_DATA_BINDINGS: per-provider config (WHERE to get data for it)
- TRADFI_VENUE_MAPPINGS: flattened merged view (identity + primary binding as dicts)

Previously scattered across instruments-service config files.
Centralized here as the system SSOT per UAC registry pattern.
"""

from __future__ import annotations

import datetime as _dt
import re
from datetime import date as date_type
from typing import Final, Literal

from pydantic import BaseModel

# --- Databento parent symbol validation ---
# Maps canonical underlying names (both exchange codes and human-readable aliases)
# to (databento_parent_symbol, dataset) tuples.
DATABENTO_VALID_PARENT_SYMBOLS: dict[str, tuple[str, str]] = {
    # CME Index Futures
    "ES": ("ES.FUT", "GLBX.MDP3"),
    "SP500": ("ES.FUT", "GLBX.MDP3"),
    "NQ": ("NQ.FUT", "GLBX.MDP3"),
    "NASDAQ100": ("NQ.FUT", "GLBX.MDP3"),
    "RTY": ("RTY.FUT", "GLBX.MDP3"),
    "RUSSELL2000": ("RTY.FUT", "GLBX.MDP3"),
    "YM": ("YM.FUT", "GLBX.MDP3"),
    "DOW": ("YM.FUT", "GLBX.MDP3"),
    # CME Energy
    "CL": ("CL.FUT", "GLBX.MDP3"),
    "CRUDE": ("CL.FUT", "GLBX.MDP3"),
    "NG": ("NG.FUT", "GLBX.MDP3"),
    "NATGAS": ("NG.FUT", "GLBX.MDP3"),
    "RB": ("RB.FUT", "GLBX.MDP3"),
    "GASOLINE": ("RB.FUT", "GLBX.MDP3"),
    "HO": ("HO.FUT", "GLBX.MDP3"),
    "HEATINGOIL": ("HO.FUT", "GLBX.MDP3"),
    # CME Metals
    "GC": ("GC.FUT", "GLBX.MDP3"),
    "GOLD": ("GC.FUT", "GLBX.MDP3"),
    "SI": ("SI.FUT", "GLBX.MDP3"),
    "SILVER": ("SI.FUT", "GLBX.MDP3"),
    "HG": ("HG.FUT", "GLBX.MDP3"),
    "COPPER": ("HG.FUT", "GLBX.MDP3"),
    "PL": ("PL.FUT", "GLBX.MDP3"),
    "PLATINUM": ("PL.FUT", "GLBX.MDP3"),
    # CME Grains
    "ZC": ("ZC.FUT", "GLBX.MDP3"),
    "CORN": ("ZC.FUT", "GLBX.MDP3"),
    "ZW": ("ZW.FUT", "GLBX.MDP3"),
    "WHEAT": ("ZW.FUT", "GLBX.MDP3"),
    "ZS": ("ZS.FUT", "GLBX.MDP3"),
    "SOYBEAN": ("ZS.FUT", "GLBX.MDP3"),
    "ZM": ("ZM.FUT", "GLBX.MDP3"),
    "SOYMEAL": ("ZM.FUT", "GLBX.MDP3"),
    "ZL": ("ZL.FUT", "GLBX.MDP3"),
    "SOYOIL": ("ZL.FUT", "GLBX.MDP3"),
    # CME Interest Rates
    "ZB": ("ZB.FUT", "GLBX.MDP3"),
    "TBOND": ("ZB.FUT", "GLBX.MDP3"),
    "ZN": ("ZN.FUT", "GLBX.MDP3"),
    "TNOTE10Y": ("ZN.FUT", "GLBX.MDP3"),
    "ZF": ("ZF.FUT", "GLBX.MDP3"),
    "TNOTE5Y": ("ZF.FUT", "GLBX.MDP3"),
    "ZT": ("ZT.FUT", "GLBX.MDP3"),
    "TNOTE2Y": ("ZT.FUT", "GLBX.MDP3"),
    # CME Currencies
    "6E": ("6E.FUT", "GLBX.MDP3"),
    "EUR": ("6E.FUT", "GLBX.MDP3"),
    "6J": ("6J.FUT", "GLBX.MDP3"),
    "JPY": ("6J.FUT", "GLBX.MDP3"),
    "6B": ("6B.FUT", "GLBX.MDP3"),
    "GBP": ("6B.FUT", "GLBX.MDP3"),
    "6C": ("6C.FUT", "GLBX.MDP3"),
    "CAD": ("6C.FUT", "GLBX.MDP3"),
    "6A": ("6A.FUT", "GLBX.MDP3"),
    "AUD": ("6A.FUT", "GLBX.MDP3"),
    "6S": ("6S.FUT", "GLBX.MDP3"),
    "CHF": ("6S.FUT", "GLBX.MDP3"),
    "6M": ("6M.FUT", "GLBX.MDP3"),
    "MXN": ("6M.FUT", "GLBX.MDP3"),
    "6N": ("6N.FUT", "GLBX.MDP3"),
    "NZD": ("6N.FUT", "GLBX.MDP3"),
    "6L": ("6L.FUT", "GLBX.MDP3"),
    "BRL": ("6L.FUT", "GLBX.MDP3"),
    "6Z": ("6Z.FUT", "GLBX.MDP3"),
    "ZAR": ("6Z.FUT", "GLBX.MDP3"),
    # CME Livestock
    "LE": ("LE.FUT", "GLBX.MDP3"),
    "LIVECATTLE": ("LE.FUT", "GLBX.MDP3"),
    "HE": ("HE.FUT", "GLBX.MDP3"),
    "LEANHOGS": ("HE.FUT", "GLBX.MDP3"),
    # CFE (CBOE Futures Exchange) - Volatility (VX/VIX) Futures.
    # The Databento dataset code for the Cboe Futures Exchange (the operator's "CFE"
    # subscription, 2026-06-18) is XCBF.PITCH — a bare "CFE" is rejected by the API
    # (400 validation_failed; verified live 2026-06-19). XCBF.PITCH is in the paid set.
    "VX": ("VX.FUT", "XCBF.PITCH"),
    "VIX_FUT": ("VX.FUT", "XCBF.PITCH"),
    # ICE Futures US (IFUS.IMPACT)
    "CT": ("CT.FUT", "IFUS.IMPACT"),
    "COTTON": ("CT.FUT", "IFUS.IMPACT"),
    "CC": ("CC.FUT", "IFUS.IMPACT"),
    "COCOA": ("CC.FUT", "IFUS.IMPACT"),
    "KC": ("KC.FUT", "IFUS.IMPACT"),
    "COFFEE": ("KC.FUT", "IFUS.IMPACT"),
    "SB": ("SB.FUT", "IFUS.IMPACT"),
    "SUGAR": ("SB.FUT", "IFUS.IMPACT"),
    "OJ": ("OJ.FUT", "IFUS.IMPACT"),
    "ORANGEJUICE": ("OJ.FUT", "IFUS.IMPACT"),
    "DX": ("DX.FUT", "IFUS.IMPACT"),
    "DOLLARINDEX": ("DX.FUT", "IFUS.IMPACT"),
    # ICE Futures Europe
    "BRN": ("BRN.FUT", "IFEU.IMPACT"),
    "BRENT": ("BRN.FUT", "IFEU.IMPACT"),
    "G": ("G.FUT", "IFEU.IMPACT"),
    "GASOIL": ("G.FUT", "IFEU.IMPACT"),
    "T": ("T.FUT", "IFEU.IMPACT"),
    "WTI": ("T.FUT", "IFEU.IMPACT"),
}

# --- Databento options symbol validation ---
DATABENTO_VALID_OPTIONS_SYMBOLS: dict[str, tuple[str, str]] = {
    "ES": ("ES.OPT", "GLBX.MDP3"),
    "SP500": ("ES.OPT", "GLBX.MDP3"),
    "NQ": ("NQ.OPT", "GLBX.MDP3"),
    "NASDAQ100": ("NQ.OPT", "GLBX.MDP3"),
    "CL": ("CL.OPT", "GLBX.MDP3"),
    "CRUDE": ("CL.OPT", "GLBX.MDP3"),
    "GC": ("GC.OPT", "GLBX.MDP3"),
    "GOLD": ("GC.OPT", "GLBX.MDP3"),
}

# --- Exchange code to human-readable name ---
EXCHANGE_CODE_TO_NAME: dict[str, str] = {
    "ES": "SP500",
    "NQ": "NASDAQ100",
    "RTY": "RUSSELL2000",
    "YM": "DOW",
    "CL": "CRUDE",
    "NG": "NATGAS",
    "RB": "GASOLINE",
    "HO": "HEATINGOIL",
    "GC": "GOLD",
    "SI": "SILVER",
    "HG": "COPPER",
    "PL": "PLATINUM",
    "ZC": "CORN",
    "ZW": "WHEAT",
    "ZS": "SOYBEAN",
    "ZM": "SOYMEAL",
    "ZL": "SOYOIL",
    "ZB": "TBOND",
    "ZN": "TNOTE10Y",
    "ZF": "TNOTE5Y",
    "ZT": "TNOTE2Y",
    "6E": "EUR",
    "6J": "JPY",
    "6B": "GBP",
    "6C": "CAD",
    "6A": "AUD",
    "6S": "CHF",
    "6L": "BRL",
    "6N": "NZD",
    "6Z": "ZAR",
    "6M": "MXN",
    "LE": "LIVECATTLE",
    "HE": "LEANHOGS",
    "VX": "VIX",
    "EW1": "SP500",
    "EW2": "SP500",
    "EW3": "SP500",
    "EW4": "SP500",
    "CT": "COTTON",
    "CC": "COCOA",
    "KC": "COFFEE",
    "SB": "SUGAR",
    "OJ": "ORANGEJUICE",
    "DX": "DOLLARINDEX",
    "BRN": "BRENT",
    "G": "GASOIL",
    "T": "WTI",
}

# ---------------------------------------------------------------------------
# Instrument identity / data-source binding types
# ---------------------------------------------------------------------------


class TradFiInstrumentDef(BaseModel, frozen=True):
    """Provider-agnostic instrument identity — what the instrument IS."""

    symbol: str  # Canonical symbol (ES.FUT, VIX-USD, SPY)
    venue: str  # Exchange/venue (CME, CBOE, ICE)
    instrument_type: str  # FUTURE, INDEX, OPTION, EQUITY, ETF
    base_asset: str  # Human-readable base (SP500, VIX, GOLD)
    quote_asset: str = "USD"
    underlying: str | None = None  # Underlying asset (e.g., ES for EW1.OPT)
    data_source: str = ""  # Provenance: which source generated this definition (for replay)


class ProviderBinding(BaseModel, frozen=True):
    """Data-source-specific config for an instrument — WHERE to get data."""

    provider: str  # databento, yahoo_finance, fred, barchart, ibkr
    use_for: Literal["historical", "live", "execution", "all"] = "all"
    dataset: str | None = None  # Databento dataset (GLBX.MDP3, IFUS.IMPACT)
    stype: str | None = None  # Databento stype (parent, raw_symbol)
    exchange_code: str | None = None  # Databento exchange code (ES, CL)
    ticker: str | None = None  # Yahoo Finance ticker (^VIX)
    series: str | None = None  # FRED series (VIXCLS)
    instrument_key: str | None = None  # Canonical GCS key (CBOE:INDEX:VIX-USD)


def get_bindings_for_symbol(symbol: str) -> list[ProviderBinding]:
    """Return all provider bindings for a given instrument symbol."""
    return list(TRADFI_DATA_BINDINGS.get(symbol, []))


def get_primary_binding(symbol: str, provider: str | None = None) -> ProviderBinding | None:
    """Return the first binding matching provider (or first overall if provider is None)."""
    bindings = TRADFI_DATA_BINDINGS.get(symbol, [])
    if provider is not None:
        return next((b for b in bindings if b.provider == provider), None)
    return bindings[0] if bindings else None


# ---------------------------------------------------------------------------
# Layer 1: Instrument identity (provider-agnostic)
# ---------------------------------------------------------------------------


def _fut(symbol: str, venue: str, base: str, underlying: str | None = None) -> TradFiInstrumentDef:
    return TradFiInstrumentDef(
        symbol=symbol,
        venue=venue,
        instrument_type="FUTURE",
        base_asset=base,
        data_source="databento",
        underlying=underlying,
    )


def _opt(symbol: str, venue: str, base: str, underlying: str | None = None) -> TradFiInstrumentDef:
    return TradFiInstrumentDef(
        symbol=symbol,
        venue=venue,
        instrument_type="OPTION",
        base_asset=base,
        data_source="databento",
        underlying=underlying,
    )


TRADFI_INSTRUMENTS: list[TradFiInstrumentDef] = [
    # CME Index Futures
    _fut("ES.FUT", "CME", "SP500"),
    _fut("NQ.FUT", "CME", "NASDAQ100"),
    _fut("RTY.FUT", "CME", "RUSSELL2000"),
    _fut("YM.FUT", "CME", "DOW"),
    # CME Energy
    _fut("CL.FUT", "CME", "CRUDE"),
    _fut("NG.FUT", "CME", "NATGAS"),
    _fut("RB.FUT", "CME", "GASOLINE"),
    _fut("HO.FUT", "CME", "HEATINGOIL"),
    # CME Metals
    _fut("GC.FUT", "CME", "GOLD"),
    _fut("SI.FUT", "CME", "SILVER"),
    _fut("HG.FUT", "CME", "COPPER"),
    _fut("PL.FUT", "CME", "PLATINUM"),
    # CME Grains
    _fut("ZC.FUT", "CME", "CORN"),
    _fut("ZW.FUT", "CME", "WHEAT"),
    _fut("ZS.FUT", "CME", "SOYBEAN"),
    _fut("ZM.FUT", "CME", "SOYMEAL"),
    _fut("ZL.FUT", "CME", "SOYOIL"),
    # CME Interest Rates
    _fut("ZB.FUT", "CME", "TBOND"),
    _fut("ZN.FUT", "CME", "TNOTE10Y"),
    _fut("ZF.FUT", "CME", "TNOTE5Y"),
    _fut("ZT.FUT", "CME", "TNOTE2Y"),
    # CME Currencies
    _fut("6E.FUT", "CME", "EUR"),
    _fut("6J.FUT", "CME", "JPY"),
    _fut("6B.FUT", "CME", "GBP"),
    _fut("6C.FUT", "CME", "CAD"),
    _fut("6A.FUT", "CME", "AUD"),
    _fut("6S.FUT", "CME", "CHF"),
    _fut("6L.FUT", "CME", "BRL"),
    _fut("6N.FUT", "CME", "NZD"),
    _fut("6Z.FUT", "CME", "ZAR"),
    _fut("6M.FUT", "CME", "MXN"),
    # CME Livestock
    _fut("LE.FUT", "CME", "LIVECATTLE"),
    _fut("HE.FUT", "CME", "LEANHOGS"),
    # CBOE — Volatility Index (calculated, not traded)
    TradFiInstrumentDef(
        symbol="VIX-USD",
        venue="CBOE",
        instrument_type="INDEX",
        base_asset="VIX",
        data_source="yahoo_finance",
    ),
    # CFE — Volatility Futures (traded on CBOE Futures Exchange; Databento dataset XCBF.PITCH)
    _fut("VX.FUT", "XCBF.PITCH", "VIX"),
    # Options
    _opt("ES.OPT", "CME", "SP500"),
    _opt("NQ.OPT", "CME", "NASDAQ100"),
    _opt("CL.OPT", "CME", "CRUDE"),
    _opt("GC.OPT", "CME", "GOLD"),
    _opt("EW1.OPT", "CME", "SP500", underlying="ES"),
    _opt("EW2.OPT", "CME", "SP500", underlying="ES"),
    _opt("EW3.OPT", "CME", "SP500", underlying="ES"),
    _opt("EW4.OPT", "CME", "SP500", underlying="ES"),
    # ICE Futures US
    _fut("CT.FUT", "ICE", "COTTON"),
    _fut("CC.FUT", "ICE", "COCOA"),
    _fut("KC.FUT", "ICE", "COFFEE"),
    _fut("SB.FUT", "ICE", "SUGAR"),
    _fut("OJ.FUT", "ICE", "ORANGEJUICE"),
    _fut("DX.FUT", "ICE", "DOLLARINDEX"),
    # ICE Futures Europe
    _fut("BRN.FUT", "ICE", "BRENT"),
    _fut("G.FUT", "ICE", "GASOIL"),
    _fut("T.FUT", "ICE", "WTI"),
]

# ---------------------------------------------------------------------------
# Layer 2: Data source bindings (provider-specific)
# ---------------------------------------------------------------------------


def _db(dataset: str, stype: str, code: str) -> ProviderBinding:
    """Shorthand for a Databento binding."""
    return ProviderBinding(provider="databento", dataset=dataset, stype=stype, exchange_code=code)


# Map instrument symbol -> list of provider bindings
TRADFI_DATA_BINDINGS: dict[str, list[ProviderBinding]] = {
    # CME futures (all via Databento GLBX.MDP3)
    "ES.FUT": [_db("GLBX.MDP3", "parent", "ES")],
    "NQ.FUT": [_db("GLBX.MDP3", "parent", "NQ")],
    "RTY.FUT": [_db("GLBX.MDP3", "parent", "RTY")],
    "YM.FUT": [_db("GLBX.MDP3", "parent", "YM")],
    "CL.FUT": [_db("GLBX.MDP3", "parent", "CL")],
    "NG.FUT": [_db("GLBX.MDP3", "parent", "NG")],
    "RB.FUT": [_db("GLBX.MDP3", "parent", "RB")],
    "HO.FUT": [_db("GLBX.MDP3", "parent", "HO")],
    "GC.FUT": [_db("GLBX.MDP3", "parent", "GC")],
    "SI.FUT": [_db("GLBX.MDP3", "parent", "SI")],
    "HG.FUT": [_db("GLBX.MDP3", "parent", "HG")],
    "PL.FUT": [_db("GLBX.MDP3", "parent", "PL")],
    "ZC.FUT": [_db("GLBX.MDP3", "parent", "ZC")],
    "ZW.FUT": [_db("GLBX.MDP3", "parent", "ZW")],
    "ZS.FUT": [_db("GLBX.MDP3", "parent", "ZS")],
    "ZM.FUT": [_db("GLBX.MDP3", "parent", "ZM")],
    "ZL.FUT": [_db("GLBX.MDP3", "parent", "ZL")],
    "ZB.FUT": [_db("GLBX.MDP3", "parent", "ZB")],
    "ZN.FUT": [_db("GLBX.MDP3", "parent", "ZN")],
    "ZF.FUT": [_db("GLBX.MDP3", "parent", "ZF")],
    "ZT.FUT": [_db("GLBX.MDP3", "parent", "ZT")],
    "6E.FUT": [_db("GLBX.MDP3", "parent", "6E")],
    "6J.FUT": [_db("GLBX.MDP3", "parent", "6J")],
    "6B.FUT": [_db("GLBX.MDP3", "parent", "6B")],
    "6C.FUT": [_db("GLBX.MDP3", "parent", "6C")],
    "6A.FUT": [_db("GLBX.MDP3", "parent", "6A")],
    "6S.FUT": [_db("GLBX.MDP3", "parent", "6S")],
    "6L.FUT": [_db("GLBX.MDP3", "parent", "6L")],
    "6N.FUT": [_db("GLBX.MDP3", "parent", "6N")],
    "6Z.FUT": [_db("GLBX.MDP3", "parent", "6Z")],
    "6M.FUT": [_db("GLBX.MDP3", "parent", "6M")],
    "LE.FUT": [_db("GLBX.MDP3", "parent", "LE")],
    "HE.FUT": [_db("GLBX.MDP3", "parent", "HE")],
    # VIX index — multiple sources (historical Barchart, ongoing Yahoo, daily FRED)
    "VIX-USD": [
        ProviderBinding(
            provider="barchart",
            use_for="historical",
            instrument_key="CBOE:INDEX:VIX-USD",
        ),
        ProviderBinding(
            provider="yahoo_finance",
            use_for="live",
            ticker="^VIX",
            instrument_key="CBOE:INDEX:VIX-USD",
        ),
        ProviderBinding(
            provider="fred",
            use_for="historical",
            series="VIXCLS",
        ),
    ],
    # VX futures (CBOE Futures Exchange via Databento) — dataset XCBF.PITCH (the
    # operator's "CFE" subscription, 2026-06-18; a bare "CFE" is rejected by the API).
    "VX.FUT": [_db("XCBF.PITCH", "parent", "VX")],
    # Options (CME via Databento)
    "ES.OPT": [_db("GLBX.MDP3", "parent", "ES")],
    "NQ.OPT": [_db("GLBX.MDP3", "parent", "NQ")],
    "CL.OPT": [_db("GLBX.MDP3", "parent", "CL")],
    "GC.OPT": [_db("GLBX.MDP3", "parent", "GC")],
    "EW1.OPT": [_db("GLBX.MDP3", "parent", "EW1")],
    "EW2.OPT": [_db("GLBX.MDP3", "parent", "EW2")],
    "EW3.OPT": [_db("GLBX.MDP3", "parent", "EW3")],
    "EW4.OPT": [_db("GLBX.MDP3", "parent", "EW4")],
    # ICE Futures US
    "CT.FUT": [_db("IFUS.IMPACT", "parent", "CT")],
    "CC.FUT": [_db("IFUS.IMPACT", "parent", "CC")],
    "KC.FUT": [_db("IFUS.IMPACT", "parent", "KC")],
    "SB.FUT": [_db("IFUS.IMPACT", "parent", "SB")],
    "OJ.FUT": [_db("IFUS.IMPACT", "parent", "OJ")],
    "DX.FUT": [_db("IFUS.IMPACT", "parent", "DX")],
    # ICE Futures Europe
    "BRN.FUT": [_db("IFEU.IMPACT", "parent", "BRN")],
    "G.FUT": [_db("IFEU.IMPACT", "parent", "G")],
    "T.FUT": [_db("IFEU.IMPACT", "parent", "T")],
}

# ---------------------------------------------------------------------------
# Flattened merged view (identity + primary binding as dicts)
# ---------------------------------------------------------------------------


def _build_venue_mappings() -> list[dict[str, str | None]]:
    """Merge identity + primary binding into flat dicts consumed by downstream services."""
    result: list[dict[str, str | None]] = []
    for inst in TRADFI_INSTRUMENTS:
        entry: dict[str, str | None] = {
            "symbol": inst.symbol,
            "venue": inst.venue,
            "type": inst.instrument_type,
            "base": inst.base_asset,
        }
        if inst.underlying is not None:
            entry["underlying"] = inst.underlying
        bindings = TRADFI_DATA_BINDINGS.get(inst.symbol, [])
        if bindings:
            primary = bindings[0]
            if primary.dataset is not None:
                entry["dataset"] = primary.dataset
            if primary.stype is not None:
                entry["stype"] = primary.stype
            if primary.exchange_code is not None:
                entry["code"] = primary.exchange_code
            if primary.ticker is not None:
                entry["yahoo_ticker"] = primary.ticker
            if primary.series is not None:
                entry["fred_series"] = primary.series
            if primary.instrument_key is not None:
                entry["instrument_key"] = primary.instrument_key
        result.append(entry)
    return result


TRADFI_VENUE_MAPPINGS: list[dict[str, str | None]] = _build_venue_mappings()

# --- Known ETF tickers ---
KNOWN_ETFS: set[str] = {
    "SPY",
    "QQQ",
    "IVV",
    "VOO",
    "VTI",
    "DIA",
    "IWM",
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
    "IBIT",
    "FBTC",
    "ARKB",
    "GBTC",
    "BITO",
}

# --- Space-to-dot symbol normalization ---
SPACE_TO_DOT_SYMBOLS: dict[str, str] = {
    "BRK B": "BRK.B",
    "BF B": "BF.B",
    "BRK A": "BRK.A",
    "BF A": "BF.A",
}

# Backward-compatible alias
TRADFI_INSTRUMENTS_CONFIG: list[dict[str, str | None]] = TRADFI_VENUE_MAPPINGS

# Named constant for the VIX index instrument definition — import this directly
# rather than scanning TRADFI_VENUE_MAPPINGS.
VIX_INDEX_INSTRUMENT: dict[str, str | None] = next(
    d for d in TRADFI_VENUE_MAPPINGS if d.get("instrument_key") == "CBOE:INDEX:VIX-USD"
)

# Named constant for the VIX instrument identity (typed)
VIX_INSTRUMENT: TradFiInstrumentDef = next(inst for inst in TRADFI_INSTRUMENTS if inst.symbol == "VIX-USD")


# ---------------------------------------------------------------------------
# CME options-chain cluster taxonomy
# ---------------------------------------------------------------------------
# 11-cluster taxonomy for ES options bundles fetched via Databento parent
# symbology. Used by ``ManifestWriter.record_captured(expected_root_clusters,
# cluster_extractor)`` to validate that a per-day options-chain parquet
# bundle actually contains rows from EVERY active sub-root, not just the
# quarterly ES root. Reference incident **TradFi MVP 2026-05-06** (closeout
# memory ``project_tradfi_mvp_closeout_2026_05_06.md``): 18 ES.OPT dates
# passed presence-only manifest validation as ``captured`` despite being
# fetched with single-parent ``ES.OPT`` only (~1,218 quarterly contracts)
# instead of all 11 parent symbols (~2,483 contracts of all expirations).

ES_OPTIONS_CLUSTERS: dict[str, str] = {
    "ES": "quarterly (3rd Fri Mar/Jun/Sep/Dec — IMM)",
    "EW": "weekly Friday (non-quarterly)",
    "EW1": "weekly Monday",
    "EW2": "weekly Wednesday",
    "EW4": "weekly Tuesday",
    "E1A": "daily Monday (0DTE)",
    "E2A": "daily Tuesday",
    "E3A": "daily Wednesday",
    "E4A": "daily Thursday",
    "E5A": "daily Friday",
    "EOM": "end-of-month",
}

# Default per-cluster minimum row count for ohlcv_1m bundles. ~3 expiries
# active x ~10 strikes per expiry x ~390 minutes (RTH) = ~11,700 rows in a
# liquid cluster — even sparsely-traded clusters typically clear 100 rows.
# Tunable per-shard by callers (e.g. weeklies on illiquid weeks may need
# lower minimums; instruments-service per-day active list is the SSOT for
# the actual expected denominator).
ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER: int = 100

# Regex matches CME futures/options symbols of form ``<root><month-letter><year-digits>``
# where root is 1-4 alphanumerics (e.g. ``ES``, ``EW``, ``EW1``, ``E1A``,
# ``E5A``, ``EOM``), month-letter is one of ``FGHJKMNQUVXZ``, and year-digits
# are 1-2 digits. Anchored to the start of the symbol so that both
# space-separated forms (``E1AN4 C5090``) and dash-separated forms
# (``ES-2024-09-20-C-5800``) are handled. Returns the root prefix (no month/year).
_ES_CLUSTER_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<root>[A-Z][A-Z0-9]{0,3}?)([FGHJKMNQUVXZ])(\d{1,2})(?=\b|\s|-|$)"
)


# Weekly-Friday and weekly-Monday/Tuesday/Wednesday roots that quote every
# US trading day. ``ES`` is the quarterly root and is always active on
# weekdays. Daily-expiry roots (``E1A``..``E5A``) and ``EOM`` are NOT
# included here — pure-calendar can't tell whether the listed-but-not-traded
# next-expiry contract has rows on the bundle's date. The
# instruments-service per-day snapshot is the SSOT for those (see
# ``get_active_es_options_clusters_for_date_from_snapshot`` in
# ``instruments-service``); this calendar fallback only enforces that the
# 5-cluster always-on baseline is present so partial-parent bundles like
# the TradFi MVP 2026-05-06 incident (single ``ES`` parent shipped instead
# of all 11) fail loud.
_ES_OPTIONS_WEEKDAY_ALWAYS_ON: tuple[str, ...] = ("ES", "EW", "EW1", "EW2", "EW4")


def get_active_es_options_clusters_for_date(
    target_date: date_type,
    *,
    min_rows_per_cluster: int = ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER,
) -> dict[str, int]:
    """Pure-calendar fallback for the active ES.OPT cluster set on ``target_date``.

    Returns ``{cluster_root: min_rows}`` — the minimum row count expected
    per cluster on the shard's date. Designed for use as
    ``ManifestWriter.record_captured(expected_root_clusters=...)`` when the
    instruments-service per-day snapshot is unavailable.

    Calendar rules:

    * **Weekdays (Mon-Fri)**: ``ES`` + ``EW`` + ``EW1`` + ``EW2`` + ``EW4``
      are always active. Quarterly + the four weekly roots quote every US
      trading day.
    * **Weekends**: empty dict — no US options trading.

    Daily-expiry roots (``E1A`` Monday, ``E2A`` Tuesday, ``E3A`` Wednesday,
    ``E4A`` Thursday, ``E5A`` Friday) and ``EOM`` are intentionally NOT
    enforced by this fallback. The pure calendar can't tell whether the
    next-expiry contract listed-but-not-yet-traded has ohlcv rows on
    ``target_date`` — that requires the instruments-service per-day
    snapshot. Use the snapshot helper as primary; fall back to this only
    when the snapshot is unavailable.

    The 5-cluster baseline is enough to catch the TradFi MVP 2026-05-06
    partial-bundle incident (single ``ES`` parent shipped instead of all
    11 clusters): the writer would observe ``ES`` only, miss
    ``EW``/``EW1``/``EW2``/``EW4``, and route to ``record_failed`` with
    :class:`ClusterCoverageError`.

    Args:
        target_date: The trading date the bundle covers.
        min_rows_per_cluster: Minimum row count per cluster. Defaults to
            :data:`ES_OPTIONS_DEFAULT_MIN_ROWS_PER_CLUSTER`.

    Returns:
        ``{cluster: min_rows}`` for each calendar-active cluster. Empty
        dict on weekends.
    """
    if target_date.weekday() >= 5:
        return {}
    return {cluster: int(min_rows_per_cluster) for cluster in _ES_OPTIONS_WEEKDAY_ALWAYS_ON}


def extract_es_options_cluster(symbol: str) -> str:
    """Extract the cluster root from a CME options symbol.

    Examples:
        ``E1AN4 C5090`` → ``E1A``
        ``ESM4 P5800`` → ``ES``
        ``EW2J4 C5400`` → ``EW2``
        ``EOMG5 C5100`` → ``EOM``

    Returns the leading root prefix (1-4 chars, all uppercase A-Z plus
    digits). Inputs that don't match the CME outright option format
    (e.g. ``UD:1V: VT 2888228`` synthetic combo spreads) return the
    leading whitespace-delimited token unchanged so callers can still
    bucket them — they should already be routed to a separate
    ``instrument_type=combo`` partition before this function is called.

    SSOT for the cluster taxonomy: :data:`ES_OPTIONS_CLUSTERS`.
    """
    head = symbol.split()[0] if symbol else ""
    match = _ES_CLUSTER_PATTERN.match(head)
    if match:
        return match.group("root")
    return head


# ---------------------------------------------------------------------------
# Futures expiry-bucket derivation
# ---------------------------------------------------------------------------

# CME month codes → calendar month number (also used in instruments-service and MTDS).
_FUTURES_MONTH_CODE: Final[dict[str, int]] = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}

# Matches a single dated futures symbol: ROOT(1-5 alphanum) + MONTH(CME letter) + YEAR(1-2 digits).
# Handles both short (``ESM6``) and long (``ESM26``) year encodings.
_SINGLE_FUT_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Z0-9]{1,5})([FGHJKMNQUVXZ])(\d{1,2})$")

# Contracts expiring within this many days of ``today`` are classified as ``front``.
_FRONT_MONTH_DAYS: Final[int] = 90


def derive_expiry_bucket(symbol: str, today: date_type) -> Literal["front", "back", "spread", "butterfly"]:
    """Classify a futures symbol into one of four expiry buckets.

    Returns:
        ``spread``    — 2-leg calendar spread (e.g. ``ESM6-ESU6``)
        ``butterfly`` — 3+ leg spread (e.g. ``ESH6-ESM6-ESU6``)
        ``front``     — single contract expiring within 90 days of *today*
        ``back``      — single contract expiring 90+ days from *today*

    Unrecognised single-leg symbols (no CME month letter) default to ``front``
    so callers receive a non-null bucket and can apply a conservative gate.
    """
    legs = symbol.split("-")
    if len(legs) >= 3:
        return "butterfly"
    if len(legs) == 2:
        return "spread"

    # Single contract — parse month + year.
    m = _SINGLE_FUT_RE.match(symbol)
    if not m:
        return "front"
    month = _FUTURES_MONTH_CODE.get(m.group(2), 1)
    year_suffix = int(m.group(3)) % 10  # normalize: both "6" and "26" → 6

    # Sliding-window year expansion: pick the nearest year >= today.year - 1
    # whose last digit matches year_suffix (handles 1- and 2-digit codes).
    decade_base = today.year - (today.year % 10) + year_suffix
    year = decade_base if decade_base >= today.year - 1 else decade_base + 10

    # Conservative expiry estimate: last day of the contract month.
    if month == 12:
        expiry = date_type(year + 1, 1, 1) - _dt.timedelta(days=1)
    else:
        expiry = date_type(year, month + 1, 1) - _dt.timedelta(days=1)

    days_remaining = (expiry - today).days
    return "front" if days_remaining < _FRONT_MONTH_DAYS else "back"


# ---------------------------------------------------------------------------
# CME event-contract shard-key extraction
# ---------------------------------------------------------------------------
# Phase 3 of cme_polymarket_arb_2026_05_08: the EVENT_CONTRACT bundled shard
# atom is (root, resolution_month, day). Cluster validation key is
# (root, resolution_month, strike_threshold). This function extracts those
# dimensions from the raw Databento CME event-contract symbol.

# Root set mirrors EVENT_CONTRACT_ROOTS in
# unified_api_contracts.canonical.domain.derivatives.tradfi_roots — duplicated
# here to avoid an intra-registry circular import (tradfi_roots imports nothing
# from registry; registry should not import from canonical.domain).
_CME_EVENT_CONTRACT_ROOT_SET: frozenset[str] = frozenset(
    {"ECES", "ECNQ", "ECRTY", "ECYM", "ECGC", "ECCL", "ECNG", "EC6E", "ECBTC"}
)

# CME month-code → zero-padded month number string.
_EC_MONTH_TO_NUM: dict[str, str] = {
    "F": "01",
    "G": "02",
    "H": "03",
    "J": "04",
    "K": "05",
    "M": "06",
    "N": "07",
    "Q": "08",
    "U": "09",
    "V": "10",
    "X": "11",
    "Z": "12",
}


def extract_event_contract_shard_key(symbol: str) -> tuple[str, str, str] | None:
    """Extract ``(root, resolution_month, strike_str)`` from a CME event-contract symbol.

    Parses space-delimited Databento CME event-contract symbols of the form
    ``{EC_ROOT} {MONTH_CODE}{YEAR_DIGIT} {STRIKE}{C|P}``::

        ``ECBTC H5 62000C``  →  ``("ECBTC", "2025-03", "62000")``
        ``ECES Z4 4900C``    →  ``("ECES",  "2024-12", "4900")``

    Returns ``None`` when the symbol is unparseable — parent/rollup symbols
    (e.g. ``ECBTC.OPT``) don't carry a specific (resolution_month, strike)
    cluster identity.  Callers silently skip ``None`` returns.

    Used by ``PartitionedTickWriter.write_chunk`` to accumulate per-
    ``(root, resolution_month)`` cluster counts for the Phase-3 EVENT_CONTRACT
    bundled manifest shard atom per ``cme_polymarket_arb_2026_05_08``.
    """
    parts = symbol.strip().upper().split()
    if len(parts) < 3:
        return None
    root = parts[0]
    if root not in _CME_EVENT_CONTRACT_ROOT_SET:
        return None
    month_year = parts[1]
    if len(month_year) < 2:
        return None
    month_code = month_year[0]
    year_part = month_year[1:]
    if month_code not in _EC_MONTH_TO_NUM or not year_part.isdigit():
        return None
    year = 2020 + int(year_part) if len(year_part) == 1 else 2000 + int(year_part)
    resolution_month = f"{year:04d}-{_EC_MONTH_TO_NUM[month_code]}"
    strike_part = parts[2].rstrip("CP")
    if not strike_part:
        return None
    return (root, resolution_month, strike_part)


# ---------------------------------------------------------------------------
# Massive (formerly Polygon.io) ticker helpers
# ---------------------------------------------------------------------------
# Massive uses native CME ticker format: ROOT + month_code + 2-digit year.
# Examples: ESH26 (ES Mar 2026), CLN26 (CL Jul 2026), GCQ26 (GC Aug 2026).
# No prefix, no separator — same as CME's own symbology and what the
# Polygon.io /v3/reference/futures/contracts ``ticker`` field returns.
# Convention determined from Polygon.io API documentation; live verification
# against Massive REST API is pending MASSIVE_API_KEY availability on worker VMs.
# See tradfi_massive_dual_source_2026_05_28.md task tradfi_massive_dual_source-005.


def massive_futures_ticker(root: str, month_code: str, year_2digit: int) -> str:
    """Return the Massive ticker string for a CME futures contract.

    Format: ``{ROOT}{month_code}{year_2digit}`` — e.g. ``ESH26``, ``CLN26``, ``GCQ26``.

    Args:
        root: CME root symbol (``ES``, ``CL``, ``GC``, …).
        month_code: Single uppercase CME month letter from ``FGHJKMNQUVXZ``.
        year_2digit: 2-digit year (e.g. 26 for 2026).

    Raises:
        ValueError: If month_code is not a valid CME month letter.
    """
    mc = month_code.upper()
    if mc not in _FUTURES_MONTH_CODE:
        raise ValueError(f"Invalid CME month code: {month_code!r}. Must be one of FGHJKMNQUVXZ.")
    return f"{root.upper()}{mc}{year_2digit:02d}"
