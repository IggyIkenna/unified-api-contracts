"""FootyStats venue-specific normalizers.

FootyStatsMatch, FootyStatsOdds -> CanonicalBetMarket, CanonicalOdds, CanonicalFixture.
Uses _d, _to_decimal, _ts_ms_to_datetime from normalize_utils._helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.domain import CanonicalBetMarket, CanonicalOdds
from unified_api_contracts.canonical.domain.sports import (
    CanonicalFixture,
    CanonicalLeague,
    CanonicalTeam,
)
from unified_api_contracts.normalize_utils._helpers import _to_decimal, _ts_sec

from .schemas import FootyStatsMatch, FootyStatsOdds


def normalize_footystats_match(raw: FootyStatsMatch, venue: str = "footystats") -> CanonicalFixture:
    """Convert FootyStatsMatch to CanonicalFixture."""
    fixture_id = str(raw.match_id or "")
    kickoff_utc = _ts_sec(raw.date_unix) if raw.date_unix > 0 else datetime.now(UTC)

    home_team = CanonicalTeam(
        team_id=str(raw.home_id or ""),
        name=raw.home_name or "",
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )
    away_team = CanonicalTeam(
        team_id=str(raw.away_id or ""),
        name=raw.away_name or "",
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )

    league = CanonicalLeague(
        league_id=str(raw.competition_id or ""),
        name="",
        country="",
        league_type=None,
        logo_url=None,
    )

    return CanonicalFixture(
        fixture_id=fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        kickoff_utc=kickoff_utc,
        venue=None,
        referee=None,
        season=raw.season or "",
        match_week=raw.game_week,
        source=venue,
        status=raw.status,
        home_goals=raw.home_goals,
        away_goals=raw.away_goals,
        home_goals_halftime=None,
        away_goals_halftime=None,
        home_xg=raw.home_xg,
        away_xg=raw.away_xg,
        home_shots_on_target=None,
        away_shots_on_target=None,
        home_total_shots=raw.home_shots,
        away_total_shots=raw.away_shots,
        home_possession=raw.home_possession,
        away_possession=raw.away_possession,
        home_corners=raw.home_corners,
        away_corners=raw.away_corners,
        home_fouls=None,
        away_fouls=None,
        home_yellow_cards=None,
        away_yellow_cards=None,
        home_red_cards=None,
        away_red_cards=None,
        home_shots_blocked=None,
        away_shots_blocked=None,
        home_offsides=None,
        away_offsides=None,
        home_passes_total=None,
        away_passes_total=None,
        home_passes_accuracy=None,
        away_passes_accuracy=None,
    )


def normalize_footystats_match_to_market(raw: FootyStatsMatch, venue: str = "footystats") -> CanonicalBetMarket:
    """Convert FootyStatsMatch to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.date_unix > 0:
        close_time = _ts_sec(raw.date_unix)

    event_name = f"{raw.home_name or ''} vs {raw.away_name or ''}"

    return CanonicalBetMarket(
        venue=venue,
        market_id=str(raw.match_id or ""),
        event_id=str(raw.match_id or ""),
        market_name=event_name,
        event_name=event_name,
        sport=None,
        competition=None,
        status=raw.status,
        in_play=None,
        timestamp=now,
        close_time=close_time,
    )


def normalize_footystats_odds(
    raw: FootyStatsOdds,
    event_name: str = "",
    venue: str = "footystats",
) -> CanonicalOdds:
    """Convert FootyStatsOdds to CanonicalOdds."""
    match_id = str(raw.match_id or "")
    dec = _to_decimal(raw.odds_value)
    if dec is None or dec <= 0:
        dec = Decimal("2.0")
    selection_id = f"{match_id}:{raw.market_type or ''}:{raw.market_option or ''}".replace(" ", "_")
    return CanonicalOdds(
        venue=venue,
        event_id=match_id,
        market_id=f"{match_id}:{raw.market_type or ''}",
        selection_id=selection_id,
        selection_name=raw.market_option or "",
        decimal_odds=dec,
        timestamp=datetime.now(UTC),
        is_back=True,
        available_size=None,
        event_name=event_name,
        sport=None,
        competition=None,
    )


__all__ = [
    "normalize_footystats_match",
    "normalize_footystats_match_to_market",
    "normalize_footystats_odds",
]
