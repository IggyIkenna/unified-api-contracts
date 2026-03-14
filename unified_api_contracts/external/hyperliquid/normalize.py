"""Hyperliquid normalizers — all normalize_hyperliquid_* functions.

Extracted from normalize_utils/ modules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import (
    CanonicalDerivativeTicker,
    CanonicalFee,
    CanonicalLiquidation,
    CanonicalOhlcvBar,
    CanonicalOrderBook,
    CanonicalTicker,
    CanonicalWebSocketLifecycle,
    FeeType,
    WebSocketEvent,
)
from ...canonical.execution import CanonicalFill, CanonicalOrder, OrderSide, OrderStatus, OrderType
from ...normalize_utils._helpers import _d, _to_decimal, _ts_ms_to_datetime
from ..hyperliquid.schemas import (
    HyperliquidCandle,
    HyperliquidFill,
    HyperliquidL2Book,
    HyperliquidL2Level,
    HyperliquidLiquidation,
    HyperliquidOpenOrder,
    HyperliquidTicker,
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


# ---------------------------------------------------------------------------
# Ticker
# ---------------------------------------------------------------------------


def normalize_hyperliquid_ticker(
    raw: HyperliquidTicker, instrument_key: str | None = None, venue: str = "hyperliquid"
) -> CanonicalTicker:
    """Convert HyperliquidTicker to CanonicalTicker."""
    ik = instrument_key or f"{venue}:PERPETUAL:{raw.coin or ''}"
    ts = datetime.now(UTC)
    return CanonicalTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=ts,
        last_price=_to_decimal(raw.markPx or raw.midPx) or Decimal("0"),
        bid_price=None,
        ask_price=None,
        volume_24h=_to_decimal(raw.dayNtlVlm),
        quote_volume_24h=None,
        price_change_24h=None,
        price_change_percent_24h=None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def _hl_levels(levels: list[HyperliquidL2Level]) -> list[tuple[Decimal, Decimal]]:
    """Convert a list of HyperliquidL2Level to [(price, size), ...]."""
    out: list[tuple[Decimal, Decimal]] = []
    for lvl in levels:
        if lvl.px is not None and lvl.sz is not None:
            out.append((Decimal(lvl.px), Decimal(lvl.sz)))
    return out


def normalize_hyperliquid_orderbook(
    raw: HyperliquidL2Book,
    venue: str = "hyperliquid",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert HyperliquidL2Book to CanonicalOrderBook."""
    ts = datetime.fromtimestamp(raw.time / 1000.0, tz=UTC) if raw.time is not None else datetime.now(UTC)
    sym = symbol or (f"{raw.coin}-USDC-PERP" if raw.coin else "UNKNOWN")
    levels = raw.levels or []
    bids = _hl_levels(levels[0]) if len(levels) > 0 else []
    asks = _hl_levels(levels[1]) if len(levels) > 1 else []
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


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Derivative Ticker
# ---------------------------------------------------------------------------


def normalize_hyperliquid_derivative_ticker(
    raw: HyperliquidTicker,
    instrument_key: str | None = None,
    venue: str = "hyperliquid",
) -> CanonicalDerivativeTicker:
    """Normalize HyperliquidTicker to CanonicalDerivativeTicker."""
    coin = raw.coin or ""
    ik = instrument_key or f"{venue}:PERPETUAL:{coin}"
    timestamp = datetime.now(UTC)
    mark_price = _to_decimal(raw.markPx)
    mid_price = _to_decimal(raw.midPx)
    prev_day_price = _to_decimal(raw.prevDayPx)
    funding_rate = _to_decimal(raw.funding)
    open_interest = _to_decimal(raw.openInterest)
    day_ntl_volume = _to_decimal(raw.dayNtlVlm)
    return CanonicalDerivativeTicker(
        instrument_key=ik,
        venue=venue,
        timestamp=timestamp,
        mark_price=mark_price,
        mid_price=mid_price,
        funding_rate=funding_rate,
        open_interest=open_interest,
        day_ntl_volume=day_ntl_volume,
        prev_day_price=prev_day_price,
    )


# ---------------------------------------------------------------------------
# OHLCV
# ---------------------------------------------------------------------------


def normalize_hyperliquid_candle(
    raw: HyperliquidCandle, symbol: str = "", venue: str = "hyperliquid"
) -> CanonicalOhlcvBar:
    """Convert HyperliquidCandle to CanonicalOhlcvBar."""
    ts = datetime.fromtimestamp((raw.t or 0) / 1000.0, tz=UTC)
    sym = symbol or raw.s or ""
    return CanonicalOhlcvBar(
        timestamp=ts,
        venue=venue,
        symbol=sym,
        open=_d(raw.o),
        high=_d(raw.h),
        low=_d(raw.low),
        close=_d(raw.c),
        volume=_d(raw.v),
        quote_volume=None,
        count=raw.n,
        vwap=None,
    )


# ---------------------------------------------------------------------------
# Fee
# ---------------------------------------------------------------------------


def normalize_hyperliquid_fee(
    fee: Decimal,
    fee_token: str,
    venue: str = "hyperliquid",
) -> CanonicalFee:
    """Normalize a Hyperliquid fill fee to CanonicalFee."""
    return CanonicalFee(
        amount=fee,
        currency=fee_token,
        asset=None,
        fee_type=FeeType.TAKER,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Liquidation
# ---------------------------------------------------------------------------


def normalize_hyperliquid_liquidation(
    raw: HyperliquidLiquidation,
    venue: str = "hyperliquid",
    symbol: str = "",
) -> CanonicalLiquidation:
    """Convert HyperliquidLiquidation to CanonicalLiquidation."""
    raw_symbol: str = symbol or "UNKNOWN"
    instrument_key = f"{venue}:PERPETUAL:{raw_symbol}"
    mark_px_raw = raw.markPx or 0.0
    mark_px = Decimal(str(mark_px_raw))
    ntl_pos_str = raw.liquidated_ntl_pos or "0"
    ntl_pos = Decimal(str(ntl_pos_str))
    account_value_str = raw.liquidated_account_value or "0"
    account_value = Decimal(str(account_value_str))
    side: str = "sell" if ntl_pos >= Decimal("0") else "buy"
    size: Decimal = abs(ntl_pos) / mark_px if mark_px > Decimal("0") and ntl_pos != Decimal("0") else Decimal("0")
    price = mark_px
    ts = datetime.now(UTC)
    liq_user: str | None = raw.liquidated_user or raw.liquidatedUser or None
    order_id: str | None = str(raw.lid) if raw.lid is not None else None
    return CanonicalLiquidation(
        instrument_key=instrument_key,
        venue=venue,
        timestamp=ts,
        side=side,
        price=price,
        size=size,
        order_id=order_id,
        liquidated_account_value=account_value if account_value != Decimal("0") else None,
        liquidated_ntl_pos=ntl_pos if ntl_pos != Decimal("0") else None,
        liquidated_user=liq_user,
    )


# ---------------------------------------------------------------------------
# WebSocket Connectivity
# ---------------------------------------------------------------------------


def normalize_hyperliquid_ws_subscription(
    status: str,
    channel: str = "",
    venue: str = "hyperliquid",
) -> CanonicalWebSocketLifecycle:
    """Normalize Hyperliquid WS subscription response."""
    evt = WebSocketEvent.SUBSCRIBE if status == "subscribed" else WebSocketEvent.ERROR
    return CanonicalWebSocketLifecycle(
        venue=venue,
        event=evt,
        timestamp=datetime.now(UTC),
        channel=channel or None,
    )


# ---------------------------------------------------------------------------
# Rate Limits
# ---------------------------------------------------------------------------

from ...normalize_utils.rate_limits import extract_hyperliquid_rate_limit  # noqa: E402

__all__ = [
    "extract_hyperliquid_rate_limit",
    "normalize_hyperliquid_candle",
    "normalize_hyperliquid_derivative_ticker",
    "normalize_hyperliquid_fee",
    "normalize_hyperliquid_fill",
    "normalize_hyperliquid_liquidation",
    "normalize_hyperliquid_order",
    "normalize_hyperliquid_orderbook",
    "normalize_hyperliquid_ticker",
    "normalize_hyperliquid_ws_subscription",
]
