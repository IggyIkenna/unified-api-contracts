"""Venue-specific normalizers for FIX protocol.

Extracted from normalize_utils/ modules. Each function converts a raw FIX
schema to its canonical counterpart.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalDuplicateOrderError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInvalidRequestError,
    CanonicalMarketClosedError,
    CanonicalOrderRejectedError,
    CanonicalSizeLimitError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import CanonicalInstrument
from unified_api_contracts.canonical.domain.execution import (
    CanonicalFill,
    CanonicalOrder,
    OrderSide,
    OrderStatus,
    OrderType,
)
from unified_api_contracts.normalize_utils._helpers import (
    _order_type,
    _status,
    _tif,
)

from .schemas import (
    FixExecutionReport,
    FixMarketDataRequest,
    FixMarketDataSnapshot,
    FixNewOrderSingle,
)

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

FIX_MAP: dict[str, Callable[..., CanonicalError]] = {
    "0": CanonicalOrderRejectedError,
    "1": CanonicalOrderRejectedError,
    "3": CanonicalOrderRejectedError,
    "4": CanonicalInsufficientBalanceError,
    "5": CanonicalOrderRejectedError,
    "6": CanonicalDuplicateOrderError,
    "14": CanonicalSizeLimitError,
    "15": CanonicalInvalidRequestError,
    "8": CanonicalMarketClosedError,
    "SESSION_REJECTED": CanonicalAuthenticationError,
    "LOGON_REJECTED": CanonicalAuthenticationError,
}


# ---------------------------------------------------------------------------
# Instrument — Market Data Snapshot
# ---------------------------------------------------------------------------


def normalize_fix_market_data_snapshot(
    raw: FixMarketDataSnapshot,
    venue: str = "fix",
) -> CanonicalInstrument:
    """Normalize FixMarketDataSnapshot (Tag 35=W) to CanonicalInstrument."""
    sym = raw.symbol or ""
    ik = f"{venue.upper()}:UNKNOWN:{sym}"
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
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
# Instrument — Market Data Request
# ---------------------------------------------------------------------------


def normalize_fix_market_data_request(
    raw: FixMarketDataRequest,
    venue: str = "fix",
) -> list[CanonicalInstrument]:
    """Normalize FixMarketDataRequest (Tag 35=V) to a list of CanonicalInstrument."""
    results: list[CanonicalInstrument] = []
    for sym in raw.symbols:
        ik = f"{venue.upper()}:UNKNOWN:{sym}"
        results.append(
            CanonicalInstrument(
                instrument_key=ik,
                venue=venue,
                symbol=sym,
                timestamp=datetime.now(UTC),
                tick_size=None,
                min_size=None,
                contract_size=None,
                base_asset=None,
                quote_asset=None,
                settle_asset=None,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Order — Execution Report
# ---------------------------------------------------------------------------


def normalize_fix_execution_report_to_order(raw: FixExecutionReport, venue: str = "fix") -> CanonicalOrder:
    """Convert FixExecutionReport to CanonicalOrder (order status view)."""
    ts = raw.transact_time if raw.transact_time.tzinfo else raw.transact_time.replace(tzinfo=UTC)
    side_str = "buy" if str(raw.side) == "1" else "sell"
    return CanonicalOrder(
        order_id=raw.order_id,
        client_order_id=raw.cl_ord_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol,
        side=OrderSide.BUY if side_str == "buy" else OrderSide.SELL,
        order_type=OrderType.LIMIT if raw.avg_px else OrderType.MARKET,
        quantity=raw.order_qty,
        price=raw.avg_px if raw.avg_px else None,
        status=_status(
            {
                "0": "open",
                "A": "open",
                "1": "partially_filled",
                "2": "filled",
                "3": "filled",
                "4": "cancelled",
                "6": "cancelled",
                "8": "rejected",
                "C": "expired",
            }.get(str(raw.ord_status), "pending")
        ),
        filled_quantity=raw.cum_qty,
        remaining_quantity=raw.leaves_qty,
        average_fill_price=raw.avg_px,
    )


# ---------------------------------------------------------------------------
# Fill — Execution Report
# ---------------------------------------------------------------------------


def normalize_fix_execution_report_to_fill(raw: FixExecutionReport, venue: str = "fix") -> CanonicalFill | None:
    """Convert FixExecutionReport to CanonicalFill when last_qty/last_px present (fill event)."""
    if raw.last_qty is None or raw.last_px is None or raw.last_qty == 0:
        return None
    ts = raw.transact_time if raw.transact_time.tzinfo else raw.transact_time.replace(tzinfo=UTC)
    side_str = "buy" if str(raw.side) == "1" else "sell"
    return CanonicalFill(
        fill_id=raw.exec_id,
        order_id=raw.order_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol,
        side=OrderSide.BUY if side_str == "buy" else OrderSide.SELL,
        price=raw.last_px,
        quantity=raw.last_qty,
        fee=None,
        fee_currency=None,
        is_maker=None,
    )


# ---------------------------------------------------------------------------
# Order — New Order Single
# ---------------------------------------------------------------------------


def normalize_fix_new_order_single(raw: FixNewOrderSingle, venue: str = "fix") -> CanonicalOrder:
    """Convert FixNewOrderSingle to CanonicalOrder (submission view)."""
    ts = raw.transact_time if raw.transact_time.tzinfo else raw.transact_time.replace(tzinfo=UTC)
    side_str = "buy" if str(raw.side) == "1" else "sell"
    return CanonicalOrder(
        order_id="",
        client_order_id=raw.cl_ord_id,
        timestamp=ts,
        venue=venue,
        instrument_id=raw.symbol,
        side=OrderSide.BUY if side_str == "buy" else OrderSide.SELL,
        order_type=_order_type(
            {"1": "market", "2": "limit", "3": "stop", "4": "stop_limit"}.get(str(raw.ord_type), "limit")
        ),
        quantity=raw.order_qty,
        price=raw.price,
        time_in_force=_tif(
            {"0": "GTC", "1": "GTC", "3": "IOC", "4": "FOK", "6": "GTD"}.get(str(raw.time_in_force), "GTC")
        ),
        status=OrderStatus.PENDING,
        filled_quantity=Decimal("0"),
        remaining_quantity=raw.order_qty,
        average_fill_price=None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_fix_error(
    error_code: str | int,
    message: str = "",
    venue: str = "fix",
) -> CanonicalError:
    """Map a FIX protocol OrdRejReason or session error to a CanonicalError subclass."""
    code = str(error_code)
    cls = FIX_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_fix_error",
    "normalize_fix_execution_report_to_fill",
    "normalize_fix_execution_report_to_order",
    "normalize_fix_market_data_request",
    "normalize_fix_market_data_snapshot",
    "normalize_fix_new_order_single",
]
