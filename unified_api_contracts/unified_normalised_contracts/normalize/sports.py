"""Sports and prediction market normalizers."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from decimal import Decimal

from ...unified_api_contracts_external.betdaq.schemas import BetdaqMarket, BetdaqOrder
from ...unified_api_contracts_external.betfair.schemas import (
    BetfairCurrentOrderSummary,
    BetfairMarketCatalogue,
    BetfairRunner,
)
from ...unified_api_contracts_external.kalshi.schemas import KalshiMarket, KalshiOrder
from ...unified_api_contracts_external.manifold.schemas import ManifoldMarket
from ...unified_api_contracts_external.odds_api.schemas import OddsApiFixture
from ...unified_api_contracts_external.onexbet.schemas import OneXBetMarket
from ...unified_api_contracts_external.pinnacle.schemas import PinnacleEvent
from ...unified_api_contracts_external.polymarket.schemas import PolymarketMarket
from ...unified_api_contracts_external.smarkets.schemas import SmarketsMarket, SmarketsOrderResponse
from ...unified_api_contracts_external.sports.canonical.betting import BetOrder
from ...unified_api_contracts_external.sports.sources.betfair.schemas import (
    BetfairMarket as BetfairSourceMarket,
)
from ..domain import CanonicalBetMarket, CanonicalBetOrder, CanonicalOdds


def normalize_kalshi_market(raw: KalshiMarket, venue: str = "kalshi") -> CanonicalBetMarket:
    """Convert KalshiMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.close_time:
        try:
            close_time = datetime.fromisoformat(raw.close_time.replace("Z", "+00:00"))
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            close_time = None
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.ticker or "",
        event_id=raw.event_ticker or "",
        market_name=raw.title or raw.subtitle or "",
        event_name=raw.event_ticker or "",
        sport=None,
        competition=None,
        status=raw.status,
        in_play=False,  # Kalshi is pre-event only
        timestamp=now,
        close_time=close_time,
    )


def normalize_kalshi_odds(raw: KalshiMarket, is_yes: bool = True, venue: str = "kalshi") -> CanonicalOdds:
    """Convert KalshiMarket to CanonicalOdds.

    yes_bid/yes_ask/no_bid/no_ask are string fixed-point dollars (e.g. "0.4500").
    Integer cent fields (yes_bid, yes_ask) are deprecated as of March 5, 2026.
    Converts probability to decimal odds: decimal = 1 / probability.
    """
    now = datetime.now(UTC)
    # Prefer string fixed-point fields; fall back to deprecated integer cent fields
    if is_yes:
        price_str = raw.yes_bid_dollars or raw.yes_ask_dollars
        if price_str is None and raw.yes_bid is not None:
            price_str = str(raw.yes_bid / 100)
        elif price_str is None and raw.yes_ask is not None:
            price_str = str(raw.yes_ask / 100)
        selection_name = "Yes"
        selection_id = f"{raw.ticker or ''}-yes"
    else:
        price_str = raw.no_bid_dollars or raw.no_ask_dollars
        if price_str is None and raw.no_bid is not None:
            price_str = str(raw.no_bid / 100)
        elif price_str is None and raw.no_ask is not None:
            price_str = str(raw.no_ask / 100)
        selection_name = "No"
        selection_id = f"{raw.ticker or ''}-no"

    prob = float(price_str) if price_str else 0.5
    # Clamp probability to avoid division by zero or absurd odds
    prob = max(0.01, min(0.99, prob))
    decimal_odds = Decimal(str(round(1.0 / prob, 6)))

    return CanonicalOdds(
        venue=venue,
        event_id=raw.event_ticker or "",
        market_id=raw.ticker or "",
        selection_id=selection_id,
        selection_name=selection_name,
        decimal_odds=decimal_odds,
        timestamp=now,
        is_back=True,
        available_size=None,
        event_name=raw.event_ticker or "",
        sport=None,
        competition=None,
    )


def normalize_polymarket_market(raw: PolymarketMarket, venue: str = "polymarket") -> CanonicalBetMarket:
    """Convert PolymarketMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.end_date_iso:
        try:
            close_time = datetime.fromisoformat(raw.end_date_iso.replace("Z", "+00:00"))
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            close_time = None
    status: str | None = None
    if raw.closed is True:
        status = "closed"
    elif raw.active is True:
        status = "open"
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.condition_id or "",
        event_id=raw.condition_id or "",
        market_name=raw.question or "",
        event_name=raw.question or "",
        sport=None,
        competition=None,
        status=status,
        in_play=False,
        timestamp=now,
        close_time=close_time,
    )


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


def normalize_odds_api_fixture(raw: OddsApiFixture, venue: str = "odds_api") -> CanonicalBetMarket:
    """Convert OddsApiFixture to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.commence_time:
        try:
            close_time = datetime.fromisoformat(raw.commence_time.replace("Z", "+00:00"))
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            close_time = None
    event_name = ""
    if raw.home_team and raw.away_team:
        event_name = f"{raw.home_team} vs {raw.away_team}"
    elif raw.home_team:
        event_name = raw.home_team
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.id or "",
        event_id=raw.id or "",
        market_name=event_name,
        event_name=event_name,
        sport=raw.sport_key,
        competition=raw.sport_title,
        status=None,
        in_play=None,
        timestamp=now,
        close_time=close_time,
    )


def normalize_manifold_market(raw: ManifoldMarket, venue: str = "manifold") -> CanonicalBetMarket:
    """Convert ManifoldMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.close_time is not None:
        try:
            close_time = datetime.fromtimestamp(raw.close_time / 1000.0, tz=UTC)
        except (ValueError, TypeError, OSError):
            close_time = None
    status: str | None = None
    if raw.resolution is not None:
        status = "closed"
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.id or "",
        event_id=raw.id or "",
        market_name=raw.question or "",
        event_name=raw.question or "",
        sport=None,
        competition=None,
        status=status,
        in_play=False,
        timestamp=now,
        close_time=close_time,
    )


def normalize_manifold_odds(raw: ManifoldMarket, venue: str = "manifold") -> CanonicalOdds:
    """Convert ManifoldMarket to CanonicalOdds.

    probability is 0.0-1.0, converted to decimal odds: decimal = 1 / probability.
    """
    now = datetime.now(UTC)
    prob = float(raw.probability or 0.5)
    # Clamp probability to avoid division by zero or absurd odds
    prob = max(0.01, min(0.99, prob))
    decimal_odds = Decimal(str(round(1.0 / prob, 6)))
    return CanonicalOdds(
        venue=venue,
        event_id=raw.id or "",
        market_id=raw.id or "",
        selection_id=f"{raw.id or ''}-yes",
        selection_name="Yes",
        decimal_odds=decimal_odds,
        timestamp=now,
        is_back=True,
        available_size=None,
        event_name=raw.question or "",
        sport=None,
        competition=None,
    )


def normalize_kalshi_order(raw: KalshiOrder, venue: str = "kalshi") -> CanonicalBetOrder:
    """Convert KalshiOrder to CanonicalBetOrder."""
    now = datetime.now(UTC)
    ts = now
    if raw.created_time:
        try:
            ts = datetime.fromisoformat(raw.created_time.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            ts = now
    # Kalshi side is "yes" or "no"; action is "buy" or "sell"
    # For CanonicalBetOrder, side is "back" (buy yes) or "lay" (sell yes / buy no)
    side = "back"
    if raw.action == "sell" or raw.side == "no":
        side = "lay"
    # Price: Kalshi uses integer cent fields (deprecated) — use yes_price in cents
    price = Decimal("0.5")
    if raw.yes_price is not None:
        price = Decimal(str(raw.yes_price / 100))
    elif raw.no_price is not None:
        # no price in cents, yes price = 1 - no_price/100
        price = Decimal(str(1 - raw.no_price / 100))
    # Convert implied probability to decimal odds
    prob = float(price)
    prob = max(0.01, min(0.99, prob))
    decimal_odds = Decimal(str(round(1.0 / prob, 6)))

    size = Decimal(str(raw.count or 0))
    remaining = Decimal(str(raw.remaining_count or 0)) if raw.remaining_count is not None else None
    matched = size - remaining if remaining is not None else None

    return CanonicalBetOrder(
        venue=venue,
        order_id=raw.order_id or "",
        market_id=raw.ticker or "",
        selection_id=f"{raw.ticker or ''}-{raw.side or 'yes'}",
        side=side,
        price=decimal_odds,
        size=size,
        status=raw.status or "unknown",
        timestamp=ts,
        matched_size=matched,
        remaining_size=remaining,
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


def normalize_sports_order(
    raw: BetOrder,
    venue: str = "sports",
) -> CanonicalBetOrder:
    """Convert BetOrder (sports canonical) to CanonicalBetOrder.

    BetOrder represents a bet to be placed at a bookmaker or exchange.
    requested_odds is the price; stake is the size.
    """
    # Convert decimal odds to implied probability for consistency
    return CanonicalBetOrder(
        venue=venue or raw.bookmaker_key,
        order_id=raw.order_id,
        market_id=raw.fixture_id,
        selection_id=raw.selection,
        side="back",  # sports bets are always backing
        price=raw.requested_odds,
        size=raw.stake,
        status="pending",
        timestamp=datetime.now(UTC),
        matched_size=None,
        remaining_size=None,
    )


def normalize_betdaq_order(raw: BetdaqOrder, venue: str = "betdaq") -> CanonicalBetOrder:
    """Convert BetdaqOrder confirmation to CanonicalBetOrder.

    BetdaqOrder is a placement acknowledgment receipt — only order ID and result code
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


def normalize_onexbet_market(raw: OneXBetMarket, venue: str = "onexbet") -> CanonicalBetMarket:
    """Convert OneXBetMarket to CanonicalBetMarket.

    OneXBetMarket has a name and a list of outcomes (selections); no distinct market ID is
    provided by the API, so the name is used as market_id.
    """
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.name or "",
        event_id=raw.name or "",
        market_name=raw.name or "",
        event_name=raw.name or "",
        sport=None,
        competition=None,
        status=None,
        in_play=None,
        timestamp=datetime.now(UTC),
        close_time=None,
    )


def normalize_smarkets_order(raw: SmarketsOrderResponse, venue: str = "smarkets") -> CanonicalBetOrder:
    """Convert SmarketsOrderResponse acknowledgment to CanonicalBetOrder.

    SmarketsOrderResponse is a placement acknowledgment — only the order ID is returned.
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
    "normalize_betdaq_market",
    "normalize_betdaq_order",
    "normalize_betfair_market",
    "normalize_betfair_odds",
    "normalize_betfair_order",
    "normalize_kalshi_market",
    "normalize_kalshi_odds",
    "normalize_kalshi_order",
    "normalize_manifold_market",
    "normalize_manifold_odds",
    "normalize_odds_api_fixture",
    "normalize_onexbet_market",
    "normalize_pinnacle_event",
    "normalize_polymarket_market",
    "normalize_smarkets_market",
    "normalize_smarkets_order",
    "normalize_sports_market",
    "normalize_sports_order",
]
