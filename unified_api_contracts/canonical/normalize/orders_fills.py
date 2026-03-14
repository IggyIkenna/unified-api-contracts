"""Order and fill normalizers: raw venue responses -> CanonicalOrder, CanonicalFill."""

import contextlib
import logging
from datetime import UTC, datetime
from decimal import Decimal

from ...external.aster.schemas import AsterOrder
from ...external.binance.order_schemas import BinanceMyTrades, BinanceOrder
from ...external.bybit.schemas import BybitExecutionWS, BybitOrder
from ...external.ccxt.schemas import CcxtOrder, CcxtTrade
from ...external.coinbase.schemas import CoinbaseFill, CoinbaseOrder
from ...external.deribit.schemas import DeribitOrder
from ...external.fix.schemas import FixExecutionReport, FixNewOrderSingle
from ...external.hyperliquid.schemas import (
    HyperliquidFill,
    HyperliquidOpenOrder,
)
from ...external.ibkr.schemas import IBKRExecution, IBKROrder
from ...external.kalshi.schemas import KalshiFill
from ...external.nautilus import Fill as NautilusFill
from ...external.nautilus import Order as NautilusOrder
from ...external.okx.schemas import OKXOrder
from ...external.polymarket.schemas import PolymarketCLOBOrder, PolymarketFill
from ...external.prime_broker.schemas import PrimeBrokerFill
from ...external.upbit.schemas import UpbitOrder
from ..execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)

_logger = logging.getLogger(__name__)


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


def _parse_iso_ts(s: str | None) -> datetime:
    """Parse ISO timestamp string to UTC datetime."""
    if not s:
        return datetime.now(UTC)
    try:
        ts = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.now(UTC)


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
            float(cost)
            if isinstance(cost, (int, float))
            else str(cost)
            if isinstance(cost, str)
            else cost
            if isinstance(cost, Decimal)
            else None
        )
        return (
            _parse_decimal(cost_val) if cost_val is not None else None,
            str(currency) if currency is not None else None,
        )
    if hasattr(fee, "cost") and hasattr(fee, "currency"):
        c = getattr(fee, "cost", None)
        curr = getattr(fee, "currency", None)
        c_val: str | float | Decimal | None = (
            float(c)
            if isinstance(c, (int, float))
            else str(c)
            if isinstance(c, str)
            else c
            if isinstance(c, Decimal)
            else None
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


def normalize_coinbase_order(raw: CoinbaseOrder, venue: str = "coinbase") -> CanonicalOrder:
    """Convert CoinbaseOrder to CanonicalOrder."""
    ts = _parse_iso_ts(raw.created_time)
    symbol = raw.product_id or ""
    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=raw.client_order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=OrderType.LIMIT if (raw.time_in_force or "").upper() != "IOC" else OrderType.MARKET,
        quantity=_parse_decimal(raw.filled_size or 0),
        price=None,
        time_in_force=_normalize_tif(raw.time_in_force),
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filled_size or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.average_filled_price) if raw.average_filled_price else None,
    )


def normalize_coinbase_fill(raw: CoinbaseFill, venue: str = "coinbase") -> CanonicalFill:
    """Convert CoinbaseFill to CanonicalFill."""
    ts = _parse_iso_ts(raw.created_time)
    symbol = raw.product_id or ""
    fill_id = str(raw.trade_id or raw.order_id or "unknown")
    liq = (raw.liquidity or "").lower()
    is_maker: bool | None = True if liq == "maker" else (False if liq == "taker" else None)
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.order_id or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.price or 0),
        quantity=_parse_decimal(raw.size or 0),
        fee=_parse_decimal(raw.fee) if raw.fee else None,
        fee_currency=None,
        is_maker=is_maker,
    )


def normalize_upbit_order(raw: UpbitOrder, venue: str = "upbit") -> CanonicalOrder:
    """Convert UpbitOrder to CanonicalOrder."""
    ts = datetime.now(UTC)
    symbol = ""
    return CanonicalOrder(
        order_id=str(raw.uuid or ""),
        client_order_id=None,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=OrderSide.SELL if (raw.side or "").lower() == "ask" else OrderSide.BUY,
        order_type=_normalize_order_type(raw.ord_type),
        quantity=_parse_decimal(raw.volume or 0),
        price=_parse_decimal(raw.price) if raw.price else None,
        status=_normalize_order_status(raw.state),
        filled_quantity=_parse_decimal(raw.executed_volume or 0),
        remaining_quantity=None,
        average_fill_price=None,
    )


def normalize_hyperliquid_order(raw: HyperliquidOpenOrder, venue: str = "hyperliquid") -> CanonicalOrder:
    """Convert HyperliquidOpenOrder to CanonicalOrder."""
    ts = _ts_ms_to_datetime(raw.timestamp)
    symbol = raw.coin or ""
    return CanonicalOrder(
        order_id=str(raw.oid or ""),
        client_order_id=None,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=OrderType.LIMIT,
        quantity=_parse_decimal(raw.sz or raw.origSz or 0),
        price=_parse_decimal(raw.limitPx) if raw.limitPx else None,
        status=OrderStatus.OPEN,
        filled_quantity=Decimal("0"),
        remaining_quantity=None,
        average_fill_price=None,
    )


def normalize_hyperliquid_fill(raw: HyperliquidFill, venue: str = "hyperliquid") -> CanonicalFill:
    """Convert HyperliquidFill to CanonicalFill."""
    ts = _ts_ms_to_datetime(raw.time)
    symbol = raw.coin or ""
    fill_id = str(raw.tid or raw.oid or "unknown")
    return CanonicalFill(
        fill_id=fill_id,
        order_id=str(raw.oid or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side or raw.dir),
        price=_parse_decimal(raw.px or 0),
        quantity=_parse_decimal(raw.sz or 0),
        fee=_parse_decimal(raw.fee) if raw.fee else None,
        fee_currency=raw.feeToken,
        is_maker=not raw.crossed if raw.crossed is not None else None,
    )


def normalize_aster_order(raw: AsterOrder, venue: str = "aster") -> CanonicalOrder:
    """Convert AsterOrder to CanonicalOrder."""
    ts = datetime.now(UTC)
    symbol = raw.market_id or ""
    return CanonicalOrder(
        order_id=str(raw.order_id or ""),
        client_order_id=None,
        timestamp=ts,
        venue=venue,
        instrument_id=symbol,
        side=_normalize_side(raw.side),
        order_type=OrderType.LIMIT,
        quantity=_parse_decimal(raw.size or 0),
        price=_parse_decimal(raw.price) if raw.price else None,
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filled_size or 0),
        remaining_quantity=None,
        average_fill_price=None,
    )


def normalize_nautilus_order(raw: NautilusOrder, venue: str = "nautilus") -> CanonicalOrder:
    """Convert NautilusTrader Order to CanonicalOrder."""
    ts = raw.timestamp if raw.timestamp.tzinfo else raw.timestamp.replace(tzinfo=UTC)
    return CanonicalOrder(
        order_id=str(raw.order_id),
        client_order_id=raw.client_order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.instrument_id or "",
        side=_normalize_side(raw.side),
        order_type=_normalize_order_type(raw.order_type),
        quantity=raw.quantity,
        price=raw.price,
        status=_normalize_order_status(raw.status),
        filled_quantity=raw.filled_qty,
        remaining_quantity=None,
        average_fill_price=raw.avg_px,
    )


def normalize_nautilus_fill(raw: NautilusFill, venue: str = "nautilus") -> CanonicalFill:
    """Convert NautilusTrader Fill to CanonicalFill."""
    ts = raw.timestamp if raw.timestamp.tzinfo else raw.timestamp.replace(tzinfo=UTC)
    return CanonicalFill(
        fill_id=raw.fill_id,
        order_id=raw.order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.instrument_id or "",
        side=_normalize_side(raw.side),
        price=raw.price,
        quantity=raw.quantity,
        fee=raw.commission if raw.commission else None,
        fee_currency=raw.commission_currency,
        is_maker=None,
    )


def normalize_ibkr_order(raw: IBKROrder, instrument_id: str = "", venue: str = "ibkr") -> CanonicalOrder:
    """Convert IBKROrder to CanonicalOrder."""
    ts = datetime.now(UTC)
    return CanonicalOrder(
        order_id=str(raw.orderId or ""),
        client_order_id=str(raw.permId) if raw.permId is not None else None,
        timestamp=ts,
        venue=venue,
        instrument_id=instrument_id,
        side=_normalize_side(raw.action),
        order_type=_normalize_order_type(raw.orderType),
        quantity=_parse_decimal(raw.totalQuantity or 0),
        price=_parse_decimal(raw.lmtPrice) if raw.lmtPrice is not None else None,
        status=_normalize_order_status(raw.status),
        filled_quantity=_parse_decimal(raw.filledQuantity or 0),
        remaining_quantity=None,
        average_fill_price=_parse_decimal(raw.avgFillPrice) if raw.avgFillPrice is not None else None,
    )


def normalize_ibkr_execution(raw: IBKRExecution, instrument_id: str = "", venue: str = "ibkr") -> CanonicalFill:
    """Convert IBKRExecution to CanonicalFill."""
    ts = datetime.now(UTC)
    if raw.time:
        try:
            ts = datetime.fromisoformat(str(raw.time).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            _logger.debug("IBKR execution time %r is not a valid ISO datetime; using current UTC time", raw.time)
    return CanonicalFill(
        fill_id=str(raw.execId or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=instrument_id,
        side=_normalize_side(raw.side),
        price=_parse_decimal(raw.price or 0),
        quantity=_parse_decimal(raw.shares or 0),
        fee=None,
        fee_currency=None,
        is_maker=None,
    )


def normalize_fix_execution_report_to_order(raw: FixExecutionReport, venue: str = "fix") -> CanonicalOrder:
    """Convert FixExecutionReport to CanonicalOrder (order status view)."""
    ts = raw.transact_time if raw.transact_time.tzinfo else raw.transact_time.replace(tzinfo=UTC)
    side_str = "buy" if str(raw.side) == "1" else "sell"
    return CanonicalOrder(
        order_id=raw.order_id,
        client_order_id=raw.cl_ord_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol,
        side=OrderSide.BUY if side_str == "buy" else OrderSide.SELL,
        order_type=OrderType.LIMIT if raw.avg_px else OrderType.MARKET,
        quantity=raw.order_qty,
        price=raw.avg_px if raw.avg_px else None,
        status=_normalize_order_status(
            {
                "0": "open",
                "A": "open",
                "1": "partially_filled",
                "2": "filled",
                "3": "filled",
                "4": "cancelled",
                "6": "cancelled",
                "8": "rejected",
                "C": "expired",
            }.get(str(raw.ord_status), "pending")
        ),
        filled_quantity=raw.cum_qty,
        remaining_quantity=raw.leaves_qty,
        average_fill_price=raw.avg_px,
    )


def normalize_fix_execution_report_to_fill(raw: FixExecutionReport, venue: str = "fix") -> CanonicalFill | None:
    """Convert FixExecutionReport to CanonicalFill when last_qty/last_px present (fill event)."""
    if raw.last_qty is None or raw.last_px is None or raw.last_qty == 0:
        return None
    ts = raw.transact_time if raw.transact_time.tzinfo else raw.transact_time.replace(tzinfo=UTC)
    side_str = "buy" if str(raw.side) == "1" else "sell"
    return CanonicalFill(
        fill_id=raw.exec_id,
        order_id=raw.order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol,
        side=OrderSide.BUY if side_str == "buy" else OrderSide.SELL,
        price=raw.last_px,
        quantity=raw.last_qty,
        fee=None,
        fee_currency=None,
        is_maker=None,
    )


def normalize_fix_new_order_single(raw: FixNewOrderSingle, venue: str = "fix") -> CanonicalOrder:
    """Convert FixNewOrderSingle to CanonicalOrder (submission view)."""
    ts = raw.transact_time if raw.transact_time.tzinfo else raw.transact_time.replace(tzinfo=UTC)
    side_str = "buy" if str(raw.side) == "1" else "sell"
    return CanonicalOrder(
        order_id="",
        client_order_id=raw.cl_ord_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol,
        side=OrderSide.BUY if side_str == "buy" else OrderSide.SELL,
        order_type=_normalize_order_type(
            {"1": "market", "2": "limit", "3": "stop", "4": "stop_limit"}.get(str(raw.ord_type), "limit")
        ),
        quantity=raw.order_qty,
        price=raw.price,
        time_in_force=_normalize_tif(
            {"0": "GTC", "1": "GTC", "3": "IOC", "4": "FOK", "6": "GTD"}.get(str(raw.time_in_force), "GTC")
        ),
        status=OrderStatus.PENDING,
        filled_quantity=Decimal("0"),
        remaining_quantity=raw.order_qty,
        average_fill_price=None,
    )


def normalize_prime_broker_fill(raw: PrimeBrokerFill, venue: str | None = None) -> CanonicalFill:
    """Convert PrimeBrokerFill to CanonicalFill."""
    v = venue or str(raw.prime_broker).lower()
    ts = raw.timestamp if raw.timestamp.tzinfo else raw.timestamp.replace(tzinfo=UTC)
    return CanonicalFill(
        fill_id=raw.fill_id,
        order_id=raw.order_id,
        timestamp=ts,
        venue=v,
        instrument_id=raw.instrument_id,
        side=_normalize_side(raw.side),
        price=raw.price,
        quantity=raw.quantity,
        fee=raw.pb_fee_usd,
        fee_currency="USD" if raw.pb_fee_usd else None,
        is_maker=None,
    )


def normalize_kalshi_fill(
    raw: KalshiFill,
    venue: str = "kalshi",
    instrument_id: str = "",
) -> CanonicalFill:
    """Convert KalshiFill to CanonicalFill.

    KalshiFill: yes_price_dollars (str decimal), count_fp (str float contracts),
    fees_dollars (str decimal), is_taker (bool), side ("yes"/"no"), action ("buy"/"sell").
    """
    ts = datetime.now(UTC)
    if raw.created_time:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromisoformat(raw.created_time.replace("Z", "+00:00"))
    price = Decimal(str(raw.yes_price_dollars or 0))
    qty = Decimal(str(raw.count_fp or 0))
    fee = Decimal(str(raw.fees_dollars or 0))
    side = OrderSide.BUY if (raw.action or "buy").lower() == "buy" else OrderSide.SELL
    return CanonicalFill(
        venue=venue,
        order_id=raw.order_id or "",
        fill_id=raw.trade_id or "",
        instrument_id=instrument_id or raw.ticker or "",
        side=side,
        price=price if price > Decimal("0") else Decimal("0.01"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        fee=fee,
        fee_currency="USD",
        timestamp=ts,
        is_maker=not raw.is_taker if raw.is_taker is not None else None,
    )


def normalize_polymarket_fill(
    raw: PolymarketFill,
    venue: str = "polymarket",
    instrument_id: str = "",
) -> CanonicalFill:
    """Convert PolymarketFill to CanonicalFill."""
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1000.0, tz=UTC) if raw.timestamp else datetime.now(UTC)
    price = Decimal(str(raw.price or 0))
    qty = Decimal(str(raw.size or 0))
    fee = Decimal(str(raw.fee or 0))
    side = OrderSide.BUY if (raw.side or "BUY").upper() == "BUY" else OrderSide.SELL
    inst = instrument_id or raw.market or raw.asset_id or ""
    return CanonicalFill(
        venue=venue,
        order_id=raw.order_id or "",
        fill_id=raw.id or "",
        instrument_id=inst,
        side=side,
        price=price if price > Decimal("0") else Decimal("0.000001"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        fee=fee,
        fee_currency="USDC",
        timestamp=ts,
        is_maker=None,
    )


def normalize_polymarket_order(
    raw: PolymarketCLOBOrder,
    venue: str = "polymarket",
    instrument_id: str = "",
) -> CanonicalOrder:
    """Convert PolymarketCLOBOrder to CanonicalOrder."""
    side = OrderSide.BUY if (raw.side or "BUY").upper() == "BUY" else OrderSide.SELL
    price = Decimal(str(raw.price or 0))
    size_matched = Decimal(str(raw.size_matched or 0))
    size_remaining = Decimal(str(raw.size_remaining or 0))
    total_qty = size_matched + size_remaining

    status_map = {
        "LIVE": OrderStatus.OPEN,
        "MATCHED": OrderStatus.FILLED,
        "CANCELED": OrderStatus.CANCELLED,
        "DELAYED": OrderStatus.PENDING,
    }
    status = status_map.get((raw.status or "LIVE").upper(), OrderStatus.OPEN)

    type_map = {"GTC": TimeInForce.GTC, "FOK": TimeInForce.FOK, "GTD": TimeInForce.GTD}
    tif = type_map.get((raw.type or "GTC").upper(), TimeInForce.GTC)

    inst = instrument_id or raw.asset_id or ""
    return CanonicalOrder(
        venue=venue,
        order_id=raw.order_id or "",
        instrument_id=inst,
        side=side,
        order_type=OrderType.LIMIT,
        price=price,
        quantity=total_qty,
        filled_quantity=size_matched,
        remaining_quantity=size_remaining,
        status=status,
        time_in_force=tif,
        timestamp=datetime.now(UTC),
    )


__all__ = [
    "normalize_aster_order",
    "normalize_binance_fill",
    "normalize_binance_order",
    "normalize_bybit_fill",
    "normalize_bybit_order",
    "normalize_ccxt_order",
    "normalize_ccxt_trade_to_fill",
    "normalize_coinbase_fill",
    "normalize_coinbase_order",
    "normalize_deribit_order",
    "normalize_fix_execution_report_to_fill",
    "normalize_fix_execution_report_to_order",
    "normalize_fix_new_order_single",
    "normalize_hyperliquid_fill",
    "normalize_hyperliquid_order",
    "normalize_ibkr_execution",
    "normalize_ibkr_order",
    "normalize_kalshi_fill",
    "normalize_nautilus_fill",
    "normalize_nautilus_order",
    "normalize_okx_order",
    "normalize_polymarket_fill",
    "normalize_polymarket_order",
    "normalize_prime_broker_fill",
    "normalize_upbit_order",
]
