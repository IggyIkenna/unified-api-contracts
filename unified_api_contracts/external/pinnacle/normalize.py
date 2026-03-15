"""Pinnacle venue-specific normalizers.

Re-exports all normalize_pinnacle_* functions from normalize_utils/ modules
into a single venue-local module.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalDuplicateOrderError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInternalServerError,
    CanonicalMarketClosedError,
    CanonicalOrderRejectedError,
    CanonicalRateLimitError,
    CanonicalSizeLimitError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import CanonicalBetMarket
from unified_api_contracts.normalize_utils.errors._utils import from_http_status

from .schemas import PinnacleEvent

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

_PINNACLE_ERROR_MAP: dict[str, Callable[..., CanonicalError]] = {
    "ACCOUNT_PROBLEM": CanonicalAuthorizationError,
    "ABOVE_MAX_BET_AMOUNT": CanonicalSizeLimitError,
    "BELOW_MIN_BET_AMOUNT": CanonicalSizeLimitError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "LINE_CHANGED": CanonicalOrderRejectedError,
    "ODDS_CHANGED": CanonicalOrderRejectedError,
    "PAST_CUTOFFTIME": CanonicalMarketClosedError,
    "DUPLICATE_UNIQUE_REQUEST_ID": CanonicalDuplicateOrderError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
    "500": CanonicalInternalServerError,
}


# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_pinnacle_event(raw: PinnacleEvent, venue: str = "pinnacle") -> CanonicalBetMarket:
    """Convert PinnacleEvent to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.starts:
        try:
            close_time = datetime.fromisoformat(raw.starts.replace("Z", "+00:00"))
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            close_time = None
    event_name = ""
    if raw.home and raw.away:
        event_name = f"{raw.home} vs {raw.away}"
    elif raw.home:
        event_name = raw.home
    return CanonicalBetMarket(
        venue=venue,
        market_id=str(raw.id or ""),
        event_id=str(raw.id or ""),
        market_name=event_name,
        event_name=event_name,
        sport=None,
        competition=None,
        status=raw.status,
        in_play=None,
        timestamp=now,
        close_time=close_time,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_pinnacle_error(
    error_code: str | int,
    message: str = "",
    venue: str = "pinnacle",
) -> CanonicalError:
    """Map a Pinnacle REST error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _PINNACLE_ERROR_MAP.get(code)
    if cls is not None:
        return cls(message=message or code, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_pinnacle_error",
    "normalize_pinnacle_event",
]
