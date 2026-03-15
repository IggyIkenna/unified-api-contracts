"""SharpAPI normalizers — all normalize_sharpapi_* functions.

SharpAPI REST API — GET /odds, /odds/best, /schedule, /events.
Maps to CanonicalBetMarket and CanonicalOdds.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.canonical.domain import CanonicalBetMarket, CanonicalOdds
from unified_api_contracts.normalize_utils._helpers import _d, _to_decimal

from .schemas import SharpApiEvent, SharpApiOddsItem


def normalize_sharpapi_market(raw: SharpApiEvent, venue: str = "sharpapi") -> CanonicalBetMarket:
    """Convert SharpApiEvent to CanonicalBetMarket."""
    now = raw.start_time if raw.start_time and raw.start_time.tzinfo else datetime.now(UTC)
    if raw.start_time and raw.start_time.tzinfo is None:
        now = raw.start_time.replace(tzinfo=UTC)
    event_name = f"{raw.home_team} vs {raw.away_team}"
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.id or "",
        event_id=raw.id or "",
        market_name=event_name,
        event_name=event_name,
        sport=raw.sport or None,
        competition=None,
        status=None,
        in_play=False,
        timestamp=now,
        close_time=raw.start_time if raw.start_time else None,
    )


def normalize_sharpapi_odds(raw: SharpApiOddsItem, venue: str = "sharpapi") -> CanonicalOdds:
    """Convert SharpApiOddsItem to CanonicalOdds."""
    dec = _to_decimal(raw.odds_decimal)
    decimal_odds = dec if dec is not None else _d("2.0")
    if decimal_odds <= _d("0"):
        decimal_odds = _d("2.0")
    event_name = f"{raw.home_team} vs {raw.away_team}"
    event_id = f"{raw.sport}:{raw.home_team}:{raw.away_team}"
    market_id = f"{event_id}:{raw.market_type}:{raw.selection}:{raw.sportsbook}"
    return CanonicalOdds(
        venue=venue,
        event_id=raw.id or "",
        market_id=market_id,
        selection_id=raw.id or "",
        selection_name=raw.selection or "",
        decimal_odds=decimal_odds,
        timestamp=datetime.now(UTC),
        is_back=True,
        available_size=None,
        event_name=event_name,
        sport=raw.sport or None,
        competition=None,
    )


__all__ = [
    "normalize_sharpapi_market",
    "normalize_sharpapi_odds",
]
