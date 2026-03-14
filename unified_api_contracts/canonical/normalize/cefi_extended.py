"""CeFi extended normalizers: Kraken, KuCoin, Gate.io, Bitfinex, Bitstamp, MEXC, Huobi/HTX, Bitget, dYdX.

Each venue provides:
  - normalize_{venue}_trade    -> CanonicalTrade
  - normalize_{venue}_orderbook -> CanonicalOrderBook
  - normalize_{venue}_order    -> CanonicalOrder
  - normalize_{venue}_fill     -> CanonicalFill  (where fill data available)

OKX fill normalizer also added here (uses OKXRealizedPnlResponse as fill proxy).
Deribit fill normalizer added (DeribitSettlementRecord / user trade via DeribitTrade).
Upbit fill normalizer added (UpbitWithdrawalResponse is not a fill; using UpbitOrder executed_volume as fill proxy).
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ...external.bitfinex.schemas import (
    BitfinexFill,
    BitfinexOrder,
    BitfinexOrderBook,
    BitfinexTrade,
)
from ...external.bitstamp.schemas import (
    BitstampFill,
    BitstampOrder,
    BitstampOrderBook,
    BitstampTrade,
)
from ...external.gateio.schemas import (
    GateioFill,
    GateioOrder,
    GateioOrderBook,
    GateioTrade,
)
from ...external.kraken.schemas import (
    KrakenFill,
    KrakenOrder,
    KrakenOrderBook,
    KrakenTrade,
)
from ...external.kucoin.schemas import (
    KucoinFill,
    KucoinOrder,
    KucoinOrderBook,
    KucoinTrade,
)
from ..domain import CanonicalOrderBook, CanonicalTrade
from ..execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from .cefi_extended2 import (
    normalize_bitget_fill,
    normalize_bitget_order,
    normalize_bitget_orderbook,
    normalize_bitget_trade,
    normalize_deribit_fill,
    normalize_dydx_fill,
    normalize_dydx_order,
    normalize_dydx_orderbook,
    normalize_dydx_trade,
    normalize_huobi_fill,
    normalize_huobi_order,
    normalize_huobi_orderbook,
    normalize_huobi_trade,
    normalize_mexc_fill,
    normalize_mexc_order,
    normalize_mexc_orderbook,
    normalize_mexc_trade,
    normalize_okx_fill,
    normalize_upbit_fill,
)

# ---------------------------------------------------------------------------
# Shared helpers (mirror orders_fills.py helpers — kept local to avoid circular)
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


def _ts_sec(ts: float | Decimal | str | None) -> datetime:
    """Convert second-precision Unix timestamp to UTC datetime."""
    if ts is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(float(str(ts)), tz=UTC)


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
# Kraken
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
# KuCoin
# ---------------------------------------------------------------------------


def normalize_kucoin_trade(raw: KucoinTrade, symbol: str = "", venue: str = "kucoin") -> CanonicalTrade:
    """Convert KucoinTrade to CanonicalTrade."""
    # KuCoin WS time is nanoseconds as a string; REST is ms int
    ts = datetime.now(UTC)
    if raw.time is not None:
        time_val = int(str(raw.time))
        if time_val > 1_000_000_000_000_000:  # nanoseconds (16+ digits)
            ts = datetime.fromtimestamp(time_val / 1e9, tz=UTC)
        else:  # milliseconds
            ts = datetime.fromtimestamp(time_val / 1000.0, tz=UTC)
    trade_id = str(raw.tradeId) if raw.tradeId else str(raw.sequence or "")
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.size),
        side=(raw.side or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.tradeId) if raw.tradeId else None,
    )


def normalize_kucoin_orderbook(raw: KucoinOrderBook, symbol: str = "", venue: str = "kucoin") -> CanonicalOrderBook:
    """Convert KucoinOrderBook to CanonicalOrderBook."""
    ts = datetime.now(UTC)
    if raw.time is not None:
        ts = datetime.fromtimestamp(int(str(raw.time)) / 1000.0, tz=UTC)
    seq = int(raw.sequence) if raw.sequence else None
    bids = [(Decimal(row[0]), Decimal(row[1])) for row in raw.bids if len(row) >= 2]
    asks = [(Decimal(row[0]), Decimal(row[1])) for row in raw.asks if len(row) >= 2]
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=seq,
    )


def normalize_kucoin_order(raw: KucoinOrder, venue: str = "kucoin") -> CanonicalOrder:
    """Convert KucoinOrder to CanonicalOrder."""
    ts = _ts_ms(raw.createdAt)
    status = _status("filled" if not raw.isActive else "open")
    if raw.status:
        status = _status(raw.status)
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=None,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        order_type=_order_type(raw.type),
        quantity=_d(raw.size),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.timeInForce),
        status=status,
        filled_quantity=_d(raw.dealSize),
        remaining_quantity=None,
        average_fill_price=None,
    )


def normalize_kucoin_fill(raw: KucoinFill, venue: str = "kucoin") -> CanonicalFill:
    """Convert KucoinFill to CanonicalFill."""
    ts = _ts_ms(raw.createdAt)
    is_maker: bool | None = None
    if raw.liquidity:
        is_maker = raw.liquidity.lower() == "maker"
    return CanonicalFill(
        fill_id=str(raw.tradeId or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol or "",
        side=_side(raw.side),
        price=_d(raw.price),
        quantity=_d(raw.size),
        fee=_d(raw.fee) if raw.fee else None,
        fee_currency=raw.feeCurrency,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Gate.io
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
# Bitfinex
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
# Bitstamp
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


__all__ = [
    # Bitfinex
    "normalize_bitfinex_fill",
    "normalize_bitfinex_order",
    "normalize_bitfinex_orderbook",
    "normalize_bitfinex_trade",
    # Bitget
    "normalize_bitget_fill",
    "normalize_bitget_order",
    "normalize_bitget_orderbook",
    "normalize_bitget_trade",
    # Bitstamp
    "normalize_bitstamp_fill",
    "normalize_bitstamp_order",
    "normalize_bitstamp_orderbook",
    "normalize_bitstamp_trade",
    # Deribit fill
    "normalize_deribit_fill",
    # dYdX
    "normalize_dydx_fill",
    "normalize_dydx_order",
    "normalize_dydx_orderbook",
    "normalize_dydx_trade",
    # Gate.io
    "normalize_gateio_fill",
    "normalize_gateio_order",
    "normalize_gateio_orderbook",
    "normalize_gateio_trade",
    # Huobi / HTX
    "normalize_huobi_fill",
    "normalize_huobi_order",
    "normalize_huobi_orderbook",
    "normalize_huobi_trade",
    # Kraken
    "normalize_kraken_fill",
    "normalize_kraken_order",
    "normalize_kraken_orderbook",
    "normalize_kraken_trade",
    # KuCoin
    "normalize_kucoin_fill",
    "normalize_kucoin_order",
    "normalize_kucoin_orderbook",
    "normalize_kucoin_trade",
    # MEXC
    "normalize_mexc_fill",
    "normalize_mexc_order",
    "normalize_mexc_orderbook",
    "normalize_mexc_trade",
    # OKX fill
    "normalize_okx_fill",
    # Upbit fill
    "normalize_upbit_fill",
]
