"""Nautilus normalizers — all normalize_nautilus_* functions.

Extracted from normalize_utils/ modules (orders_fills, instruments, errors).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from ...canonical.crosscutting.errors import (
    CanonicalError,
    CanonicalInsufficientMarginError,
    CanonicalInvalidRequestError,
    CanonicalOrderRejectedError,
    CanonicalServiceUnavailableError,
    CanonicalSizeLimitError,
    ErrorAction,
)
from ...canonical.domain import CanonicalInstrument
from ...canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
)
from ...normalize_utils._helpers import order_type, side, status
from .schemas import Fill as NautilusFill
from .schemas import Instrument as NautilusInstrument
from .schemas import Order as NautilusOrder

# ---------------------------------------------------------------------------
# Private helpers (from normalize_utils/orders_fills.py)
# ---------------------------------------------------------------------------


def _normalize_side(s: str | None) -> OrderSide:
    return side(s)


def _normalize_order_type(t: str | None) -> OrderType:
    return order_type(t)


def _normalize_order_status(s: str | None) -> OrderStatus:
    return status(s)


# ---------------------------------------------------------------------------
# Order and fill normalizers (from normalize_utils/orders_fills.py)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Instrument normalizer (from normalize_utils/instruments.py)
# ---------------------------------------------------------------------------


def normalize_nautilus_instrument(
    raw: NautilusInstrument,
    venue: str = "",
) -> CanonicalInstrument:
    """Normalize NautilusTrader Instrument to CanonicalInstrument."""
    v = venue or raw.venue or "nautilus"
    sym = raw.symbol or ""
    ik = raw.instrument_id or f"{v.upper()}:UNKNOWN:{sym}"
    return CanonicalInstrument(
        instrument_key=ik,
        venue=v,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


# ---------------------------------------------------------------------------
# Error normalizer (from normalize_utils/errors/_normalize_b.py)
# ---------------------------------------------------------------------------


NAUTILUS_MAP: dict[str, Callable[..., CanonicalError]] = {
    "ORDER_DENIED": CanonicalOrderRejectedError,
    "POSITION_NOT_FOUND": CanonicalOrderRejectedError,
    "INSUFFICIENT_MARGIN": CanonicalInsufficientMarginError,
    "ACCOUNT_NOT_FOUND": CanonicalInvalidRequestError,
    "INVALID_QUANTITY": CanonicalSizeLimitError,
    "VENUE_NOT_AVAILABLE": CanonicalServiceUnavailableError,
}


def normalize_nautilus_error(
    error_code: str | int,
    message: str = "",
    venue: str = "nautilus",
) -> CanonicalError:
    """Map a Nautilus Trader error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = NAUTILUS_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_nautilus_error",
    "normalize_nautilus_fill",
    "normalize_nautilus_instrument",
    "normalize_nautilus_order",
]
