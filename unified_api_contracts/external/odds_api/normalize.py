"""The Odds API normalizers — OddsApiMarket, OddsApiFixture to canonical types."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ...canonical.domain import CanonicalBetMarket, CanonicalInstrument
from ...canonical.domain.sports.odds import CanonicalBookmakerMarket, OddsType, OutcomeType
from .schemas import OddsApiBookmaker, OddsApiFixture, OddsApiMarket

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

# BTTS outcomes from The Odds API use "Yes"/"No" names which map to
# OutcomeType.YES / OutcomeType.NO.
_BTTS_OUTCOME_MAP: dict[str, str] = {
    "Yes": OutcomeType.YES,
    "No": OutcomeType.NO,
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


def normalize_btts_outcomes(
    bookmaker: OddsApiBookmaker,
) -> list[CanonicalBookmakerMarket]:
    """Extract BTTS markets from a bookmaker response, mapping Yes/No outcomes.

    Returns a CanonicalBookmakerMarket for each BTTS market found in the
    bookmaker's market list. The outcome names "Yes" and "No" are normalised
    to OutcomeType.YES and OutcomeType.NO.
    """
    results: list[CanonicalBookmakerMarket] = []
    if not bookmaker.markets:
        return results
    for market in bookmaker.markets:
        if market.key != "btts":
            continue
        outcomes: dict[str, Decimal] = {}
        for outcome in market.outcomes or []:
            name = _BTTS_OUTCOME_MAP.get(outcome.name or "", outcome.name or "")
            price = Decimal(str(outcome.price)) if outcome.price is not None else Decimal("0")
            outcomes[name] = price
        results.append(
            CanonicalBookmakerMarket(
                bookmaker_key=bookmaker.key or "",
                market=OddsType.BOTH_TEAMS_SCORE,
                outcomes=outcomes,
            )
        )
    return results


__all__ = [
    "normalize_btts_outcomes",
    "normalize_odds_api_fixture",
    "normalize_odds_api_market",
]
