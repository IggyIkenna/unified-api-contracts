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

# Leaf-to-leaf import of the canonical MVP SSOT (crosscutting/_mvp_scope_rules.py).
# Safe direction: crosscutting.mvp_scope already imports FROM registry leaves
# (cefi_instrument_universe.py, market_data_categories.py) — NEITHER of those
# leaves imports tradfi_instrument_universe.py back, so this import can never
# complete a cycle regardless of which module a caller touches first (verified
# empirically for both orderings: package-mediated via registry/__init__.py's
# sequential imports, and a direct leaf-first import bypassing __init__.py
# entirely — the shape test_cme_options_universe.py itself uses).
from unified_api_contracts.canonical.crosscutting._mvp_scope_rules import (
    MVP_SCOPE,
    TradFiMvpRule,
)


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
    # COMEX/NYMEX platinum-group metals — Binance XPT/XPD perp coverage (2026-06-24).
    DatabentoInstrumentDef("PL.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "PLATINUM", "commodity", "PL"),
    DatabentoInstrumentDef("PA.FUT", "CME", "FUTURE", "GLBX.MDP3", "parent", "PALLADIUM", "commodity", "PA"),
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
# asset_group=COMMODITY: VX/VIX is a volatility product, not an equity — within the
# canonical AssetClass taxonomy (equity/fx/commodity/fixed_income/crypto) volatility maps
# to COMMODITY (operator 2026-06-25). This is the per-instrument SSOT consumed by the
# databento adapter's _resolve_asset_group (step 1: underlying "VX" → asset_group), so the
# 82 cumulative VX FUTURE rows land COMMODITY, not the previous mis-classified EQUITY.
_CFE_FUTURES: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("VX.FUT", "CBOE", "FUTURE", "XCBF.PITCH", "parent", "VIX", "commodity", "VX"),
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
# CME options-on-futures for the COMMODITY + INDEX basis underlyings (2026-06-24).
# Options on the cash-commodity / index FUTURE are valid basis-arb cash legs for
# the Binance commodity/index perps (alongside the future + the representative
# ETF). SCOPE: commodities + indices ONLY — single-stock options are SKIPPED
# (too many) and equity/ETF options are OPRA (NOT in our 3-dataset databento
# allowlist GLBX.MDP3 + DBEQ.BASIC + XCBF.PITCH, NOT in massive) → IGNORED.
# Every root below was PROBED LIVE against GLBX.MDP3 (definition + trades
# resolve, 2026-06-24); phantom roots that did NOT resolve were DROPPED:
# LN.OPT (NatGas alt), RTY.OPT (Russell), YM.OPT (Dow) — no GLBX.MDP3 coverage.
# Source: databento GLBX.MDP3 primary (these are CME options-on-futures; massive
# carries no options-on-futures, so no massive-primary tag applies here).
_CME_COMMODITY_OPTIONS: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("OG.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "GOLD", "commodity", "OG"),
    DatabentoInstrumentDef("SO.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "SILVER", "commodity", "SO"),
    DatabentoInstrumentDef("PO.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "PLATINUM", "commodity", "PO"),
    DatabentoInstrumentDef("PAO.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "PALLADIUM", "commodity", "PAO"),
    DatabentoInstrumentDef("HXE.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "COPPER", "commodity", "HXE"),
    DatabentoInstrumentDef("LO.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "CRUDE", "commodity", "LO"),
    DatabentoInstrumentDef("ON.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "NATGAS", "commodity", "ON"),
    DatabentoInstrumentDef("OH.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "HEATING_OIL", "commodity", "OH"),
    DatabentoInstrumentDef("OB.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "GASOLINE", "commodity", "OB"),
]

# CME options-on-futures for the index basis underlyings (2026-06-24). ES options
# already exist in _CME_ES_OPTIONS; NQ.OPT is the Nasdaq-100 add (probed live —
# definition + trades resolve). RTY/YM options DROPPED (no GLBX.MDP3 resolve).
_CME_INDEX_OPTIONS: list[DatabentoInstrumentDef] = [
    DatabentoInstrumentDef("NQ.OPT", "CME", "OPTION", "GLBX.MDP3", "parent", "NASDAQ100", "equity", "NQ"),
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
    *_CME_COMMODITY_OPTIONS,
    *_CME_INDEX_OPTIONS,
    *_CME_EVENT_CONTRACTS,
    *_CFE_FUTURES,
    *_BTC_SPOT_ETFS,
    *_ETH_SPOT_ETFS,
    *_NET_PROFITABLE_EQUITY_PERP_SINGLES,
]

# ---------------------------------------------------------------------------
# FX spot pairs (Yahoo Finance — static definitions, not Databento)
# ---------------------------------------------------------------------------
# G10 FX majors added 2026-06-26 — these are the cash cross rates needed as
# cefi features (DXY context, polymarket EUR/USD arb, cross-asset macro signals).
# Tickers use the standard Yahoo Finance ``{BASE}{QUOTE}=X`` format.
# KRW/USD is retained for kimchi-premium basis computation.
# USD/MXN included because 6M (MXN CME future) is in the Databento universe.
# History availability: all G10 crosses available via Yahoo daily back to 2003+
# (empirically confirmed; backfill floor is the operator target 2019-01-01).
FX_SPOT_PAIRS: list[FxSpotPairDef] = [
    # G10 FX majors — daily ohlcv_24h via Yahoo Finance (BATCH_YAHOO path)
    FxSpotPairDef("EUR", "USD", "EURUSD=X"),
    FxSpotPairDef("GBP", "USD", "GBPUSD=X"),
    FxSpotPairDef("USD", "JPY", "USDJPY=X"),
    FxSpotPairDef("AUD", "USD", "AUDUSD=X"),
    FxSpotPairDef("USD", "CAD", "USDCAD=X"),
    FxSpotPairDef("USD", "CHF", "USDCHF=X"),
    FxSpotPairDef("NZD", "USD", "NZDUSD=X"),
    FxSpotPairDef("EUR", "GBP", "EURGBP=X"),
    FxSpotPairDef("EUR", "JPY", "EURJPY=X"),
    FxSpotPairDef("USD", "MXN", "USDMXN=X"),
    # KRW/USD — for kimchi-premium basis computation (Binance KRX arb)
    FxSpotPairDef("KRW", "USD", "KRWUSD=X"),
]


@dataclass(frozen=True, slots=True)
class KrxEquityDef:
    """A static KRX (Korea Exchange) equity definition fetched via Yahoo Finance.

    KRX equities have no Databento dataset in our subscription — they are sourced
    via Yahoo Finance using the ``.KS`` ticker suffix. Mirrors the basis-arb
    cash-equity twin pattern of the DBEQ.BASIC US equities (these are the
    Korean single-stock underliers of the Binance tradfi-perps).

    Attributes:
        symbol: Canonical bare symbol used as the instrument symbol (e.g.
            ``005930`` — the KRX numeric code, matching the Yahoo ticker root).
        name: Human-readable issuer name (Samsung Electronics, Hyundai Motor, …).
        yahoo_ticker: Yahoo Finance ticker (e.g. ``005930.KS``).
        first_available_date: Empirically-confirmed Yahoo history floor (the
            instrument's ``available_from`` + the data-status could-exist start).
    """

    symbol: str
    name: str
    yahoo_ticker: str
    first_available_date: date


# KRX (Korea Exchange) single-stock equities — Yahoo-sourced (source="yahoo",
# venue="KRX"). The Korean underliers of the Binance tradfi-perps (HYUNDAI /
# SAMSUNG / SKHYNIX) — added 2026-06-24 to close the equity-perp basis universe
# (previously BLOCKED-DATA "no US-listed twin"; now sourced DIRECTLY via KRX/Yahoo,
# not a US ADR twin). Daily history confirmed back to 2019 on all three
# (probed 2026-06-24: 005930.KS ~1744 daily bars 2019-05→today; 1h/15m/1m intraday
# also serve within the Yahoo lookback ladder). instrument_type=EQUITY.
KRX_EQUITIES: list[KrxEquityDef] = [
    KrxEquityDef("005380", "Hyundai Motor", "005380.KS", date(2019, 1, 2)),
    KrxEquityDef("005930", "Samsung Electronics", "005930.KS", date(2019, 1, 2)),
    KrxEquityDef("000660", "SK Hynix", "000660.KS", date(2019, 1, 2)),
]

# Canonical KRX symbols (the bare numeric codes) — the basis-universe membership
# keys + the data-status / MVP carve-out lookup. Yahoo tickers append ``.KS``.
KRX_EQUITY_SYMBOLS: frozenset[str] = frozenset(eq.symbol for eq in KRX_EQUITIES)

# Bare-KRX-code -> human-readable issuer name. The SSOT display-name lookup for the
# KRX single-stock equities, whose canonical ``instrument_key`` is the opaque 6-digit
# code (``KRX:EQUITY:005930``). Consumed by the instruments-service reference-data
# adapter (``_create_krx_equity_records`` stamps ``InstrumentRecord.name``) AND the
# catalogue roll-up's on-the-fly ``name`` stamp (keyed on ``base_asset`` = the bare
# code), so the data-status Catalogue Explorer / CSV can render "Samsung Electronics"
# next to ``005930`` without a re-fetch. Keyed on the bare code (the ``base_asset`` the
# catalogue carries), covering both the bare ``KRX:EQUITY:005930`` and any legacy
# ``.KS``-suffixed variant (same ``base_asset``).
KRX_EQUITY_NAMES: dict[str, str] = {eq.symbol: eq.name for eq in KRX_EQUITIES}


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
    # VIX cash-index (^VIX daily, ohlcv_24h) REMOVED 2026-06-25 — the CBOE cash-index is
    # retired (operator 2026-06-23). VIX-15m is now AGGREGATED from the VX FUTURES front
    # contract (XCBF.PITCH; see VX.FUT above). G1.f.2 2026-06-26: the ohlcv_15m index
    # source-resolver (data_source_continuity) also retired — VX futures is the only source.
    # ICE/NYBOT US Dollar Index — daily ohlcv_24h via Yahoo (DX-Y.NYB).
    # Full history back to 2019-01-02 (1,864 bars empirically confirmed 2026-06-11).
    # 1h is capped to the last 730 days by Yahoo; use daily for long history.
    # Venue stays ICE — the ONLY retained ICE exception (operator 2026-06-25): DXY is the
    # ICE/NYBOT US Dollar Index, sourced via Yahoo (NOT Databento), so ICE here is a valid
    # Yahoo-sourced tradfi venue and does NOT violate the ICE-Databento-datasets-out-of-
    # subscription purge (which retired only ICE *Databento* datasets, e.g. BRN Brent).
    YahooIndexDef("DXY", "ICE", "DXY", "DX-Y.NYB", date(2019, 1, 2), "fx"),
    # CBOE interest-rate indices — daily ohlcv_24h via Yahoo. Each "close" is the
    # par yield in percent (e.g. 4.53 = 4.53%). The cash-yield tenors (3M/5Y/10Y/30Y,
    # ^IRX/^FVX/^TNX/^TYX) have full history back to 2000-01-03 (6,642 daily bars
    # empirically confirmed 2026-06-11). US2Y ADDED 2026-06-25 (operator: the target
    # curve is 3M/2Y/5Y/10Y) via the only Yahoo 2Y series — the 2-Year Yield future
    # ``2YY=F`` (CME yield-futures; later genesis than the cash tenors). 2YY=F was
    # previously noted stale/zero-volume; the operator directs including it anyway —
    # backfill honest-absence surfaces freshness. Genesis 2018-08-13 (CME yield-futures
    # launch) is a best-estimate — VERIFY the true first bar at backfill.
    YahooIndexDef("US3M", "CBOE", "US3M", "^IRX", date(2000, 1, 3), "fixed_income"),
    YahooIndexDef("US2Y", "CBOE", "US2Y", "2YY=F", date(2018, 8, 13), "fixed_income"),
    YahooIndexDef("US5Y", "CBOE", "US5Y", "^FVX", date(2000, 1, 3), "fixed_income"),
    YahooIndexDef("US10Y", "CBOE", "US10Y", "^TNX", date(2000, 1, 3), "fixed_income"),
    YahooIndexDef("US30Y", "CBOE", "US30Y", "^TYX", date(2000, 1, 3), "fixed_income"),
    # KRX (Korea Exchange) broad-market indices — daily ohlcv_24h via Yahoo Finance.
    # Added 2026-06-27: operator directed "daily KOSPI prices from Yahoo Finance".
    # KOSPI (^KS11) is the Korea Composite Stock Price Index (the KRX benchmark).
    # KOSPI 200 (^KS200) is the large-cap sub-index used in futures/options.
    # Daily history confirmed available back to 2019-01-02 on Yahoo (same floor as DXY).
    # Venue = KRX (Korea Exchange); asset_group = equity; holiday_calendar = XKRX.
    # These are INDEX instruments (non-tradeable pricing references), distinct from the
    # 3 KRX single-stock EQUITYs in KRX_EQUITIES (Samsung/Hyundai/SK Hynix).
    YahooIndexDef("KOSPI", "KRX", "KOSPI", "^KS11", date(2019, 1, 2), "equity"),
    YahooIndexDef("KOSPI200", "KRX", "KOSPI200", "^KS200", date(2019, 1, 2), "equity"),
]

# ---------------------------------------------------------------------------
# Exchange code → human-readable name (for display / grouping)
# ---------------------------------------------------------------------------
EXCHANGE_CODE_TO_NAME: dict[str, str] = {
    # FX futures (standard vs micro are DIFFERENT contract sizes on the same underlying --
    # kept distinguishable, never collapsed to one value; "MICRO-" prefix convention matches
    # the already-shipped, live-consumed `tradfi_symbology.py::EXCHANGE_CODE_TO_NAME["MES"]`
    # value rather than inventing a second convention -- operator ruling 2026-08-07).
    "6A": "AUD",
    "M6A": "MICRO-AUD",
    "6B": "GBP",
    "M6B": "MICRO-GBP",
    "6E": "EUR",
    "M6E": "MICRO-EUR",
    "6J": "JPY",
    "M6J": "MICRO-JPY",
    "6C": "CAD",
    "M6C": "MICRO-CAD",
    "6N": "NZD",
    "M6N": "MICRO-NZD",
    "6S": "CHF",
    "M6S": "MICRO-CHF",
    "6M": "MXN",
    "6Z": "ZAR",
    "6L": "BRL",
    # Energy + metals (same micro-vs-standard distinction as FX above)
    "CL": "CRUDE",
    "MCL": "MICRO-CRUDE",
    "GC": "GOLD",
    "MGC": "MICRO-GOLD",
    "NG": "NATGAS",
    "MNG": "MICRO-NATGAS",
    "HO": "HEATINGOIL",
    "RB": "GASOLINE",
    "SI": "SILVER",
    "MSI": "MICRO-SILVER",
    "HG": "COPPER",
    "MHG": "MICRO-COPPER",
    "PL": "PLATINUM",
    "PA": "PALLADIUM",
    # Agriculture -- naming style (SOYBEAN/SOYOIL/SOYMEAL, not SOYBEANS/SOYBEAN_OIL/
    # SOYBEAN_MEAL) matches the compact convention `tradfi_symbology.py` already uses for
    # these 3 shared codes (operator ruling 2026-08-07: adopt the existing 33-code precedent
    # + standard market terminology over the more verbose form).
    "ZS": "SOYBEAN",
    "ZC": "CORN",
    "ZW": "WHEAT",
    "ZL": "SOYOIL",
    "ZM": "SOYMEAL",
    "LE": "LIVECATTLE",
    "HE": "LEANHOGS",
    # VIX / VX futures (CFE dataset)
    "VX": "VIX",
    # Crypto
    "BTC": "BTC",
    "ETH": "ETH",
    # Index futures (micro-vs-standard distinction, see FX comment above; "MICRO-SP500"
    # exactly matches the pre-existing `tradfi_symbology.py` value for MES)
    "ES": "SP500",
    "MES": "MICRO-SP500",
    "NQ": "NASDAQ100",
    "MNQ": "MICRO-NASDAQ100",
    "RTY": "RUSSELL2000",
    "M2K": "MICRO-RUSSELL2000",
    "YM": "DOW",
    "MYM": "MICRO-DOW",
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
    # Treasuries -- TBOND/TNOTE{n}Y matches both `tradfi_symbology.py`'s existing values and
    # standard market terminology (operator ruling 2026-08-07, see agriculture comment above)
    "ZT": "TNOTE2Y",
    "ZF": "TNOTE5Y",
    "ZN": "TNOTE10Y",
    "ZB": "TBOND",
    # Options on ES (SP500 weekly/daily roots)
    "EW": "SP500",
    "EW1": "SP500",
    "EW2": "SP500",
    "EW3": "SP500",
    "EW4": "SP500",
    "EW5": "SP500",
    "E1A": "SP500",
    "E2A": "SP500",
    "E3A": "SP500",
    "E4A": "SP500",
    "E5A": "SP500",
    "EOM": "SP500",
    # Options-on-futures: commodity options (different root codes from the futures)
    # OG = gold options (underlying GC), LO = crude options (underlying CL),
    # ON = natgas options (underlying NG), HXE = copper options (underlying HG),
    # SO = silver options (underlying SI), PO = platinum options (underlying PL),
    # PAO = palladium options (underlying PA), OH = heating oil options (underlying HO),
    # OB = gasoline options (underlying RB).
    "OG": "GOLD",
    "LO": "CRUDE",
    "ON": "NATGAS",
    "HXE": "COPPER",
    "SO": "SILVER",
    "PO": "PLATINUM",
    "PAO": "PALLADIUM",
    "OH": "HEATING_OIL",
    "OB": "GASOLINE",
    # CME Event Contract roots (ECES = SP500 binary, ECNQ = NQ binary, etc.)
    "ECES": "SP500",
    "ECNQ": "NASDAQ100",
    "ECRTY": "RUSSELL2000",
    "ECYM": "DOW",
    "ECGC": "GOLD",
    "ECCL": "CRUDE",
    "ECNG": "NATGAS",
    "EC6E": "EUR",
    "ECBTC": "BTC",
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
# MVP CME exchange codes — the parent symbols downloaded in MVP mode.
#
# tradfi_mvp_mode_unreachable_dead_gate_2026_07_08.md / mvp_universal_fetch_mode
# (2026-07-10): this set is now DERIVED from the canonical cross-asset-group MVP
# SSOT (``unified_api_contracts.canonical.crosscutting.mvp_scope.MVP_SCOPE["tradfi"]``
# — a ``TradFiMvpRule`` whose ``underliers`` frozenset is ES/NQ/VX + the 7
# commodity roots backing a Binance tradfi-perp), NOT a hand-maintained parallel
# literal. Before this fix the two lists had already drifted (this file's old
# hand list omitted "VX", present in the canonical rule since v10) — deriving the
# BASE root set here means a future canonical-rule change (new/removed root)
# propagates automatically instead of silently drifting again.
#
# Databento's symbology has finer per-product-family granularity than the
# canonical rule's (venue, instrument_type, underlier) grain — a single MVP
# root like "ES" fans out to weekly/day-of-week 0DTE option roots (EW/EW1-4/
# E1A-5A/EOM) and CME event contracts (ECES) that the canonical rule has no
# notion of. That Databento-specific expansion is NECESSARILY hand-listed
# (there is no coarser SSOT for it) in ``_MVP_ROOT_DATABENTO_SUBCODES`` below;
# only the ROOT keys driving the expansion come from the canonical rule.
#
# NOTE: the options-on-futures use DIFFERENT exchange codes from their
# underlying futures (e.g. OG ≠ GC, LO ≠ CL). Both the future AND the
# option root are listed here so get_mvp_databento_symbols_for_venue returns
# the full options-on-futures universe. The adapter uses TRADFI_DATABENTO_INSTRUMENTS
# directly (no MVP filter), so this set gates only get_mvp_databento_symbols_for_venue.
# ---------------------------------------------------------------------------

# Databento sub-codes each canonical MVP root (``TradFiMvpRule.underliers``)
# expands to: the root's own micro-contract + option-surface + event-contract
# exchange codes that don't share the root's own code. Keyed by canonical
# root so a root that disappears from the canonical rule silently drops its
# sub-codes too (no orphaned entries to hand-prune).
_MVP_ROOT_DATABENTO_SUBCODES: dict[str, frozenset[str]] = {
    "ES": frozenset(
        {
            "MES",  # MES.FUT (Micro E-mini S&P 500 futures)
            "EW",  # EW.OPT  (weekly Friday options)
            "EW1",  # EW1.OPT (Monday weekly options)
            "EW2",  # EW2.OPT (Wednesday weekly options)
            "EW4",  # EW4.OPT (Tuesday weekly options)
            "E1A",  # E1A.OPT (Monday 0DTE)
            "E2A",  # E2A.OPT (Tuesday 0DTE)
            "E3A",  # E3A.OPT (Wednesday 0DTE)
            "E4A",  # E4A.OPT (Thursday 0DTE)
            "E5A",  # E5A.OPT (Friday 0DTE)
            "EOM",  # EOM.OPT (end-of-month options)
            "ECES",  # ECES.OPT (S&P 500 event contract)
        }
    ),
    "NQ": frozenset({"ECNQ"}),  # ECNQ.OPT (Nasdaq 100 event contract)
    "GC": frozenset({"OG", "ECGC"}),  # OG.OPT (gold options); ECGC.OPT (gold event contract)
    "CL": frozenset({"LO", "ECCL"}),  # LO.OPT (crude oil options); ECCL.OPT (crude event contract)
    "NG": frozenset({"ON", "ECNG"}),  # ON.OPT (natgas options); ECNG.OPT (natgas event contract)
    "HG": frozenset({"HXE"}),  # HXE.OPT (copper options)
    "SI": frozenset({"SO"}),  # SO.OPT (silver options)
    "PL": frozenset({"PO"}),  # PO.OPT (platinum options)
    "PA": frozenset({"PAO"}),  # PAO.OPT (palladium options)
}

# Codes with no canonical MVP underlier of their own — ECBTC (Bitcoin event
# contract) rides the ES/commodity event-contract family but BTC isn't a
# TradFi underlier root, so it can't be derived from ``TradFiMvpRule.underliers``.
_MVP_ALWAYS_ON_CODES: frozenset[str] = frozenset({"ECBTC"})


def _mvp_tradfi_underliers() -> frozenset[str]:
    """Return the canonical TradFi MVP underlier roots (ES/NQ/VX + commodities).

    Reads ``MVP_SCOPE["tradfi"]`` — the SAME cross-asset-group SSOT CeFi's
    ``get_mvp_data_types_for_cefi_venue`` reads — so this file carries zero
    independent MVP membership judgment; it only derives Databento
    exchange-code granularity from a rule this module doesn't own.
    """
    rule = MVP_SCOPE.get("tradfi")
    if not isinstance(rule, TradFiMvpRule):
        return frozenset()  # pragma: no cover — defensive; MVP_SCOPE always declares tradfi
    return rule.underliers


def _compute_mvp_cme_exchange_codes() -> frozenset[str]:
    """Derive the full CME MVP exchange-code allowlist from the canonical roots."""
    roots = _mvp_tradfi_underliers()
    codes: set[str] = set(roots)
    for root in roots:
        codes.update(_MVP_ROOT_DATABENTO_SUBCODES.get(root, frozenset()))
    codes.update(_MVP_ALWAYS_ON_CODES)
    return frozenset(codes)


MVP_CME_EXCHANGE_CODES: frozenset[str] = _compute_mvp_cme_exchange_codes()


def get_mvp_databento_symbols_for_venue(venue: str) -> list[DatabentoInstrumentDef]:
    """Return MVP-filtered instruments for a venue.

    For CME: gates on ``MVP_CME_EXCHANGE_CODES`` (SP500 complex + NQ + commodity
    futures + commodity options-on-futures + event contracts for MVP roots).
    All other venues: return the full curated list unchanged.
    """
    all_defs = get_databento_symbols_for_venue(venue)
    if venue.upper() == "CME":
        return [d for d in all_defs if d.exchange_code in MVP_CME_EXCHANGE_CODES]
    return all_defs
