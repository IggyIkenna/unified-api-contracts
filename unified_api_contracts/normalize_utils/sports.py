"""Sports and prediction market normalizers."""

from __future__ import annotations

from datetime import UTC, datetime

from ..canonical.domain import CanonicalBetMarket, CanonicalBetOrder
from ..canonical.domain.sports.betting import BetOrder, BetSide
from ..external.betfair.normalize import (
    normalize_betfair_market,
    normalize_betfair_odds,
    normalize_betfair_order,
)
from ..external.betfair.schemas import (
    BetfairMarket as BetfairSourceMarket,
)
from ..external.kalshi.normalize import (
    normalize_kalshi_market,
    normalize_kalshi_odds,
    normalize_kalshi_order,
)
from ..external.odds_api.normalize import normalize_odds_api_fixture
from ..external.onexbet.normalize import normalize_onexbet_market
from ..external.pinnacle.normalize import normalize_pinnacle_event
from ..external.polymarket.normalize import normalize_polymarket_market
from ..registry.venue_constants import SPORTS_EXCHANGE_VENUES

# ---------------------------------------------------------------------------
# Sports domain — no external venue equivalent
# ---------------------------------------------------------------------------


def normalize_sports_order(
    raw: BetOrder,
    venue: str = "sports",
    side: BetSide = BetSide.BACK,
) -> CanonicalBetOrder:
    """Convert BetOrder (sports canonical) to CanonicalBetOrder.

    BetOrder represents a bet to be placed at a bookmaker or exchange.
    requested_odds is the price; stake is the size.

    Exchange venues (Betfair, Smarkets, etc.) support both back and lay;
    bookmakers only support back.
    """
    effective_side = side if venue.upper() in SPORTS_EXCHANGE_VENUES else BetSide.BACK
    return CanonicalBetOrder(
        venue=venue or raw.bookmaker_key,
        order_id=raw.order_id,
        market_id=raw.fixture_id,
        selection_id=raw.selection,
        side=effective_side.value,
        price=raw.requested_odds,
        size=raw.stake,
        status="pending",
        timestamp=datetime.now(UTC),
        matched_size=None,
        remaining_size=None,
    )


def normalize_sports_market(raw: BetfairSourceMarket, venue: str = "betfair") -> CanonicalBetMarket:
    """Convert BetfairMarket (sports source schema) to CanonicalBetMarket.

    BetfairMarket from sports/sources/betfair is a richer local exchange schema
    with typed status, runners, and event metadata. Distinct from the external
    BetfairMarketCatalogue used by normalize_betfair_market.
    """
    close_time: datetime | None = None
    if raw.market_start_time is not None:
        if raw.market_start_time.tzinfo is None:
            close_time = raw.market_start_time.replace(tzinfo=UTC)
        else:
            close_time = raw.market_start_time
    status_str: str | None = raw.status.value if raw.status is not None else None
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.market_id,
        event_id=raw.event_id or raw.market_id,
        market_name=raw.market_name,
        event_name=raw.event_name or raw.market_name,
        sport=None,
        competition=None,
        status=status_str,
        in_play=None,
        timestamp=datetime.now(UTC),
        close_time=close_time,
    )


__all__ = [
    "normalize_betfair_market",
    "normalize_betfair_odds",
    "normalize_betfair_order",
    "normalize_kalshi_market",
    "normalize_kalshi_odds",
    "normalize_kalshi_order",
    "normalize_odds_api_fixture",
    "normalize_onexbet_market",
    "normalize_pinnacle_event",
    "normalize_polymarket_market",
    "normalize_sports_market",
    "normalize_sports_order",
]
