"""API-Football venue-specific normalizers.

ApiFootballFixture, ApiFootballOdds -> CanonicalBetMarket, CanonicalOdds, CanonicalFixture.
Uses _d, _to_decimal, _ts_ms_to_datetime from normalize_utils._helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.canonical.domain import CanonicalBetMarket, CanonicalOdds
from unified_api_contracts.canonical.domain.sports import (
    CanonicalFixture,
    CanonicalLeague,
    CanonicalTeam,
    CanonicalVenue,
    build_fixture_id,
    build_league_id,
    build_season_id,
    build_team_id,
    build_venue_id,
)
from unified_api_contracts.normalize_utils._helpers import _iso, _to_decimal, _ts_ms_to_datetime

from .schemas import ApiFootballFixture, ApiFootballOdds, ApiFootballOddsValue


def normalize_api_football_fixture(raw: ApiFootballFixture, venue: str = "api_football") -> CanonicalFixture:
    """Convert ApiFootballFixture to CanonicalFixture.

    Uses canonical ID builders for human-readable IDs:
      - league_id: build_league_id(country, name) → "ENG_PREMIER_LEAGUE"
      - team_id: build_team_id(name) → "ARSENAL"
      - fixture_id: build_fixture_id(league, home, away, date) → "ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322"
    """
    raw_fixture_id = str(raw.id or "")
    kickoff_utc: datetime
    if raw.date:
        kickoff_utc = _iso(raw.date)
    elif raw.timestamp is not None and raw.timestamp > 0:
        kickoff_utc = _ts_ms_to_datetime(raw.timestamp * 1000)
    else:
        kickoff_utc = datetime.now(UTC)

    home_team = CanonicalTeam(
        team_id="", name="", short_name=None, country=None, founded=None, logo_url=None, venue=None
    )
    away_team = CanonicalTeam(
        team_id="", name="", short_name=None, country=None, founded=None, logo_url=None, venue=None
    )
    if raw.teams:
        home_raw = raw.teams.get("home")
        away_raw = raw.teams.get("away")
        if home_raw:
            home_team = CanonicalTeam(
                team_id=build_team_id(home_raw.name or ""),
                name=home_raw.name or "",
                short_name=home_raw.code,
                country=home_raw.country,
                founded=None,
                logo_url=home_raw.logo,
                venue=None,
            )
        if away_raw:
            away_team = CanonicalTeam(
                team_id=build_team_id(away_raw.name or ""),
                name=away_raw.name or "",
                short_name=away_raw.code,
                country=away_raw.country,
                founded=None,
                logo_url=away_raw.logo,
                venue=None,
            )

    league = CanonicalLeague(league_id="", name="", country="", league_type=None, logo_url=None)
    if raw.league:
        league = CanonicalLeague(
            league_id=build_league_id(raw.league.country or "", raw.league.name or ""),
            name=raw.league.name or "",
            country=raw.league.country or "",
            league_type=raw.league.type,
            logo_url=raw.league.logo,
        )

    venue_obj: CanonicalVenue | None = None
    if raw.venue and isinstance(raw.venue, dict):
        v = raw.venue
        _city = v.get("city")
        _country = v.get("country")
        _vname = str(v.get("name") or "")
        venue_obj = CanonicalVenue(
            venue_id=build_venue_id(_vname) if _vname else "",
            name=_vname,
            city=str(_city) if _city is not None else None,
            country=str(_country) if _country is not None else None,
            capacity=None,
            surface=None,
            latitude=None,
            longitude=None,
            altitude=None,
        )
    elif hasattr(raw.venue, "id") and raw.venue is not None:
        v = raw.venue
        _vname2 = getattr(v, "name", "") or ""
        venue_obj = CanonicalVenue(
            venue_id=build_venue_id(_vname2) if _vname2 else "",
            name=_vname2,
            city=getattr(v, "city", None),
            country=getattr(v, "country", None) if hasattr(v, "country") else None,
            capacity=None,
            surface=None,
            latitude=None,
            longitude=None,
            altitude=None,
        )

    home_goals = raw.goals.get("home") if raw.goals and isinstance(raw.goals, dict) else None
    away_goals = raw.goals.get("away") if raw.goals and isinstance(raw.goals, dict) else None
    home_ht_int: int | None = None
    away_ht_int: int | None = None
    if raw.score and isinstance(raw.score, dict):
        ht = raw.score.get("halftime")
        if isinstance(ht, dict):
            h = ht.get("home")
            a = ht.get("away")
            home_ht_int = int(h) if h is not None and isinstance(h, (int, float)) else None
            away_ht_int = int(a) if a is not None and isinstance(a, (int, float)) else None
    elif hasattr(raw.score, "halftime") and raw.score and raw.score.halftime:
        home_ht_int = raw.score.halftime.home
        away_ht_int = raw.score.halftime.away

    status: str | None = None
    if raw.status:
        if isinstance(raw.status, dict):
            status = str(raw.status.get("long") or raw.status.get("short") or "")
        else:
            status = getattr(raw.status, "long", None) or getattr(raw.status, "short", None)

    # Build human-readable fixture ID: ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322
    # Falls back to raw API-Football numeric ID if team/league names are empty
    date_str = kickoff_utc.strftime("%Y%m%d")
    canonical_fixture_id = build_fixture_id(
        league_id=league.league_id,
        home_team_id=home_team.team_id,
        away_team_id=away_team.team_id,
        date_str=date_str,
    ) if home_team.team_id and away_team.team_id else raw_fixture_id

    # Build canonical season: YYYY/YY
    season_raw = raw.league.season if raw.league else None
    season_str = build_season_id(int(str(season_raw))) if season_raw else ""

    return CanonicalFixture(
        fixture_id=canonical_fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        kickoff_utc=kickoff_utc,
        venue=venue_obj,
        referee=None,
        season=season_str,
        match_week=None,
        source=venue,
        status=status,
        home_goals=home_goals,
        away_goals=away_goals,
        home_goals_halftime=home_ht_int,
        away_goals_halftime=away_ht_int,
        home_xg=None,
        away_xg=None,
        home_shots_on_target=None,
        away_shots_on_target=None,
        home_total_shots=None,
        away_total_shots=None,
        home_possession=None,
        away_possession=None,
        home_corners=None,
        away_corners=None,
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


def normalize_api_football_fixture_to_market(
    raw: ApiFootballFixture, venue: str = "api_football"
) -> CanonicalBetMarket:
    """Convert ApiFootballFixture to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.date:
        close_time = _iso(raw.date)
    elif raw.timestamp is not None and raw.timestamp > 0:
        close_time = _ts_ms_to_datetime(raw.timestamp * 1000)

    event_name = ""
    if raw.teams:
        home = raw.teams.get("home")
        away = raw.teams.get("away")
        if home and away:
            event_name = f"{home.name or ''} vs {away.name or ''}"
        elif home:
            event_name = home.name or ""
        elif away:
            event_name = away.name or ""

    sport = raw.league.name if raw.league else None
    competition = raw.league.name if raw.league else None

    return CanonicalBetMarket(
        venue=venue,
        market_id=str(raw.id or ""),
        event_id=str(raw.id or ""),
        market_name=event_name,
        event_name=event_name,
        sport=sport,
        competition=competition,
        status=None,
        in_play=None,
        timestamp=now,
        close_time=close_time,
    )


def _normalize_api_football_odds_value(
    val: ApiFootballOddsValue,
    fixture_id: str,
    market_id: str,
    market_name: str,
    bookmaker_name: str,
    event_name: str = "",
    venue: str = "api_football",
) -> CanonicalOdds | None:
    """Convert a single ApiFootballOddsValue to CanonicalOdds."""
    odd_str = val.odd if val.odd else None
    dec = _to_decimal(odd_str) if odd_str else None
    if dec is None or dec <= 0:
        return None
    selection_name = val.value or ""
    selection_id = f"{fixture_id}:{market_id}:{selection_name}".replace(" ", "_")
    return CanonicalOdds(
        venue=venue,
        event_id=fixture_id,
        market_id=market_id,
        selection_id=selection_id,
        selection_name=selection_name,
        decimal_odds=dec,
        timestamp=datetime.now(UTC),
        is_back=True,
        available_size=None,
        event_name=event_name,
        sport=None,
        competition=None,
    )


def normalize_api_football_odds(
    raw: ApiFootballOdds,
    event_name: str = "",
    venue: str = "api_football",
) -> list[CanonicalOdds]:
    """Convert ApiFootballOdds to list of CanonicalOdds.

    Iterates over all bets and values, yielding one CanonicalOdds per selection.
    """
    fixture_id = str(raw.fixture_id or "")
    out: list[CanonicalOdds] = []
    if not raw.bets:
        return out
    for bet in raw.bets:
        market_id = f"{fixture_id}:{bet.name or bet.id or 'unknown'}"
        market_name = bet.name or ""
        if not bet.values:
            continue
        for val in bet.values:
            if val.suspended:
                continue
            co = _normalize_api_football_odds_value(val, fixture_id, market_id, market_name, "", event_name, venue)
            if co is not None:
                out.append(co)
    return out


__all__ = [
    "normalize_api_football_fixture",
    "normalize_api_football_fixture_to_market",
    "normalize_api_football_odds",
]
