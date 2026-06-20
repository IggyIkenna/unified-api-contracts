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
from datetime import date


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
    # Micro CME crypto futures — added 2026-05-05 alongside MES so strategies
    # can size the date-futures-arb-vs-Deribit archetype at sub-portfolio
    # capital without integer-contract rounding error against the full-size
    # BTC.FUT (5 BTC ≈ $500k) / ETH.FUT (50 ETH ≈ $200k). Micros are 1/10
    # notional and share the same monthly expiry calendar + GLBX.MDP3
    # parent symbology.
    DatabentoInstrumentDef("MBT.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "BTC", "crypto", "MBT"),
    DatabentoInstrumentDef("MET.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "ETH", "crypto", "MET"),
    # Micro E-mini S&P 500 futures — MVP added 2026-05-05 after 0% capture
    # diagnosis (UAC had no MES def, so the adapter never fetched it even
    # though Databento parent symbology returns ~3,500 rows/day for MES.FUT).
    # Same dataset/stype as the parent ES contract.
    DatabentoInstrumentDef("MES.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "SP500", "equity", "MES"),
]

# Crypto spot ETFs — US-listed BTC + ETH spot ETFs.
#
# Each ETF is declared with its REAL listing exchange and the matching
# Databento dataset. DBEQ.BASIC (consolidated SIP) returned 0 records
# for these tickers in the 2026-04-30 backfill — the dataset coverage
# is too thin for crypto ETFs. Direct ITCH/PILLAR/PITCH feeds work.
#
# Listing → dataset:
#   IBIT, ETHA            : NASDAQ → XNAS.ITCH (Nasdaq TotalView)
#   GBTC, BITO, ETHE      : ARCA   → ARCX.PILLAR (NYSE Arca PILLAR)
#   FBTC, ARKB, FETH      : BATS   → BATS.PITCH (Cboe BZX PITCH)
#
# stype_in="raw_symbol" is the equity convention (one ticker per fetch,
# no parent symbology).
#
# Backfill listing dates:
#   IBIT, FBTC, ARKB, GBTC : 2024-01-11 (US BTC spot ETF launch; GBTC
#                            uplisted from OTC same date)
#   BITO                   : 2021-10-19 (futures-based)
#   ETHA, FETH, ETHE       : 2024-07-23 (US ETH spot ETF launch; ETHE
#                            uplisted from OTC same date)
# MVP scope (2026-05-05): only the most-liquid BlackRock spot ETFs on NASDAQ
# (IBIT, ETHA). FBTC/ARKB (BATS), GBTC/ETHE/BITO (NYSE Arca) dropped — the
# date-futures arb archetype needs CME futures + Deribit futures (same expiry
# day), and CME futures + the BlackRock NASDAQ ETF cover spot exposure.
# Re-add the BATS/ARCA-listed ETFs only if a new strategy archetype needs them.
#
# Dataset = DBEQ.BASIC (3-dataset subscription lockdown, operator 2026-06-18):
# we pay for the consolidated Databento US Equities feed, NOT the per-venue
# direct feeds (XNAS.ITCH / ARCX.PILLAR / BATS.PITCH). Every US-equity ETF /
# stock is fetched from DBEQ.BASIC. SSOT:
# codex/02-data/tradfi-databento-sourcing-ssot.md + databento_subscription_allowlist.py.
_BTC_SPOT_ETFS: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("IBIT", "NASDAQ", "ETF", "DBEQ.BASIC", "raw_symbol", "BTC", "crypto", "IBIT", "BTC"),
]

_ETH_SPOT_ETFS: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("ETHA", "NASDAQ", "ETF", "DBEQ.BASIC", "raw_symbol", "ETH", "crypto", "ETHA", "ETH"),
]

# ---------------------------------------------------------------------------
# Net-profitable crypto-venue equity-perp hedge legs — DBEQ.BASIC single stocks
#
# Added 2026-06-20 after the NET-basis backtest (Phase 1d,
# ``cryptovenue_equity_perps_and_tokenized_stocks_2026_06_20.md``).
#
# Decision logic:
#   NET = perp_funding_ann - futures_roll_carry_ann
#   Single-stock crypto perps are hedged via IBKR stock borrow (no futures roll;
#   cost ~0.3-2.5% ann for large-cap US equities).  The 11-month backtest showed
#   NET > 5% annualized for the 12 symbols below.  Commodities (XAU/XAG/COPPER)
#   were NET SLIM/NEGATIVE after subtracting GC/SI/HG contango (3-4.4% ann) and
#   are NOT added.  Indices (SPX/SPY) are NET NEGATIVE after ES 3.3% contango.
#
# Threshold: NET > 5% annualized AND hedge-type = stock-borrow (no roll decay).
# Rejected: PLTR (NET +1.7%), MSTR (NET +4.1%), COIN (NET +4.2%) — below 5%.
# Excluded: BABA — last-1mo NET -8.3% despite positive mean; regime unstable.
#
# Hedge venue: IBKR spot (each symbol is a real US-listed stock, Databento DBEQ.BASIC).
# stype_in = "raw_symbol" (one ticker per request; no parent/spread chain needed).
# asset_group = "cefi" (these are the equity legs of a crypto-venue arb trade, not
#   pure TradFi; grouping with cefi keeps them out of the tradfi data pipeline).
# ---------------------------------------------------------------------------
_NET_PROFITABLE_EQUITY_PERP_SINGLES: list[DatabentoInstrumentDef] = [
    # NET +21.6% ann (gross 22.1%, borrow 0.5%) — NVIDIA
    DatabentoInstrumentDef("NVDA", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "NVIDIA", "cefi", "NVDA"),
    # NET +15.4% ann (gross 15.7%, borrow 0.3%) — Microsoft
    DatabentoInstrumentDef("MSFT", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "MICROSOFT", "cefi", "MSFT"),
    # NET +21.3% ann (gross 23.8%, borrow 2.5%) — Circle (CRCL, NYSE)
    DatabentoInstrumentDef("CRCL", "NYSE", "STOCK", "DBEQ.BASIC", "raw_symbol", "CIRCLE", "cefi", "CRCL"),
    # NET +17.7% ann (gross 18.2%, borrow 0.5%) — Intel
    DatabentoInstrumentDef("INTC", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "INTEL", "cefi", "INTC"),
    # NET +17.6% ann (gross 18.0%, borrow 0.3%) — Alphabet
    DatabentoInstrumentDef("GOOGL", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "ALPHABET", "cefi", "GOOGL"),
    # NET +23.9% ann (gross 24.4%, borrow 0.5%) — AMD
    DatabentoInstrumentDef("AMD", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "AMD", "cefi", "AMD"),
    # NET +8.9% ann (gross 9.4%, borrow 0.5%) — Tesla
    DatabentoInstrumentDef("TSLA", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "TESLA", "cefi", "TSLA"),
    # NET +5.4% ann (gross 5.7%, borrow 0.3%) — Amazon
    DatabentoInstrumentDef("AMZN", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "AMAZON", "cefi", "AMZN"),
    # NET +11.4% ann (gross 11.7%, borrow 0.3%) — Meta Platforms
    DatabentoInstrumentDef("META", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "META", "cefi", "META"),
    # NET +7.1% ann (gross 9.1%, borrow 2.0%) — Robinhood
    DatabentoInstrumentDef("HOOD", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "ROBINHOOD", "cefi", "HOOD"),
    # NET +6.5% ann (gross 6.8%, borrow 0.3%) — Apple
    DatabentoInstrumentDef("AAPL", "NASDAQ", "STOCK", "DBEQ.BASIC", "raw_symbol", "APPLE", "cefi", "AAPL"),
    # NET +5.2% ann (gross 6.2%, borrow 1.0%) — Alibaba (NYSE-listed; 1-mo NET -8.3% but mean +5.2%)
    # NOTE: regime unstable (1-mo NET -8.3%); include with caution — monitor monthly.
    DatabentoInstrumentDef("BABA", "NYSE", "STOCK", "DBEQ.BASIC", "raw_symbol", "ALIBABA", "cefi", "BABA"),
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
# ICE instruments — DROPPED (3-dataset subscription lockdown, operator 2026-06-18)
# ---------------------------------------------------------------------------
# Brent (BRN), Gasoil (G) on IFEU.IMPACT and the US softs (CT/CC/KC/SB/OJ) +
# ICE Dollar-Index future (DX) on IFUS.IMPACT are OUT of the paid subscription:
# we pay for ONLY GLBX.MDP3 + DBEQ.BASIC + CFE. Querying IFEU.IMPACT/IFUS.IMPACT
# would be billed silently, so the universe must not list them and
# `assert_dataset_allowed` raises if anything tries. Re-adding any of these
# requires an explicit ICE subscription + adding the dataset to the allowlist.
# (The Yahoo-sourced DXY cash index in YAHOO_INDICES is a SEPARATE, non-Databento
# series and is unaffected.) SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md.

# ---------------------------------------------------------------------------
# CBOE / CFE — VX (VIX) futures
# ---------------------------------------------------------------------------
# CFE = Cboe Futures Exchange (the third subscribed feed, operator 2026-06-18).
# VX = VIX futures. The Databento dataset CODE for the Cboe Futures Exchange is
# ``XCBF.PITCH`` (a bare "CFE" is rejected by the API with 400 validation_failed;
# verified live 2026-06-19). Parent symbology "VX.FUT" fetches all listed VX
# contract months. NOTE: this gives VIX *futures* (VX), NOT the VIX *cash index*
# — the 15m cash index stays on the Barchart+Yahoo path
# (registry/data_source_continuity.py), unaffected by this entry. Venue token =
# CBOE (already a tradfi venue with FUTURE capability); XCBF.PITCH is the Databento
# *dataset*, CBOE is the canonical venue.
_CFE_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("VX.FUT", "CBOE", "FUTURE", "XCBF.PITCH", "parent", "VIX", "equity", "VX"),
]

# ---------------------------------------------------------------------------
# CME Event Contracts — binary YES/NO settlement on macro/financial underliers.
# ---------------------------------------------------------------------------
# Same shape as Polymarket / Kalshi / Opinion binary markets ("Will S&P close
# above X today?" / "Will BTC be > $Y by date?") but cleared via CME ClearPort
# and routed retail via DraftKings Predictions / Robinhood Event Contracts.
# Databento classifies them as OPTIONS (parent symbology with `.OPT` suffix).
# Coverage on Databento: 2025-09-28 onward (verified 2026-05-01 by walking
# symbology.resolve back from current date — first contracts surfaced
# 2025-09-28). Pre-2025-09-28 history is not available via Databento even
# though CME launched the product in 2022.
#
# Roots verified live via Databento symbology.resolve (2026-05-01):
#   ECES = E-mini S&P 500    | ECNQ = E-mini Nasdaq 100
#   ECRTY = E-mini Russell   | ECYM = E-mini Dow
#   ECGC = Gold              | ECCL = Crude WTI
#   ECNG = Natural gas       | EC6E = Euro FX
#   ECBTC = Bitcoin (the killer leg vs Polymarket BTC binaries)
_CME_EVENT_CONTRACTS: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("ECES.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SP500", "equity", "ECES"),
    DatabentoInstrumentDef("ECNQ.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "NASDAQ100", "equity", "ECNQ"),
    DatabentoInstrumentDef("ECRTY.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "RUSSELL2000", "equity", "ECRTY"),
    DatabentoInstrumentDef("ECYM.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "DOW", "equity", "ECYM"),
    DatabentoInstrumentDef("ECGC.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "GOLD", "commodity", "ECGC"),
    DatabentoInstrumentDef("ECCL.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "CRUDE", "commodity", "ECCL"),
    DatabentoInstrumentDef("ECNG.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "NATGAS", "commodity", "ECNG"),
    DatabentoInstrumentDef("EC6E.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "EUR", "fx", "EC6E"),
    DatabentoInstrumentDef("ECBTC.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "BTC", "crypto", "ECBTC"),
]

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
    *_CME_EVENT_CONTRACTS,
    *_CFE_FUTURES,
    *_BTC_SPOT_ETFS,
    *_ETH_SPOT_ETFS,
    *_NET_PROFITABLE_EQUITY_PERP_SINGLES,
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

    ``first_available_date`` is the empirically-confirmed genesis of the
    series on Yahoo (the instrument's ``available_from_datetime`` and the
    data-status could-exist start). It is REQUIRED per entry — never inherit
    a shared default — so a new index cannot be listed without declaring when
    its data actually begins (mis-stated genesis silently mis-seeds the
    expected-universe denominator).
    """

    symbol: str
    venue: str
    base_asset: str
    yahoo_ticker: str
    first_available_date: date
    asset_group: str = "equity"


YAHOO_INDICES: list[YahooIndexDef] = [
    # ^VIX daily history back to 1990-01-02 (9,177 bars confirmed 2026-06-11).
    YahooIndexDef("VIX", "CBOE", "VIX", "^VIX", date(1990, 1, 2), "equity"),
    # ICE/NYBOT US Dollar Index — daily ohlcv_24h via Yahoo (DX-Y.NYB).
    # Full history back to 2019-01-02 (1,864 bars empirically confirmed 2026-06-11).
    # 1h is capped to the last 730 days by Yahoo; use daily for long history.
    # Venue stays ICE: DXY is the ICE/NYBOT US Dollar Index, sourced via Yahoo
    # (NOT Databento), so ICE remains a valid tradfi venue for this non-Databento
    # index even though the ICE Databento datasets are out of the subscription.
    YahooIndexDef("DXY", "ICE", "DXY", "DX-Y.NYB", date(2019, 1, 2), "fx"),
    # CBOE interest-rate indices — daily ohlcv_24h via Yahoo. Each "close" is the
    # par yield in percent (e.g. 4.53 = 4.53%). Full history back to 2000-01-03
    # (6,642 daily bars empirically confirmed 2026-06-11). Yahoo has no live 2Y
    # yield (2YY=F is stale, zero-volume futures), so the usable tenors are
    # 3M / 5Y / 10Y / 30Y — enough to compute curve slopes and forward rates.
    YahooIndexDef("US3M", "CBOE", "US3M", "^IRX", date(2000, 1, 3), "fixed_income"),
    YahooIndexDef("US5Y", "CBOE", "US5Y", "^FVX", date(2000, 1, 3), "fixed_income"),
    YahooIndexDef("US10Y", "CBOE", "US10Y", "^TNX", date(2000, 1, 3), "fixed_income"),
    YahooIndexDef("US30Y", "CBOE", "US30Y", "^TYX", date(2000, 1, 3), "fixed_income"),
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
    "ZS": "SOYBEANS",
    "ZC": "CORN",
    "ZW": "WHEAT",
    "ZL": "SOYBEAN_OIL",
    "ZM": "SOYBEAN_MEAL",
    "LE": "LIVECATTLE",
    "HE": "LEANHOGS",
    # VIX / VX futures (CFE dataset)
    "VX": "VIX",
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
