"""OddsJam normalizers — all normalize_oddsjam_* functions.

OddsJam provides real-time odds via REST/WebSocket API with built-in
arb/value detection. Maps to CanonicalBetMarket and CanonicalOdds.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.canonical.domain import CanonicalBetMarket, CanonicalOdds
from unified_api_contracts.normalize_utils._helpers import _d, _to_decimal

from .schemas import OddsJamGame, OddsJamMarket, OddsJamOdds


def normalize_oddsjam_market(raw: OddsJamGame, venue: str = "oddsjam") -> CanonicalBetMarket:
    """Convert OddsJamGame to CanonicalBetMarket."""
    now = datetime.now(UTC)
    if raw.start_date:
        now = raw.start_date if raw.start_date.tzinfo else raw.start_date.replace(tzinfo=UTC)
    event_name = f"{raw.home_team} vs {raw.away_team}"
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.game_id or "",
        event_id=raw.game_id or "",
        market_name=event_name,
        event_name=event_name,
        sport=raw.sport or None,
        competition=raw.league or None,
        status=None,
        in_play=raw.is_live,
        timestamp=now,
        close_time=raw.start_date if raw.start_date else None,
    )


def normalize_oddsjam_market_from_market(
    raw: OddsJamMarket,
    game_id: str,
    event_name: str,
    sport: str | None = None,
    competition: str | None = None,
    is_live: bool = False,
    venue: str = "oddsjam",
) -> CanonicalBetMarket:
    """Convert OddsJamMarket to CanonicalBetMarket (requires game context)."""
    market_id = f"{game_id}:{raw.market_name}:{raw.bet_name}"
    if raw.line is not None:
        market_id = f"{market_id}:{raw.line}"
    return CanonicalBetMarket(
        venue=venue,
        market_id=market_id,
        event_id=game_id,
        market_name=f"{raw.market_name} {raw.bet_name}",
        event_name=event_name,
        sport=sport,
        competition=competition,
        status=None,
        in_play=is_live,
        timestamp=datetime.now(UTC),
        close_time=None,
    )


def normalize_oddsjam_odds(
    raw: OddsJamOdds,
    market_id: str,
    event_id: str,
    selection_id: str,
    selection_name: str,
    event_name: str = "",
    sport: str | None = None,
    competition: str | None = None,
    venue: str = "oddsjam",
) -> CanonicalOdds:
    """Convert OddsJamOdds to CanonicalOdds."""
    dec = _to_decimal(raw.odds)
    decimal_odds = dec if dec is not None else _d("2.0")
    if decimal_odds <= _d("0"):
        decimal_odds = _d("2.0")
    return CanonicalOdds(
        venue=venue,
        event_id=event_id,
        market_id=market_id,
        selection_id=selection_id,
        selection_name=selection_name,
        decimal_odds=decimal_odds,
        timestamp=datetime.now(UTC),
        is_back=True,
        available_size=None,
        event_name=event_name,
        sport=sport,
        competition=competition,
    )


__all__ = [
    "normalize_oddsjam_market",
    "normalize_oddsjam_market_from_market",
    "normalize_oddsjam_odds",
]
