"""Per-source normalizers for bitget."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalFee, CanonicalOrderBook, CanonicalTicker, CanonicalTrade, FeeType
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
    BitgetFeeDetail,
    BitgetFill,
    BitgetOrder,
    BitgetOrderBook,
    BitgetTicker,
    BitgetTrade,
)

# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_bitget_ticker(
    raw: BitgetTicker, instrument_key: str | None = None, venue: str = "bitget"
) -> CanonicalTicker:
    """Convert BitgetTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=datetime.now(UTC),
        last_price=_to_decimal(raw.close) or Decimal("0"),
        bid_price=_to_decimal(raw.bidPr),
        ask_price=_to_decimal(raw.askPr),
        volume_24h=_to_decimal(raw.baseVol),
        quote_volume_24h=_to_decimal(raw.quoteVol),
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_bitget_trade(raw: BitgetTrade, symbol: str = "", venue: str = "bitget") -> CanonicalTrade:
    """Convert BitgetTrade to CanonicalTrade."""
    ts = _ts_ms(raw.ts)
    sym = symbol or "UNKNOWN"
    trade_id = str(raw.tradeId) if raw.tradeId else ""
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.fillPrice),
        quantity=_d(raw.baseVolume),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=trade_id or None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_bitget_orderbook(raw: BitgetOrderBook, symbol: str = "", venue: str = "bitget") -> CanonicalOrderBook:
    """Convert BitgetOrderBook to CanonicalOrderBook."""
    ts = _ts_ms(raw.ts) if raw.ts else datetime.now(UTC)
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


def normalize_bitget_order(raw: BitgetOrder, venue: str = "bitget") -> CanonicalOrder:
    """Convert BitgetOrder to CanonicalOrder."""
    ts = _ts_ms(raw.cTime)
    status_map = {
        "live": "open",
        "partially_fill": "partially_filled",
        "filled": "filled",
        "cancelled": "cancelled",
        "expired": "expired",
        "none": "pending",
    }
    raw_status = (raw.status or "").lower()
    mapped_status = status_map.get(raw_status, raw_status)
    return CanonicalOrder(
        order_id=str(raw.orderId or ""),
        client_order_id=raw.clientOid,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        order_type=_order_type(raw.orderType),
        quantity=_d(raw.size),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.force),
        status=_status(mapped_status),
        filled_quantity=_d(raw.baseVolume),
        remaining_quantity=None,
        average_fill_price=_d(raw.priceAvg) if raw.priceAvg else None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_bitget_fill(raw: BitgetFill, venue: str = "bitget") -> CanonicalFill:
    """Convert BitgetFill to CanonicalFill."""
    ts = _ts_ms(raw.cTime)
    is_maker: bool | None = None
    if raw.tradeScope:
        is_maker = raw.tradeScope.lower() == "maker"
    fee_amt: Decimal | None = None
    fee_ccy: str | None = None
    if raw.feeDetail:
        if raw.feeDetail.totalDeductionFee:
            fee_amt = _d(raw.feeDetail.totalDeductionFee)
        fee_ccy = raw.feeDetail.feeCoin
    fill_id = str(raw.tradeId or "")
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        price=_d(raw.priceAvg),
        quantity=_d(raw.size),
        fee=fee_amt,
        fee_currency=fee_ccy,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_bitget_fee(
    raw: BitgetFeeDetail,
    fee_type: FeeType = FeeType.TAKER,
    venue: str = "bitget",
) -> CanonicalFee:
    """Normalize a BitgetFeeDetail to CanonicalFee."""
    amount = Decimal(raw.totalDeductionFee) if raw.totalDeductionFee is not None else Decimal("0")
    return CanonicalFee(
        amount=amount,
        currency=raw.feeCoin or "",
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

from ...normalize_utils.errors._normalize_a import normalize_bitget_error

__all__ = [
    "normalize_bitget_error",
    "normalize_bitget_fee",
    "normalize_bitget_fill",
    "normalize_bitget_order",
    "normalize_bitget_orderbook",
    "normalize_bitget_ticker",
    "normalize_bitget_trade",
]
