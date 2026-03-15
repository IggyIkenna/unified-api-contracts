"""Betdaq venue-specific normalizers.

Re-exports all normalize_betdaq_* functions from normalize_utils/ modules
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
    CanonicalInsufficientBalanceError,
    CanonicalInternalServerError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    CanonicalSizeLimitError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalBetMarket,
    CanonicalBetOrder,
)
from unified_api_contracts.normalize_utils.errors._utils import from_http_status

from .schemas import BetdaqMarket, BetdaqOrder

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

_BETDAQ_ERROR_MAP: dict[str, Callable[..., CanonicalError]] = {
    "40": CanonicalInsufficientBalanceError,  # InsufficientFunds
    "41": CanonicalSizeLimitError,  # BelowMinimumStake
    "42": CanonicalSizeLimitError,  # AboveMaximumStake
    "1001": CanonicalRateLimitError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
    "503": CanonicalServiceUnavailableError,
}


# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_betdaq_market(raw: BetdaqMarket, venue: str = "betdaq") -> CanonicalBetMarket:
    """Convert BetdaqMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    return CanonicalBetMarket(
        venue=venue,
        market_id=str(raw.id or ""),
        event_id=str(raw.id or ""),
        market_name=raw.name or "",
        event_name=raw.name or "",
        sport=None,
        competition=None,
        status=None,
        in_play=None,
        timestamp=now,
        close_time=None,
    )


def normalize_betdaq_order(raw: BetdaqOrder, venue: str = "betdaq") -> CanonicalBetOrder:
    """Convert BetdaqOrder confirmation to CanonicalBetOrder.

    BetdaqOrder is a placement acknowledgment receipt -- only order ID and result code
    are returned by the API. Price/size/market context is not included.
    result == 0 means accepted; result == -1 means rejected.
    """
    status = "accepted" if raw.result >= 0 else "rejected"
    return CanonicalBetOrder(
        venue=venue,
        order_id=str(raw.id or ""),
        market_id="",
        selection_id="",
        side="back",
        price=Decimal("1"),
        size=Decimal("0"),
        status=status,
        timestamp=datetime.now(UTC),
        matched_size=None,
        remaining_size=None,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_betdaq_error(
    error_code: str | int,
    message: str = "",
    venue: str = "betdaq",
) -> CanonicalError:
    """Map a Betdaq SOAP/REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BETDAQ_ERROR_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_betdaq_error",
    "normalize_betdaq_market",
    "normalize_betdaq_order",
]
