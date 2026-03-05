"""Reference data normalizers: venue-specific instrument metadata -> CanonicalMarketInfo."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime

from ...unified_api_contracts_external.aster.schemas import AsterExchangeInfo, AsterMarket
from ...unified_api_contracts_external.binance.market_schemas import (
    BinanceInstrumentInfo,
    BinanceSymbol,
)
from ...unified_api_contracts_external.bybit.schemas import BybitInstrumentInfo
from ...unified_api_contracts_external.ccxt.schemas import CcxtMarket, CcxtMarketLimits
from ...unified_api_contracts_external.coingecko.schemas import GlobalMarketData, GlobalMarketResponse
from ...unified_api_contracts_external.deribit.schemas import DeribitInstrument
from ...unified_api_contracts_external.dydx.schemas import DydxPerpetualMarket
from ...unified_api_contracts_external.fix.schemas import FixMarketDataRequest, FixMarketDataSnapshot
from ...unified_api_contracts_external.ibkr.schemas import IBKRContractDetails
from ...unified_api_contracts_external.matchbook.schemas import MatchbookMarket
from ...unified_api_contracts_external.metabet.schemas import MetabetMarket
from ...unified_api_contracts_external.nautilus import Instrument as NautilusInstrument
from ...unified_api_contracts_external.odds_api.schemas import OddsApiMarket
from ...unified_api_contracts_external.odds_engine.schemas import OddsEngineMarket
from ...unified_api_contracts_external.okx.schemas import OKXInstrumentInfo
from ...unified_api_contracts_external.predictit.schemas import PredictItMarket
from ...unified_api_contracts_external.sports.canonical.arbitrage import ArbitrageMarket
from ...unified_api_contracts_external.tardis.schemas import TardisInstrument
from ...unified_api_contracts_external.upbit.schemas import UpbitMarket
from ..domain import CanonicalMarketInfo

# ---------------------------------------------------------------------------
# Binance
# ---------------------------------------------------------------------------


def _binance_filter_value(
    filters: list[dict[str, object]] | None,
    filter_type: str,
    key: str,
) -> float | None:
    """Extract a float value from a Binance filters list by filterType and key."""
    if not filters:
        return None
    for f in filters:
        if f.get("filterType") == filter_type:
            raw = f.get(key)
            if raw is not None:
                return float(str(raw))
    return None


def _binance_instrument_type(raw: BinanceInstrumentInfo | BinanceSymbol) -> str:
    """Infer instrument type string from Binance schema.

    - BinanceInstrumentInfo has contractType (PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER, DELIVERY)
    - BinanceSymbol is always a spot instrument
    """
    if isinstance(raw, BinanceInstrumentInfo):
        contract_type = (raw.contractType or "").upper()
        if contract_type == "PERPETUAL":
            return "PERPETUAL"
        if contract_type in ("CURRENT_QUARTER", "NEXT_QUARTER", "DELIVERY"):
            return "FUTURE"
        return "SPOT"
    # BinanceSymbol is always spot
    return "SPOT"


def normalize_binance_symbol(
    raw: BinanceInstrumentInfo | BinanceSymbol,
    venue: str = "binance",
) -> CanonicalMarketInfo:
    """Normalize a BinanceInstrumentInfo or BinanceSymbol to CanonicalMarketInfo.

    instrument_type is inferred from contractType:
    - PERPETUAL -> PERPETUAL
    - CURRENT_QUARTER / NEXT_QUARTER / DELIVERY -> FUTURE
    - absent (spot symbol) -> SPOT

    tick_size: PRICE_FILTER.tickSize
    min_size:  LOT_SIZE.minQty
    """
    instrument_type = _binance_instrument_type(raw)
    symbol = raw.symbol
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size: float | None = None
    min_size: float | None = None

    if isinstance(raw, BinanceInstrumentInfo) and raw.filters:
        tick_size = _binance_filter_value(raw.filters, "PRICE_FILTER", "tickSize")
        min_size = _binance_filter_value(raw.filters, "LOT_SIZE", "minQty")

    base_asset = raw.baseAsset
    quote_asset = raw.quoteAsset

    contract_size: float | None = None
    if isinstance(raw, BinanceInstrumentInfo) and raw.contractSize is not None:
        contract_size = float(raw.contractSize)

    return CanonicalMarketInfo(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=contract_size,
        base_asset=base_asset,
        quote_asset=quote_asset,
        settle_asset=raw.marginAsset if isinstance(raw, BinanceInstrumentInfo) else None,
    )


# ---------------------------------------------------------------------------
# Bybit
# ---------------------------------------------------------------------------


def _bybit_instrument_type(raw: BybitInstrumentInfo) -> str:
    """Infer instrument type from Bybit contractType field.

    contractType values: LinearPerpetual, LinearFutures, InversePerpetual,
    InverseFutures, or None (spot has no contractType).
    Also covers category-style inference from settleCoin/optionsType.
    """
    contract_type = (raw.contractType or "").lower()
    if "perpetual" in contract_type:
        return "PERPETUAL"
    if "future" in contract_type or "futures" in contract_type:
        return "FUTURE"
    if raw.optionsType is not None:
        return "OPTION"
    # No contractType => spot
    return "SPOT"


def normalize_bybit_market(
    raw: BybitInstrumentInfo,
    venue: str = "bybit",
) -> CanonicalMarketInfo:
    """Normalize a BybitInstrumentInfo to CanonicalMarketInfo.

    tick_size:   priceFilter["tickSize"]
    min_size:    lotSizeFilter["minOrderQty"]
    """
    instrument_type = _bybit_instrument_type(raw)
    symbol = raw.symbol
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size: float | None = None
    min_size: float | None = None

    if raw.priceFilter:
        raw_tick = raw.priceFilter.get("tickSize")
        if raw_tick is not None:
            tick_size = float(str(raw_tick))

    if raw.lotSizeFilter:
        raw_min_qty = raw.lotSizeFilter.get("minOrderQty")
        if raw_min_qty is not None:
            min_size = float(str(raw_min_qty))

    return CanonicalMarketInfo(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=None,
        base_asset=raw.baseCoin,
        quote_asset=raw.quoteCoin,
        settle_asset=raw.settleCoin,
    )


# ---------------------------------------------------------------------------
# OKX
# ---------------------------------------------------------------------------


def _okx_instrument_type(inst_type: str | None) -> str:
    """Map OKX instType to canonical instrument type string.

    OKX instType values: SPOT, MARGIN, SWAP, FUTURES, OPTION
    """
    mapping: dict[str, str] = {
        "SPOT": "SPOT",
        "MARGIN": "SPOT",
        "SWAP": "PERPETUAL",
        "FUTURES": "FUTURE",
        "OPTION": "OPTION",
    }
    return mapping.get((inst_type or "").upper(), "SPOT")


def normalize_okx_market(
    raw: OKXInstrumentInfo,
    venue: str = "okx",
) -> CanonicalMarketInfo:
    """Normalize an OKXInstrument to CanonicalMarketInfo.

    instrument_type: SPOT/MARGIN->SPOT, SWAP->PERPETUAL, FUTURES->FUTURE, OPTION->OPTION
    tick_size:  tickSz
    min_size:   minSz (min order size); lotSz used as fallback
    contract_size: ctVal (contract value in base currency)
    settle_asset: settleCcy
    """
    instrument_type = _okx_instrument_type(raw.instType)
    symbol = raw.instId
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size = float(raw.tickSz) if raw.tickSz is not None else None
    min_size = float(raw.minSz) if raw.minSz is not None else (float(raw.lotSz) if raw.lotSz is not None else None)
    contract_size = float(raw.ctVal) if raw.ctVal is not None else None

    return CanonicalMarketInfo(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=contract_size,
        base_asset=raw.baseCcy,
        quote_asset=raw.quoteCcy,
        settle_asset=raw.settleCcy,
    )


# ---------------------------------------------------------------------------
# Deribit
# ---------------------------------------------------------------------------


def _deribit_instrument_type(kind: str | None) -> str:
    """Map Deribit kind to canonical instrument type string.

    kind values: future, option, spot, perpetual, future_combo, option_combo
    """
    mapping: dict[str, str] = {
        "future": "FUTURE",
        "option": "OPTION",
        "spot": "SPOT",
        "perpetual": "PERPETUAL",
        "future_combo": "FUTURE",
        "option_combo": "OPTION",
    }
    return mapping.get((kind or "").lower(), "FUTURE")


def normalize_deribit_instrument(
    raw: DeribitInstrument,
    venue: str = "deribit",
) -> CanonicalMarketInfo:
    """Normalize a DeribitInstrument to CanonicalMarketInfo.

    DeribitInstrument is the base schema; DeribitInstrumentInfoFull has more fields
    but both share instrument_name, kind, base_currency, quote_currency,
    tick_size, and min_trade_amount.
    """
    instrument_type = _deribit_instrument_type(raw.kind)
    symbol = raw.instrument_name or ""
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size = float(raw.tick_size) if raw.tick_size is not None else None
    min_size = float(raw.min_trade_amount) if raw.min_trade_amount is not None else None

    return CanonicalMarketInfo(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=None,
        base_asset=raw.base_currency,
        quote_asset=raw.quote_currency,
        settle_asset=raw.settlement_currency,
    )


# ---------------------------------------------------------------------------
# CCXT
# ---------------------------------------------------------------------------


def _ccxt_instrument_type(raw: CcxtMarket) -> str:
    """Infer instrument type from CCXT market boolean flags.

    CCXT sets: spot, swap, future, option (bool fields).
    Falls back to the type string if flags are absent.
    """
    if raw.type == "option":
        return "OPTION"
    if raw.swap:
        return "PERPETUAL"
    if raw.futures:
        return "FUTURE"
    if raw.spot:
        return "SPOT"
    # Fallback to type string
    type_str = (raw.type or "").lower()
    type_map: dict[str, str] = {
        "spot": "SPOT",
        "swap": "PERPETUAL",
        "future": "FUTURE",
        "futures": "FUTURE",
        "option": "OPTION",
    }
    return type_map.get(type_str, "SPOT")


def normalize_ccxt_market(
    raw: CcxtMarket,
    venue: str = "ccxt",
) -> CanonicalMarketInfo:
    """Normalize a CcxtMarket to CanonicalMarketInfo.

    tick_size:    precision.price (step size for price)
    min_size:     limits.amount["min"]
    contract_size: contractSize
    settle_asset: settle
    """
    instrument_type = _ccxt_instrument_type(raw)
    symbol = raw.symbol or raw.id or ""
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size: float | None = None
    min_size: float | None = None

    if raw.precision is not None:
        price_prec = raw.precision.get("price") if isinstance(raw.precision, dict) else raw.precision.price
        if price_prec is not None:
            tick_size = float(str(price_prec))

    if isinstance(raw.limits, CcxtMarketLimits) and raw.limits.amount is not None:
        _min = raw.limits.amount.get("min")
        if _min is not None:
            min_size = float(_min)

    return CanonicalMarketInfo(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=float(raw.contractSize) if raw.contractSize is not None else None,
        base_asset=raw.base,
        quote_asset=raw.quote,
        settle_asset=raw.settle,
    )


# ---------------------------------------------------------------------------
# IBKR
# ---------------------------------------------------------------------------


def _ibkr_instrument_type(sec_type: str | None) -> str:
    """Map IBKR secType to canonical instrument type string.

    secType values: STK, OPT, FUT, CASH, CFD, BAG, WAR, BOND, FUND, CMDTY, IND
    """
    mapping: dict[str, str] = {
        "STK": "SPOT",
        "CASH": "SPOT",
        "CFD": "SPOT",
        "IND": "SPOT",
        "FUND": "SPOT",
        "CMDTY": "SPOT",
        "FUT": "FUTURE",
        "OPT": "OPTION",
        "WAR": "OPTION",
        "BAG": "FUTURE",
        "BOND": "SPOT",
    }
    return mapping.get((sec_type or "").upper(), "SPOT")


def normalize_ibkr_contract_details(
    raw: IBKRContractDetails,
    venue: str = "ibkr",
) -> CanonicalMarketInfo:
    """Normalize an IBKRContractDetails to CanonicalMarketInfo.

    tick_size:  minTick
    min_size:   not available in IBKRContractDetails (None)
    contract_size: multiplier (string -> float)
    base_asset: symbol (underlying)
    quote_asset: currency
    """
    instrument_type = _ibkr_instrument_type(raw.secType)
    # Use localSymbol if available for uniqueness, otherwise plain symbol
    symbol = raw.localSymbol or raw.symbol or ""
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"

    tick_size = float(raw.minTick) if raw.minTick is not None else None

    contract_size: float | None = None
    if raw.multiplier is not None:
        try:
            contract_size = float(raw.multiplier)
        except (ValueError, TypeError):
            contract_size = None

    return CanonicalMarketInfo(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=None,
        contract_size=contract_size,
        base_asset=raw.symbol,
        quote_asset=raw.currency,
        settle_asset=None,
    )


def normalize_aster_market(
    raw: AsterMarket,
    venue: str = "aster",
) -> CanonicalMarketInfo:
    """Normalize AsterMarket to CanonicalMarketInfo."""
    sym = raw.symbol or raw.market_id or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=raw.base_asset,
        quote_asset=raw.quote_asset,
        settle_asset=None,
    )


def normalize_aster_exchange_info(
    raw: AsterExchangeInfo,
    venue: str = "aster",
) -> CanonicalMarketInfo:
    """Normalize AsterExchangeInfo (exchange-level info) to CanonicalMarketInfo.

    AsterExchangeInfo is an exchange metadata response; mapped to a pseudo-instrument
    representing the exchange itself. Use normalize_aster_market for per-symbol info.
    """
    ik = f"{venue.upper()}:EXCHANGE:INFO"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol="EXCHANGE_INFO",
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_coingecko_global_market(
    raw: GlobalMarketData,
    venue: str = "coingecko",
) -> CanonicalMarketInfo:
    """Normalize CoinGecko GlobalMarketData to CanonicalMarketInfo.

    GlobalMarketData is a macro-level aggregate (not a single instrument),
    mapped to a pseudo-instrument representing the global crypto market cap.
    """
    ik = f"{venue.upper()}:INDEX:GLOBAL"
    total_mcap_usd = raw.total_market_cap.get("usd") if raw.total_market_cap else None
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol="GLOBAL",
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=total_mcap_usd,  # repurpose for total market cap
        base_asset=None,
        quote_asset="USD",
        settle_asset=None,
    )


def normalize_coingecko_global_market_response(
    raw: GlobalMarketResponse,
    venue: str = "coingecko",
) -> CanonicalMarketInfo:
    """Normalize CoinGecko GlobalMarketResponse (wrapper) to CanonicalMarketInfo."""
    return normalize_coingecko_global_market(raw.data, venue=venue)


def normalize_dydx_perpetual_market(
    raw: DydxPerpetualMarket,
    venue: str = "dydx",
) -> CanonicalMarketInfo:
    """Normalize DydxPerpetualMarket to CanonicalMarketInfo."""
    sym = raw.market or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    tick_size: float | None = None
    if raw.tickSize is not None:
        with contextlib.suppress(ValueError, TypeError):
            tick_size = float(raw.tickSize)
    min_size: float | None = None
    if raw.stepSize is not None:
        with contextlib.suppress(ValueError, TypeError):
            min_size = float(raw.stepSize)
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=None,
        base_asset=raw.baseAsset,
        quote_asset=raw.quoteAsset,
        settle_asset=None,
    )


def normalize_fix_market_data_snapshot(
    raw: FixMarketDataSnapshot,
    venue: str = "fix",
) -> CanonicalMarketInfo:
    """Normalize FixMarketDataSnapshot (Tag 35=W) to CanonicalMarketInfo."""
    sym = raw.symbol or ""
    ik = f"{venue.upper()}:UNKNOWN:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_fix_market_data_request(
    raw: FixMarketDataRequest,
    venue: str = "fix",
) -> list[CanonicalMarketInfo]:
    """Normalize FixMarketDataRequest (Tag 35=V) to a list of CanonicalMarketInfo.

    One entry per symbol in the request.
    """
    results: list[CanonicalMarketInfo] = []
    for sym in raw.symbols:
        ik = f"{venue.upper()}:UNKNOWN:{sym}"
        results.append(
            CanonicalMarketInfo(
                instrument_key=ik,
                venue=venue,
                symbol=sym,
                timestamp=datetime.now(UTC),
                tick_size=None,
                min_size=None,
                contract_size=None,
                base_asset=None,
                quote_asset=None,
                settle_asset=None,
            )
        )
    return results


def normalize_matchbook_market(
    raw: MatchbookMarket,
    venue: str = "matchbook",
) -> CanonicalMarketInfo:
    """Normalize MatchbookMarket to CanonicalMarketInfo."""
    sym = str(raw.id or "")
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_metabet_market(
    raw: MetabetMarket,
    venue: str = "metabet",
) -> CanonicalMarketInfo:
    """Normalize MetabetMarket to CanonicalMarketInfo."""
    sym = raw.market or ""
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_nautilus_instrument(
    raw: NautilusInstrument,
    venue: str = "",
) -> CanonicalMarketInfo:
    """Normalize NautilusTrader Instrument to CanonicalMarketInfo."""
    v = venue or raw.venue or "nautilus"
    sym = raw.symbol or ""
    ik = raw.instrument_id or f"{v.upper()}:UNKNOWN:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=v,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_odds_api_market(
    raw: OddsApiMarket,
    venue: str = "odds_api",
) -> CanonicalMarketInfo:
    """Normalize OddsApiMarket to CanonicalMarketInfo."""
    sym = raw.key or ""
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_odds_engine_market(
    raw: OddsEngineMarket,
    venue: str = "odds_engine",
) -> CanonicalMarketInfo:
    """Normalize OddsEngineMarket to CanonicalMarketInfo."""
    sym = raw.market or ""
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_predictit_market(
    raw: PredictItMarket,
    venue: str = "predictit",
) -> CanonicalMarketInfo:
    """Normalize PredictItMarket to CanonicalMarketInfo."""
    sym = raw.short_name or raw.name or str(raw.id or "")
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_arbitrage_market(
    raw: ArbitrageMarket,
    venue: str = "sports",
) -> CanonicalMarketInfo:
    """Normalize ArbitrageMarket (sports canonical) to CanonicalMarketInfo.

    ArbitrageMarket represents one leg of an arbitrage opportunity at a bookmaker.
    """
    sym = raw.selection or ""
    ik = f"{venue.upper()}:MARKET:{raw.bookmaker_key}:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_tardis_instrument(
    raw: TardisInstrument,
    venue: str = "",
) -> CanonicalMarketInfo:
    """Normalize TardisInstrument to CanonicalMarketInfo."""
    v = venue or raw.exchange or "tardis"
    sym = raw.symbol or ""
    ik = f"{v.upper()}:UNKNOWN:{sym}"
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=v,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


def normalize_upbit_market(
    raw: UpbitMarket,
    venue: str = "upbit",
) -> CanonicalMarketInfo:
    """Normalize UpbitMarket to CanonicalMarketInfo.

    UpbitMarket.market format is "KRW-BTC" (quote-base). Base/quote split on "-".
    """
    sym = raw.market or ""
    ik = f"{venue.upper()}:SPOT:{sym}"
    parts = sym.split("-", 1)
    quote_asset = parts[0] if len(parts) == 2 else None
    base_asset = parts[1] if len(parts) == 2 else None
    return CanonicalMarketInfo(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=base_asset,
        quote_asset=quote_asset,
        settle_asset=None,
    )


__all__ = [
    "normalize_arbitrage_market",
    "normalize_aster_exchange_info",
    "normalize_aster_market",
    "normalize_binance_symbol",
    "normalize_bybit_market",
    "normalize_ccxt_market",
    "normalize_coingecko_global_market",
    "normalize_coingecko_global_market_response",
    "normalize_deribit_instrument",
    "normalize_dydx_perpetual_market",
    "normalize_fix_market_data_request",
    "normalize_fix_market_data_snapshot",
    "normalize_ibkr_contract_details",
    "normalize_matchbook_market",
    "normalize_metabet_market",
    "normalize_nautilus_instrument",
    "normalize_odds_api_market",
    "normalize_odds_engine_market",
    "normalize_okx_market",
    "normalize_predictit_market",
    "normalize_tardis_instrument",
    "normalize_upbit_market",
]
