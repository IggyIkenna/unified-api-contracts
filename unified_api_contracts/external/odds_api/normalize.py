"""The Odds API normalizers — OddsApiMarket, OddsApiFixture to canonical types."""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain import CanonicalBetMarket, CanonicalInstrument
from ...canonical.domain.sports.odds import OddsType
from .schemas import OddsApiFixture, OddsApiMarket

_MARKET_KEY_MAP: dict[str, OddsType] = {
    "h2h": OddsType.H2H,
    "spreads": OddsType.ASIAN_HANDICAP,
    "totals": OddsType.OVER_UNDER,
    "btts": OddsType.BOTH_TEAMS_SCORE,
    "draw_no_bet": OddsType.DRAW_NO_BET,
    "double_chance": OddsType.DOUBLE_CHANCE,
    "outrights": OddsType.OUTRIGHT,
    "correct_score": OddsType.CORRECT_SCORE,
}


def normalize_odds_api_market(
    raw: OddsApiMarket,
    venue: str = "odds_api",
) -> CanonicalInstrument:
    """Normalize OddsApiMarket to CanonicalInstrument."""
    sym = raw.key or ""
    ik = f"{venue.upper()}:MARKET:{sym}"
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
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


__all__ = [
    "normalize_odds_api_fixture",
    "normalize_odds_api_market",
]
