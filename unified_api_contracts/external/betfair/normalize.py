"""Betfair venue-specific normalizers.

Re-exports all normalize_betfair_* functions from normalize_utils/ modules
into a single venue-local module.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalAuthenticationError,
    CanonicalAuthorizationError,
    CanonicalError,
    CanonicalInsufficientBalanceError,
    CanonicalInvalidRequestError,
    CanonicalMarketClosedError,
    CanonicalRateLimitError,
    CanonicalServiceUnavailableError,
    CanonicalSizeLimitError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalBetMarket,
    CanonicalBetOrder,
    CanonicalMarketStateEvent,
    CanonicalOdds,
    MarketState,
)
from unified_api_contracts.normalize_utils.errors._utils import from_http_status
from unified_api_contracts.normalize_utils.market_state import normalize_market_state

from .schemas import (
    BetfairCurrentOrderSummary,
    BetfairMarketCatalogue,
    BetfairRunner,
)

# ---------------------------------------------------------------------------
# Error map
# ---------------------------------------------------------------------------

_BETFAIR_ERROR_MAP: dict[str, Callable[..., CanonicalError]] = {
    "TOO_MANY_REQUESTS": CanonicalRateLimitError,
    "ANGX-0001": CanonicalRateLimitError,  # Exceeded throttle limit
    "INVALID_SESSION_INFORMATION": CanonicalAuthenticationError,
    "NO_APP_KEY": CanonicalAuthenticationError,
    "INVALID_APP_KEY": CanonicalAuthenticationError,
    "SERVICE_BUSY": CanonicalServiceUnavailableError,
    "TIMEOUT_ERROR": CanonicalServiceUnavailableError,
    "MARKET_CLOSED": CanonicalMarketClosedError,
    "MARKET_SUSPENDED": CanonicalMarketClosedError,
    "INSUFFICIENT_FUNDS": CanonicalInsufficientBalanceError,
    "INVALID_BET_SIZE": CanonicalSizeLimitError,
    "BET_OUTSIDE_PRICE_BOUNDS": CanonicalInvalidRequestError,
    "INVALID_PROFIT_RATIO": CanonicalInvalidRequestError,
    "429": CanonicalRateLimitError,
    "401": CanonicalAuthenticationError,
    "403": CanonicalAuthorizationError,
}

# ---------------------------------------------------------------------------
# Market state map
# ---------------------------------------------------------------------------

_BETFAIR_STATUS_MAP: dict[str, MarketState] = {
    "INACTIVE": MarketState.PRE_MARKET,
    "OPEN": MarketState.NORMAL,
    "SUSPENDED": MarketState.HALTED,
    "CLOSED": MarketState.CLOSED,
}


# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_betfair_market(raw: BetfairMarketCatalogue, venue: str = "betfair") -> CanonicalBetMarket:
    """Convert BetfairMarketCatalogue to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.market_start_time:
        try:
            close_time = datetime.fromisoformat(raw.market_start_time.replace("Z", "+00:00"))
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            close_time = None
    sport: str | None = None
    if raw.event_type is not None:
        sport = raw.event_type.name
    competition: str | None = None
    if raw.competition is not None:
        competition = raw.competition.name
    event_name: str = ""
    if raw.event is not None and raw.event.name:
        event_name = raw.event.name
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.market_id or "",
        event_id=(raw.event.id if raw.event and raw.event.id else raw.market_id) or "",
        market_name=raw.market_name or "",
        event_name=event_name,
        sport=sport,
        competition=competition,
        status=None,
        in_play=None,
        timestamp=now,
        close_time=close_time,
    )


def normalize_betfair_odds(
    raw: BetfairRunner,
    market_id: str,
    event_name: str = "",
    venue: str = "betfair",
) -> CanonicalOdds:
    """Convert BetfairRunner to CanonicalOdds (back side, best available price).

    BetfairRunner.ex contains availableToBack and availableToLay lists of {price, size}.
    last_price_traded is the last matched price (already decimal format).
    """
    now = datetime.now(UTC)
    decimal_odds = Decimal("2.0")  # default fallback
    available_size: Decimal | None = None

    ex = raw.ex
    if isinstance(ex, dict):
        back_list = ex.get("availableToBack")
        if isinstance(back_list, list) and back_list:
            first_back = back_list[0]
            price_val = first_back.get("price")
            size_val = first_back.get("size")
            if price_val is not None:
                decimal_odds = Decimal(str(price_val))
            if size_val is not None:
                available_size = Decimal(str(size_val))

    if decimal_odds <= Decimal("1.0") and raw.last_price_traded is not None:
        decimal_odds = Decimal(str(raw.last_price_traded))

    return CanonicalOdds(
        venue=venue,
        event_id=market_id,
        market_id=market_id,
        selection_id=str(raw.selection_id or ""),
        selection_name="",
        decimal_odds=decimal_odds,
        timestamp=now,
        is_back=True,
        available_size=available_size,
        event_name=event_name,
        sport=None,
        competition=None,
    )


def normalize_betfair_order(
    raw: BetfairCurrentOrderSummary,
    venue: str = "betfair",
) -> CanonicalBetOrder:
    """Convert BetfairCurrentOrderSummary to CanonicalBetOrder.

    BetfairCurrentOrderSummary comes from listCurrentOrders REST endpoint.
    side: "B" (back) or "L" (lay).
    price/size from priceSize field.
    """
    side = "back" if (raw.side or "B").upper() == "B" else "lay"
    price = Decimal(str(raw.price_size.price or 1)) if raw.price_size is not None else Decimal("1")
    size = Decimal(str(raw.price_size.size or 0)) if raw.price_size is not None else Decimal("0")
    size_matched = Decimal(str(raw.size_matched or 0))
    ts = datetime.now(UTC)
    if raw.placed_date:
        with contextlib.suppress(ValueError, TypeError):
            ts = datetime.fromisoformat(raw.placed_date.replace("Z", "+00:00"))
    return CanonicalBetOrder(
        venue=venue,
        order_id=raw.bet_id or "",
        market_id=raw.market_id or "",
        selection_id=str(raw.selection_id or ""),
        side=side,
        price=price,
        size=size,
        status=(raw.status or "unknown").lower(),
        timestamp=ts,
        matched_size=size_matched if size_matched > Decimal("0") else None,
        remaining_size=None,
    )


# ---------------------------------------------------------------------------
# Market state
# ---------------------------------------------------------------------------


def normalize_betfair_market_state(
    status: str,
    market_id: str,
    previous_state: MarketState | None = None,
    reason: str | None = None,
    timestamp: datetime | None = None,
    venue: str = "betfair",
) -> CanonicalMarketStateEvent:
    """Normalize a Betfair market status to CanonicalMarketStateEvent.

    Betfair market status: INACTIVE | OPEN | SUSPENDED | CLOSED.

    Args:
        status:    Market status.
        market_id: Betfair market ID (e.g. 1.234567).
        previous_state: Previous state.
        reason:    Suspension or closure reason.
        timestamp: Event time.
        venue:     Venue tag.
    """
    ik = f"{venue}:MARKET:{market_id}"
    return normalize_market_state(
        raw_state=status,
        venue=venue,
        instrument_key=ik,
        state_map=_BETFAIR_STATUS_MAP,
        previous_state=previous_state,
        reason=reason,
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_betfair_error(
    error_code: str | int,
    message: str = "",
    venue: str = "betfair",
) -> CanonicalError:
    """Map a Betfair JSON-RPC or HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    cls = _BETFAIR_ERROR_MAP.get(code)
    if cls is not None:
        return cls(message=message or cls.__name__, venue=venue)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_betfair_error",
    "normalize_betfair_market",
    "normalize_betfair_market_state",
    "normalize_betfair_odds",
    "normalize_betfair_order",
]
