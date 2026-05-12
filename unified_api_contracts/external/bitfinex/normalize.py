"""Per-source normalizers for bitfinex."""

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
    _ts_ms,
)
from .schemas import (
    BitfinexFill,
    BitfinexOrder,
    BitfinexOrderBook,
    BitfinexTicker,
    BitfinexTrade,
)

# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_bitfinex_ticker(
    raw: BitfinexTicker, instrument_key: str | None = None, venue: str = "bitfinex"
) -> CanonicalTicker:
    """Convert BitfinexTicker (v2 array-based) to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.LAST_PRICE) or Decimal("0"),
        bid_price=_to_decimal(raw.BID),
        ask_price=_to_decimal(raw.ASK),
        volume_24h=_to_decimal(raw.VOLUME),
        quote_volume_24h=None,
        price_change_24h=_to_decimal(raw.DAILY_CHANGE),
        price_change_percent_24h=_to_decimal(raw.DAILY_CHANGE_RELATIVE),
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_bitfinex_trade(raw: BitfinexTrade, symbol: str = "", venue: str = "bitfinex") -> CanonicalTrade:
    """Convert BitfinexTrade to CanonicalTrade.

    AMOUNT > 0 = buy, < 0 = sell.
    """
    ts = _ts_ms(raw.MTS) if raw.MTS else datetime.now(UTC)
    amount = raw.AMOUNT or 0.0
    side = "buy" if amount >= 0 else "sell"
    trade_id = str(raw.ID) if raw.ID is not None else ""
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.PRICE),
        quantity=_d(abs(amount)),
        side=side,
        buyer_maker=None,
        venue_trade_id=trade_id or None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_bitfinex_orderbook(
    raw: BitfinexOrderBook, symbol: str = "", venue: str = "bitfinex"
) -> CanonicalOrderBook:
    """Convert BitfinexOrderBook to CanonicalOrderBook."""
    ts = datetime.now(UTC)
    sym = symbol or "UNKNOWN"
    bids: list[tuple[Decimal, Decimal]] = [
        (Decimal(str(lvl.PRICE)), Decimal(str(abs(lvl.AMOUNT)))) for lvl in raw.bids if lvl.COUNT > 0
    ]
    asks: list[tuple[Decimal, Decimal]] = [
        (Decimal(str(lvl.PRICE)), Decimal(str(abs(lvl.AMOUNT)))) for lvl in raw.asks if lvl.COUNT > 0
    ]
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_bitfinex_order(raw: BitfinexOrder, symbol: str = "", venue: str = "bitfinex") -> CanonicalOrder:
    """Convert BitfinexOrder to CanonicalOrder.

    AMOUNT > 0 = buy, < 0 = sell.
    """
    ts = _ts_ms(raw.MTS_CREATE)
    amount = raw.AMOUNT or 0.0
    amount_orig = raw.AMOUNT_ORIG or 0.0
    side = "buy" if amount_orig >= 0 else "sell"
    filled = abs(amount_orig) - abs(amount)
    sym = symbol or (raw.SYMBOL.lstrip("t") if raw.SYMBOL else "") or ""
    return CanonicalOrder(
        order_id=str(raw.ID) if raw.ID is not None else "",
        client_order_id=str(raw.CID) if raw.CID is not None else None,
        timestamp=ts,
        venue=venue,
        instrument_id=sym,
        side=_side(side),
        order_type=_order_type(raw.TYPE),
        quantity=_d(abs(amount_orig)),
        price=_d(raw.PRICE) if raw.PRICE else None,
        status=_status(raw.STATUS),
        filled_quantity=_d(max(0.0, filled)),
        remaining_quantity=_d(abs(amount)),
        average_fill_price=_d(raw.PRICE_AVG) if raw.PRICE_AVG else None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_bitfinex_fill(raw: BitfinexFill, venue: str = "bitfinex") -> CanonicalFill:
    """Convert BitfinexFill to CanonicalFill.

    EXEC_AMOUNT > 0 = buy, < 0 = sell.
    MAKER: 1 = maker, -1 = taker.
    """
    ts = _ts_ms(raw.MTS_CREATE)
    exec_amount = raw.EXEC_AMOUNT or 0.0
    side = "buy" if exec_amount >= 0 else "sell"
    is_maker: bool | None = True if raw.MAKER == 1 else (False if raw.MAKER == -1 else None)
    sym = (raw.PAIR or "").lstrip("t")
    return CanonicalFill(
        fill_id=str(raw.ID) if raw.ID is not None else "",
        order_id=str(raw.ORDER_ID) if raw.ORDER_ID is not None else "",
        timestamp=ts,
        venue=venue,
        instrument_id=sym,
        side=_side(side),
        price=_d(raw.EXEC_PRICE),
        quantity=_d(abs(exec_amount)),
        fee=_d(abs(raw.FEE)) if raw.FEE else None,
        fee_currency=raw.FEE_CURRENCY,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_b import normalize_bitfinex_error

__all__ = [
    "normalize_bitfinex_error",
    "normalize_bitfinex_fill",
    "normalize_bitfinex_order",
    "normalize_bitfinex_orderbook",
    "normalize_bitfinex_ticker",
    "normalize_bitfinex_trade",
]
