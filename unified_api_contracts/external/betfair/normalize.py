"""Betfair venue-specific normalizers.

Re-exports all normalize_betfair_* functions from normalize_utils/ modules
into a single venue-local module.

Includes historical data mapping utilities for converting Betfair streaming
data (MCM format) to the canonical sampled schema used by the arb backtest.
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

# Direct submodule imports to avoid circular import via normalize_utils.__init__
# (normalize_utils.__init__ → sports → betfair.normalize → normalize_utils)
from unified_api_contracts.normalize_utils.errors._utils import (
    from_http_status,  # direct submodule to avoid circular import
)
from unified_api_contracts.normalize_utils.market_state import (
    normalize_market_state,  # direct submodule to avoid circular import
)

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


# ---------------------------------------------------------------------------
# Historical data mapping (MCM streaming → canonical sampled schema)
# ---------------------------------------------------------------------------

# Betfair market_type → (market_key, point).
# Point is None when it's embedded in market_type name or not applicable.
BETFAIR_MARKET_TYPE_TO_MARKET_KEY: dict[str, tuple[str, float | None]] = {
    "MATCH_ODDS": ("h2h", None),
    "OVER_UNDER_05": ("totals", 0.5),
    "OVER_UNDER_15": ("totals", 1.5),
    "OVER_UNDER_25": ("totals", 2.5),
    "OVER_UNDER_35": ("totals", 3.5),
    "OVER_UNDER_45": ("totals", 4.5),
    "OVER_UNDER_55": ("totals", 5.5),
    "OVER_UNDER_65": ("totals", 6.5),
    "OVER_UNDER_75": ("totals", 7.5),
    "OVER_UNDER_85": ("totals", 8.5),
    "BOTH_TEAMS_TO_SCORE": ("btts", None),
    # ASIAN_HANDICAP: point comes from streaming data's definition.handicap / .hc field,
    # not from the market_type name. None signals "read point from data".
    "ASIAN_HANDICAP": ("spreads", None),
}

# OddsPapi integer market_id for each market_key+point.
# Must stay in sync with oddspapi_to_sampled_fast.py MARKET_MAP.
_TOTALS_POINTS_TO_MARKET_ID: dict[float, int] = {
    0.5: 106,
    1.5: 108,
    2.5: 110,
    3.5: 112,
    4.5: 114,
    5.5: 116,
    6.5: 118,
    7.5: 120,
    8.5: 122,
}
_MARKET_KEY_TO_ID: dict[str, int] = {"h2h": 101, "btts": 104}

# Asian Handicap points → OddsPapi market_id.
# Must stay in sync with oddspapi_to_sampled_fast.py _AH list.
_AH_POINTS = [
    -6,
    -5.75,
    -5.5,
    -5.25,
    -5,
    -4.75,
    -4.5,
    -4.25,
    -4,
    -3.75,
    -3.5,
    -3.25,
    -3,
    -2.75,
    -2.5,
    -2.25,
    -2,
    -1.75,
    -1.5,
    -1.25,
    -1,
    -0.75,
    -0.5,
    -0.25,
    0,
    0.25,
    0.5,
    0.75,
    1,
    1.25,
    1.5,
    1.75,
    2,
    2.25,
    2.5,
    2.75,
    3,
    3.25,
    3.5,
    3.75,
    4,
    4.25,
    4.5,
    4.75,
    5,
    5.25,
    5.5,
    5.75,
    6,
]
_AH_POINTS_TO_MARKET_ID: dict[float, int] = {h: 1024 + i * 2 for i, h in enumerate(_AH_POINTS)}

# Canonical outcome_id (matches OddsPapi convention).
_OUTCOME_NAME_TO_ID: dict[str, int] = {
    "HOME": 101,
    "DRAW": 102,
    "AWAY": 103,
    "Yes": 104,
    "No": 105,
}


def parse_betfair_event_teams(event_name: str) -> tuple[str, str]:
    """Parse Betfair event_name into (home_team, away_team).

    Betfair format: ``"Newcastle v Sunderland"`` or ``"Team A v Team B"``.
    The separator is `` v `` (space-v-space).

    Returns:
        Tuple of (home_team, away_team). If parsing fails, returns
        (event_name, "") so callers can handle gracefully.
    """
    parts = event_name.split(" v ", maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    # Fallback: try " vs " separator
    parts = event_name.split(" vs ", maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return event_name.strip(), ""


def resolve_betfair_runner_to_outcome(
    runner_name: str,
    market_type: str,
    home_team: str = "",
    away_team: str = "",
) -> str:
    """Map a Betfair runner_name to canonical outcome_name.

    Args:
        runner_name: Runner name from Betfair streaming data.
        market_type: Betfair market type (e.g. "MATCH_ODDS", "OVER_UNDER_25").
        home_team: Home team name (from event_name parsing).
        away_team: Away team name (from event_name parsing).

    Returns:
        Canonical outcome name: "HOME", "AWAY", "DRAW", "OVER", "UNDER",
        "Yes", "No", or the raw runner_name if unmapped.
    """
    rn = runner_name.strip()
    rn_lower = rn.lower()

    # BTTS: "Yes" / "No"
    if market_type == "BOTH_TEAMS_TO_SCORE":
        if rn_lower == "yes":
            return "Yes"
        if rn_lower == "no":
            return "No"
        return rn

    # Over/Under totals: "Over X.X Goals" / "Under X.X Goals"
    if market_type.startswith("OVER_UNDER"):
        if rn_lower.startswith("over"):
            return "OVER"
        if rn_lower.startswith("under"):
            return "UNDER"
        return rn

    # MATCH_ODDS: map by team name or "The Draw"
    if market_type == "MATCH_ODDS":
        if rn_lower in ("the draw", "draw"):
            return "DRAW"
        # Match against home/away team names (case-insensitive substring)
        if home_team and _team_name_matches(rn, home_team):
            return "HOME"
        if away_team and _team_name_matches(rn, away_team):
            return "AWAY"
        return rn

    # ASIAN_HANDICAP: runner names are team names → HOME/AWAY (no draw)
    if market_type == "ASIAN_HANDICAP":
        if home_team and _team_name_matches(rn, home_team):
            return "HOME"
        if away_team and _team_name_matches(rn, away_team):
            return "AWAY"
        return rn

    return rn


def _team_name_matches(runner: str, team: str) -> bool:
    """Check if a Betfair runner name matches a team name.

    Uses case-insensitive comparison with substring matching for shortened
    Betfair names (e.g. "Newcastle" matches "Newcastle United").
    """
    r = runner.lower().strip()
    t = team.lower().strip()
    if r == t:
        return True
    # Betfair often uses shortened names: "Newcastle" for "Newcastle United"
    if r in t or t in r:
        return True
    # First-word match for multi-word names
    r_first = r.split()[0] if r else ""
    t_first = t.split()[0] if t else ""
    return bool(len(r_first) >= 4 and r_first == t_first)


def betfair_market_id_for(market_key: str, point: float | None) -> int:
    """Get the OddsPapi-compatible integer market_id for a Betfair market.

    Args:
        market_key: Canonical market key ("h2h", "totals", "btts").
        point: Point value for totals (e.g. 2.5). None for h2h/btts.

    Returns:
        Integer market_id matching OddsPapi convention, or 0 if unmapped.
    """
    if market_key == "totals" and point is not None:
        return _TOTALS_POINTS_TO_MARKET_ID.get(point, 0)
    if market_key == "spreads" and point is not None:
        return _AH_POINTS_TO_MARKET_ID.get(point, 0)
    return _MARKET_KEY_TO_ID.get(market_key, 0)


def betfair_outcome_id_for(outcome_name: str, market_key: str, point: float | None) -> int:
    """Get the OddsPapi-compatible integer outcome_id.

    Args:
        outcome_name: Canonical outcome name ("HOME", "AWAY", "DRAW", etc.).
        market_key: Market key for context.
        point: Point value for totals.

    Returns:
        Integer outcome_id matching OddsPapi convention, or 0 if unmapped.
    """
    fixed = _OUTCOME_NAME_TO_ID.get(outcome_name)
    if fixed is not None:
        return fixed
    # Totals: OVER = market_id, UNDER = market_id + 1
    if market_key == "totals" and point is not None:
        mid = _TOTALS_POINTS_TO_MARKET_ID.get(point, 0)
        if mid > 0:
            return mid if outcome_name == "OVER" else mid + 1
    # Spreads (Asian Handicap): HOME = market_id (even), AWAY = market_id + 1 (odd)
    if market_key == "spreads" and point is not None:
        mid = _AH_POINTS_TO_MARKET_ID.get(point, 0)
        if mid > 0:
            return mid if outcome_name == "HOME" else mid + 1
    return 0


__all__ = [
    "BETFAIR_MARKET_TYPE_TO_MARKET_KEY",
    "betfair_market_id_for",
    "betfair_outcome_id_for",
    "normalize_betfair_error",
    "normalize_betfair_market",
    "normalize_betfair_market_state",
    "normalize_betfair_odds",
    "normalize_betfair_order",
    "parse_betfair_event_teams",
    "resolve_betfair_runner_to_outcome",
]
