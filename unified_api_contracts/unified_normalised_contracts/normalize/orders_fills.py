"""Order and fill normalizers: raw venue responses -> CanonicalOrder, CanonicalFill."""

from datetime import UTC, datetime
from decimal import Decimal

from ...unified_api_contracts_external.binance import BinanceMyTrades, BinanceOrder
from ...unified_api_contracts_external.bybit.schemas import BybitExecutionWS, BybitOrder
from ...unified_api_contracts_external.ccxt.schemas import CcxtOrder, CcxtTrade
from ...unified_api_contracts_external.deribit.schemas import DeribitOrder
from ...unified_api_contracts_external.okx.schemas import OKXOrder
from ..execution import CanonicalFill, CanonicalOrder, OrderSide, OrderStatus, OrderType, TimeInForce


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _ts_ms_to_datetime(ts: int | None) -> datetime:
    if ts is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(ts / 1000.0, tz=UTC)


def _normalize_side(s: str | None) -> OrderSide:
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short") else OrderSide.BUY


def _normalize_order_type(t: str | None) -> OrderType:
    if not t:
        return OrderType.LIMIT
    t = str(t).lower()
    if t in ("market", "m"):
        return OrderType.MARKET
    if t in ("limit", "l"):
        return OrderType.LIMIT
    if t in ("stop", "stop_market"):
        return OrderType.STOP
    if t in ("stop_limit", "stop_limit_order"):
        return OrderType.STOP_LIMIT
    return OrderType.LIMIT


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


def _extract_ccxt_fee(trade: CcxtTrade) -> tuple[Decimal | None, str | None]:
    fee = trade.fee
    if fee is None:
        return None, None
    if isinstance(fee, dict):
        cost = fee.get("cost")
        currency = fee.get("currency")
        cost_val: str | float | Decimal | None = (
            float(cost) if isinstance(cost, (int, float)) else
            str(cost) if isinstance(cost, str) else
            cost if isinstance(cost, Decimal) else None
        )
        return (
            _parse_decimal(cost_val) if cost_val is not None else None,
            str(currency) if currency is not None else None,
        )
    if hasattr(fee, "cost") and hasattr(fee, "currency"):
        c = getattr(fee, "cost", None)
        curr = getattr(fee, "currency", None)
        c_val: str | float | Decimal | None = (
            float(c) if isinstance(c, (int, float)) else
            str(c) if isinstance(c, str) else
            c if isinstance(c, Decimal) else None
        )
        return (_parse_decimal(c_val) if c_val is not None else None, curr)
    return None, None


def normalize_ccxt_order(raw: CcxtOrder, venue: str = "ccxt"):
    ts = _ts_ms_to_datetime(raw.timestamp)
    symbol = raw.symbol or ""
    return CanonicalOrder(
        order_id=raw.id,
        client_order_id=raw.clientOrderId,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=_normalize_order_type(raw.type),
        quantity=_parse_decimal(raw.amount or 0),
        price=_parse_decimal(raw.price) if raw.price is not None else None,
        time_in_force=_normalize_tif(raw.timeInForce),
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filled or 0),
        remaining_quantity=_parse_decimal(raw.remaining) if raw.remaining is not None else None,
        average_fill_price=_parse_decimal(raw.average) if raw.average is not None else None,
    )


def normalize_ccxt_trade_to_fill(raw: CcxtTrade, venue: str = "ccxt"):
    ts = _ts_ms_to_datetime(raw.timestamp)
    symbol = raw.symbol or ""
    fill_id = raw.id or f"{raw.order or 'unknown'}-{raw.timestamp or 0}"
    fee_val, fee_ccy = _extract_ccxt_fee(raw)
    is_maker = raw.takerOrMaker.lower() == "maker" if raw.takerOrMaker else None
    return CanonicalFill(
        fill_id=str(fill_id),
        order_id=str(raw.order or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.price or 0),
        quantity=_parse_decimal(raw.amount or 0),
        fee=fee_val,
        fee_currency=fee_ccy,
        is_maker=is_maker,
    )


def normalize_binance_order(raw: BinanceOrder, venue: str = "binance"):
    ts = _ts_ms_to_datetime(raw.time or raw.updateTime)
    symbol = raw.symbol or ""
    return CanonicalOrder(
        order_id=str(raw.orderId or ""),
        client_order_id=raw.clientOrderId,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=_normalize_order_type(raw.type),
        quantity=_parse_decimal(raw.origQty or 0),
        price=_parse_decimal(raw.price) if raw.price else None,
        time_in_force=_normalize_tif(raw.timeInForce),
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.executedQty or raw.cumQty or 0),
        remaining_quantity=None,
        average_fill_price=None,
    )


def normalize_binance_fill(raw: BinanceMyTrades, venue: str = "binance"):
    ts = _ts_ms_to_datetime(raw.time)
    symbol = raw.symbol or ""
    return CanonicalFill(
        fill_id=str(raw.id),
        order_id=str(raw.orderId),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.price),
        quantity=_parse_decimal(raw.qty),
        fee=_parse_decimal(raw.commission),
        fee_currency=raw.commissionAsset,
        is_maker=raw.maker,
    )


def normalize_okx_order(raw: OKXOrder, venue: str = "okx"):
    ts = datetime.now(UTC)
    symbol = raw.instId or ""
    return CanonicalOrder(
        order_id=str(raw.ordId or ""),
        client_order_id=raw.clOrdId,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=_normalize_order_type(raw.ordType),
        quantity=_parse_decimal(raw.sz or 0),
        price=_parse_decimal(raw.px) if raw.px else None,
        status=_normalize_order_status(raw.state),
        filled_quantity=_parse_decimal(raw.accFillSz or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.fillPx) if raw.fillPx else None,
    )


def normalize_bybit_order(raw: BybitOrder, venue: str = "bybit"):
    ts = datetime.now(UTC)
    symbol = raw.symbol or ""
    return CanonicalOrder(
        order_id=str(raw.orderId or ""),
        client_order_id=raw.orderLinkId,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=_normalize_order_type(raw.orderType),
        quantity=_parse_decimal(raw.qty or 0),
        price=_parse_decimal(raw.price) if raw.price else None,
        status=_normalize_order_status(raw.orderStatus),
        filled_quantity=_parse_decimal(raw.cumExecQty or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.avgPrice) if raw.avgPrice else None,
    )


def normalize_bybit_fill(raw: BybitExecutionWS, venue: str = "bybit"):
    ts = _ts_ms_to_datetime(raw.execTime)
    symbol = raw.symbol or ""
    return CanonicalFill(
        fill_id=str(raw.execId),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.execPrice),
        quantity=_parse_decimal(raw.execQty),
        fee=_parse_decimal(raw.execFee) if raw.execFee else None,
        fee_currency=None,
        is_maker=raw.isMaker,
    )


def normalize_deribit_order(raw: DeribitOrder, venue: str = "deribit"):
    ts = _ts_ms_to_datetime(raw.creation_timestamp)
    symbol = raw.instrument_name or ""
    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=None,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.direction),
        order_type=OrderType.LIMIT,
        quantity=_parse_decimal(raw.amount or 0),
        price=_parse_decimal(raw.price) if raw.price is not None else None,
        status=_normalize_order_status(raw.order_state),
        filled_quantity=_parse_decimal(raw.filled_amount or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.average_price) if raw.average_price is not None else None,
    )


__all__ = [
    "normalize_binance_fill",
    "normalize_binance_order",
    "normalize_bybit_fill",
    "normalize_bybit_order",
    "normalize_ccxt_order",
    "normalize_ccxt_trade_to_fill",
    "normalize_deribit_order",
    "normalize_okx_order",
]
