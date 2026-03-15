"""Polymarket venue-specific normalizers.

Re-exports all normalize_polymarket_* functions from normalize_utils/ modules
into a single venue-local module.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalMarketClosedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalBetMarket,
    CanonicalOrderBook,
    CanonicalTrade,
)
from unified_api_contracts.canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from unified_api_contracts.normalize_utils.errors._utils import from_http_status

from .schemas import (
    PolymarketCLOBOrder,
    PolymarketFill,
    PolymarketMarket,
    PolymarketOrderBook,
    PolymarketTrade,
)

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

_POLYMARKET_ERROR_MAP: dict[str, type[CanonicalError]] = {
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "400": CanonicalInvalidRequestError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
    "RATE_LIMIT": CanonicalRateLimitError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "MARKET_CLOSED": CanonicalMarketClosedError,
}


# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_polymarket_market(raw: PolymarketMarket, venue: str = "polymarket") -> CanonicalBetMarket:
    """Convert PolymarketMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.end_date_iso:
        try:
            close_time = datetime.fromisoformat(raw.end_date_iso.replace("Z", "+00:00"))
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            close_time = None
    status: str | None = None
    if raw.closed is True:
        status = "closed"
    elif raw.active is True:
        status = "open"
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.condition_id or "",
        event_id=raw.condition_id or "",
        market_name=raw.question or "",
        event_name=raw.question or "",
        sport=None,
        competition=None,
        status=status,
        in_play=False,
        timestamp=now,
        close_time=close_time,
    )


# ---------------------------------------------------------------------------
# Fills
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_polymarket_orderbook(
    raw: PolymarketOrderBook,
    venue: str = "polymarket",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert PolymarketOrderBook to CanonicalOrderBook.

    Polymarket bids/asks: [[price, size], ...] as float lists.
    """
    sym = symbol or raw.market or raw.asset_id or ""
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for entry in raw.bids or []:
        if len(entry) >= 2:
            with contextlib.suppress(Exception):
                bids.append((Decimal(str(entry[0])), Decimal(str(entry[1]))))
    for entry in raw.asks or []:
        if len(entry) >= 2:
            with contextlib.suppress(Exception):
                asks.append((Decimal(str(entry[0])), Decimal(str(entry[1]))))
    return CanonicalOrderBook(
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        bids=bids,
        asks=asks,
        sequence_number=None,
        levels=len(bids) or len(asks) or 1,
    )


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------


def normalize_polymarket_trade(
    raw: PolymarketTrade,
    venue: str = "polymarket",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert PolymarketTrade to CanonicalTrade.

    Polymarket CLOB: price (float), size (float), side (BUY/SELL), timestamp (ms).
    """
    sym = symbol or raw.market or raw.asset_id or "UNKNOWN"
    ts = datetime.fromtimestamp((raw.timestamp or 0) / 1000.0, tz=UTC) if raw.timestamp else datetime.now(UTC)
    side = "buy" if (raw.side or "").upper() == "BUY" else "sell"
    price = Decimal(str(raw.price or 0))
    qty = Decimal(str(raw.size or 0))
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.id or "",
        timestamp=ts,
        price=price if price > Decimal("0") else Decimal("0.000001"),
        quantity=qty if qty > Decimal("0") else Decimal("0.000001"),
        side=side,
        buyer_maker=None,
        venue_trade_id=raw.id,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_polymarket_error(
    error_code: str | int,
    message: str = "",
    venue: str = "polymarket",
) -> CanonicalError:
    """Map a Polymarket HTTP status or error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _POLYMARKET_ERROR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_polymarket_error",
    "normalize_polymarket_fill",
    "normalize_polymarket_market",
    "normalize_polymarket_order",
    "normalize_polymarket_orderbook",
    "normalize_polymarket_trade",
]
