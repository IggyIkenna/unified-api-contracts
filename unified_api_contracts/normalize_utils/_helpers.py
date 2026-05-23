"""Shared conversion utilities for normalize_utils.

Centralises helpers that were duplicated across tickers.py, orderbooks.py,
cefi_extended.py, cefi_extended2.py, orders_fills.py, and ohlcv.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ..canonical.domain.execution import OrderSide, OrderStatus, OrderType, TimeInForce

# ---------------------------------------------------------------------------
# Decimal conversion
# ---------------------------------------------------------------------------


def _to_decimal(val: Decimal | float | str | None) -> Decimal | None:
    """Convert a numeric-ish value to Decimal; return None on failure or None input."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _d(val: str | float | int | Decimal | None) -> Decimal:
    """Parse a value to Decimal; returns Decimal('0') for None."""
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------


def _ts_ms_to_datetime(ts_ms: int | None) -> datetime:
    """Convert millisecond timestamp (int) to UTC datetime.

    Returns current UTC time when ts_ms is None or non-positive.
    """
    if ts_ms is not None and ts_ms > 0:
        return datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
    return datetime.now(UTC)


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


# ---------------------------------------------------------------------------
# Orderbook level parsing
# ---------------------------------------------------------------------------


def _to_levels(
    rows: list[list[str | float]] | list[list[str]] | list[list[float]],
) -> list[tuple[Decimal, Decimal]]:
    """Convert [[price, size], ...] to [(Decimal, Decimal), ...]."""
    out: list[tuple[Decimal, Decimal]] = []
    for row in rows:
        if len(row) >= 2:
            out.append((Decimal(str(row[0])), Decimal(str(row[1]))))
    return out


# ---------------------------------------------------------------------------
# Databento fixed-point price conversion
# ---------------------------------------------------------------------------


def _databento_price(px: int) -> Decimal:
    """Databento fixed-point price (divide by 1e9)."""
    return Decimal(px) / Decimal("1e9")


# ---------------------------------------------------------------------------
# Order/execution helpers (used by cefi_extended, orders_fills)
# ---------------------------------------------------------------------------


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


# Public aliases for cross-module use (avoids reportPrivateUsage when importing)
to_decimal = _to_decimal
to_levels = _to_levels
ts_ms_to_datetime = _ts_ms_to_datetime
ts_ms = _ts_ms
d = _d
unix_sec_to_utc = _ts_sec
iso = _iso
side = _side
order_type = _order_type
status = _status
tif = _tif
databento_price = _databento_price

__all__ = [
    "_d",
    "_databento_price",
    "_iso",
    "_order_type",
    "_side",
    "_status",
    "_tif",
    "_to_decimal",
    "_to_levels",
    "_ts_ms",
    "_ts_ms_to_datetime",
    "_ts_sec",
    "d",
    "databento_price",
    "iso",
    "order_type",
    "side",
    "status",
    "tif",
    "to_decimal",
    "to_levels",
    "ts_ms",
    "ts_ms_to_datetime",
    "unix_sec_to_utc",
]
