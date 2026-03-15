"""Per-source normalizers for gateio."""

from __future__ import annotations

import contextlib
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
    _ts_sec,
)
from .schemas import (
    GateioFill,
    GateioOrder,
    GateioOrderBook,
    GateioTicker,
    GateioTrade,
)

# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_gateio_trade(raw: GateioTrade, symbol: str = "", venue: str = "gateio") -> CanonicalTrade:
    """Convert GateioTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.create_time_ms:
        ts = _ts_ms(raw.create_time_ms)
    elif raw.create_time:
        ts = _ts_sec(raw.create_time)
    trade_id = str(raw.id) if raw.id else str(raw.trade_seq or "")
    sym = symbol or raw.currency_pair or "UNKNOWN"
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.amount),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.id) if raw.id else None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_gateio_orderbook(raw: GateioOrderBook, symbol: str = "", venue: str = "gateio") -> CanonicalOrderBook:
    """Convert GateioOrderBook to CanonicalOrderBook."""
    ts = _ts_ms(raw.current) if raw.current else datetime.now(UTC)
    bids = [(Decimal(row[0]), Decimal(row[1])) for row in raw.bids if len(row) >= 2]
    asks = [(Decimal(row[0]), Decimal(row[1])) for row in raw.asks if len(row) >= 2]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.id,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_gateio_order(raw: GateioOrder, venue: str = "gateio") -> CanonicalOrder:
    """Convert GateioOrder to CanonicalOrder."""
    ts = datetime.now(UTC)
    if raw.create_time_ms:
        ts = _ts_ms(raw.create_time_ms)
    elif raw.create_time:
        ts = _ts_sec(raw.create_time)
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=raw.text,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.currency_pair or "",
        side=_side(raw.side),
        order_type=_order_type(raw.type),
        quantity=_d(raw.amount),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.time_in_force),
        status=_status(raw.status),
        filled_quantity=_d(raw.filled_amount),
        remaining_quantity=_d(raw.left) if raw.left else None,
        average_fill_price=_d(raw.avg_deal_price) if raw.avg_deal_price else None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_gateio_fill(raw: GateioFill, venue: str = "gateio") -> CanonicalFill:
    """Convert GateioFill to CanonicalFill."""
    ts = datetime.now(UTC)
    if raw.create_time_ms:
        with contextlib.suppress(ValueError, TypeError):
            ts = _ts_ms(int(float(str(raw.create_time_ms))))
    elif raw.create_time:
        ts = _ts_sec(raw.create_time)
    is_maker: bool | None = None
    if raw.role:
        is_maker = raw.role.lower() == "maker"
    return CanonicalFill(
        fill_id=str(raw.id or ""),
        order_id=str(raw.order_id or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.currency_pair or "",
        side=_side(raw.side),
        price=_d(raw.price),
        quantity=_d(raw.amount),
        fee=_d(raw.fee) if raw.fee else None,
        fee_currency=raw.fee_currency,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_b import normalize_gateio_error  # noqa: E402

__all__ = [
    "normalize_gateio_error",
    "normalize_gateio_fill",
    "normalize_gateio_order",
    "normalize_gateio_orderbook",
    "normalize_gateio_ticker",
    "normalize_gateio_trade",
]
