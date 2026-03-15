"""Binance normalizers — all normalize_binance_* functions.

Extracted from normalize_utils/ modules (tickers, orderbooks, trades,
orders_fills, derivative_tickers, ohlcv, fees, instruments, liquidations,
market_state, connectivity, rate_limits, errors).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import (
    CanonicalDerivativeTicker,
    CanonicalFee,
    CanonicalInstrument,
    CanonicalLiquidation,
    CanonicalMarketStateEvent,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    FeeType,
    MarketState,
    WebSocketEvent,
)
from ...canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from ...normalize_utils._helpers import (
    _d,
    _to_decimal,
    _to_levels,
    _ts_ms_to_datetime,
)
from ...normalize_utils.market_state import _BINANCE_STATE_MAP, normalize_market_state
from ..binance.account_schemas import BinanceFeeRate
from ..binance.market_schemas import (
    BinanceInstrumentInfo,
    BinanceKline,
    BinanceOrderBook,
    BinancePremiumIndex,
    BinanceSymbol,
    BinanceTicker,
    BinanceTrade,
)
from ..binance.order_schemas import BinanceMyTrades, BinanceOrder
from ..binance.ws_schemas import BinanceLiquidationOrder

# ---------------------------------------------------------------------------
# Helpers (local — delegate to _helpers where possible)
# ---------------------------------------------------------------------------


def _normalize_side(s: str | None) -> str:
    """Side helper for orders/fills (returns enum, import-free)."""
    if not s:
        return OrderSide.BUY
    return OrderSide.SELL if str(s).lower() in ("sell", "short") else OrderSide.BUY


def _normalize_order_type(t: str | None) -> str:
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


def _normalize_order_status(s: str | None) -> str:
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


def _normalize_tif(tif: str | None) -> str:
    if not tif:
        return TimeInForce.GTC
    t = str(tif).upper()
    if t in ("IOC", "GTC", "FOK", "GTD", "POST_ONLY"):
        return TimeInForce(t)
    return TimeInForce.GTC


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_binance_ticker(
    raw: BinanceTicker, instrument_key: str | None = None, venue: str = "binance"
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol}"
    ts = _ts_ms_to_datetime(raw.time or raw.closeTime)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.lastPrice) or Decimal("0"),
        bid_price=_to_decimal(raw.bidPrice),
        ask_price=_to_decimal(raw.askPrice),
        volume_24h=_to_decimal(raw.volume),
        quote_volume_24h=_to_decimal(raw.quoteVolume),
        price_change_24h=_to_decimal(raw.priceChange),
        price_change_percent_24h=_to_decimal(raw.priceChangePercent),
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_binance_orderbook(
    raw: BinanceOrderBook,
    venue: str = "binance",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert BinanceOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC) if timestamp_ms is not None else datetime.now(UTC)
    bids = _to_levels([[p, q] for p, q in raw.bids])
    asks = _to_levels([[p, q] for p, q in raw.asks])
    return CanonicalOrderBook(
        venue=venue,
        symbol=symbol,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.lastUpdateId,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_binance_trade(raw: BinanceTrade, venue: str = "binance", symbol: str = "") -> CanonicalTrade:
    """Convert BinanceTrade to CanonicalTrade."""
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC)
    side = "buy" if not raw.isBuyerMaker else "sell"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or "UNKNOWN",
        trade_id=str(raw.id),
        timestamp=ts,
        price=raw.price,
        quantity=raw.qty,
        side=side,
        buyer_maker=raw.isBuyerMaker,
        venue_trade_id=str(raw.id),
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_binance_order(raw: BinanceOrder, venue: str = "binance") -> CanonicalOrder:
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


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_binance_fill(raw: BinanceMyTrades, venue: str = "binance") -> CanonicalFill:
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


# ---------------------------------------------------------------------------
# Derivative Ticker
# ---------------------------------------------------------------------------


def normalize_binance_derivative_ticker(
    raw: BinancePremiumIndex | BinanceTicker,
    instrument_key: str | None = None,
    venue: str = "binance",
) -> CanonicalDerivativeTicker:
    """Normalize Binance premium-index or USD-M futures ticker."""
    symbol: str = ""
    mark_price: Decimal | None = None
    index_price: Decimal | None = None
    last_price: Decimal | None = None
    funding_rate: Decimal | None = None
    next_funding_timestamp: datetime | None = None
    timestamp: datetime = datetime.now(UTC)

    def _ms_to_utc(ts_ms: object | None) -> datetime | None:
        if ts_ms is None:
            return None
        try:
            ms = int(str(ts_ms))
            if ms <= 0:
                return None
            return datetime.fromtimestamp(ms / 1000.0, tz=UTC)
        except (ValueError, TypeError, OSError):
            return None

    if isinstance(raw, BinancePremiumIndex):
        symbol = raw.symbol or ""
        mark_price = _to_decimal(raw.markPrice)
        index_price = _to_decimal(raw.indexPrice)
        funding_rate = _to_decimal(raw.lastFundingRate)
        next_funding_timestamp = _ms_to_utc(raw.nextFundingTime)
        ts_dt = _ms_to_utc(raw.time)
        if ts_dt is not None:
            timestamp = ts_dt
    else:
        symbol = raw.symbol
        last_price = _to_decimal(raw.lastPrice)
        funding_rate = _to_decimal(raw.lastFundingRate)
        next_funding_timestamp = _ms_to_utc(raw.nextFundingTime)
        ts_dt = _ms_to_utc(raw.time or raw.closeTime)
        if ts_dt is not None:
            timestamp = ts_dt

    ik = instrument_key or f"{venue}:PERPETUAL:{symbol}"
    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate,
        next_funding_timestamp=next_funding_timestamp,
    )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_binance_kline(raw: BinanceKline, symbol: str, venue: str = "binance") -> CanonicalOhlcvBar:
    """Convert BinanceKline to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp(raw.open_time / 1000.0, tz=UTC)
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=_d(raw.open_price),
        high=_d(raw.high_price),
        low=_d(raw.low_price),
        close=_d(raw.close_price),
        volume=_d(raw.volume),
        quote_volume=_d(raw.quote_asset_volume),
        count=raw.number_of_trades,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_binance_fee_rate(
    raw: BinanceFeeRate,
    fee_type: FeeType = FeeType.MAKER,
    venue: str = "binance",
) -> CanonicalFee:
    """Normalize a BinanceFeeRate to CanonicalFee."""
    amount = Decimal(raw.takerCommission) if fee_type is FeeType.TAKER else Decimal(raw.makerCommission)
    return CanonicalFee(
        amount=amount,
        currency=raw.symbol,
        asset=raw.symbol,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def _binance_filter_value(
    filters: list[dict[str, object]] | None,
    filter_type: str,
    key: str,
) -> float | None:
    if not filters:
        return None
    for f in filters:
        if f.get("filterType") == filter_type:
            raw_val = f.get(key)
            if raw_val is not None:
                return float(str(raw_val))
    return None


def _binance_instrument_type(raw: BinanceInstrumentInfo | BinanceSymbol) -> str:
    if isinstance(raw, BinanceInstrumentInfo):
        contract_type = (raw.contractType or "").upper()
        if contract_type == "PERPETUAL":
            return "PERPETUAL"
        if contract_type in ("CURRENT_QUARTER", "NEXT_QUARTER", "DELIVERY"):
            return "FUTURE"
        return "SPOT"
    return "SPOT"


def normalize_binance_symbol(
    raw: BinanceInstrumentInfo | BinanceSymbol,
    venue: str = "binance",
) -> CanonicalInstrument:
    """Normalize a BinanceInstrumentInfo or BinanceSymbol to CanonicalInstrument."""
    instrument_type = _binance_instrument_type(raw)
    symbol = raw.symbol
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"
    tick_size: float | None = None
    min_size: float | None = None
    if isinstance(raw, BinanceInstrumentInfo) and raw.filters:
        tick_size = _binance_filter_value(raw.filters, "PRICE_FILTER", "tickSize")
        min_size = _binance_filter_value(raw.filters, "LOT_SIZE", "minQty")
    base_asset = raw.baseAsset
    quote_asset = raw.quoteAsset
    contract_size: float | None = None
    if isinstance(raw, BinanceInstrumentInfo) and raw.contractSize is not None:
        contract_size = float(raw.contractSize)
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=contract_size,
        base_asset=base_asset,
        quote_asset=quote_asset,
        settle_asset=raw.marginAsset if isinstance(raw, BinanceInstrumentInfo) else None,
    )


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_binance_liquidation(
    raw: BinanceLiquidationOrder,
    venue: str = "binance",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert BinanceLiquidationOrder (forceOrder WS event) to CanonicalLiquidation."""
    order: dict[str, object] = raw.o
    raw_symbol: str = symbol or str(order.get("s") or "UNKNOWN")
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"
    raw_side: str = str(order.get("S") or "BUY").upper()
    side: str = "buy" if raw_side == "BUY" else "sell"
    ap_raw = order.get("ap") or order.get("p") or "0"
    price = Decimal(str(ap_raw))
    z_raw = order.get("z") or order.get("q") or "0"
    size = Decimal(str(z_raw))
    trade_time_ms = order.get("T") or raw.E
    ts = datetime.fromtimestamp(int(str(trade_time_ms)) / 1000.0, tz=UTC)
    order_id_raw = order.get("i")
    order_id: str | None = str(order_id_raw) if order_id_raw is not None else None
    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=order_id,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# Market State
# ---------------------------------------------------------------------------


def normalize_binance_market_state(
    status: str,
    symbol: str,
    instrument_type: str = "SPOT",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "binance",
) -> CanonicalMarketStateEvent:
    """Normalize a Binance symbol status string to CanonicalMarketStateEvent."""
    ik = f"{venue}:{instrument_type}:{symbol}"
    return normalize_market_state(
        raw_state=status,
        venue=venue,
        instrument_key=ik,
        state_map=_BINANCE_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_binance_ws_subscription(
    result: str | None,
    channel: str = "",
    venue: str = "binance",
) -> CanonicalWebSocketLifecycle:
    """Normalize Binance WS subscription response."""
    event = WebSocketEvent.SUBSCRIBE if result is None else WebSocketEvent.ERROR
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=event,
        timestamp=datetime.now(UTC),
        channel=channel or None,
        reason=result,
    )


# ---------------------------------------------------------------------------
# Rate Limits
# ---------------------------------------------------------------------------


from ...normalize_utils.rate_limits import extract_binance_rate_limit  # noqa: E402

__all__ = [
    "extract_binance_rate_limit",
    "normalize_binance_derivative_ticker",
    "normalize_binance_fee_rate",
    "normalize_binance_fill",
    "normalize_binance_kline",
    "normalize_binance_liquidation",
    "normalize_binance_market_state",
    "normalize_binance_order",
    "normalize_binance_orderbook",
    "normalize_binance_symbol",
    "normalize_binance_ticker",
    "normalize_binance_trade",
    "normalize_binance_ws_subscription",
]
