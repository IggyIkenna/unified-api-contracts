"""Per-source normalizers for bitstamp."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalOrderBook, CanonicalTicker, CanonicalTrade
from ...canonical.domain.execution import CanonicalFill, CanonicalOrder, OrderSide, OrderType
from ...normalize_utils._helpers import (
    _d,
    _iso,
    _side,
    _status,
    _to_decimal,
    _ts_sec,
)
from .schemas import (
    BitstampFill,
    BitstampOrder,
    BitstampOrderBook,
    BitstampTicker,
    BitstampTrade,
)

# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_bitstamp_trade(raw: BitstampTrade, symbol: str = "", venue: str = "bitstamp") -> CanonicalTrade:
    """Convert BitstampTrade to CanonicalTrade.

    type: 0=buy, 1=sell.
    """
    ts = datetime.now(UTC)
    if raw.microtimestamp:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromtimestamp(int(raw.microtimestamp) / 1e6, tz=UTC)
    elif raw.timestamp:
        ts = _ts_sec(raw.timestamp)
    side = "buy" if raw.type == 0 else "sell"
    trade_id = str(raw.id) if raw.id is not None else ""
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price_str or raw.price),
        quantity=_d(raw.amount_str or raw.amount),
        side=side,
        buyer_maker=side == "buy",
        venue_trade_id=trade_id or None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_bitstamp_orderbook(
    raw: BitstampOrderBook, symbol: str = "", venue: str = "bitstamp"
) -> CanonicalOrderBook:
    """Convert BitstampOrderBook to CanonicalOrderBook."""
    ts = datetime.now(UTC)
    if raw.microtimestamp:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromtimestamp(int(raw.microtimestamp) / 1e6, tz=UTC)
    elif raw.timestamp:
        ts = _ts_sec(raw.timestamp)
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


def normalize_bitstamp_order(raw: BitstampOrder, symbol: str = "", venue: str = "bitstamp") -> CanonicalOrder:
    """Convert BitstampOrder to CanonicalOrder.

    type: "0"=buy, "1"=sell.
    """
    ts = _iso(raw.datetime)
    side = "buy" if str(raw.type or "0") == "0" else "sell"
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=raw.client_order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol or raw.currency_pair or "",
        side=_side(side),
        order_type=OrderType.LIMIT,  # Bitstamp orders are limit-only in REST
        quantity=_d(raw.amount),
        price=_d(raw.price) if raw.price else None,
        status=_status(raw.status),
        filled_quantity=Decimal("0"),
        remaining_quantity=_d(raw.amount_remaining) if raw.amount_remaining else None,
        average_fill_price=None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_bitstamp_fill(raw: BitstampFill, symbol: str = "", venue: str = "bitstamp") -> CanonicalFill:
    """Convert BitstampFill (user transaction type=2) to CanonicalFill.

    Price is typically stored as the pair rate key (e.g. btc_usd).
    Symbol must be passed in since BitstampFill doesn't carry it directly.
    """
    ts = _iso(raw.datetime)
    # Amount and price: try to extract from generic extra dict or known fields
    price_val: Decimal = _d(raw.btc_usd)
    qty_val: Decimal = _d(raw.btc)
    if raw.extra:
        # Look for {base}_{quote} rate key
        for key, val in raw.extra.items():
            if "_" in key:
                price_val = _d(val)
            elif price_val == Decimal("0"):
                qty_val = _d(val)
    return CanonicalFill(
        fill_id=str(raw.id or ""),
        order_id=str(raw.order_id or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=OrderSide.BUY,  # Bitstamp fill doesn't clearly carry side; default buy
        price=price_val,
        quantity=qty_val,
        fee=_d(raw.fee) if raw.fee else None,
        fee_currency=None,
        is_maker=None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_b import normalize_bitstamp_error  # noqa: E402

__all__ = [
    "normalize_bitstamp_error",
    "normalize_bitstamp_fill",
    "normalize_bitstamp_order",
    "normalize_bitstamp_orderbook",
    "normalize_bitstamp_ticker",
    "normalize_bitstamp_trade",
]
