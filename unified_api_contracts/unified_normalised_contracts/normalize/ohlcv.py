"""OHLCV normalizers: raw venue OHLCV -> CanonicalOhlcvBar / ProcessedCandle."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime

from ...unified_api_contracts_external.aster.schemas import AsterKline
from ...unified_api_contracts_external.barchart.schemas import BarchartOhlcv15m
from ...unified_api_contracts_external.binance.market_schemas import BinanceKline
from ...unified_api_contracts_external.bybit.schemas import BybitKline
from ...unified_api_contracts_external.ccxt.schemas import CcxtOhlcv
from ...unified_api_contracts_external.coinbase.schemas import CoinbaseCandle
from ...unified_api_contracts_external.databento.schemas import DATABENTO_PRICE_DIVISOR, DatabentoOhlcvBar
from ...unified_api_contracts_external.hyperliquid.schemas import HyperliquidCandle
from ...unified_api_contracts_external.kalshi.schemas import KalshiCandlestick
from ...unified_api_contracts_external.okx.schemas import OKXCandleWS
from ...unified_api_contracts_external.yahoo_finance import YahooOhlcv
from ...unified_api_contracts_external.yahoo_finance.schemas import YahooOhlcv24h
from ..domain import CanonicalOhlcvBar


def _databento_price(px: int) -> float:
    """Convert Databento fixed-point price to float."""
    return float(px) / float(DATABENTO_PRICE_DIVISOR)


def normalize_databento_ohlcv_bar(
    raw: DatabentoOhlcvBar, venue: str = "databento", symbol: str = ""
) -> CanonicalOhlcvBar:
    """Convert DatabentoOhlcvBar to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp(raw.ts_event / 1e9, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol or str(raw.instrument_id),
        open=_databento_price(raw.open),
        high=_databento_price(raw.high),
        low=_databento_price(raw.low),
        close=_databento_price(raw.close),
        volume=float(raw.volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_binance_kline(raw: BinanceKline, symbol: str, venue: str = "binance") -> CanonicalOhlcvBar:
    """Convert BinanceKline to CanonicalOhlcvBar.

    Binance kline open_time is in milliseconds.
    """
    ts = datetime.fromtimestamp(raw.open_time / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=float(raw.open_price),
        high=float(raw.high_price),
        low=float(raw.low_price),
        close=float(raw.close_price),
        volume=float(raw.volume),
        quote_volume=float(raw.quote_asset_volume),
        count=raw.number_of_trades,
        vwap=None,
    )


def normalize_bybit_kline(raw: BybitKline, symbol: str, venue: str = "bybit") -> CanonicalOhlcvBar:
    """Convert BybitKline to CanonicalOhlcvBar.

    Bybit kline startTime is a string of milliseconds.
    """
    ts = datetime.fromtimestamp(int(raw.startTime) / 1000.0, tz=UTC)
    quote_vol = float(raw.turnover) if raw.turnover is not None else None
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=float(raw.openPrice),
        high=float(raw.highPrice),
        low=float(raw.lowPrice),
        close=float(raw.closePrice),
        volume=float(raw.volume),
        quote_volume=quote_vol,
        count=None,
        vwap=None,
    )


def normalize_okx_kline(raw: OKXCandleWS, symbol: str, venue: str = "okx") -> CanonicalOhlcvBar:
    """Convert OKXCandleWS to CanonicalOhlcvBar.

    OKX candle ts is a string of milliseconds (bar open time).
    volCcyQuote is the quote currency volume when available.
    """
    ts = datetime.fromtimestamp(int(raw.ts) / 1000.0, tz=UTC)
    quote_vol = float(raw.volCcyQuote) if raw.volCcyQuote is not None else None
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=float(raw.o),
        high=float(raw.h),
        low=float(raw.l),
        close=float(raw.c),
        volume=float(raw.vol),
        quote_volume=quote_vol,
        count=None,
        vwap=None,
    )


def normalize_barchart_ohlcv(raw: BarchartOhlcv15m, venue: str = "barchart") -> CanonicalOhlcvBar:
    """Convert BarchartOhlcv15m to CanonicalOhlcvBar.

    Barchart Time field is a string in US Eastern Time (YYYY-MM-DD HH:MM).
    It is stored as-is (no timezone conversion) and treated as a naive
    local timestamp; callers requiring UTC should convert before calling.
    The field is parsed as UTC-naive then made UTC-aware by attaching UTC tz.
    """
    ts = datetime.strptime(raw.Time, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
    symbol = "BARCHART"
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=raw.Open,
        high=raw.High,
        low=raw.Low,
        close=raw.Last,
        volume=raw.Volume if raw.Volume is not None else 0.0,
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_yahoo_ohlcv(raw: YahooOhlcv, venue: str = "yahoo_finance") -> CanonicalOhlcvBar:
    """Convert YahooOhlcv to CanonicalOhlcvBar.

    timestamp_ms is Unix milliseconds (converted from pandas Timestamp by caller).
    """
    ts = datetime.fromtimestamp(raw.timestamp_ms / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=raw.symbol,
        open=raw.Open,
        high=raw.High,
        low=raw.Low,
        close=raw.Close,
        volume=raw.Volume,
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_aster_kline(raw: AsterKline, symbol: str = "", venue: str = "aster") -> CanonicalOhlcvBar:
    """Convert AsterKline to CanonicalOhlcvBar (Binance Futures-compatible format)."""
    ts = datetime.fromtimestamp(raw.openTime / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=float(raw.open),
        high=float(raw.high),
        low=float(raw.low),
        close=float(raw.close),
        volume=float(raw.volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_ccxt_ohlcv(raw: CcxtOhlcv, symbol: str = "", venue: str = "ccxt") -> CanonicalOhlcvBar:
    """Convert CcxtOhlcv to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=float(raw.open or 0),
        high=float(raw.high or 0),
        low=float(raw.low or 0),
        close=float(raw.close or 0),
        volume=float(raw.volume or 0),
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_coinbase_candle(raw: CoinbaseCandle, symbol: str = "", venue: str = "coinbase") -> CanonicalOhlcvBar:
    """Convert CoinbaseCandle to CanonicalOhlcvBar.

    Coinbase candle timestamp is Unix seconds.
    """
    ts = datetime.fromtimestamp(float(raw.timestamp), tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=float(raw.open),
        high=float(raw.high),
        low=float(raw.low),
        close=float(raw.close),
        volume=float(raw.volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_hyperliquid_candle(
    raw: HyperliquidCandle, symbol: str = "", venue: str = "hyperliquid"
) -> CanonicalOhlcvBar:
    """Convert HyperliquidCandle to CanonicalOhlcvBar.

    Hyperliquid candle timestamps are Unix milliseconds. Symbol from raw.s field.
    """
    ts = datetime.fromtimestamp((raw.t or 0) / 1000.0, tz=UTC)
    sym = symbol or raw.s or ""
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=sym,
        open=float(raw.o or 0),
        high=float(raw.h or 0),
        low=float(raw.low or 0),
        close=float(raw.c or 0),
        volume=float(raw.v or 0),
        quote_volume=None,
        count=raw.n,
        vwap=None,
    )


def normalize_yahoo_finance_ohlcv24h(
    raw: YahooOhlcv24h, symbol: str = "", venue: str = "yahoo_finance"
) -> CanonicalOhlcvBar:
    """Convert YahooOhlcv24h (daily history bar) to CanonicalOhlcvBar.

    Date is a string like "2024-01-15"; treated as midnight UTC.
    """
    ts = datetime.now(UTC)
    if raw.Date:
        with contextlib.suppress(ValueError):
            ts = datetime.strptime(raw.Date, "%Y-%m-%d").replace(tzinfo=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=raw.Open or 0.0,
        high=raw.High or 0.0,
        low=raw.Low or 0.0,
        close=raw.Close or 0.0,
        volume=raw.Volume or 0.0,
        quote_volume=None,
        count=None,
        vwap=None,
    )


def normalize_kalshi_candlestick(raw: KalshiCandlestick, symbol: str = "", venue: str = "kalshi") -> CanonicalOhlcvBar:
    """Convert KalshiCandlestick to CanonicalOhlcvBar.

    Kalshi uses yes_*_dollars fields (string decimals) and end_period_ts (ISO string).
    Open/high/low/close are approximated from yes_open/high/low/close_dollars.
    Volume from volume_fp (string float contracts).
    """
    ts = datetime.now(UTC)
    if raw.end_period_ts:
        with contextlib.suppress(ValueError):
            ts = datetime.fromisoformat(raw.end_period_ts.replace("Z", "+00:00"))
    sym = symbol or raw.ticker or ""
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=sym,
        open=float(raw.yes_open_dollars or 0),
        high=float(raw.yes_high_dollars or 0),
        low=float(raw.yes_low_dollars or 0),
        close=float(raw.yes_close_dollars or 0),
        volume=float(raw.volume_fp or 0),
        quote_volume=None,
        count=None,
        vwap=None,
    )


__all__ = [
    "normalize_aster_kline",
    "normalize_barchart_ohlcv",
    "normalize_binance_kline",
    "normalize_bybit_kline",
    "normalize_ccxt_ohlcv",
    "normalize_coinbase_candle",
    "normalize_databento_ohlcv_bar",
    "normalize_hyperliquid_candle",
    "normalize_kalshi_candlestick",
    "normalize_okx_kline",
    "normalize_yahoo_finance_ohlcv24h",
    "normalize_yahoo_ohlcv",
]
