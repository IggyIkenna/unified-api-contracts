"""Deribit normalizers — all normalize_deribit_* functions.

Extracted from normalize_utils/ modules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from ...canonical.domain import (
    CanonicalDerivativeTicker,
    CanonicalFee,
    CanonicalInstrument,
    CanonicalLiquidation,
    CanonicalMarketStateEvent,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    FeeType,
    MarketState,
    WebSocketEvent,
)
from ...canonical.execution import CanonicalFill, CanonicalOrder, OrderSide, OrderStatus, OrderType
from ...normalize_utils._helpers import _d, _to_decimal, _to_levels, _ts_ms, _ts_ms_to_datetime
from ...normalize_utils._helpers import _side as _side_helper
from ...normalize_utils.market_state import _DERIBIT_STATE_MAP, normalize_market_state
from ..deribit.schemas import (
    DeribitInstrument,
    DeribitLiquidationOrder,
    DeribitOrder,
    DeribitOrderBook,
    DeribitTicker,
    DeribitTickerFull,
    DeribitTrade,
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


def normalize_deribit_ticker(
    raw: DeribitTicker | DeribitTickerFull,
    instrument_key: str | None = None,
    venue: str = "deribit",
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:OPTION:{raw.instrument_name or ''}"
    ts = datetime.now(UTC)
    if isinstance(raw, DeribitTickerFull) and raw.timestamp:
        ts = _ts_ms_to_datetime(raw.timestamp)
    vol_24h = None
    price_change = None
    price_change_pct = None
    if raw.stats:
        vol_24h = _to_decimal(cast(Decimal | float | str | None, raw.stats.get("volume")))
        price_change = _to_decimal(cast(Decimal | float | str | None, raw.stats.get("price_change")))
        price_change_pct = _to_decimal(cast(Decimal | float | str | None, raw.stats.get("price_change_percentage")))
    bid = _to_decimal(getattr(raw, "best_bid_price", None) or getattr(raw, "bid_price", None))
    ask = _to_decimal(getattr(raw, "best_ask_price", None) or getattr(raw, "ask_price", None))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.last_price) or Decimal("0"),
        bid_price=bid,
        ask_price=ask,
        volume_24h=vol_24h,
        quote_volume_24h=None,
        price_change_24h=price_change,
        price_change_percent_24h=price_change_pct,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_deribit_orderbook(
    raw: DeribitOrderBook,
    venue: str = "deribit",
    symbol: str = "",
    timestamp_ms: int | None = None,
) -> CanonicalOrderBook:
    """Convert DeribitOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC) if timestamp_ms is not None else datetime.now(UTC)
    sym = symbol or (raw.instrument_name or "")
    bids = _to_levels([[float(p), float(q)] for p, q in raw.bids])
    asks = _to_levels([[float(p), float(q)] for p, q in raw.asks])
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=ts,
        bids=bids,
        asks=asks,
        sequence_number=raw.change_id,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_deribit_trade(raw: DeribitTrade, venue: str = "deribit", symbol: str = "") -> CanonicalTrade:
    """Convert DeribitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.instrument_name or "") or "UNKNOWN",
        trade_id=str(raw.trade_id) if raw.trade_id else "",
        timestamp=ts,
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.amount or 0)),
        side=(raw.direction or "buy").lower(),
        buyer_maker=None,
        venue_trade_id=str(raw.trade_id) if raw.trade_id else None,
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_deribit_order(raw: DeribitOrder, venue: str = "deribit") -> CanonicalOrder:
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


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_deribit_fill(
    raw: DeribitTrade,
    order_id: str = "",
    venue: str = "deribit",
) -> CanonicalFill:
    """Convert DeribitTrade (user trade/fill) to CanonicalFill."""
    ts = _ts_ms(raw.timestamp)
    trade_id = str(raw.trade_id) if raw.trade_id else str(raw.trade_seq or "")
    return CanonicalFill(
        fill_id=trade_id,
        order_id=order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.instrument_name or "",
        side=_side_helper(raw.direction),
        price=_d(raw.price),
        quantity=_d(raw.amount),
        fee=None,
        fee_currency=None,
        is_maker=None,
    )


# ---------------------------------------------------------------------------
# Derivative Ticker
# ---------------------------------------------------------------------------


def normalize_deribit_derivative_ticker(
    raw: DeribitTickerFull,
    instrument_key: str | None = None,
    venue: str = "deribit",
) -> CanonicalDerivativeTicker:
    """Normalize DeribitTickerFull to CanonicalDerivativeTicker."""

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

    ik = instrument_key or f"{venue}:PERPETUAL:{raw.instrument_name}"
    timestamp = _ms_to_utc(raw.timestamp) or datetime.now(UTC)
    mark_price = _to_decimal(raw.mark_price)
    index_price = _to_decimal(raw.index_price)
    last_price = _to_decimal(raw.last_price)
    funding_rate = _to_decimal(raw.funding_8h)
    open_interest = _to_decimal(raw.open_interest)
    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        index_price=index_price,
        last_price=last_price,
        funding_rate=funding_rate,
        open_interest=open_interest,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_deribit_fee(
    fee: Decimal,
    currency: str,
    fee_type: FeeType = FeeType.TAKER,
    venue: str = "deribit",
) -> CanonicalFee:
    """Normalize a Deribit fill fee to CanonicalFee."""
    return CanonicalFee(
        amount=fee,
        currency=currency,
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def _deribit_instrument_type(kind: str | None) -> str:
    mapping: dict[str, str] = {
        "future": "FUTURE",
        "option": "OPTION",
        "spot": "SPOT",
        "perpetual": "PERPETUAL",
        "future_combo": "FUTURE",
        "option_combo": "OPTION",
    }
    return mapping.get((kind or "").lower(), "FUTURE")


def normalize_deribit_instrument(
    raw: DeribitInstrument,
    venue: str = "deribit",
) -> CanonicalInstrument:
    """Normalize a DeribitInstrument to CanonicalInstrument."""
    instrument_type = _deribit_instrument_type(raw.kind)
    symbol = raw.instrument_name or ""
    instrument_key = f"{venue.upper()}:{instrument_type}:{symbol}"
    tick_size = float(raw.tick_size) if raw.tick_size is not None else None
    min_size = float(raw.min_trade_amount) if raw.min_trade_amount is not None else None
    return CanonicalInstrument(
        instrument_key=instrument_key,
        venue=venue,
        symbol=symbol,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=None,
        base_asset=raw.base_currency,
        quote_asset=raw.quote_currency,
        settle_asset=raw.settlement_currency,
    )


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_deribit_liquidation(
    raw: DeribitLiquidationOrder,
    venue: str = "deribit",
) -> CanonicalLiquidation:
    """Convert DeribitLiquidationOrder to CanonicalLiquidation."""
    raw_symbol: str = str(raw.instrument_name or "UNKNOWN")
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"
    side: str = str(raw.side or "buy").lower()
    price = Decimal(str(raw.price or 0))
    size = Decimal(str(raw.amount or 0))
    ts_ms_val = raw.timestamp or 0
    ts = datetime.fromtimestamp(int(ts_ms_val) / 1000.0, tz=UTC)
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


def normalize_deribit_market_state(
    state: str,
    instrument_name: str,
    instrument_type: str = "PERPETUAL",
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "deribit",
) -> CanonicalMarketStateEvent:
    """Normalize a Deribit instrument state to CanonicalMarketStateEvent."""
    ik = f"{venue}:{instrument_type}:{instrument_name}"
    return normalize_market_state(
        raw_state=state,
        venue=venue,
        instrument_key=ik,
        state_map=_DERIBIT_STATE_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_deribit_ws_heartbeat(
    method: str,
    venue: str = "deribit",
) -> CanonicalWebSocketLifecycle:
    """Normalize Deribit WS heartbeat event."""
    evt = WebSocketEvent.PING if method == "heartbeat" else WebSocketEvent.PONG
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Rate Limits
# ---------------------------------------------------------------------------

from ...normalize_utils.rate_limits import extract_deribit_rate_limit, extract_deribit_ws_rate_limit  # noqa: E402

__all__ = [
    "extract_deribit_rate_limit",
    "extract_deribit_ws_rate_limit",
    "normalize_deribit_derivative_ticker",
    "normalize_deribit_fee",
    "normalize_deribit_fill",
    "normalize_deribit_instrument",
    "normalize_deribit_liquidation",
    "normalize_deribit_market_state",
    "normalize_deribit_order",
    "normalize_deribit_orderbook",
    "normalize_deribit_ticker",
    "normalize_deribit_trade",
    "normalize_deribit_ws_heartbeat",
]
