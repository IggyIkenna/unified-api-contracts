"""API-Football venue-specific normalizers.

ApiFootballFixture, ApiFootballOdds -> CanonicalBetMarket, CanonicalOdds, CanonicalFixture.
Uses _d, _to_decimal, _ts_ms_to_datetime from normalize_utils._helpers.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from unified_api_contracts.canonical.domain import CanonicalBetMarket, CanonicalOdds
from unified_api_contracts.canonical.domain.sports import (
    CanonicalFixture,
    CanonicalLeague,
    CanonicalReferee,
    CanonicalTeam,
    CanonicalVenue,
    build_fixture_id,
    build_league_id,
    build_referee_id,
    build_season_id,
    build_team_id,
    build_venue_id,
)
from unified_api_contracts.normalize_utils._helpers import _iso, _to_decimal, _ts_ms_to_datetime

from .schemas import ApiFootballFixture, ApiFootballOdds, ApiFootballOddsValue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Boundary validation: required fields per entity type
# ---------------------------------------------------------------------------
# Fields that MUST be present for a record to be meaningful. If missing,
# the record is skipped (shard-level failure isolation — skip, don't raise).

_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "player_stats_team": frozenset({"team"}),
    "player_stats_player": frozenset({"player"}),
}


def _extract_dict(container: dict[str, object], key: str) -> dict[str, object]:
    """Safely extract a nested dict, returning empty dict for None/missing.

    API Football nests stat categories (games, shots, goals, etc.) as sub-dicts.
    A missing or None sub-dict is structurally valid — it means no data for
    that category. The empty dict allows safe ``.get()`` calls downstream.
    """
    val = container.get(key)
    if isinstance(val, dict):
        return val
    return {}


def _extract_list(container: dict[str, object], key: str) -> list[object]:
    """Safely extract a nested list, returning empty list for None/missing."""
    val = container.get(key)
    if isinstance(val, list):
        return val
    return []


def _require_str(container: dict[str, object], key: str, entity_context: str) -> str | None:
    """Extract a required string field. Returns None and logs warning if missing/empty."""
    val = container.get(key)
    if val is None or str(val).strip() == "":
        logger.warning("Missing required field %r in %s — skipping record", key, entity_context)
        return None
    return str(val)


def _extract_referee(raw: ApiFootballFixture) -> CanonicalReferee | None:
    """Extract referee from API-Football fixture response."""
    ref_name = raw.referee
    if not ref_name:
        return None
    return CanonicalReferee(
        referee_id=build_referee_id(str(ref_name)),
        name=str(ref_name),
        nationality=None,
    )


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
            status = str(raw.status.get("short") or raw.status.get("long") or "")
        else:
            status = getattr(raw.status, "short", None) or getattr(raw.status, "long", None)

    # Build human-readable fixture ID: ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322
    # Falls back to raw API-Football numeric ID if team/league names are empty
    date_str = kickoff_utc.strftime("%Y%m%d")
    canonical_fixture_id = (
        build_fixture_id(
            league_id=league.league_id,
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id,
            date_str=date_str,
        )
        if home_team.team_id and away_team.team_id
        else raw_fixture_id
    )

    # Build canonical season: YYYY/YY
    season_raw = raw.league.season if raw.league else None
    season_str = build_season_id(int(str(season_raw))) if season_raw else ""

    return CanonicalFixture(
        fixture_id=canonical_fixture_id,
        source_fixture_id=raw_fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        kickoff_utc=kickoff_utc,
        venue=venue_obj,
        referee=_extract_referee(raw),
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


def normalize_api_football_standing(raw: dict[str, object], league_id: str = "", season: str = "") -> dict[str, object]:
    """Normalize a single API-Football standing row."""
    return {"league_id": league_id, "season": season, **{k: v for k, v in raw.items() if isinstance(k, str)}}


def normalize_api_football_injury(raw: dict[str, object]) -> dict[str, object]:
    """Normalize a single API-Football injury row."""
    return dict(raw) if isinstance(raw, dict) else {}


def normalize_api_football_fixture_stats(raw: dict[str, object], fixture_id: str = "") -> dict[str, object]:
    """Normalize a single API-Football fixture stats row."""
    result = dict(raw) if isinstance(raw, dict) else {}
    result["fixture_id"] = fixture_id
    return result


def normalize_api_football_fixture_event(raw: dict[str, object], fixture_id: str = "") -> dict[str, object]:
    """Normalize a single API-Football fixture event row."""
    result = dict(raw) if isinstance(raw, dict) else {}
    result["fixture_id"] = fixture_id
    return result


def normalize_api_football_lineup(raw: dict[str, object], fixture_id: str = "") -> list[dict[str, object]]:
    """Normalize a single API-Football lineup row into player-level records."""
    result = dict(raw) if isinstance(raw, dict) else {}
    result["fixture_id"] = fixture_id
    return [result]


def _safe_int(val: object) -> int | None:
    """Parse a value to int, stripping percentage signs and other suffixes.

    API Football returns some stats as ``"44%"`` strings. This function
    handles: int, float, ``"44"``, ``"44%"``, ``None``.
    """
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    s = str(val).strip().rstrip("%").strip()
    if not s or s.lower() in ("none", "null", "-"):
        return None
    try:
        return int(float(s))
    except (ValueError, OverflowError):
        return None


_INT_STAT_FIELDS = frozenset(
    {
        "minutes_played",
        "offsides",
        "shots_total",
        "shots_on",
        "goals_total",
        "goals_conceded",
        "assists",
        "saves",
        "passes_total",
        "passes_key",
        "passes_accuracy",
        "tackles_total",
        "blocks",
        "interceptions",
        "duels_total",
        "duels_won",
        "dribbles_attempts",
        "dribbles_success",
        "dribbles_past",
        "fouls_drawn",
        "fouls_committed",
        "yellow_cards",
        "red_cards",
        "penalty_won",
        "penalty_committed",
        "penalty_scored",
        "penalty_missed",
        "penalty_saved",
    }
)


def normalize_api_football_player_stats(raw: dict[str, object], fixture_id: str = "") -> list[dict[str, object]]:
    """Normalize API-Football player statistics into per-player records.

    Handles percentage strings (``"44%"`` → ``44``) and nested stat
    structures from the API Football ``/fixtures/players`` endpoint.
    """
    if not isinstance(raw, dict):
        return []

    # API Football nests player stats under teams→players→statistics
    # The raw dict may be a team-level response or a flat player record.
    teams: list[dict[str, object]] = []
    if "team" in raw and "players" in raw:
        teams = [raw]
    elif "response" in raw:
        resp = raw["response"]
        if isinstance(resp, list):
            teams = [t for t in resp if isinstance(t, dict)]
    else:
        # Flat record — sanitise int fields and drop nested structures
        result = {k: v for k, v in raw.items() if not isinstance(v, (dict, list))}
        result["fixture_id"] = fixture_id
        for field in _INT_STAT_FIELDS:
            if field in result:
                result[field] = _safe_int(result[field])
        return [result]

    records: list[dict[str, object]] = []
    for team_block in teams:
        team_info = _extract_dict(team_block, "team")
        if not team_info:
            continue
        team_id = _require_str(team_info, "id", "player_stats.team")
        if team_id is None:
            continue
        team_name = str(team_info.get("name") or team_id)

        players = _extract_list(team_block, "players")
        if not players:
            continue

        for player_block in players:
            if not isinstance(player_block, dict):
                continue
            player_info = _extract_dict(player_block, "player")
            if not player_info:
                continue

            player_id = _require_str(player_info, "id", "player_stats.player")
            if player_id is None:
                continue
            player_name = str(player_info.get("name") or player_id)

            stats_list = _extract_list(player_block, "statistics")
            if not stats_list:
                continue

            # Merge all stat blocks (usually just one per player per fixture)
            merged: dict[str, object] = {
                "fixture_id": fixture_id,
                "team_id": team_id,
                "team_name": team_name,
                "player_id": player_id,
                "player_name": player_name,
            }

            for stat_block in stats_list:
                if not isinstance(stat_block, dict):
                    continue
                # Map API Football nested keys to flat CanonicalPlayerPerformance fields
                games = _extract_dict(stat_block, "games")
                merged["minutes_played"] = _safe_int(games.get("minutes"))
                merged["position"] = games.get("position")
                merged["rating"] = float(games.get("rating", 0) or 0) if games.get("rating") else None
                merged["captain"] = games.get("captain")
                merged["substitute"] = games.get("substitute")
                merged["offsides"] = _safe_int(games.get("offsides") or stat_block.get("offsides"))

                shots = _extract_dict(stat_block, "shots")
                merged["shots_total"] = _safe_int(shots.get("total"))
                merged["shots_on"] = _safe_int(shots.get("on"))

                goals = _extract_dict(stat_block, "goals")
                merged["goals_total"] = _safe_int(goals.get("total"))
                merged["goals_conceded"] = _safe_int(goals.get("conceded"))
                merged["assists"] = _safe_int(goals.get("assists"))
                merged["saves"] = _safe_int(goals.get("saves"))

                passes = _extract_dict(stat_block, "passes")
                merged["passes_total"] = _safe_int(passes.get("total"))
                merged["passes_key"] = _safe_int(passes.get("key"))
                merged["passes_accuracy"] = _safe_int(passes.get("accuracy"))

                tackles = _extract_dict(stat_block, "tackles")
                merged["tackles_total"] = _safe_int(tackles.get("total"))
                merged["blocks"] = _safe_int(tackles.get("blocks"))
                merged["interceptions"] = _safe_int(tackles.get("interceptions"))

                duels = _extract_dict(stat_block, "duels")
                merged["duels_total"] = _safe_int(duels.get("total"))
                merged["duels_won"] = _safe_int(duels.get("won"))

                dribbles = _extract_dict(stat_block, "dribbles")
                merged["dribbles_attempts"] = _safe_int(dribbles.get("attempts"))
                merged["dribbles_success"] = _safe_int(dribbles.get("success"))
                merged["dribbles_past"] = _safe_int(dribbles.get("past"))

                fouls = _extract_dict(stat_block, "fouls")
                merged["fouls_drawn"] = _safe_int(fouls.get("drawn"))
                merged["fouls_committed"] = _safe_int(fouls.get("committed"))

                cards = _extract_dict(stat_block, "cards")
                merged["yellow_cards"] = _safe_int(cards.get("yellow"))
                merged["red_cards"] = _safe_int(cards.get("red"))

                penalty = _extract_dict(stat_block, "penalty")
                merged["penalty_won"] = _safe_int(penalty.get("won"))
                merged["penalty_committed"] = _safe_int(penalty.get("commited"))  # API typo: "commited"
                merged["penalty_scored"] = _safe_int(penalty.get("scored"))
                merged["penalty_missed"] = _safe_int(penalty.get("missed"))
                merged["penalty_saved"] = _safe_int(penalty.get("saved"))

            records.append(merged)

    return records


__all__ = [
    "normalize_api_football_fixture",
    "normalize_api_football_fixture_event",
    "normalize_api_football_fixture_stats",
    "normalize_api_football_fixture_to_market",
    "normalize_api_football_injury",
    "normalize_api_football_lineup",
    "normalize_api_football_odds",
    "normalize_api_football_player_stats",
    "normalize_api_football_standing",
]
