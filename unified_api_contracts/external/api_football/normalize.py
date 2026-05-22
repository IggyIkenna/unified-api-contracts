"""API-Football venue-specific normalizers.

ApiFootballFixture, ApiFootballOdds -> CanonicalBetMarket, CanonicalOdds, CanonicalFixture.
Uses _d, _to_decimal, _ts_ms_to_datetime from normalize_utils._helpers.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import cast

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
from unified_api_contracts.normalize_utils._helpers import iso, to_decimal, ts_ms_to_datetime

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
        return cast(dict[str, object], val)
    return {}


def _extract_list(container: dict[str, object], key: str) -> list[object]:
    """Safely extract a nested list, returning empty list for None/missing."""
    val = container.get(key)
    if isinstance(val, list):
        return cast(list[object], val)
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
        kickoff_utc = iso(raw.date)
    elif raw.timestamp is not None and raw.timestamp > 0:
        kickoff_utc = ts_ms_to_datetime(raw.timestamp * 1000)
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

    home_goals: int | None = None
    away_goals: int | None = None
    if raw.goals:
        home_goals = raw.goals.home
        away_goals = raw.goals.away
    home_ht_int: int | None = None
    away_ht_int: int | None = None
    if raw.score and isinstance(raw.score, dict):
        ht = cast(dict[str, object] | None, raw.score.get("halftime"))
        if ht is not None:
            home_ht_int = cast(int | None, ht.get("home"))
            away_ht_int = cast(int | None, ht.get("away"))
    elif raw.score and not isinstance(raw.score, dict) and raw.score.halftime:
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
        announced_at=kickoff_utc - timedelta(days=7),
    )


def normalize_api_football_fixture_to_market(
    raw: ApiFootballFixture, venue: str = "api_football"
) -> CanonicalBetMarket:
    """Convert ApiFootballFixture to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.date:
        close_time = iso(raw.date)
    elif raw.timestamp is not None and raw.timestamp > 0:
        close_time = ts_ms_to_datetime(raw.timestamp * 1000)

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
    dec = to_decimal(odd_str) if odd_str else None
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


def normalize_api_football_standing(
    raw: dict[str, object] | None, league_id: str = "", season: str = ""
) -> dict[str, object]:
    """Flatten a single API-Football standing row to a flat dict.

    Raw API-Football payload has nested team / all / home / away structs.
    PyArrow flattens these inconsistently or silently drops the nested array,
    so we surface every useful field at the top level (same pattern as
    ``normalize_api_football_injury``).

    See ``codex/02-data/match-end-time-cascade.md`` neighbouring docs for the
    motivation: nested-struct columns are a wide spot for silent data loss.
    """
    if raw is None:
        return {"league_id": league_id, "season": season}

    team = _extract_dict(raw, "team")
    all_stats = _extract_dict(raw, "all")
    home_stats = _extract_dict(raw, "home")
    away_stats = _extract_dict(raw, "away")
    all_goals = _extract_dict(all_stats, "goals")
    home_goals = _extract_dict(home_stats, "goals")
    away_goals = _extract_dict(away_stats, "goals")

    return {
        "rank": _safe_int(raw.get("rank")),
        "team_id": _safe_int(team.get("id")),
        "team_name": team.get("name"),
        "team_logo": team.get("logo"),
        "points": _safe_int(raw.get("points")),
        "goals_diff": _safe_int(raw.get("goalsDiff")),
        "group": raw.get("group"),
        "form": raw.get("form"),
        "status": raw.get("status"),
        "description": raw.get("description"),
        "all_played": _safe_int(all_stats.get("played")),
        "all_win": _safe_int(all_stats.get("win")),
        "all_draw": _safe_int(all_stats.get("draw")),
        "all_lose": _safe_int(all_stats.get("lose")),
        "all_goals_for": _safe_int(all_goals.get("for")),
        "all_goals_against": _safe_int(all_goals.get("against")),
        "home_played": _safe_int(home_stats.get("played")),
        "home_win": _safe_int(home_stats.get("win")),
        "home_draw": _safe_int(home_stats.get("draw")),
        "home_lose": _safe_int(home_stats.get("lose")),
        "home_goals_for": _safe_int(home_goals.get("for")),
        "home_goals_against": _safe_int(home_goals.get("against")),
        "away_played": _safe_int(away_stats.get("played")),
        "away_win": _safe_int(away_stats.get("win")),
        "away_draw": _safe_int(away_stats.get("draw")),
        "away_lose": _safe_int(away_stats.get("lose")),
        "away_goals_for": _safe_int(away_goals.get("for")),
        "away_goals_against": _safe_int(away_goals.get("against")),
        "update": raw.get("update"),
        "league_id": league_id,
        "season": season,
    }


def normalize_api_football_injury(raw: dict[str, object] | None) -> dict[str, object]:
    """Flatten a single API-Football ``/injuries`` row into a flat dict.

    The raw shape has 4 nested struct columns (``player`` / ``team`` /
    ``fixture`` / ``league``). We surface every useful field at the top
    level so downstream readers don't need pyarrow struct accessors.

    Returns a single dict (one injury report = one row).
    """
    if raw is None:
        return {}
    player = _extract_dict(raw, "player")
    team = _extract_dict(raw, "team")
    fixture = _extract_dict(raw, "fixture")
    league = _extract_dict(raw, "league")
    out: dict[str, object] = {
        "player_id": _safe_int(player.get("id")),
        "player_name": player.get("name"),
        "player_photo": player.get("photo"),
        "player_type": player.get("type"),
        "player_reason": player.get("reason"),
        "team_id": _safe_int(team.get("id")),
        "team_name": team.get("name"),
        "fixture_id": _safe_int(fixture.get("id")),
        "league_id": _safe_int(league.get("id")),
        "league_season": _safe_int(league.get("season")),
    }
    return out


def _safe_pct(val: object) -> int | None:
    """Parse a percentage value to int 0..100.

    Handles ``"44%"``, ``"44"``, ``44``, ``44.0``, ``None``. Returns
    ``None`` when the value is missing / unparseable / sentinel.
    """
    return _safe_int(val)


def _safe_float(val: object) -> float | None:
    """Parse a numeric value to float, accepting strings + percent suffix."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().rstrip("%").strip()
    if not s or s.lower() in ("none", "null", "-"):
        return None
    try:
        return float(s)
    except (ValueError, OverflowError):
        return None


# Closed-set mapping of API-Football statistic ``type`` strings to the flat
# column name we expose on the parquet. Values to the right are the
# canonical column names in SPORTS_FIXTURE_STATS. Each is paired with a
# parser — _safe_int for counts, _safe_pct for percentages, _safe_float
# for xG / goals_prevented.
_FIXTURE_STAT_TYPE_MAP: dict[str, tuple[str, str]] = {
    "Shots on Goal": ("shots_on_target", "int"),
    "Shots off Goal": ("shots_off_target", "int"),
    "Total Shots": ("shots_total", "int"),
    "Blocked Shots": ("shots_blocked", "int"),
    "Shots insidebox": ("shots_inside_box", "int"),
    "Shots outsidebox": ("shots_outside_box", "int"),
    "Fouls": ("fouls", "int"),
    "Corner Kicks": ("corners", "int"),
    "Offsides": ("offsides", "int"),
    "Ball Possession": ("ball_possession_pct", "pct"),
    "Yellow Cards": ("yellow_cards", "int"),
    "Red Cards": ("red_cards", "int"),
    "Goalkeeper Saves": ("goalkeeper_saves", "int"),
    "Total passes": ("passes_total", "int"),
    "Passes accurate": ("passes_accurate", "int"),
    "Passes %": ("passes_pct", "pct"),
    "expected_goals": ("expected_goals", "float"),
    "goals_prevented": ("goals_prevented", "float"),
}


def normalize_api_football_fixture_stats(raw: dict[str, object], fixture_id: str = "") -> list[dict[str, object]]:
    """Flatten a single API-Football ``/fixtures/statistics`` team-stats row.

    Each call covers ONE team's stat block — the API returns a list of
    {team, statistics: [{type, value}, ...]} rows, two per fixture (home,
    away). Caller chains the results across the list.

    Returns a list of length 1 (one row per team) with explicit columns
    per the closed `_FIXTURE_STAT_TYPE_MAP`. ``team_id`` is stamped from
    the nested team struct; ``is_home`` is left to the caller (we cannot
    determine home/away without the fixture context).

    Returns ``[]`` if the row shape is malformed.
    """
    team = _extract_dict(raw, "team")
    stats_list = _extract_list(raw, "statistics")

    row: dict[str, object] = {
        "fixture_id": fixture_id,
        "team_id": _safe_int(team.get("id")),
        "team_name": team.get("name"),
        "is_home": None,  # Caller stamps based on (raw.team.id == fixture.teams.home.id).
    }

    # Pre-populate every known stat column with None so the parquet has
    # a stable schema even when a stat type is absent for a fixture.
    for _typ, (col_name, _kind) in _FIXTURE_STAT_TYPE_MAP.items():
        if col_name not in row:
            row[col_name] = None

    for stat in stats_list:
        if not isinstance(stat, dict):
            continue
        stat_d = cast(dict[str, object], stat)
        stat_type = cast(str | None, stat_d.get("type"))
        stat_value = stat_d.get("value")
        if not isinstance(stat_type, str):
            continue
        mapping = _FIXTURE_STAT_TYPE_MAP.get(stat_type)
        if mapping is None:
            # Unknown stat type — skip silently. New types added by the
            # provider get picked up the next time we extend the map.
            continue
        col_name, kind = mapping
        if kind == "int":
            row[col_name] = _safe_int(stat_value)
        elif kind == "pct":
            row[col_name] = _safe_pct(stat_value)
        else:  # "float"
            row[col_name] = _safe_float(stat_value)

    return [row]


def normalize_api_football_fixture_event(raw: dict[str, object], fixture_id: str = "") -> list[dict[str, object]]:
    """Flatten one API-Football ``/fixtures/events`` row into one event row.

    Each call covers a single event (goal / card / sub / VAR) with nested
    ``time``, ``team``, ``player``, ``assist`` structs. We surface every
    useful field at the top level.

    Returns a list of length 1 (one event = one row); returns ``[]`` for
    malformed input. List-shape preserves caller symmetry with
    ``normalize_api_football_fixture_stats`` and
    ``normalize_api_football_lineup`` so the orchestrator can use a
    uniform ``chain.from_iterable`` regardless of normalizer.
    """
    time_block = _extract_dict(raw, "time")
    team = _extract_dict(raw, "team")
    player = _extract_dict(raw, "player")
    assist = _extract_dict(raw, "assist")

    row: dict[str, object] = {
        "fixture_id": fixture_id,
        "time_elapsed": _safe_int(time_block.get("elapsed")),
        "time_extra": _safe_int(time_block.get("extra")),
        "team_id": _safe_int(team.get("id")),
        "team_name": team.get("name"),
        "player_id": _safe_int(player.get("id")),
        "player_name": player.get("name"),
        "assist_id": _safe_int(assist.get("id")) if assist else None,
        "assist_name": assist.get("name") if assist else None,
        "event_type": raw.get("type"),
        "event_detail": raw.get("detail"),
        "comments": raw.get("comments"),
    }
    return [row]


def normalize_api_football_lineup(raw: dict[str, object], fixture_id: str = "") -> list[dict[str, object]]:
    """Flatten one API-Football ``/fixtures/lineups`` team block into rows.

    Each call covers ONE team's lineup with nested ``startXI`` (11 starters),
    ``substitutes`` (~7 bench players), ``coach``, and ``formation``. We
    explode to one row per (team, player) — coach NOT emitted as a row by
    default (would mix grain). ``is_starter`` distinguishes starters from
    subs.

    Returns a list of length ~18 (11 starters + 7 subs); returns ``[]``
    for malformed input.
    """
    team = _extract_dict(raw, "team")
    coach = _extract_dict(raw, "coach")
    formation = raw.get("formation")
    start_xi = _extract_list(raw, "startXI")
    substitutes = _extract_list(raw, "substitutes")

    team_id = _safe_int(team.get("id"))
    team_name = team.get("name")
    coach_id = _safe_int(coach.get("id")) if coach else None
    coach_name = coach.get("name") if coach else None

    rows: list[dict[str, object]] = []

    def _emit(entry: object, is_starter: bool) -> None:
        # API-Football wraps each player block as {"player": {id, name, number, pos, grid}}.
        if not isinstance(entry, dict):
            return
        player = _extract_dict(cast(dict[str, object], entry), "player")
        if not player:
            return
        rows.append(
            {
                "fixture_id": fixture_id,
                "team_id": team_id,
                "team_name": team_name,
                "formation": formation,
                "coach_id": coach_id,
                "coach_name": coach_name,
                "player_id": _safe_int(player.get("id")),
                "player_name": player.get("name"),
                "player_number": _safe_int(player.get("number")),
                "player_pos": player.get("pos"),
                "player_grid": player.get("grid"),
                "is_starter": is_starter,
            }
        )

    for entry in start_xi:
        _emit(entry, is_starter=True)
    for entry in substitutes:
        _emit(entry, is_starter=False)

    return rows


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
    # API Football nests player stats under teams→players→statistics
    # The raw dict may be a team-level response or a flat player record.
    teams: list[dict[str, object]] = []
    if "team" in raw and "players" in raw:
        teams = [raw]
    elif "response" in raw:
        resp = raw["response"]
        if isinstance(resp, list):
            teams = [cast(dict[str, object], t) for t in cast(list[object], resp) if isinstance(t, dict)]
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
            player_block_d = cast(dict[str, object], player_block)
            player_info = _extract_dict(player_block_d, "player")
            if not player_info:
                continue

            player_id = _require_str(player_info, "id", "player_stats.player")
            if player_id is None:
                continue
            player_name = str(player_info.get("name") or player_id)

            stats_list = _extract_list(player_block_d, "statistics")
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
                stat_block_d = cast(dict[str, object], stat_block)
                # Map API Football nested keys to flat CanonicalPlayerPerformance fields
                games = _extract_dict(stat_block_d, "games")
                merged["minutes_played"] = _safe_int(games.get("minutes"))
                merged["position"] = games.get("position")
                merged["rating"] = _safe_float(games.get("rating"))
                merged["captain"] = games.get("captain")
                merged["substitute"] = games.get("substitute")
                merged["offsides"] = _safe_int(games.get("offsides") or stat_block_d.get("offsides"))

                shots = _extract_dict(stat_block_d, "shots")
                merged["shots_total"] = _safe_int(shots.get("total"))
                merged["shots_on"] = _safe_int(shots.get("on"))

                goals = _extract_dict(stat_block_d, "goals")
                merged["goals_total"] = _safe_int(goals.get("total"))
                merged["goals_conceded"] = _safe_int(goals.get("conceded"))
                merged["assists"] = _safe_int(goals.get("assists"))
                merged["saves"] = _safe_int(goals.get("saves"))

                passes = _extract_dict(stat_block_d, "passes")
                merged["passes_total"] = _safe_int(passes.get("total"))
                merged["passes_key"] = _safe_int(passes.get("key"))
                merged["passes_accuracy"] = _safe_int(passes.get("accuracy"))

                tackles = _extract_dict(stat_block_d, "tackles")
                merged["tackles_total"] = _safe_int(tackles.get("total"))
                merged["blocks"] = _safe_int(tackles.get("blocks"))
                merged["interceptions"] = _safe_int(tackles.get("interceptions"))

                duels = _extract_dict(stat_block_d, "duels")
                merged["duels_total"] = _safe_int(duels.get("total"))
                merged["duels_won"] = _safe_int(duels.get("won"))

                dribbles = _extract_dict(stat_block_d, "dribbles")
                merged["dribbles_attempts"] = _safe_int(dribbles.get("attempts"))
                merged["dribbles_success"] = _safe_int(dribbles.get("success"))
                merged["dribbles_past"] = _safe_int(dribbles.get("past"))

                fouls = _extract_dict(stat_block_d, "fouls")
                merged["fouls_drawn"] = _safe_int(fouls.get("drawn"))
                merged["fouls_committed"] = _safe_int(fouls.get("committed"))

                cards = _extract_dict(stat_block_d, "cards")
                merged["yellow_cards"] = _safe_int(cards.get("yellow"))
                merged["red_cards"] = _safe_int(cards.get("red"))

                penalty = _extract_dict(stat_block_d, "penalty")
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
