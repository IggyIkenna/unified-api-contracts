"""Per-source normalizers for huobi."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalOrderBook, CanonicalTicker, CanonicalTrade
from ...canonical.domain.execution import CanonicalFill, CanonicalOrder
from ...normalize_utils._helpers import (
    d,
    order_type,
    side,
    status,
    to_decimal,
    ts_ms,
    ts_ms_to_datetime,
)
from .schemas import (
    HuobiFill,
    HuobiOrder,
    HuobiOrderBook,
    HuobiTicker,
    HuobiTrade,
)

# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_huobi_ticker(
    raw: HuobiTicker, instrument_key: str | None = None, venue: str = "huobi"
) -> CanonicalTicker:
    """Convert HuobiTicker (GET /market/detail/merged) to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:"
    ts = ts_ms_to_datetime(raw.ts)
    bid_price = to_decimal(raw.bid[0]) if raw.bid else None
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=to_decimal(raw.close) or Decimal("0"),
        bid_price=bid_price,
        ask_price=None,
        volume_24h=to_decimal(raw.amount),
        quote_volume_24h=to_decimal(raw.vol),
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_huobi_trade(raw: HuobiTrade, symbol: str = "", venue: str = "huobi") -> CanonicalTrade:
    """Convert HuobiTrade to CanonicalTrade."""
    ts = ts_ms(raw.ts or raw.trade_time)
    trade_id = str(raw.tradeId) if raw.tradeId is not None else str(raw.id or "")
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=trade_id,
        timestamp=ts,
        price=d(raw.price),
        quantity=d(raw.amount),
        side=(raw.direction or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=trade_id or None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_huobi_orderbook(raw: HuobiOrderBook, symbol: str = "", venue: str = "huobi") -> CanonicalOrderBook:
    """Convert HuobiOrderBook to CanonicalOrderBook."""
    ts = ts_ms(raw.ts) if raw.ts else datetime.now(UTC)
    bids: list[tuple[Decimal, Decimal]] = [
        (Decimal(str(row[0])), Decimal(str(row[1]))) for row in raw.bids if len(row) >= 2
    ]
    asks: list[tuple[Decimal, Decimal]] = [
        (Decimal(str(row[0])), Decimal(str(row[1]))) for row in raw.asks if len(row) >= 2
    ]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.version,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_huobi_order(raw: HuobiOrder, venue: str = "huobi") -> CanonicalOrder:
    """Convert HuobiOrder to CanonicalOrder.

    type encodes side + order_type (e.g. "buy-limit", "sell-market").
    """
    ts = ts_ms(raw.created_at)
    type_parts = str(raw.type or "buy-limit").split("-", 1)
    side_str = type_parts[0] if type_parts else "buy"
    order_type_str = type_parts[1] if len(type_parts) > 1 else "limit"
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=raw.client_order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=side(side_str),
        order_type=order_type(order_type_str),
        quantity=d(raw.amount),
        price=d(raw.price) if raw.price else None,
        status=status(raw.state),
        filled_quantity=d(raw.field_amount),
        remaining_quantity=None,
        average_fill_price=None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_huobi_fill(raw: HuobiFill, venue: str = "huobi") -> CanonicalFill:
    """Convert HuobiFill to CanonicalFill."""
    ts = ts_ms(raw.created_at)
    type_parts = str(raw.type or "buy-limit").split("-", 1)
    side_str = type_parts[0] if type_parts else "buy"
    is_maker: bool | None = None
    if raw.role:
        is_maker = raw.role.lower() == "maker"
    fill_id = str(raw.id or raw.match_id or "")
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.order_id or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=side(side_str),
        price=d(raw.price),
        quantity=d(raw.filled_amount),
        fee=d(raw.filled_fees) if raw.filled_fees else None,
        fee_currency=None,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_a import normalize_huobi_error

__all__ = [
    "normalize_huobi_error",
    "normalize_huobi_fill",
    "normalize_huobi_order",
    "normalize_huobi_orderbook",
    "normalize_huobi_ticker",
    "normalize_huobi_trade",
]
