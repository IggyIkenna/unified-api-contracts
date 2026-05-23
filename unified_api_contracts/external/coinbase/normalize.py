"""Coinbase normalizers — all normalize_coinbase_* functions.

Extracted from normalize_utils/ modules.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import (
    CanonicalFee,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    FeeType,
    WebSocketEvent,
)
from ...canonical.domain.execution import CanonicalFill, CanonicalOrder, OrderSide, OrderStatus, OrderType, TimeInForce
from ...normalize_utils._helpers import d as _d
from ...normalize_utils._helpers import to_decimal as _to_decimal
from ...normalize_utils._helpers import to_levels as _to_levels
from ..coinbase.schemas import (
    CoinbaseCandle,
    CoinbaseFill,
    CoinbaseOrder,
    CoinbaseOrderBook,
    CoinbaseTicker,
    CoinbaseTrade,
)

_logger = logging.getLogger(__name__)


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _normalize_side(s: str | None) -> OrderSide:
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short") else OrderSide.BUY


def _normalize_order_status(s: str | None) -> OrderStatus:
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


def _normalize_tif(tif: str | None) -> TimeInForce:
    if not tif:
        return TimeInForce.GTC
    t = str(tif).upper()
    if t in ("IOC", "GTC", "FOK", "GTD", "POST_ONLY"):
        return TimeInForce(t)
    return TimeInForce.GTC


def _parse_iso_ts(s: str | None) -> datetime:
    if not s:
        return datetime.now(UTC)
    try:
        ts = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_coinbase_orderbook(
    raw: CoinbaseOrderBook,
    venue: str = "coinbase",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert CoinbaseOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC) if timestamp_ms is not None else datetime.now(UTC)
    bids = _to_levels(raw.bids)
    asks = _to_levels(raw.asks)
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.sequence,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_coinbase_trade(raw: CoinbaseTrade, venue: str = "coinbase", symbol: str = "") -> CanonicalTrade:
    """Convert CoinbaseTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.time:
        try:
            ts = datetime.fromisoformat(raw.time.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            _logger.debug("Coinbase trade time %r is not a valid ISO datetime; using current UTC time", raw.time)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=str(raw.trade_id),
        timestamp=ts,
        price=raw.price,
        quantity=raw.size,
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.trade_id),
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_coinbase_order(raw: CoinbaseOrder, venue: str = "coinbase") -> CanonicalOrder:
    """Convert CoinbaseOrder to CanonicalOrder."""
    ts = _parse_iso_ts(raw.created_time)
    symbol = raw.product_id or ""
    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=raw.client_order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=OrderType.LIMIT if (raw.time_in_force or "").upper() != "IOC" else OrderType.MARKET,
        quantity=_parse_decimal(raw.filled_size or 0),
        price=None,
        time_in_force=_normalize_tif(raw.time_in_force),
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filled_size or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.average_filled_price) if raw.average_filled_price else None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_coinbase_fill(raw: CoinbaseFill, venue: str = "coinbase") -> CanonicalFill:
    """Convert CoinbaseFill to CanonicalFill."""
    ts = _parse_iso_ts(raw.created_time)
    symbol = raw.product_id or ""
    fill_id = str(raw.trade_id or raw.order_id or "unknown")
    liq = (raw.liquidity or "").lower()
    is_maker: bool | None = True if liq == "maker" else (False if liq == "taker" else None)
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.order_id or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.price or 0),
        quantity=_parse_decimal(raw.size or 0),
        fee=_parse_decimal(raw.fee) if raw.fee else None,
        fee_currency=None,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_coinbase_candle(raw: CoinbaseCandle, symbol: str = "", venue: str = "coinbase") -> CanonicalOhlcvBar:
    """Convert CoinbaseCandle to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp(float(raw.timestamp), tz=UTC)
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
# Fee
# ---------------------------------------------------------------------------


def normalize_coinbase_fee(
    fee: Decimal,
    currency: str = "USD",
    venue: str = "coinbase",
) -> CanonicalFee:
    """Normalize a Coinbase fill fee to CanonicalFee."""
    return CanonicalFee(
        amount=fee,
        currency=currency,
        asset=None,
        fee_type=FeeType.TAKER,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Market State
# ---------------------------------------------------------------------------


# normalize_coinbase_market_state is imported from normalize_utils.market_state


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_coinbase_ws_subscription(
    type_str: str,
    channel: str = "",
    venue: str = "coinbase",
) -> CanonicalWebSocketLifecycle:
    """Normalize Coinbase Advanced Trade WS subscription response."""
    if type_str == "subscriptions":
        evt = WebSocketEvent.SUBSCRIBE
    elif type_str == "error":
        evt = WebSocketEvent.ERROR
    else:
        evt = WebSocketEvent.SUBSCRIBE
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


# ---------------------------------------------------------------------------
# Rate Limits
# ---------------------------------------------------------------------------

from ...normalize_utils.rate_limits import extract_coinbase_rate_limit

__all__ = [
    "extract_coinbase_rate_limit",
    "normalize_coinbase_candle",
    "normalize_coinbase_fee",
    "normalize_coinbase_fill",
    "normalize_coinbase_order",
    "normalize_coinbase_orderbook",
    "normalize_coinbase_ticker",
    "normalize_coinbase_trade",
    "normalize_coinbase_ws_subscription",
]
