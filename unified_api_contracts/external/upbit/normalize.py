"""Venue-specific normalizers for Upbit.

Extracted from normalize_utils/ modules. Each function converts a raw Upbit
schema to its canonical counterpart.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalDuplicateOrderError,
    CanonicalError,
    CanonicalRateLimitError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalFee,
    CanonicalInstrument,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalTrade,
    CanonicalWebSocketLifecycle,
    FeeType,
)
from unified_api_contracts.canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
)
from unified_api_contracts.normalize_utils._helpers import (
    _d,
    _order_type,
    _status,
    _to_decimal,
    _ts_ms_to_datetime,
)
from unified_api_contracts.normalize_utils.connectivity import normalize_ws_disconnect

from .schemas import (
    UpbitFeeRate,
    UpbitMarket,
    UpbitOrderBook,
    UpbitTicker,
    UpbitTrade,
)
from .schemas import (
    UpbitOrder as UpbitOrderSchema,
)


def _parse_decimal(val: str | float | Decimal | None) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

UPBIT_MAP: dict[str, Callable[..., CanonicalError]] = {
    "too_many_requests": CanonicalRateLimitError,
    "invalid_access_key": CanonicalAuthenticationError,
    "invalid_query_payload": CanonicalError,
    "jwt_verification": CanonicalAuthenticationError,
    "expired_access_key": CanonicalAuthenticationError,
    "nonce_used": CanonicalDuplicateOrderError,
    "no_authorization_i_p": CanonicalAuthorizationError,
    "out_of_scope": CanonicalAuthorizationError,
}


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_upbit_ticker(
    raw: UpbitTicker, instrument_key: str | None = None, venue: str = "upbit"
) -> CanonicalTicker:
    ik = instrument_key or f"{venue}:SPOT:{raw.market or ''}"
    ts = datetime.now(UTC)
    t_ts = raw.info.get("timestamp") if raw.info else None
    if isinstance(t_ts, (int, float)):
        ts = _ts_ms_to_datetime(int(t_ts))
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.trade_price) or Decimal("0"),
        bid_price=_to_decimal(raw.bid_price),
        ask_price=_to_decimal(raw.ask_price),
        volume_24h=_to_decimal(raw.acc_trade_volume_24h),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_upbit_trade(raw: UpbitTrade, venue: str = "upbit", symbol: str = "") -> CanonicalTrade:
    """Convert UpbitTrade to CanonicalTrade."""
    ts = datetime.now(UTC)
    if raw.timestamp is not None:
        ts = datetime.fromtimestamp(raw.timestamp / 1000.0, tz=UTC)
    elif raw.sequential_id is not None:
        pass  # no ts from sequential_id
    side = "buy" if (raw.ask_bid or "").upper() == "BID" else "sell"
    return CanonicalTrade(
        venue=venue,
        symbol=symbol or (raw.market or "") or "UNKNOWN",
        trade_id=str(raw.sequential_id) if raw.sequential_id is not None else "",
        timestamp=ts,
        price=Decimal(str(raw.trade_price or 0)),
        quantity=Decimal(str(raw.trade_volume or 0)),
        side=side,
        buyer_maker=None,
        venue_trade_id=str(raw.sequential_id) if raw.sequential_id is not None else None,
    )


# ---------------------------------------------------------------------------
# Order Book
# ---------------------------------------------------------------------------


def normalize_upbit_orderbook(
    raw: UpbitOrderBook,
    venue: str = "upbit",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert UpbitOrderBook to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.timestamp, tz=UTC) if raw.timestamp is not None else datetime.now(UTC)
    sym = symbol or (raw.market or "")
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for unit in raw.orderbook_units:
        if unit.bid_price is not None and unit.bid_size is not None:
            bids.append((Decimal(str(unit.bid_price)), Decimal(str(unit.bid_size))))
        if unit.ask_price is not None and unit.ask_size is not None:
            asks.append((Decimal(str(unit.ask_price)), Decimal(str(unit.ask_size))))
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


def normalize_upbit_order(raw: UpbitOrderSchema, venue: str = "upbit") -> CanonicalOrder:
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
        order_type=_order_type(raw.ord_type),
        quantity=_parse_decimal(raw.volume or 0),
        price=_parse_decimal(raw.price) if raw.price else None,
        status=_status(raw.state),
        filled_quantity=_parse_decimal(raw.executed_volume or 0),
        remaining_quantity=None,
        average_fill_price=None,
    )


# ---------------------------------------------------------------------------
# Fill (synthetic from executed order)
# ---------------------------------------------------------------------------


def normalize_upbit_fill(raw: UpbitOrderSchema, venue: str = "upbit") -> CanonicalFill | None:
    """Convert UpbitOrder (state=done) to CanonicalFill.

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


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def normalize_upbit_market(
    raw: UpbitMarket,
    venue: str = "upbit",
) -> CanonicalInstrument:
    """Normalize UpbitMarket to CanonicalInstrument."""
    sym = raw.market or ""
    ik = f"{venue.upper()}:SPOT:{sym}"
    parts = sym.split("-", 1)
    quote_asset = parts[0] if len(parts) == 2 else None
    base_asset = parts[1] if len(parts) == 2 else None
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=base_asset,
        quote_asset=quote_asset,
        settle_asset=None,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_upbit_fee_rate(
    raw: UpbitFeeRate,
    fee_type: FeeType = FeeType.TAKER,
    venue: str = "upbit",
) -> CanonicalFee:
    """Normalize an UpbitFeeRate to CanonicalFee."""
    raw_rate = raw.taker_fee_rate if fee_type is FeeType.TAKER else raw.maker_fee_rate
    amount = Decimal(str(raw_rate)) if raw_rate is not None else Decimal("0")
    return CanonicalFee(
        amount=amount,
        currency=raw.currency or "",
        asset=raw.market,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# WebSocket lifecycle
# ---------------------------------------------------------------------------


def normalize_upbit_ws_close(
    code: int,
    reason: str | None = None,
    venue: str = "upbit",
) -> CanonicalWebSocketLifecycle:
    """Normalize Upbit WebSocket close frame."""
    return normalize_ws_disconnect(venue=venue, code=code, reason=reason)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_upbit_error(
    error_code: str | int,
    message: str = "",
    venue: str = "upbit",
) -> CanonicalError:
    """Map an Upbit error name to a CanonicalError subclass."""
    code = str(error_code)
    cls = UPBIT_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_upbit_error",
    "normalize_upbit_fee_rate",
    "normalize_upbit_fill",
    "normalize_upbit_market",
    "normalize_upbit_order",
    "normalize_upbit_orderbook",
    "normalize_upbit_ticker",
    "normalize_upbit_trade",
    "normalize_upbit_ws_close",
]
