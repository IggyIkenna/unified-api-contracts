"""Normalize raw venue ticker responses to CanonicalTicker."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from ...unified_api_contracts_external.aster.schemas import AsterTicker24hr
from ...unified_api_contracts_external.binance.market_schemas import BinanceTicker
from ...unified_api_contracts_external.bitfinex.schemas import BitfinexTicker
from ...unified_api_contracts_external.bitget.schemas import BitgetTicker
from ...unified_api_contracts_external.bitstamp.schemas import BitstampTicker
from ...unified_api_contracts_external.bybit.schemas import BybitTicker
from ...unified_api_contracts_external.ccxt.schemas import CcxtTicker
from ...unified_api_contracts_external.coinbase.schemas import CoinbaseTicker
from ...unified_api_contracts_external.deribit.schemas import DeribitTicker, DeribitTickerFull
from ...unified_api_contracts_external.gateio.schemas import GateioTicker
from ...unified_api_contracts_external.huobi.schemas import HuobiTicker
from ...unified_api_contracts_external.hyperliquid.schemas import HyperliquidTicker
from ...unified_api_contracts_external.ibkr.schemas import IBKRTicker
from ...unified_api_contracts_external.kalshi.schemas import KalshiWebSocketTickerMsg
from ...unified_api_contracts_external.kraken.schemas import KrakenTicker
from ...unified_api_contracts_external.kucoin.schemas import KucoinTicker
from ...unified_api_contracts_external.mexc.schemas import MexcTicker
from ...unified_api_contracts_external.okx.schemas import OKXTicker
from ...unified_api_contracts_external.upbit.schemas import UpbitTicker
from ..domain import CanonicalTicker


def _to_decimal(val: Decimal | float | str | None) -> Decimal | None:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (ValueError, TypeError):
        return None


def _ts_ms_to_datetime(ts_ms: int | None) -> datetime:
    if ts_ms is not None and ts_ms > 0:
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
    return datetime.now(UTC)


def normalize_binance_ticker(
    raw: BinanceTicker, instrument_key: str | None = None, venue: str = "binance"
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol}"
    ts = _ts_ms_to_datetime(raw.time or raw.closeTime)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.lastPrice) or Decimal("0"),
        bid_price=_to_decimal(raw.bidPrice),
        ask_price=_to_decimal(raw.askPrice),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=_to_decimal(raw.quoteVolume),
        price_change_24h=_to_decimal(raw.priceChange),
        price_change_percent_24h=_to_decimal(raw.priceChangePercent),
    )


def normalize_ccxt_ticker(raw: CcxtTicker, instrument_key: str | None = None, venue: str = "ccxt") -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("timestamp") if raw.info else None
    if isinstance(t_ts, (int, float)):
        ts = _ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.last) or Decimal("0"),
        bid_price=_to_decimal(raw.bid),
        ask_price=_to_decimal(raw.ask),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_coinbase_ticker(raw: CoinbaseTicker, instrument_key: str, venue: str = "coinbase") -> CanonicalTicker:
    try:
        ts = datetime.fromisoformat(raw.time.replace("Z", "+00:00")) if raw.time else datetime.now(UTC)
    except (ValueError, TypeError):
        ts = datetime.now(UTC)
    return CanonicalTicker(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.price) or Decimal("0"),
        bid_price=_to_decimal(raw.bid),
        ask_price=_to_decimal(raw.ask),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_bybit_ticker(
    raw: BybitTicker, instrument_key: str | None = None, venue: str = "bybit"
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("ts") if raw.info else None
    if isinstance(t_ts, (int, float)):
        ts = _ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.lastPrice) or Decimal("0"),
        bid_price=_to_decimal(raw.bid1Price),
        ask_price=_to_decimal(raw.ask1Price),
        volume_24h=_to_decimal(raw.volume24h),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_okx_ticker(raw: OKXTicker, instrument_key: str | None = None, venue: str = "okx") -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.instId or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("ts") if raw.info else None
    if isinstance(t_ts, (int, float, str)):
        ts = _ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.last) or Decimal("0"),
        bid_price=_to_decimal(raw.bidPx),
        ask_price=_to_decimal(raw.askPx),
        volume_24h=_to_decimal(raw.vol24h),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_deribit_ticker(
    raw: DeribitTicker | DeribitTickerFull, instrument_key: str | None = None, venue: str = "deribit"
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:OPTION:{raw.instrument_name or ''}"
    ts = datetime.now(UTC)
    if isinstance(raw, DeribitTickerFull) and raw.timestamp:
        ts = _ts_ms_to_datetime(raw.timestamp)
    vol_24h = None
    price_change = None
    price_change_pct = None
    if raw.stats:
        vol_24h = _to_decimal(cast(Decimal | float | str | None, raw.stats.get("volume")))
        price_change = _to_decimal(cast(Decimal | float | str | None, raw.stats.get("price_change")))
        price_change_pct = _to_decimal(cast(Decimal | float | str | None, raw.stats.get("price_change_percentage")))
    bid = _to_decimal(getattr(raw, "best_bid_price", None) or getattr(raw, "bid_price", None))
    ask = _to_decimal(getattr(raw, "best_ask_price", None) or getattr(raw, "ask_price", None))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.last_price) or Decimal("0"),
        bid_price=bid,
        ask_price=ask,
        volume_24h=vol_24h,
        quote_volume_24h=None,
        price_change_24h=price_change,
        price_change_percent_24h=price_change_pct,
    )


def normalize_aster_ticker(
    raw: AsterTicker24hr, instrument_key: str | None = None, venue: str = "aster"
) -> CanonicalTicker:
    """Convert AsterTicker24hr to CanonicalTicker."""
    ik = instrument_key or f"{venue}:PERPETUAL:{raw.symbol or ''}"
    ts = _ts_ms_to_datetime(raw.closeTime or raw.openTime)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.lastPrice) or Decimal("0"),
        bid_price=None,
        ask_price=None,
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=_to_decimal(raw.quoteVolume),
        price_change_24h=_to_decimal(raw.priceChange),
        price_change_percent_24h=_to_decimal(raw.priceChangePercent),
    )


def normalize_ibkr_ticker(raw: IBKRTicker, instrument_key: str, venue: str = "ibkr") -> CanonicalTicker:
    """Convert IBKRTicker to CanonicalTicker."""
    ts = datetime.now(UTC)
    return CanonicalTicker(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.last) or Decimal("0"),
        bid_price=_to_decimal(raw.bid),
        ask_price=_to_decimal(raw.ask),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_hyperliquid_ticker(
    raw: HyperliquidTicker, instrument_key: str | None = None, venue: str = "hyperliquid"
) -> CanonicalTicker:
    """Convert HyperliquidTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:PERPETUAL:{raw.coin or ''}"
    ts = datetime.now(UTC)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.markPx or raw.midPx) or Decimal("0"),
        bid_price=None,
        ask_price=None,
        volume_24h=_to_decimal(raw.dayNtlVlm),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_upbit_ticker(
    raw: UpbitTicker, instrument_key: str | None = None, venue: str = "upbit"
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.market or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("timestamp") if raw.info else None
    if isinstance(t_ts, (int, float)):
        ts = _ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.trade_price) or Decimal("0"),
        bid_price=_to_decimal(raw.bid_price),
        ask_price=_to_decimal(raw.ask_price),
        volume_24h=_to_decimal(raw.acc_trade_volume_24h),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_bitfinex_ticker(
    raw: BitfinexTicker, instrument_key: str | None = None, venue: str = "bitfinex"
) -> CanonicalTicker:
    """Convert BitfinexTicker (v2 array-based) to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.LAST_PRICE) or Decimal("0"),
        bid_price=_to_decimal(raw.BID),
        ask_price=_to_decimal(raw.ASK),
        volume_24h=_to_decimal(raw.VOLUME),
        quote_volume_24h=None,
        price_change_24h=_to_decimal(raw.DAILY_CHANGE),
        price_change_percent_24h=_to_decimal(raw.DAILY_CHANGE_RELATIVE),
    )


def normalize_bitget_ticker(
    raw: BitgetTicker, instrument_key: str | None = None, venue: str = "bitget"
) -> CanonicalTicker:
    """Convert BitgetTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.close) or Decimal("0"),
        bid_price=_to_decimal(raw.bidPr),
        ask_price=_to_decimal(raw.askPr),
        volume_24h=_to_decimal(raw.baseVol),
        quote_volume_24h=_to_decimal(raw.quoteVol),
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_bitstamp_ticker(
    raw: BitstampTicker, instrument_key: str | None = None, venue: str = "bitstamp"
) -> CanonicalTicker:
    """Convert BitstampTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:"
    ts = datetime.now(UTC)
    if raw.timestamp:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromtimestamp(float(raw.timestamp), tz=UTC)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.last) or Decimal("0"),
        bid_price=_to_decimal(raw.bid),
        ask_price=_to_decimal(raw.ask),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_gateio_ticker(
    raw: GateioTicker, instrument_key: str | None = None, venue: str = "gateio"
) -> CanonicalTicker:
    """Convert GateioTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.currency_pair or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.last) or Decimal("0"),
        bid_price=_to_decimal(raw.highest_bid),
        ask_price=_to_decimal(raw.lowest_ask),
        volume_24h=_to_decimal(raw.base_volume),
        quote_volume_24h=_to_decimal(raw.quote_volume),
        price_change_24h=None,
        price_change_percent_24h=_to_decimal(raw.change_percentage),
    )


def normalize_huobi_ticker(
    raw: HuobiTicker, instrument_key: str | None = None, venue: str = "huobi"
) -> CanonicalTicker:
    """Convert HuobiTicker (GET /market/detail/merged) to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:"
    ts = _ts_ms_to_datetime(raw.ts)
    bid_price = _to_decimal(raw.bid[0]) if raw.bid else None
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.close) or Decimal("0"),
        bid_price=bid_price,
        ask_price=None,
        volume_24h=_to_decimal(raw.amount),
        quote_volume_24h=_to_decimal(raw.vol),
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_kraken_ticker(
    raw: KrakenTicker, instrument_key: str | None = None, venue: str = "kraken"
) -> CanonicalTicker:
    """Convert KrakenTicker to CanonicalTicker.

    Fields: a=[ask,...], b=[bid,...], c=[last,...], v=[vol today, vol 24h], h=[high today, high 24h]
    """
    ik = instrument_key or f"{venue}:SPOT:"
    last = _to_decimal(raw.c[0]) if raw.c else None
    bid = _to_decimal(raw.b[0]) if raw.b else None
    ask = _to_decimal(raw.a[0]) if raw.a else None
    vol_24h = _to_decimal(raw.v[1]) if len(raw.v) > 1 else (_to_decimal(raw.v[0]) if raw.v else None)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=last or Decimal("0"),
        bid_price=bid,
        ask_price=ask,
        volume_24h=vol_24h,
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


def normalize_kucoin_ticker(
    raw: KucoinTicker, instrument_key: str | None = None, venue: str = "kucoin"
) -> CanonicalTicker:
    """Convert KucoinTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.last) or Decimal("0"),
        bid_price=_to_decimal(raw.buy),
        ask_price=_to_decimal(raw.sell),
        volume_24h=_to_decimal(raw.vol),
        quote_volume_24h=_to_decimal(raw.volValue),
        price_change_24h=_to_decimal(raw.changePrice),
        price_change_percent_24h=_to_decimal(raw.changeRate),
    )


def normalize_mexc_ticker(raw: MexcTicker, instrument_key: str | None = None, venue: str = "mexc") -> CanonicalTicker:
    """Convert MexcTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.lastPrice) or Decimal("0"),
        bid_price=_to_decimal(raw.bidPrice),
        ask_price=_to_decimal(raw.askPrice),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=_to_decimal(raw.quoteVolume),
        price_change_24h=_to_decimal(raw.priceChange),
        price_change_percent_24h=_to_decimal(raw.priceChangePercent),
    )


def normalize_kalshi_ticker(
    raw: KalshiWebSocketTickerMsg,
    instrument_key: str | None = None,
    venue: str = "kalshi",
) -> CanonicalTicker:
    """Convert KalshiWebSocketTickerMsg to CanonicalTicker.

    Kalshi prices are in cents (integer). Divide by 100 to get dollar price.
    Volume and open_interest in integer contracts.
    """
    sym = raw.market_ticker or ""
    ik = instrument_key or f"{venue}:MARKET:{sym}"
    last = Decimal(str(raw.yes_price or 0)) / Decimal("100")
    bid = Decimal(str(raw.yes_bid or 0)) / Decimal("100") if raw.yes_bid is not None else None
    ask = Decimal(str(raw.yes_ask or 0)) / Decimal("100") if raw.yes_ask is not None else None
    ts = datetime.fromtimestamp((raw.ts or 0) / 1000.0, tz=UTC) if raw.ts else datetime.now(UTC)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=last,
        bid_price=bid,
        ask_price=ask,
        volume_24h=Decimal(str(raw.volume)) if raw.volume is not None else None,
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )
