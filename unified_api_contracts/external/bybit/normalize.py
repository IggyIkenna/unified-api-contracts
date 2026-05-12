"""Bybit normalizers — all normalize_bybit_* functions.

Extracted from normalize_utils/ modules.
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
from ...canonical.domain.execution import CanonicalFill, CanonicalOrder, OrderSide, OrderStatus, OrderType
from ...normalize_utils._helpers import _d, _to_decimal, _to_levels, _ts_ms_to_datetime
from ...normalize_utils.market_state import _BYBIT_STATE_MAP, normalize_market_state
from ..bybit.schemas import (
    BybitExecutionWS,
    BybitFeeRate,
    BybitFundingRateHistory,
    BybitInstrumentInfo,
    BybitKline,
    BybitLiquidationOrder,
    BybitOrder,
    BybitOrderBook,
    BybitTicker,
    BybitTrade,
)


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


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


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_bybit_ticker(
    raw: BybitTicker, instrument_key: str | None = None, venue: str = "bybit"
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.symbol or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("ts") if raw.info else None
    if isinstance(t_ts, (int, float)):
        ts = _ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.lastPrice) or Decimal("0"),
        bid_price=_to_decimal(raw.bid1Price),
        ask_price=_to_decimal(raw.ask1Price),
        volume_24h=_to_decimal(raw.volume24h),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_bybit_orderbook(
    raw: BybitOrderBook,
    venue: str = "bybit",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert BybitOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.ts / 1000.0, tz=UTC) if raw.ts is not None else datetime.now(UTC)
    sym = symbol or (raw.s or "")
    bids = _to_levels(raw.b)
    asks = _to_levels(raw.a)
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.u,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_bybit_trade(raw: BybitTrade, venue: str = "bybit", symbol: str = "") -> CanonicalTrade:
    """Convert BybitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.execTime is not None:
        ts = datetime.fromtimestamp(raw.execTime / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.symbol or "") or "UNKNOWN",
        trade_id=str(raw.execId) if raw.execId else "",
        timestamp=ts,
        price=Decimal(str(raw.execPrice or 0)),
        quantity=Decimal(str(raw.execQty or 0)),
        side=(raw.side or "buy").lower(),
        buyer_maker=raw.isMaker,
        venue_trade_id=str(raw.execId) if raw.execId else None,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_bybit_order(raw: BybitOrder, venue: str = "bybit") -> CanonicalOrder:
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


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_bybit_fill(raw: BybitExecutionWS, venue: str = "bybit") -> CanonicalFill:
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


# ---------------------------------------------------------------------------
# Derivative Ticker
# ---------------------------------------------------------------------------


def normalize_bybit_derivative_ticker(
    raw: BybitTicker,
    funding: BybitFundingRateHistory | None = None,
    instrument_key: str | None = None,
    venue: str = "bybit",
) -> CanonicalDerivativeTicker:
    """Normalize Bybit ticker (+ optional funding history) to CanonicalDerivativeTicker."""
    symbol = raw.symbol or ""
    ik = instrument_key or f"{venue}:PERPETUAL:{symbol}"
    last_price = _to_decimal(raw.lastPrice)
    info: dict[str, object] = raw.info or {}

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

    mark_price = _to_decimal(info.get("markPrice"))
    index_price = _to_decimal(info.get("indexPrice"))
    funding_rate_val = _to_decimal(info.get("fundingRate"))
    next_funding_ts = _ms_to_utc(str(info["nextFundingTime"]) if info.get("nextFundingTime") else None)
    open_interest = _to_decimal(info.get("openInterest"))
    open_interest_value = _to_decimal(info.get("openInterestValue"))
    predicted_funding = _to_decimal(info.get("predictedFundingRate"))

    ts_raw = info.get("ts")
    timestamp: datetime = (
        _ms_to_utc(int(ts_raw)) or datetime.now(UTC) if isinstance(ts_raw, (int, float)) else datetime.now(UTC)
    )

    funding_timestamp: datetime | None = None
    if funding is not None:
        if funding.fundingRate is not None:
            funding_rate_val = _to_decimal(funding.fundingRate)
        if funding.fundingRateTimestamp is not None:
            funding_timestamp = _ms_to_utc(funding.fundingRateTimestamp)

    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate_val,
        predicted_funding_rate=predicted_funding,
        funding_timestamp=funding_timestamp,
        next_funding_timestamp=next_funding_ts,
        open_interest=open_interest,
        open_interest_value=open_interest_value,
    )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_bybit_kline(raw: BybitKline, symbol: str, venue: str = "bybit") -> CanonicalOhlcvBar:
    """Convert BybitKline to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp(int(raw.startTime) / 1000.0, tz=UTC)
    quote_vol = _d(raw.turnover) if raw.turnover is not None else None
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=symbol,
        open=_d(raw.openPrice),
        high=_d(raw.highPrice),
        low=_d(raw.lowPrice),
        close=_d(raw.closePrice),
        volume=_d(raw.volume),
        quote_volume=quote_vol,
        count=None,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_bybit_fee_rate(
    raw: BybitFeeRate,
    fee_type: FeeType = FeeType.MAKER,
    venue: str = "bybit",
) -> CanonicalFee:
    """Normalize a BybitFeeRate to CanonicalFee."""
    raw_rate = raw.takerFeeRate if fee_type is FeeType.TAKER else raw.makerFeeRate
    amount = Decimal(raw_rate) if raw_rate is not None else Decimal("0")
    currency = raw.baseCoin if raw.baseCoin is not None else (raw.symbol if raw.symbol is not None else "")
    return CanonicalFee(
        amount=amount,
        currency=currency,
        asset=raw.symbol,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def _bybit_instrument_type(raw: BybitInstrumentInfo) -> str:
    contract_type = (raw.contractType or "").lower()
    if "perpetual" in contract_type:
        return "PERPETUAL"
    if "future" in contract_type or "futures" in contract_type:
        return "FUTURE"
    if raw.optionsType is not None:
        return "OPTION"
    return "SPOT_PAIR"


def normalize_bybit_market(
    raw: BybitInstrumentInfo,
    venue: str = "bybit",
) -> CanonicalInstrument:
    """Normalize a BybitInstrumentInfo to CanonicalInstrument."""
    instrument_type = _bybit_instrument_type(raw)
    symbol = raw.symbol
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"
    tick_size: Decimal | None = None
    min_size: Decimal | None = None
    if raw.priceFilter:
        raw_tick = raw.priceFilter.get("tickSize")
        if raw_tick is not None:
            tick_size = Decimal(str(raw_tick))
    if raw.lotSizeFilter:
        raw_min_qty = raw.lotSizeFilter.get("minOrderQty")
        if raw_min_qty is not None:
            min_size = Decimal(str(raw_min_qty))
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=None,
        base_asset=raw.baseCoin,
        quote_asset=raw.quoteCoin,
        settle_asset=raw.settleCoin,
    )


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_bybit_liquidation(
    raw: BybitLiquidationOrder,
    venue: str = "bybit",
) -> CanonicalLiquidation:
    """Convert BybitLiquidationOrder to CanonicalLiquidation."""
    raw_symbol: str = str(raw.s or "UNKNOWN")
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"
    raw_side: str = str(raw.S or "Buy")
    side: str = "buy" if raw_side.lower() == "buy" else "sell"
    price = Decimal(str(raw.p or "0"))
    size = Decimal(str(raw.v or "0"))
    ts_ms = raw.T or 0
    ts = datetime.fromtimestamp(int(ts_ms) / 1000.0, tz=UTC)
    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=None,
        liquidated_account_value=None,
        liquidated_ntl_pos=None,
        liquidated_user=None,
    )


# ---------------------------------------------------------------------------
# Market State
# ---------------------------------------------------------------------------


def normalize_bybit_market_state(
    status: str,
    symbol: str,
    instrument_type: str = "PERPETUAL",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "bybit",
) -> CanonicalMarketStateEvent:
    """Normalize a Bybit symbol status to CanonicalMarketStateEvent."""
    ik = f"{venue}:{instrument_type}:{symbol}"
    return normalize_market_state(
        raw_state=status,
        venue=venue,
        instrument_key=ik,
        state_map=_BYBIT_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_bybit_ws_subscription(
    success: bool,
    topic: str = "",
    venue: str = "bybit",
) -> CanonicalWebSocketLifecycle:
    """Normalize Bybit WS subscription response."""
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=WebSocketEvent.SUBSCRIBE if success else WebSocketEvent.ERROR,
        timestamp=datetime.now(UTC),
        channel=topic or None,
    )


# ---------------------------------------------------------------------------
# Rate Limits
# ---------------------------------------------------------------------------

from ...normalize_utils.rate_limits import extract_bybit_rate_limit

__all__ = [
    "extract_bybit_rate_limit",
    "normalize_bybit_derivative_ticker",
    "normalize_bybit_fee_rate",
    "normalize_bybit_fill",
    "normalize_bybit_kline",
    "normalize_bybit_liquidation",
    "normalize_bybit_market",
    "normalize_bybit_market_state",
    "normalize_bybit_order",
    "normalize_bybit_orderbook",
    "normalize_bybit_ticker",
    "normalize_bybit_trade",
    "normalize_bybit_ws_subscription",
]
