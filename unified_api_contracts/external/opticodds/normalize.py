"""OpticOdds normalizers — all normalize_opticodds_* functions.

OpticOdds provides low-latency odds streaming via WebSocket and REST API.
Maps to CanonicalBetMarket and CanonicalOdds.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.canonical.domain import CanonicalBetMarket, CanonicalOdds
from unified_api_contracts.normalize_utils._helpers import _d, _to_decimal

from .schemas import OpticOddsFixture, OpticOddsMarket


def normalize_opticodds_market(raw: OpticOddsFixture, venue: str = "opticodds") -> CanonicalBetMarket:
    """Convert OpticOddsFixture to CanonicalBetMarket."""
    now = raw.start_time if raw.start_time and raw.start_time.tzinfo else datetime.now(UTC)
    if raw.start_time and raw.start_time.tzinfo is None:
        now = raw.start_time.replace(tzinfo=UTC)
    event_name = f"{raw.home_team} vs {raw.away_team}"
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.fixture_id or "",
        event_id=raw.fixture_id or "",
        market_name=event_name,
        event_name=event_name,
        sport=raw.sport or None,
        competition=raw.league or None,
        status=None,
        in_play=raw.is_live,
        timestamp=now,
        close_time=raw.start_time if raw.start_time else None,
    )


def normalize_opticodds_market_from_market(
    raw: OpticOddsMarket,
    fixture_id: str,
    event_name: str,
    sportsbook_id: str,
    sport: str | None = None,
    competition: str | None = None,
    is_live: bool = False,
    venue: str = "opticodds",
) -> CanonicalBetMarket:
    """Convert OpticOddsMarket to CanonicalBetMarket (requires fixture context)."""
    market_id = f"{fixture_id}:{sportsbook_id}:{raw.market_id}"
    return CanonicalBetMarket(
        venue=venue,
        market_id=market_id,
        event_id=fixture_id,
        market_name=f"{raw.market_type}",
        event_name=event_name,
        sport=sport,
        competition=competition,
        status=None,
        in_play=is_live,
        timestamp=datetime.now(UTC),
        close_time=None,
    )


def normalize_opticodds_odds(
    raw: OpticOddsMarket,
    fixture_id: str,
    sportsbook_id: str,
    selection: str,
    event_name: str = "",
    sport: str | None = None,
    competition: str | None = None,
    venue: str = "opticodds",
) -> CanonicalOdds | None:
    """Convert OpticOddsMarket odds field to CanonicalOdds.

    selection: one of 'home', 'draw', 'away', 'over', 'under'.
    Returns None if the selection has no odds.
    """
    sel_lower = selection.lower()
    odds_val = None
    if sel_lower == "home":
        odds_val = raw.home_odds
    elif sel_lower == "draw":
        odds_val = raw.draw_odds
    elif sel_lower == "away":
        odds_val = raw.away_odds
    elif sel_lower == "over":
        odds_val = raw.over_odds
    elif sel_lower == "under":
        odds_val = raw.under_odds
    if odds_val is None:
        return None
    dec = _to_decimal(odds_val)
    decimal_odds = dec if dec is not None else _d("2.0")
    if decimal_odds <= _d("0"):
        decimal_odds = _d("2.0")
    market_id = f"{fixture_id}:{sportsbook_id}:{raw.market_id}"
    selection_id = f"{raw.market_id}:{selection}"
    return CanonicalOdds(
        venue=venue,
        event_id=fixture_id,
        market_id=market_id,
        selection_id=selection_id,
        selection_name=selection,
        decimal_odds=decimal_odds,
        timestamp=datetime.now(UTC),
        is_back=True,
        available_size=None,
        event_name=event_name,
        sport=sport,
        competition=competition,
    )


__all__ = [
    "normalize_opticodds_market",
    "normalize_opticodds_market_from_market",
    "normalize_opticodds_odds",
]
