"""Per-source normalizers for aster."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import (
    CanonicalDerivativeTicker,
    CanonicalInstrument,
    CanonicalLiquidation,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    WebSocketEvent,
)
from ...canonical.domain.execution import CanonicalOrder, OrderSide, OrderStatus, OrderType
from ...normalize_utils._helpers import (
    _d,
    _to_decimal,
    _to_levels,
    _ts_ms_to_datetime,
)
from ...normalize_utils.connectivity import normalize_ws_disconnect
from .schemas import (
    AsterExchangeInfo,
    AsterFundingRate,
    AsterKline,
    AsterLiquidationOrder,
    AsterMarket,
    AsterMarkPrice,
    AsterOpenInterest,
    AsterOrder,
    AsterOrderBook,
    AsterTicker24hr,
    AsterTrade,
)

# ---------------------------------------------------------------------------
# Helpers (module-level)
# ---------------------------------------------------------------------------

_parse_decimal = _d

_now_utc = lambda: datetime.now(UTC)  # noqa: E731


def _ms_to_utc(ts_ms: object | None) -> datetime | None:
    if ts_ms is None:
        return None
    try:
        ms = int(str(ts_ms))
        if ms <= 0:
            return None
        return datetime.fromtimestamp(ms / 1000.0, tz=UTC)
    except (ValueError, TypeError, OSError):
        return None


def _normalize_side(s: str | None) -> str:
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short") else OrderSide.BUY


def _normalize_order_status(s: str | None) -> str:
    if not s:
        return OrderStatus.PENDING
    s = str(s).lower()
    if s in ("open", "live", "new", "partiallyfilled"):
        return OrderStatus.OPEN
    if s in ("partially_filled", "partiallyfilled"):
        return OrderStatus.PARTIALLY_FILLED
    if s in ("closed", "filled", "done"):
        return OrderStatus.FILLED
    if s in ("canceled", "cancelled", "cancel"):
        return OrderStatus.CANCELLED
    if s == "rejected":
        return OrderStatus.REJECTED
    if s == "expired":
        return OrderStatus.EXPIRED
    return OrderStatus.PENDING


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_aster_orderbook(
    raw: AsterOrderBook,
    venue: str = "aster",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert AsterOrderBook to CanonicalOrderBook."""
    ts = (
        datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)
        if timestamp_ms is not None
        else (datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC) if raw.timestamp else datetime.now(UTC))
    )
    bids = _to_levels(raw.bids or [])
    asks = _to_levels(raw.asks or [])
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or (raw.market_id or ""),
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_aster_trade(raw: AsterTrade, venue: str = "aster", symbol: str = "") -> CanonicalTrade:
    """Convert AsterTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC) if raw.time else datetime.now(UTC)
    side = "sell" if raw.isBuyerMaker else "buy"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=str(raw.id),
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.qty or 0)),
        side=side,
        buyer_maker=raw.isBuyerMaker,
        venue_trade_id=str(raw.id),
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_aster_order(raw: AsterOrder, venue: str = "aster") -> CanonicalOrder:
    """Convert AsterOrder to CanonicalOrder."""
    ts = datetime.now(UTC)
    symbol = raw.market_id or ""
    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=None,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=OrderType.LIMIT,
        quantity=_parse_decimal(raw.size or 0),
        price=_parse_decimal(raw.price) if raw.price else None,
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filled_size or 0),
        remaining_quantity=None,
        average_fill_price=None,
    )


# ---------------------------------------------------------------------------
# Derivative Ticker
# ---------------------------------------------------------------------------


def normalize_aster_derivative_ticker(
    mark: AsterMarkPrice,
    oi: AsterOpenInterest | None = None,
    funding: AsterFundingRate | None = None,
    instrument_key: str | None = None,
    venue: str = "aster",
) -> CanonicalDerivativeTicker:
    """Normalize Aster mark price (+ optional OI + funding) to CanonicalDerivativeTicker."""
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
# OHLCV
# ---------------------------------------------------------------------------


def normalize_aster_kline(raw: AsterKline, symbol: str = "", venue: str = "aster") -> CanonicalOhlcvBar:
    """Convert AsterKline to CanonicalOhlcvBar (Binance Futures-compatible format)."""
    ts = datetime.fromtimestamp(raw.openTime / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=_d(raw.open),
        high=_d(raw.high),
        low=_d(raw.low),
        close=_d(raw.close),
        volume=_d(raw.volume),
        quote_volume=None,
        count=None,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def normalize_aster_market(
    raw: AsterMarket,
    venue: str = "aster",
) -> CanonicalInstrument:
    """Normalize AsterMarket to CanonicalInstrument."""
    sym = raw.symbol or raw.market_id or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    return CanonicalInstrument(
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
) -> CanonicalInstrument:
    """Normalize AsterExchangeInfo (exchange-level info) to CanonicalInstrument."""
    ik = f"{venue.upper()}:EXCHANGE:INFO"
    return CanonicalInstrument(
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


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_aster_liquidation(
    raw: AsterLiquidationOrder,
    venue: str = "aster",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert AsterLiquidationOrder (@forceOrder WS event) to CanonicalLiquidation."""
    o: dict[str, object] = raw.o or {}
    sym = symbol or str(o.get("s") or "")
    ik = f"{venue.upper()}:PERP:{sym}"
    ts = datetime.fromtimestamp((raw.E or 0) / 1000.0, tz=UTC)
    side_raw = str(o.get("S") or "").upper()
    side = "buy" if side_raw == "BUY" else "sell"
    price = Decimal(str(o.get("ap") or o.get("p") or "0"))
    size = Decimal(str(o.get("q") or "0"))
    return CanonicalLiquidation(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price if price > Decimal("0") else Decimal("0"),
        size=size if size > Decimal("0") else Decimal("0"),
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_aster_ws_subscription(
    method: str,
    channel: str = "",
    venue: str = "aster",
) -> CanonicalWebSocketLifecycle:
    """Normalize Aster WS subscription request/response (Binance Futures-compatible)."""
    if method.upper() == "SUBSCRIBE":
        evt = WebSocketEvent.SUBSCRIBE
    elif method.upper() == "UNSUBSCRIBE":
        evt = WebSocketEvent.UNSUBSCRIBE
    else:
        evt = WebSocketEvent.SUBSCRIBE
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


def normalize_aster_ws_close(
    code: int,
    reason: str | None = None,
    venue: str = "aster",
) -> CanonicalWebSocketLifecycle:
    """Normalize Aster WebSocket close frame."""
    return normalize_ws_disconnect(venue=venue, code=code, reason=reason)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_a import normalize_aster_error  # noqa: E402

__all__ = [
    "normalize_aster_derivative_ticker",
    "normalize_aster_error",
    "normalize_aster_exchange_info",
    "normalize_aster_kline",
    "normalize_aster_liquidation",
    "normalize_aster_market",
    "normalize_aster_order",
    "normalize_aster_orderbook",
    "normalize_aster_ticker",
    "normalize_aster_trade",
    "normalize_aster_ws_close",
    "normalize_aster_ws_subscription",
]
