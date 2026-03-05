"""Normalize raw venue ticker responses to CanonicalTicker."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from ...unified_api_contracts_external.binance.market_schemas import BinanceTicker
from ...unified_api_contracts_external.bybit.schemas import BybitTicker
from ...unified_api_contracts_external.ccxt.schemas import CcxtTicker
from ...unified_api_contracts_external.coinbase.schemas import CoinbaseTicker
from ...unified_api_contracts_external.deribit.schemas import DeribitTicker, DeribitTickerFull
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
