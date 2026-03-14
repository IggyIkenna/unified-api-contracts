"""Normalize raw venue derivative ticker responses to CanonicalDerivativeTicker.

Covers perp/futures venues: Binance (BinancePremiumIndex / BinanceTicker),
Bybit (BybitTicker + BybitFundingRateHistory), OKX (OKXTicker + OKXFundingRate +
OKXOpenInterest), Deribit (DeribitTickerFull), Hyperliquid (HyperliquidTicker),
and Aster (AsterMarkPrice + AsterOpenInterest + AsterFundingRate).

Tardis is a data-replay vendor with no live derivative ticker schema; a stub is
provided that accepts a plain dict and maps whichever keys are present.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ..canonical.domain import CanonicalDerivativeTicker
from ..external.aster.schemas import (
    AsterFundingRate,
    AsterMarkPrice,
    AsterOpenInterest,
)
from ..external.binance.market_schemas import (
    BinancePremiumIndex,
    BinanceTicker,
)
from ..external.bybit.schemas import (
    BybitFundingRateHistory,
    BybitTicker,
)
from ..external.ccxt.schemas import CcxtFundingRate
from ..external.deribit.schemas import DeribitTickerFull
from ..external.hyperliquid.schemas import HyperliquidTicker
from ..external.okx.schemas import (
    OKXFundingRate,
    OKXOpenInterest,
    OKXTicker,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_decimal(val: object | None) -> Decimal | None:
    """Convert any numeric-ish value to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _ms_to_utc(ts_ms: object | None) -> datetime | None:
    """Convert millisecond timestamp (int or str) to an aware UTC datetime."""
    if ts_ms is None:
        return None
    try:
        ms = int(str(ts_ms))
        if ms <= 0:
            return None
        return datetime.fromtimestamp(ms / 1000.0, tz=UTC)
    except (ValueError, TypeError, OSError):
        return None


def _now_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Binance — BinancePremiumIndex or BinanceTicker (futures)
# ---------------------------------------------------------------------------


def normalize_binance_derivative_ticker(
    raw: BinancePremiumIndex | BinanceTicker,
    instrument_key: str | None = None,
    venue: str = "binance",
) -> CanonicalDerivativeTicker:
    """Normalize Binance premium-index or USD-M futures ticker to CanonicalDerivativeTicker.

    BinancePremiumIndex: markPrice, indexPrice, lastFundingRate, nextFundingTime.
    BinanceTicker (USD-M): lastPrice, lastFundingRate, nextFundingTime — no mark/index.
    """
    symbol: str = ""
    mark_price: Decimal | None = None
    index_price: Decimal | None = None
    last_price: Decimal | None = None
    funding_rate: Decimal | None = None
    next_funding_timestamp: datetime | None = None
    timestamp: datetime = _now_utc()

    if isinstance(raw, BinancePremiumIndex):
        symbol = raw.symbol or ""
        mark_price = _to_decimal(raw.markPrice)
        index_price = _to_decimal(raw.indexPrice)
        funding_rate = _to_decimal(raw.lastFundingRate)
        next_funding_timestamp = _ms_to_utc(raw.nextFundingTime)
        ts_dt = _ms_to_utc(raw.time)
        if ts_dt is not None:
            timestamp = ts_dt
    else:
        # BinanceTicker (USD-M futures path)
        symbol = raw.symbol
        last_price = _to_decimal(raw.lastPrice)
        funding_rate = _to_decimal(raw.lastFundingRate)
        next_funding_timestamp = _ms_to_utc(raw.nextFundingTime)
        ts_dt = _ms_to_utc(raw.time or raw.closeTime)
        if ts_dt is not None:
            timestamp = ts_dt

    ik = instrument_key or f"{venue}:PERPETUAL:{symbol}"
    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate,
        next_funding_timestamp=next_funding_timestamp,
    )


# ---------------------------------------------------------------------------
# Bybit — BybitTicker + optional BybitFundingRateHistory
# ---------------------------------------------------------------------------


def normalize_bybit_derivative_ticker(
    raw: BybitTicker,
    funding: BybitFundingRateHistory | None = None,
    instrument_key: str | None = None,
    venue: str = "bybit",
) -> CanonicalDerivativeTicker:
    """Normalize Bybit ticker (+ optional funding history row) to CanonicalDerivativeTicker.

    BybitTicker carries lastPrice, bid1Price, ask1Price, volume24h, and info dict
    which may contain markPrice, indexPrice, fundingRate, nextFundingTime, openInterest.

    An optional BybitFundingRateHistory row (from GET /v5/market/funding/history) can
    be supplied to enrich funding_rate and funding_timestamp.
    """
    symbol = raw.symbol or ""
    ik = instrument_key or f"{venue}:PERPETUAL:{symbol}"

    last_price = _to_decimal(raw.lastPrice)

    # BybitTicker.info carries the full V5 response fields for derivatives
    info: dict[str, object] = raw.info or {}

    mark_price = _to_decimal(info.get("markPrice"))
    index_price = _to_decimal(info.get("indexPrice"))
    funding_rate_val = _to_decimal(info.get("fundingRate"))
    next_funding_ts = _ms_to_utc(str(info["nextFundingTime"]) if info.get("nextFundingTime") else None)
    open_interest = _to_decimal(info.get("openInterest"))
    open_interest_value = _to_decimal(info.get("openInterestValue"))
    predicted_funding = _to_decimal(info.get("predictedFundingRate"))

    # Extract timestamp from info["ts"] (ms)
    ts_raw = info.get("ts")
    timestamp: datetime = _ms_to_utc(int(ts_raw)) or _now_utc() if isinstance(ts_raw, (int, float)) else _now_utc()

    # Enrich with explicit funding history row if provided
    funding_timestamp: datetime | None = None
    if funding is not None:
        if funding.fundingRate is not None:
            funding_rate_val = _to_decimal(funding.fundingRate)
        if funding.fundingRateTimestamp is not None:
            funding_timestamp = _ms_to_utc(funding.fundingRateTimestamp)

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate_val,
        predicted_funding_rate=predicted_funding,
        funding_timestamp=funding_timestamp,
        next_funding_timestamp=next_funding_ts,
        open_interest=open_interest,
        open_interest_value=open_interest_value,
    )


# ---------------------------------------------------------------------------
# OKX — OKXTicker + optional OKXFundingRate + optional OKXOpenInterest
# ---------------------------------------------------------------------------


def normalize_okx_derivative_ticker(
    raw: OKXTicker,
    funding: OKXFundingRate | None = None,
    oi: OKXOpenInterest | None = None,
    instrument_key: str | None = None,
    venue: str = "okx",
) -> CanonicalDerivativeTicker:
    """Normalize OKX ticker (+ optional funding + OI) to CanonicalDerivativeTicker.

    OKXTicker.info may carry markPx, indexPx, fundingRate, nextFundingTime,
    openInterest from the GET /api/v5/market/ticker response for SWAP instType.

    OKXFundingRate (WS channel: funding-rate or REST /public/funding-rate) carries
    fundingRate, fundingTime, nextFundingRate, nextFundingTime.
    OKXOpenInterest carries oi, oiCcy.
    """
    inst_id = raw.instId or ""
    ik = instrument_key or f"{venue}:PERPETUAL:{inst_id}"

    last_price = _to_decimal(raw.last)

    info: dict[str, object] = raw.info or {}

    mark_price = _to_decimal(info.get("markPx") or info.get("mark_px"))
    index_price = _to_decimal(info.get("idxPx") or info.get("idx_px"))

    # Timestamp from OKXTicker.info["ts"] (ms string)
    ts_raw = info.get("ts")
    timestamp: datetime = _ms_to_utc(ts_raw) or _now_utc() if ts_raw is not None else _now_utc()

    funding_rate_val: Decimal | None = None
    predicted_funding: Decimal | None = None
    next_funding_timestamp: datetime | None = None
    funding_timestamp: datetime | None = None

    if funding is not None:
        funding_rate_val = _to_decimal(funding.fundingRate)
        funding_timestamp = _ms_to_utc(funding.fundingTime)
        predicted_funding = _to_decimal(funding.nextFundingRate)
        next_funding_timestamp = _ms_to_utc(funding.nextFundingTime)

    open_interest_val: Decimal | None = None
    open_interest_value_val: Decimal | None = None
    if oi is not None:
        open_interest_val = _to_decimal(oi.oi)
        open_interest_value_val = _to_decimal(oi.oiCcy)

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate_val,
        predicted_funding_rate=predicted_funding,
        funding_timestamp=funding_timestamp,
        next_funding_timestamp=next_funding_timestamp,
        open_interest=open_interest_val,
        open_interest_value=open_interest_value_val,
    )


# ---------------------------------------------------------------------------
# Deribit — DeribitTickerFull (has funding_8h, open_interest, mark/index)
# ---------------------------------------------------------------------------


def normalize_deribit_derivative_ticker(
    raw: DeribitTickerFull,
    instrument_key: str | None = None,
    venue: str = "deribit",
) -> CanonicalDerivativeTicker:
    """Normalize DeribitTickerFull to CanonicalDerivativeTicker.

    DeribitTickerFull carries:
    - mark_price, index_price, last_price, settlement_price
    - funding_8h (8-hour funding rate for perpetuals; None for futures/options)
    - open_interest (in base currency contracts)
    - timestamp (ms)
    """
    ik = instrument_key or f"{venue}:PERPETUAL:{raw.instrument_name}"
    timestamp = _ms_to_utc(raw.timestamp) or _now_utc()

    mark_price = _to_decimal(raw.mark_price)
    index_price = _to_decimal(raw.index_price)
    last_price = _to_decimal(raw.last_price)
    # funding_8h is the 8-hour cumulative funding rate for perps
    funding_rate = _to_decimal(raw.funding_8h)
    open_interest = _to_decimal(raw.open_interest)

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate,
        open_interest=open_interest,
    )


# ---------------------------------------------------------------------------
# Hyperliquid — HyperliquidTicker
# ---------------------------------------------------------------------------


def normalize_hyperliquid_derivative_ticker(
    raw: HyperliquidTicker,
    instrument_key: str | None = None,
    venue: str = "hyperliquid",
) -> CanonicalDerivativeTicker:
    """Normalize HyperliquidTicker to CanonicalDerivativeTicker.

    HyperliquidTicker fields:
    - coin: symbol
    - markPx: mark price (str)
    - midPx: mid price (str)
    - prevDayPx: previous day price (str)
    - dayNtlVlm: daily notional volume in USD (str)
    - funding: current hourly funding rate (str)
    - openInterest: OI in base (str)
    """
    coin = raw.coin or ""
    ik = instrument_key or f"{venue}:PERPETUAL:{coin}"
    timestamp = _now_utc()

    mark_price = _to_decimal(raw.markPx)
    mid_price = _to_decimal(raw.midPx)
    prev_day_price = _to_decimal(raw.prevDayPx)
    funding_rate = _to_decimal(raw.funding)
    open_interest = _to_decimal(raw.openInterest)
    day_ntl_volume = _to_decimal(raw.dayNtlVlm)

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        mid_price=mid_price,
        funding_rate=funding_rate,
        open_interest=open_interest,
        day_ntl_volume=day_ntl_volume,
        prev_day_price=prev_day_price,
    )


# ---------------------------------------------------------------------------
# Aster — AsterMarkPrice + optional AsterOpenInterest + AsterFundingRate
# ---------------------------------------------------------------------------


def normalize_aster_derivative_ticker(
    mark: AsterMarkPrice,
    oi: AsterOpenInterest | None = None,
    funding: AsterFundingRate | None = None,
    instrument_key: str | None = None,
    venue: str = "aster",
) -> CanonicalDerivativeTicker:
    """Normalize Aster mark price (+ optional OI + funding) to CanonicalDerivativeTicker.

    AsterMarkPrice: symbol, markPrice, indexPrice, lastFundingRate, nextFundingTime, time.
    AsterOpenInterest: symbol, openInterest, time.
    AsterFundingRate: symbol, fundingRate, fundingTime, markPrice.
    """
    symbol = mark.symbol or (oi.symbol if oi else "") or (funding.symbol if funding else "")
    ik = instrument_key or f"{venue}:PERPETUAL:{symbol}"

    timestamp = _ms_to_utc(mark.time) or _now_utc()
    mark_price = _to_decimal(mark.markPrice) if mark.markPrice else None
    index_price = _to_decimal(mark.indexPrice) if mark.indexPrice else None
    funding_rate = _to_decimal(mark.lastFundingRate) if mark.lastFundingRate else None
    next_funding_timestamp = _ms_to_utc(mark.nextFundingTime) if mark.nextFundingTime else None

    open_interest: Decimal | None = None
    if oi is not None and oi.openInterest:
        open_interest = _to_decimal(oi.openInterest)

    explicit_funding_dt: datetime | None = None
    if funding is not None:
        if funding.fundingRate:
            funding_rate = _to_decimal(funding.fundingRate)
        if funding.fundingTime:
            explicit_funding_dt = _ms_to_utc(funding.fundingTime)

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        funding_rate=funding_rate,
        funding_timestamp=explicit_funding_dt,
        next_funding_timestamp=next_funding_timestamp,
        open_interest=open_interest,
    )


# ---------------------------------------------------------------------------
# Tardis — data-replay vendor; no dedicated live derivative ticker schema.
# Accepts a plain dict (e.g. from a parsed Tardis CSV/WebSocket replay message)
# and maps whichever keys are present.
# ---------------------------------------------------------------------------


def normalize_tardis_derivative_ticker(
    raw: dict[str, str | int | float | None],
    instrument_key: str | None = None,
    venue: str = "tardis",
) -> CanonicalDerivativeTicker:
    """Normalize a Tardis replay derivative ticker dict to CanonicalDerivativeTicker.

    Tardis replays raw exchange messages; there is no dedicated Pydantic schema.
    Expected keys (all optional): symbol, timestamp (ms), markPrice, indexPrice,
    lastPrice, fundingRate, nextFundingTime (ms), openInterest.
    """
    symbol = str(raw.get("symbol") or raw.get("s") or "")
    ik = instrument_key or f"{venue}:PERPETUAL:{symbol}"

    ts_raw = raw.get("timestamp") or raw.get("ts")
    timestamp = _ms_to_utc(ts_raw) or _now_utc()

    mark_price = _to_decimal(raw.get("markPrice") or raw.get("mark_price"))
    index_price = _to_decimal(raw.get("indexPrice") or raw.get("index_price"))
    last_price = _to_decimal(raw.get("lastPrice") or raw.get("last_price"))
    funding_rate = _to_decimal(raw.get("fundingRate") or raw.get("funding_rate"))
    next_funding_timestamp = _ms_to_utc(raw.get("nextFundingTime") or raw.get("next_funding_timestamp"))
    open_interest = _to_decimal(raw.get("openInterest") or raw.get("open_interest"))
    open_interest_value = _to_decimal(raw.get("openInterestValue") or raw.get("open_interest_value"))

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate,
        next_funding_timestamp=next_funding_timestamp,
        open_interest=open_interest,
        open_interest_value=open_interest_value,
    )


def normalize_ccxt_funding_rate(
    raw: CcxtFundingRate,
    venue: str = "ccxt",
    symbol: str = "",
) -> CanonicalDerivativeTicker:
    """Convert CcxtFundingRate to CanonicalDerivativeTicker.

    CCXT fetch_funding_rate: symbol, fundingRate (float), fundingTimestamp (ms).
    Maps to CanonicalDerivativeTicker with funding_rate; mark_price etc. are None.
    """
    sym = symbol or raw.symbol or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.fundingTimestamp or 0) / 1000.0, tz=UTC)
    funding_rate: Decimal | None = None
    if raw.fundingRate is not None:
        with contextlib.suppress(InvalidOperation):
            funding_rate = Decimal(str(raw.fundingRate))
    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        mark_price=None,
        index_price=None,
        funding_rate=funding_rate,
        next_funding_timestamp=None,
        open_interest=None,
        open_interest_value=None,
        predicted_funding_rate=None,
    )


__all__ = [
    "normalize_aster_derivative_ticker",
    "normalize_binance_derivative_ticker",
    "normalize_bybit_derivative_ticker",
    "normalize_ccxt_funding_rate",
    "normalize_deribit_derivative_ticker",
    "normalize_hyperliquid_derivative_ticker",
    "normalize_okx_derivative_ticker",
    "normalize_tardis_derivative_ticker",
]
