"""CeFi extended normalizers (part 2): MEXC, Huobi/HTX, Bitget, dYdX v4, OKX fill, Deribit fill, Upbit fill.

Split from cefi_extended.py to keep each file under the 900-line limit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...external.bitget.schemas import (
    BitgetFill,
    BitgetOrder,
    BitgetOrderBook,
    BitgetTrade,
)
from ...external.deribit.schemas import DeribitTrade as DeribitUserTrade
from ...external.dydx.schemas import (
    DydxFill,
    DydxOrder,
    DydxOrderBook,
    DydxTrade,
)
from ...external.huobi.schemas import (
    HuobiFill,
    HuobiOrder,
    HuobiOrderBook,
    HuobiTrade,
)
from ...external.mexc.schemas import (
    MexcFill,
    MexcOrder,
    MexcOrderBook,
    MexcTrade,
)
from ...external.okx.schemas import OKXOrderUpdateWS
from ...external.upbit.schemas import UpbitOrder as UpbitOrderSchema
from ..domain import CanonicalOrderBook, CanonicalTrade
from ..execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)

# ---------------------------------------------------------------------------
# Shared helpers (copied from cefi_extended.py to keep files self-contained)
# ---------------------------------------------------------------------------


def _d(val: str | float | int | Decimal | None) -> Decimal:
    """Parse a value to Decimal; returns Decimal('0') for None."""
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _ts_ms(ts: int | str | None) -> datetime:
    """Convert millisecond timestamp (int or str) to UTC datetime."""
    if ts is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(int(str(ts)) / 1000.0, tz=UTC)


def _iso(s: str | None) -> datetime:
    """Parse ISO 8601 timestamp string to UTC datetime."""
    if not s:
        return datetime.now(UTC)
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.now(UTC)


def _side(s: str | None) -> OrderSide:
    """Normalize side string to OrderSide."""
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short", "ask", "s") else OrderSide.BUY


def _order_type(t: str | None) -> OrderType:
    """Normalize order type string to OrderType."""
    if not t:
        return OrderType.LIMIT
    t_lower = str(t).lower().replace("-", "_").replace(" ", "_")
    if "market" in t_lower:
        return OrderType.MARKET
    if "stop_limit" in t_lower:
        return OrderType.STOP_LIMIT
    if "stop" in t_lower:
        return OrderType.STOP
    return OrderType.LIMIT


def _status(s: str | None) -> OrderStatus:
    """Normalize order status string to OrderStatus."""
    if not s:
        return OrderStatus.PENDING
    s_lower = str(s).lower().replace("-", "_").replace(" ", "_")
    if s_lower in ("open", "live", "new", "active", "submitted", "best_effort_opened"):
        return OrderStatus.OPEN
    if s_lower in (
        "partially_filled",
        "partial_filled",
        "partially fill",
        "partiallyfilled",
        "partial",
    ):
        return OrderStatus.PARTIALLY_FILLED
    if s_lower in ("closed", "filled", "done", "executed"):
        return OrderStatus.FILLED
    if s_lower in ("canceled", "cancelled", "cancel", "cancel_attempted", "best_effort_canceled"):
        return OrderStatus.CANCELLED
    if s_lower == "rejected":
        return OrderStatus.REJECTED
    if s_lower == "expired":
        return OrderStatus.EXPIRED
    return OrderStatus.PENDING


def _tif(t: str | None) -> TimeInForce:
    """Normalize time-in-force string to TimeInForce."""
    if not t:
        return TimeInForce.GTC
    upper = str(t).upper()
    if upper in ("IOC", "GTC", "FOK", "GTD", "POST_ONLY"):
        return TimeInForce(upper)
    return TimeInForce.GTC


# ---------------------------------------------------------------------------
# MEXC
# ---------------------------------------------------------------------------


def normalize_mexc_trade(raw: MexcTrade, symbol: str = "", venue: str = "mexc") -> CanonicalTrade:
    """Convert MexcTrade to CanonicalTrade.

    isBuyerMaker=True means the buyer is the market maker (sell taker aggressor).
    """
    ts = _ts_ms(raw.time)
    # isBuyerMaker=True -> seller is aggressor (sell trade); False -> buyer is aggressor (buy trade)
    side = "sell" if raw.isBuyerMaker else "buy"
    if raw.tradeType:
        side = "sell" if raw.tradeType.upper() == "ASK" else "buy"
    trade_id = str(raw.id) if raw.id else ""
    sym = symbol or "UNKNOWN"
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.qty),
        side=side,
        buyer_maker=raw.isBuyerMaker,
        venue_trade_id=trade_id or None,
    )


def normalize_mexc_orderbook(raw: MexcOrderBook, symbol: str = "", venue: str = "mexc") -> CanonicalOrderBook:
    """Convert MexcOrderBook to CanonicalOrderBook."""
    ts = _ts_ms(raw.timestamp) if raw.timestamp else datetime.now(UTC)
    bids = [(Decimal(row[0]), Decimal(row[1])) for row in raw.bids if len(row) >= 2]
    asks = [(Decimal(row[0]), Decimal(row[1])) for row in raw.asks if len(row) >= 2]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.lastUpdateId,
    )


def normalize_mexc_order(raw: MexcOrder, venue: str = "mexc") -> CanonicalOrder:
    """Convert MexcOrder to CanonicalOrder."""
    ts = _ts_ms(raw.time)
    return CanonicalOrder(
        order_id=str(raw.orderId or ""),
        client_order_id=raw.clientOrderId,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        order_type=_order_type(raw.type),
        quantity=_d(raw.origQty),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.timeInForce),
        status=_status(raw.status),
        filled_quantity=_d(raw.executedQty),
        remaining_quantity=None,
        average_fill_price=_d(raw.avgPrice) if raw.avgPrice else None,
    )


def normalize_mexc_fill(raw: MexcFill, venue: str = "mexc") -> CanonicalFill:
    """Convert MexcFill to CanonicalFill."""
    ts = _ts_ms(raw.time)
    side = "buy" if raw.isBuyer else "sell"
    return CanonicalFill(
        fill_id=str(raw.id or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(side),
        price=_d(raw.price),
        quantity=_d(raw.qty),
        fee=_d(raw.commission) if raw.commission else None,
        fee_currency=raw.commissionAsset,
        is_maker=raw.isMaker,
    )


# ---------------------------------------------------------------------------
# Huobi / HTX
# ---------------------------------------------------------------------------


def normalize_huobi_trade(raw: HuobiTrade, symbol: str = "", venue: str = "huobi") -> CanonicalTrade:
    """Convert HuobiTrade to CanonicalTrade."""
    ts = _ts_ms(raw.ts or raw.trade_time)
    trade_id = str(raw.tradeId) if raw.tradeId is not None else str(raw.id or "")
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.amount),
        side=(raw.direction or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=trade_id or None,
    )


def normalize_huobi_orderbook(raw: HuobiOrderBook, symbol: str = "", venue: str = "huobi") -> CanonicalOrderBook:
    """Convert HuobiOrderBook to CanonicalOrderBook."""
    ts = _ts_ms(raw.ts) if raw.ts else datetime.now(UTC)
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


def normalize_huobi_order(raw: HuobiOrder, venue: str = "huobi") -> CanonicalOrder:
    """Convert HuobiOrder to CanonicalOrder.

    type encodes side + order_type (e.g. "buy-limit", "sell-market").
    """
    ts = _ts_ms(raw.created_at)
    type_parts = str(raw.type or "buy-limit").split("-", 1)
    side_str = type_parts[0] if type_parts else "buy"
    order_type_str = type_parts[1] if len(type_parts) > 1 else "limit"
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=raw.client_order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(side_str),
        order_type=_order_type(order_type_str),
        quantity=_d(raw.amount),
        price=_d(raw.price) if raw.price else None,
        status=_status(raw.state),
        filled_quantity=_d(raw.field_amount),
        remaining_quantity=None,
        average_fill_price=None,
    )


def normalize_huobi_fill(raw: HuobiFill, venue: str = "huobi") -> CanonicalFill:
    """Convert HuobiFill to CanonicalFill."""
    ts = _ts_ms(raw.created_at)
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
        side=_side(side_str),
        price=_d(raw.price),
        quantity=_d(raw.filled_amount),
        fee=_d(raw.filled_fees) if raw.filled_fees else None,
        fee_currency=None,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Bitget
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
# dYdX
# ---------------------------------------------------------------------------


def normalize_dydx_trade(raw: DydxTrade, symbol: str = "", venue: str = "dydx") -> CanonicalTrade:
    """Convert DydxTrade to CanonicalTrade."""
    ts = _iso(raw.createdAt)
    trade_id = str(raw.id) if raw.id else ""
    sym = symbol or "UNKNOWN"  # DydxTrade.market is the path param, not on the object
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.size),
        side="buy" if (raw.side or "BUY").upper() == "BUY" else "sell",
        buyer_maker=None,
        venue_trade_id=trade_id or None,
    )


def normalize_dydx_orderbook(raw: DydxOrderBook, symbol: str = "", venue: str = "dydx") -> CanonicalOrderBook:
    """Convert DydxOrderBook to CanonicalOrderBook."""
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


def normalize_dydx_order(raw: DydxOrder, venue: str = "dydx") -> CanonicalOrder:
    """Convert DydxOrder to CanonicalOrder."""
    ts = _iso(raw.createdAt)
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=raw.clientId,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.market or "",
        side=_side(raw.side),
        order_type=_order_type(raw.type),
        quantity=_d(raw.size),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.timeInForce),
        status=_status(raw.status),
        filled_quantity=_d(raw.totalFilled),
        remaining_quantity=_d(raw.remainingSize) if raw.remainingSize else None,
        average_fill_price=None,
    )


def normalize_dydx_fill(raw: DydxFill, venue: str = "dydx") -> CanonicalFill:
    """Convert DydxFill to CanonicalFill."""
    ts = _iso(raw.createdAt)
    is_maker: bool | None = None
    if raw.liquidity:
        is_maker = raw.liquidity.upper() == "MAKER"
    return CanonicalFill(
        fill_id=str(raw.id or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.market or "",
        side=_side(raw.side),
        price=_d(raw.price),
        quantity=_d(raw.size),
        fee=_d(raw.fee) if raw.fee else None,
        fee_currency=None,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# OKX fill normalizer (supplement to orders_fills.py)
# OKX fills come via GET /api/v5/trade/fills — using OKXRealizedPnlResponse as proxy.
# ---------------------------------------------------------------------------


def normalize_okx_fill(raw: OKXOrderUpdateWS, venue: str = "okx") -> CanonicalFill | None:
    """Convert OKXOrderUpdateWS (fill event, state=filled/partially_filled) to CanonicalFill.

    Only yields a fill when fillSz is present (i.e. the WS push is a fill event).
    Returns None if this is not a fill event (no fillSz).
    """
    if not raw.fillSz or raw.fillSz == "0":
        return None
    ts = datetime.now(UTC)
    if raw.fillTime:
        ts = _ts_ms(raw.fillTime)
    elif raw.uTime:
        ts = _ts_ms(raw.uTime)
    is_maker: bool | None = None
    if raw.execType:
        is_maker = raw.execType.upper() == "M"
    fill_id = str(raw.tradeId) if raw.tradeId else f"{raw.ordId}-{raw.fillTime or 0}"
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.ordId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.instId or "",
        side=_side(raw.side),
        price=_d(raw.fillPx),
        quantity=_d(raw.fillSz),
        fee=None,
        fee_currency=None,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Deribit fill normalizer
# Deribit user trades (fills) are exposed via DeribitTrade with trade context.
# ---------------------------------------------------------------------------


def normalize_deribit_fill(
    raw: DeribitUserTrade,
    order_id: str = "",
    venue: str = "deribit",
) -> CanonicalFill:
    """Convert DeribitTrade (user trade/fill) to CanonicalFill.

    Deribit exposes user fills as trade records from private/get_user_trades_by_instrument.
    order_id must be injected by caller as DeribitTrade doesn't carry it inline.
    """
    ts = _ts_ms(raw.timestamp)
    trade_id = str(raw.trade_id) if raw.trade_id else str(raw.trade_seq or "")
    return CanonicalFill(
        fill_id=trade_id,
        order_id=order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.instrument_name or "",
        side=_side(raw.direction),
        price=_d(raw.price),
        quantity=_d(raw.amount),
        fee=None,
        fee_currency=None,
        is_maker=None,
    )


# ---------------------------------------------------------------------------
# Upbit fill normalizer
# Upbit is spot-only; fills are inferred from executed order volume.
# ---------------------------------------------------------------------------


def normalize_upbit_fill(raw: UpbitOrderSchema, venue: str = "upbit") -> CanonicalFill | None:
    """Convert UpbitOrder (state=done) to CanonicalFill.

    Upbit does not expose a separate fills endpoint for spot.
    This normalizer yields a synthetic fill from a fully-executed order.
    Returns None if executed_volume is zero (order not filled).
    """
    exec_vol = _d(raw.executed_volume)
    if exec_vol == Decimal("0"):
        return None
    ts = datetime.now(UTC)
    side = OrderSide.SELL if (raw.side or "").lower() == "ask" else OrderSide.BUY
    fill_id = str(raw.uuid or "") + "-fill"
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.uuid or ""),
        timestamp=ts,
        venue=venue,
        instrument_id="",
        side=side,
        price=_d(raw.price),
        quantity=exec_vol,
        fee=None,
        fee_currency=None,
        is_maker=None,
    )


__all__ = [
    # Bitget
    "normalize_bitget_fill",
    "normalize_bitget_order",
    "normalize_bitget_orderbook",
    "normalize_bitget_trade",
    # Deribit fill (supplement)
    "normalize_deribit_fill",
    # dYdX
    "normalize_dydx_fill",
    "normalize_dydx_order",
    "normalize_dydx_orderbook",
    "normalize_dydx_trade",
    # Huobi / HTX
    "normalize_huobi_fill",
    "normalize_huobi_order",
    "normalize_huobi_orderbook",
    "normalize_huobi_trade",
    # MEXC
    "normalize_mexc_fill",
    "normalize_mexc_order",
    "normalize_mexc_orderbook",
    "normalize_mexc_trade",
    # OKX fill (supplement)
    "normalize_okx_fill",
    # Upbit fill (supplement)
    "normalize_upbit_fill",
]
