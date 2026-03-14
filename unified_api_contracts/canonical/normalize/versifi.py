"""VersiFi order and fill normalizers.

Converts VersiFi REST API responses to CanonicalOrder and CanonicalFill.

VersiFi algo order types and their canonical mapping:
- TWAP (Time-Weighted Average Price) -> OrderType.TWAP
- VWAP (Volume-Weighted Average Price) -> OrderType.VWAP
- IS (Implementation Shortfall) -> OrderType.LIMIT (no direct canonical equivalent)
- MARKET -> OrderType.MARKET
- LIMIT -> OrderType.LIMIT
- STOP_LOSS | STOP_LOSS_LIMIT -> OrderType.STOP
- TAKE_PROFIT | TAKE_PROFIT_LIMIT -> OrderType.STOP_LIMIT

Status mapping from VersiFi to canonical:
- NEW, OPEN, ACTIVE, PENDING_NEW, ACK -> OrderStatus.OPEN
- PARTIALLY_FILLED -> OrderStatus.PARTIALLY_FILLED
- FILLED, DONE, CLOSED -> OrderStatus.FILLED
- CANCELLED, CANCELED -> OrderStatus.CANCELLED
- REJECTED -> OrderStatus.REJECTED

Timestamp notes:
- order list timestamp: Unix epoch seconds
- start_time (algo): UTC epoch microseconds
- WebSocket fill timestamps: nested in child_order.trades

Fill extraction: VersiFi fills are nested in child_order.trades within the order
sub-object. Use normalize_versifi_trade_to_fill() for each trade record.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...external.versifi.schemas import (
    VersiFiAlgoOrder,
    VersiFiBasicOrder,
    VersiFiChildOrderTrade,
    VersiFiOrderDetail,
    VersiFiOrderListItem,
    VersiFiOrderResponse,
    VersiFiRejectReason,
    parse_reject_reason,
)
from ..execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _parse_versifi_side(side: str | None) -> OrderSide:
    return OrderSide.SELL if (side or "").upper() == "SELL" else OrderSide.BUY


def _parse_versifi_order_type(ot: str | None) -> OrderType:
    """Map VersiFi order_type string to canonical OrderType.

    TWAP and VWAP map to their dedicated canonical types.
    IS (Implementation Shortfall) has no canonical equivalent; maps to LIMIT.
    STOP_LOSS / STOP_LOSS_LIMIT map to STOP.
    TAKE_PROFIT / TAKE_PROFIT_LIMIT map to STOP_LIMIT.
    """
    if not ot:
        return OrderType.LIMIT
    ot_upper = ot.upper()
    if ot_upper == "MARKET":
        return OrderType.MARKET
    if ot_upper == "LIMIT":
        return OrderType.LIMIT
    if ot_upper == "TWAP":
        return OrderType.TWAP
    if ot_upper == "VWAP":
        return OrderType.VWAP
    if ot_upper in ("STOP_LOSS", "STOP_LOSS_LIMIT"):
        return OrderType.STOP
    if ot_upper in ("TAKE_PROFIT", "TAKE_PROFIT_LIMIT"):
        return OrderType.STOP_LIMIT
    # IS (Implementation Shortfall) -> LIMIT as closest canonical representation
    return OrderType.LIMIT


def _parse_versifi_status(status: str | None) -> OrderStatus:
    """Map VersiFi status string to canonical OrderStatus."""
    if not status:
        return OrderStatus.PENDING
    s = status.upper()
    if s in ("OPEN", "ACTIVE", "PENDING_NEW", "NEW", "ACK"):
        return OrderStatus.OPEN
    if s == "PARTIALLY_FILLED":
        return OrderStatus.PARTIALLY_FILLED
    if s in ("FILLED", "DONE", "CLOSED"):
        return OrderStatus.FILLED
    if s in ("CANCELLED", "CANCELED"):
        return OrderStatus.CANCELLED
    if s == "REJECTED":
        return OrderStatus.REJECTED
    if s == "EXPIRED":
        return OrderStatus.EXPIRED
    return OrderStatus.PENDING


def _parse_versifi_tif(tif: str | None) -> TimeInForce:
    """Map VersiFi tif string to canonical TimeInForce.

    VersiFi supports: FOK, GTC, GTD, IOC, GTX, POST_ON.
    GTX and POST_ON map to POST_ONLY (post-only maker orders).
    """
    if not tif:
        return TimeInForce.GTC
    t = tif.upper()
    if t == "FOK":
        return TimeInForce.FOK
    if t == "IOC":
        return TimeInForce.IOC
    if t == "GTD":
        return TimeInForce.GTD
    if t in ("GTX", "POST_ON"):
        return TimeInForce.POST_ONLY
    return TimeInForce.GTC


def resolve_versifi_reject_reason(raw: str | None) -> str | None:
    """Parse VersiFi reject_reason string into a typed exchange error, then return msg.

    Detects BinanceError (integer code) vs OKXError (string code) automatically.
    Returns the exchange error message string, or the raw value if not JSON.
    """
    if not raw:
        return None
    parsed: VersiFiRejectReason | None = parse_reject_reason(raw)
    if parsed is not None:
        return parsed.msg or raw
    return raw  # not JSON — pass through as-is


def _ts_epoch_seconds_to_datetime(ts: int | None) -> datetime:
    """Convert Unix epoch seconds to UTC datetime."""
    if ts is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(float(ts), tz=UTC)


def _extract_basic_order_fields(
    order: VersiFiBasicOrder,
) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    """Extract (symbol, side, order_type, qty, price, filled_qty) from VersiFiBasicOrder."""
    return (
        order.symbol or "",
        order.side,
        order.order_type,
        order.quantity,
        order.price,
        order.filled_quantity,
    )


def _extract_algo_order_fields(
    order: VersiFiAlgoOrder,
) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    """Extract (symbol, side, order_type, qty, price, filled_qty) from VersiFiAlgoOrder."""
    return (
        order.symbol or "",
        order.side,
        order.order_type,
        order.quantity,
        None,  # Algo orders have no limit price
        order.filled_quantity,
    )


def normalize_versifi_order_list_item(raw: VersiFiOrderListItem, venue: str = "versifi") -> CanonicalOrder:
    """Convert VersiFiOrderListItem (GET /api/v2/orders list) to CanonicalOrder.

    Uses basic_order if present, else algo_order, else pair_order for field extraction.
    timestamp is Unix epoch seconds in the list response.
    """
    ts = _ts_epoch_seconds_to_datetime(raw.timestamp)

    symbol: str = ""
    side_str: str | None = None
    order_type_str: str | None = raw.request_order_type
    qty_str: str | None = None
    price_str: str | None = None
    filled_qty_str: str | None = None
    avg_price_str: str | None = None

    if raw.basic_order is not None:
        symbol, side_str, ot, qty_str, price_str, filled_qty_str = _extract_basic_order_fields(raw.basic_order)
        order_type_str = ot or order_type_str
        avg_price_str = raw.basic_order.average_price
    elif raw.algo_order is not None:
        symbol, side_str, ot, qty_str, price_str, filled_qty_str = _extract_algo_order_fields(raw.algo_order)
        order_type_str = ot or order_type_str
        avg_price_str = raw.algo_order.average_price
    elif raw.pair_order is not None and raw.pair_order.lead_leg is not None:
        symbol = raw.pair_order.lead_leg.symbol or ""

    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=str(raw.client_order_id) if raw.client_order_id is not None else None,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_parse_versifi_side(side_str),
        order_type=_parse_versifi_order_type(order_type_str),
        quantity=_parse_decimal(qty_str),
        price=_parse_decimal(price_str) if price_str is not None else None,
        status=_parse_versifi_status(raw.status),
        filled_quantity=_parse_decimal(filled_qty_str),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(avg_price_str) if avg_price_str is not None else None,
    )


def normalize_versifi_order_detail(raw: VersiFiOrderDetail, venue: str = "versifi") -> CanonicalOrder:
    """Convert VersiFiOrderDetail (GET /v2/orders/{id}) to CanonicalOrder.

    Includes filled_quantity and average_fill_price from the nested order sub-object
    when available. timestamp is Unix epoch seconds.
    """
    ts = _ts_epoch_seconds_to_datetime(raw.timestamp)

    symbol: str = ""
    side_str: str | None = None
    order_type_str: str | None = raw.request_order_type
    qty_str: str | None = None
    price_str: str | None = None
    filled_qty_str: str | None = None
    avg_price_str: str | None = None
    tif_str: str | None = None

    if raw.basic_order is not None:
        symbol, side_str, ot, qty_str, price_str, filled_qty_str = _extract_basic_order_fields(raw.basic_order)
        order_type_str = ot or order_type_str
        avg_price_str = raw.basic_order.average_price
        tif_str = raw.basic_order.tif
    elif raw.algo_order is not None:
        symbol, side_str, ot, qty_str, price_str, filled_qty_str = _extract_algo_order_fields(raw.algo_order)
        order_type_str = ot or order_type_str
        avg_price_str = raw.algo_order.average_price
        tif_str = raw.algo_order.tif
    elif raw.pair_order is not None and raw.pair_order.lead_leg is not None:
        symbol = raw.pair_order.lead_leg.symbol or ""

    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=str(raw.client_order_id) if raw.client_order_id is not None else None,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_parse_versifi_side(side_str),
        order_type=_parse_versifi_order_type(order_type_str),
        quantity=_parse_decimal(qty_str),
        price=_parse_decimal(price_str) if price_str is not None else None,
        time_in_force=_parse_versifi_tif(tif_str),
        status=_parse_versifi_status(raw.status),
        filled_quantity=_parse_decimal(filled_qty_str),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(avg_price_str) if avg_price_str is not None else None,
    )


def normalize_versifi_order_response(
    raw: VersiFiOrderResponse,
    side: str = "BUY",
    symbol: str = "",
    order_type: str = "LIMIT",
    quantity: str = "0",
    venue: str = "versifi",
) -> CanonicalOrder:
    """Convert VersiFiOrderResponse (POST /v2/orders/basic/ creation ack) to CanonicalOrder.

    The creation response only contains order_id, client_order_id, and status.
    Callers must supply side, symbol, order_type, and quantity from the original request
    to produce a complete canonical record.
    Full order state is delivered via WebSocket execution_report after exchange acknowledgement.
    """
    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=str(raw.client_order_id) if raw.client_order_id is not None else None,
        timestamp=datetime.now(UTC),
        venue=venue,
        instrument_id=symbol,
        side=_parse_versifi_side(side),
        order_type=_parse_versifi_order_type(order_type),
        quantity=_parse_decimal(quantity),
        price=None,
        status=_parse_versifi_status(raw.status),
        filled_quantity=Decimal("0"),
        remaining_quantity=None,
        average_fill_price=None,
    )


def normalize_versifi_trade_to_fill(
    raw: VersiFiChildOrderTrade,
    order_id: str,
    symbol: str,
    side: str = "BUY",
    venue: str = "versifi",
) -> CanonicalFill:
    """Convert a VersiFiChildOrderTrade (nested trade record) to CanonicalFill.

    Trade records appear in child_order.trades within the order detail response
    and in WebSocket execution_report messages (with extra fill fields:
    average_price, cummulative_filled_quantity, executed_price, executed_quantity).

    Uses executed_price if present (WebSocket fill), else falls back to price.
    Uses executed_quantity if present, else falls back to quantity.
    fee is a flat string amount (no currency provided by VersiFi API).
    """
    price_str = raw.executed_price or raw.price
    qty_str = raw.executed_quantity or raw.quantity
    derived_symbol = raw.symbol or symbol
    derived_side = raw.side or side
    fill_id = str(raw.trade_id or f"{order_id}-{raw.child_order_id or 0}")

    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.order_id or order_id),
        timestamp=datetime.now(UTC),
        venue=venue,
        instrument_id=derived_symbol,
        side=_parse_versifi_side(derived_side),
        price=_parse_decimal(price_str),
        quantity=_parse_decimal(qty_str),
        fee=_parse_decimal(raw.fee) if raw.fee is not None else None,
        fee_currency=None,  # VersiFi API does not expose fee currency in trade records
        is_maker=None,
    )


__all__ = [
    "normalize_versifi_order_detail",
    "normalize_versifi_order_list_item",
    "normalize_versifi_order_response",
    "normalize_versifi_trade_to_fill",
]
