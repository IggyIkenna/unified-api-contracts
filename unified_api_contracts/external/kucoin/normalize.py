"""Per-source normalizers for kucoin."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalOrderBook, CanonicalTicker, CanonicalTrade
from ...canonical.domain.execution import CanonicalFill, CanonicalOrder
from ...normalize_utils._helpers import (
    _d,
    _order_type,
    _side,
    _status,
    _tif,
    _to_decimal,
    _ts_ms,
)
from .schemas import (
    KucoinFill,
    KucoinOrder,
    KucoinOrderBook,
    KucoinTicker,
    KucoinTrade,
)

# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_kucoin_trade(raw: KucoinTrade, symbol: str = "", venue: str = "kucoin") -> CanonicalTrade:
    """Convert KucoinTrade to CanonicalTrade."""
    # KuCoin WS time is nanoseconds as a string; REST is ms int
    ts = datetime.now(UTC)
    if raw.time is not None:
        time_val = int(str(raw.time))
        if time_val > 1_000_000_000_000_000:  # nanoseconds (16+ digits)
            ts = datetime.fromtimestamp(time_val / 1e9, tz=UTC)
        else:  # milliseconds
            ts = datetime.fromtimestamp(time_val / 1000.0, tz=UTC)
    trade_id = str(raw.tradeId) if raw.tradeId else str(raw.sequence or "")
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.size),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.tradeId) if raw.tradeId else None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_kucoin_orderbook(raw: KucoinOrderBook, symbol: str = "", venue: str = "kucoin") -> CanonicalOrderBook:
    """Convert KucoinOrderBook to CanonicalOrderBook."""
    ts = datetime.now(UTC)
    if raw.time is not None:
        ts = datetime.fromtimestamp(int(str(raw.time)) / 1000.0, tz=UTC)
    seq = int(raw.sequence) if raw.sequence else None
    bids = [(Decimal(row[0]), Decimal(row[1])) for row in raw.bids if len(row) >= 2]
    asks = [(Decimal(row[0]), Decimal(row[1])) for row in raw.asks if len(row) >= 2]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=seq,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_kucoin_order(raw: KucoinOrder, venue: str = "kucoin") -> CanonicalOrder:
    """Convert KucoinOrder to CanonicalOrder."""
    ts = _ts_ms(raw.createdAt)
    status = _status("filled" if not raw.isActive else "open")
    if raw.status:
        status = _status(raw.status)
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=None,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        order_type=_order_type(raw.type),
        quantity=_d(raw.size),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.timeInForce),
        status=status,
        filled_quantity=_d(raw.dealSize),
        remaining_quantity=None,
        average_fill_price=None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_kucoin_fill(raw: KucoinFill, venue: str = "kucoin") -> CanonicalFill:
    """Convert KucoinFill to CanonicalFill."""
    ts = _ts_ms(raw.createdAt)
    is_maker: bool | None = None
    if raw.liquidity:
        is_maker = raw.liquidity.lower() == "maker"
    return CanonicalFill(
        fill_id=str(raw.tradeId or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        price=_d(raw.price),
        quantity=_d(raw.size),
        fee=_d(raw.fee) if raw.fee else None,
        fee_currency=raw.feeCurrency,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_a import normalize_kucoin_error

__all__ = [
    "normalize_kucoin_error",
    "normalize_kucoin_fill",
    "normalize_kucoin_order",
    "normalize_kucoin_orderbook",
    "normalize_kucoin_ticker",
    "normalize_kucoin_trade",
]
