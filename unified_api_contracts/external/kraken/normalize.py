"""Per-source normalizers for kraken."""

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
    _to_decimal,
    _ts_sec,
)
from .schemas import (
    KrakenFill,
    KrakenOrder,
    KrakenOrderBook,
    KrakenTicker,
    KrakenTrade,
)

# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_kraken_trade(raw: KrakenTrade, symbol: str = "", venue: str = "kraken") -> CanonicalTrade:
    """Convert KrakenTrade to CanonicalTrade."""
    ts = _ts_sec(raw.time)
    side = "buy" if str(raw.buy_sell) == "b" else "sell"
    trade_id = str(raw.trade_id) if raw.trade_id is not None else f"{raw.time}-{raw.price}"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.vol),
        side=side,
        buyer_maker=side == "buy",
        venue_trade_id=str(raw.trade_id) if raw.trade_id is not None else None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_kraken_orderbook(raw: KrakenOrderBook, symbol: str = "", venue: str = "kraken") -> CanonicalOrderBook:
    """Convert KrakenOrderBook to CanonicalOrderBook."""
    ts = datetime.now(UTC)
    bids = [(Decimal(row[0]), Decimal(row[1])) for row in raw.bids if len(row) >= 2]
    asks = [(Decimal(row[0]), Decimal(row[1])) for row in raw.asks if len(row) >= 2]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_kraken_order(raw: KrakenOrder, symbol: str = "", venue: str = "kraken") -> CanonicalOrder:
    """Convert KrakenOrder to CanonicalOrder."""
    ts = _ts_sec(raw.opentm)
    descr = raw.descr
    sym = symbol or (descr.pair if descr else None) or ""
    side_str = descr.type if descr else None
    order_type_str = descr.ordertype if descr else None
    price_str = descr.price if descr else None
    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=str(raw.userref) if raw.userref else None,
        timestamp=ts,
        venue=venue,
        instrument_id=sym,
        side=_side(side_str),
        order_type=_order_type(order_type_str),
        quantity=_d(raw.vol),
        price=_d(price_str) if price_str and price_str not in ("0", "0.00000", "") else None,
        status=_status(raw.status),
        filled_quantity=_d(raw.vol_exec),
        remaining_quantity=None,
        average_fill_price=_d(raw.price) if raw.price and raw.price not in ("0", "0.00000") else None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_kraken_fill(raw: KrakenFill, venue: str = "kraken") -> CanonicalFill:
    """Convert KrakenFill (user trade history) to CanonicalFill."""
    ts = _ts_sec(raw.time)
    fill_id = str(raw.trade_id) if raw.trade_id else f"{raw.ordertxid}-{raw.time}"
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.ordertxid or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.pair or "",
        side=_side(raw.type),
        price=_d(raw.price),
        quantity=_d(raw.vol),
        fee=_d(raw.fee) if raw.fee else None,
        fee_currency=None,
        is_maker=None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_a import normalize_kraken_error  # noqa: E402

__all__ = [
    "normalize_kraken_error",
    "normalize_kraken_fill",
    "normalize_kraken_order",
    "normalize_kraken_orderbook",
    "normalize_kraken_ticker",
    "normalize_kraken_trade",
]
