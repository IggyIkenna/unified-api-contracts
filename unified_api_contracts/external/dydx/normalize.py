"""Venue-specific normalizers for dYdX.

Extracted from normalize_utils/ modules. Each function converts a raw dYdX
schema to its canonical counterpart.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalDuplicateOrderError,
    CanonicalError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import CanonicalInstrument, CanonicalOrderBook, CanonicalTrade
from unified_api_contracts.canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
)
from unified_api_contracts.normalize_utils._helpers import (
    _d,
    _iso,
    _order_type,
    _side,
    _status,
    _tif,
)
from unified_api_contracts.normalize_utils.errors._utils import from_http_status

from .schemas import (
    DydxFill,
    DydxOrder,
    DydxOrderBook,
    DydxPerpetualMarket,
    DydxTrade,
)

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

DYDX_MAP: dict[str, Callable[..., CanonicalError]] = {
    "INVALID_ARGUMENT": CanonicalInvalidRequestError,
    "NOT_FOUND": CanonicalOrderRejectedError,
    "ALREADY_EXISTS": CanonicalDuplicateOrderError,
    "PERMISSION_DENIED": CanonicalAuthorizationError,
    "UNAUTHENTICATED": CanonicalAuthenticationError,
    "RESOURCE_EXHAUSTED": CanonicalRateLimitError,
    "INTERNAL": CanonicalInternalServerError,
    "UNAVAILABLE": CanonicalServiceUnavailableError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def normalize_dydx_trade(raw: DydxTrade, symbol: str = "", venue: str = "dydx") -> CanonicalTrade:
    """Convert DydxTrade to CanonicalTrade."""
    ts = _iso(raw.createdAt)
    trade_id = str(raw.id) if raw.id else ""
    sym = symbol or "UNKNOWN"
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=trade_id,
        timestamp=ts,
        price=_d(raw.price),
        quantity=_d(raw.size),
        side="buy" if (raw.side or "BUY").upper() == "BUY" else "sell",
        buyer_maker=None,
        venue_trade_id=trade_id or None,
    )


# ---------------------------------------------------------------------------
# Order Book
# ---------------------------------------------------------------------------


def normalize_dydx_orderbook(raw: DydxOrderBook, symbol: str = "", venue: str = "dydx") -> CanonicalOrderBook:
    """Convert DydxOrderBook to CanonicalOrderBook."""
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


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def normalize_dydx_order(raw: DydxOrder, venue: str = "dydx") -> CanonicalOrder:
    """Convert DydxOrder to CanonicalOrder."""
    ts = _iso(raw.createdAt)
    return CanonicalOrder(
        order_id=str(raw.id or ""),
        client_order_id=raw.clientId,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.market or "",
        side=_side(raw.side),
        order_type=_order_type(raw.type),
        quantity=_d(raw.size),
        price=_d(raw.price) if raw.price else None,
        time_in_force=_tif(raw.timeInForce),
        status=_status(raw.status),
        filled_quantity=_d(raw.totalFilled),
        remaining_quantity=_d(raw.remainingSize) if raw.remainingSize else None,
        average_fill_price=None,
    )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


def normalize_dydx_fill(raw: DydxFill, venue: str = "dydx") -> CanonicalFill:
    """Convert DydxFill to CanonicalFill."""
    ts = _iso(raw.createdAt)
    is_maker: bool | None = None
    if raw.liquidity:
        is_maker = raw.liquidity.upper() == "MAKER"
    return CanonicalFill(
        fill_id=str(raw.id or ""),
        order_id=str(raw.orderId or ""),
        timestamp=ts,
        venue=venue,
        instrument_id=raw.market or "",
        side=_side(raw.side),
        price=_d(raw.price),
        quantity=_d(raw.size),
        fee=_d(raw.fee) if raw.fee else None,
        fee_currency=None,
        is_maker=is_maker,
    )


# ---------------------------------------------------------------------------
# Instrument
# ---------------------------------------------------------------------------


def normalize_dydx_perpetual_market(
    raw: DydxPerpetualMarket,
    venue: str = "dydx",
) -> CanonicalInstrument:
    """Normalize DydxPerpetualMarket to CanonicalInstrument."""
    sym = raw.market or ""
    ik = f"{venue.upper()}:PERP:{sym}"
    tick_size: float | None = None
    if raw.tickSize is not None:
        with contextlib.suppress(ValueError, TypeError):
            tick_size = float(raw.tickSize)
    min_size: float | None = None
    if raw.stepSize is not None:
        with contextlib.suppress(ValueError, TypeError):
            min_size = float(raw.stepSize)
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=tick_size,
        min_size=min_size,
        contract_size=None,
        base_asset=raw.baseAsset,
        quote_asset=raw.quoteAsset,
        settle_asset=None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_dydx_error(
    error_code: str | int,
    message: str = "",
    venue: str = "dydx",
) -> CanonicalError:
    """Map a dYdX v4 gRPC/HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = DYDX_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_dydx_error",
    "normalize_dydx_fill",
    "normalize_dydx_order",
    "normalize_dydx_orderbook",
    "normalize_dydx_perpetual_market",
    "normalize_dydx_trade",
]
