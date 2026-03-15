"""Smarkets venue-specific normalizers.

Re-exports all normalize_smarkets_* functions from normalize_utils/ modules
into a single venue-local module.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInternalServerError,
    CanonicalInvalidRequestError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalBetMarket,
    CanonicalBetOrder,
    CanonicalOrderBook,
)
from unified_api_contracts.normalize_utils.errors._utils import from_http_status

from .schemas import (
    SmarketsMarket,
    SmarketsOrderBook,
    SmarketsOrderResponse,
)

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

_SMARKETS_ERROR_MAP: dict[str, Callable[..., CanonicalError]] = {
    "unauthorized": CanonicalAuthenticationError,
    "forbidden": CanonicalAuthorizationError,
    "bad_request": CanonicalInvalidRequestError,
    "not_found": CanonicalOrderRejectedError,
    "too_many_requests": CanonicalRateLimitError,
    "service_unavailable": CanonicalServiceUnavailableError,
    "internal_server_error": CanonicalInternalServerError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_smarkets_market(raw: SmarketsMarket, venue: str = "smarkets") -> CanonicalBetMarket:
    """Convert SmarketsMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.id or "",
        event_id=raw.id or "",
        market_name=raw.name or "",
        event_name=raw.name or "",
        sport=None,
        competition=None,
        status=None,
        in_play=None,
        timestamp=now,
        close_time=None,
    )


def normalize_smarkets_order(raw: SmarketsOrderResponse, venue: str = "smarkets") -> CanonicalBetOrder:
    """Convert SmarketsOrderResponse acknowledgment to CanonicalBetOrder.

    SmarketsOrderResponse is a placement acknowledgment -- only the order ID is returned.
    Price/size/market context is not included in the response.
    """
    return CanonicalBetOrder(
        venue=venue,
        order_id=raw.id or "",
        market_id="",
        selection_id="",
        side="back",
        price=Decimal("1"),
        size=Decimal("0"),
        status="submitted",
        timestamp=datetime.now(UTC),
        matched_size=None,
        remaining_size=None,
    )


# ---------------------------------------------------------------------------
# Orderbook
# ---------------------------------------------------------------------------


def normalize_smarkets_orderbook(
    raw: SmarketsOrderBook,
    venue: str = "smarkets",
    symbol: str = "",
) -> CanonicalOrderBook:
    """Convert SmarketsOrderBook to CanonicalOrderBook.

    Smarkets backs/lays are lists of SmarketsPriceLevel (back=bid, lay=ask).
    """
    sym = symbol or (f"{raw.market_id}:{raw.runner_id}" if raw.runner_id else raw.market_id or "")
    bids: list[tuple[Decimal, Decimal]] = []
    asks: list[tuple[Decimal, Decimal]] = []
    for level in raw.backs or []:
        if level.price is not None and level.size is not None:
            bids.append((Decimal(str(level.price)), Decimal(str(level.size))))
    for level in raw.lays or []:
        if level.price is not None and level.size is not None:
            asks.append((Decimal(str(level.price)), Decimal(str(level.size))))
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
# Error
# ---------------------------------------------------------------------------


def normalize_smarkets_error(
    error_code: str | int,
    message: str = "",
    venue: str = "smarkets",
) -> CanonicalError:
    """Map a Smarkets REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _SMARKETS_ERROR_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_smarkets_error",
    "normalize_smarkets_market",
    "normalize_smarkets_order",
    "normalize_smarkets_orderbook",
]
