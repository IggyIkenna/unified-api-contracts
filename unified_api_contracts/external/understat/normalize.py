"""Understat normalizers — sports reference domain.

Converts Understat* schemas to CanonicalFixture, CanonicalTeam, CanonicalLeague,
CanonicalPlayer, CanonicalFeatureRecord using normalize_utils._helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from unified_api_contracts.canonical.domain import (
    CanonicalFeatureRecord,
    CanonicalFixture,
    CanonicalLeague,
    CanonicalPlayer,
    CanonicalTeam,
)
from unified_api_contracts.canonical.domain.features import FeatureMetadata

from .schemas import (
    UnderstatMatch,
    UnderstatMatchSource,
    UnderstatMatchTeam,
    UnderstatPlayer,
    UnderstatShot,
    UnderstatTeam,
    USMatchRaw,
    USPlayerRaw,
    USPlayerSeasonRaw,
)


def _parse_iso(s: str | None) -> datetime:
    """Parse ISO 8601 timestamp string to UTC datetime."""
    if not s:
        return datetime.now(UTC)
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.now(UTC)


def _safe_str(val: object) -> str:
    return str(val) if val is not None else ""


def _extract_team(raw: UnderstatMatchTeam | dict[str, object] | None) -> CanonicalTeam:
    """Extract CanonicalTeam from UnderstatMatchTeam or dict."""
    if raw is None:
        return CanonicalTeam(
            team_id="", name="", short_name=None, country=None, founded=None, logo_url=None, venue=None
        )
    if isinstance(raw, dict):
        tid = raw.get("id")
        nm = raw.get("title") or raw.get("name")
        short = raw.get("short_title")
        return CanonicalTeam(
            team_id=str(tid) if tid is not None else "",
            name=str(nm) if nm is not None else "",
            short_name=str(short) if short is not None else None,
            country=None,
            founded=None,
            logo_url=None,
            venue=None,
        )
    return CanonicalTeam(
        team_id=_safe_str(raw.id),
        name=_safe_str(raw.title or raw.short_title),
        short_name=_safe_str(raw.short_title) if raw.short_title else None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )


def normalize_understat_league(
    raw: UnderstatTeam,
    league_name: str,
    season: str,
    venue: str = "understat",
) -> CanonicalLeague:
    """Build CanonicalLeague from Understat context (league_name/season)."""
    return CanonicalLeague(
        league_id=_safe_str(league_name),
        name=league_name,
        country="unknown",
        league_type=None,
        logo_url=None,
    )


def normalize_understat_team(
    raw: UnderstatTeam,
    venue: str = "understat",
) -> CanonicalTeam:
    """Convert UnderstatTeam to CanonicalTeam."""
    return CanonicalTeam(
        team_id=_safe_str(raw.id),
        name=_safe_str(raw.title or raw.short_title),
        short_name=_safe_str(raw.short_title) or None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )


def normalize_understat_player(
    raw: UnderstatPlayer | USPlayerRaw | USPlayerSeasonRaw,
    venue: str = "understat",
) -> CanonicalPlayer:
    """Convert UnderstatPlayer or USPlayerRaw/USPlayerSeasonRaw to CanonicalPlayer."""
    player_id: str | int | None = getattr(raw, "id", None) or getattr(raw, "us_player_id", None)
    name_raw = getattr(raw, "player_name", None) or getattr(raw, "team_name", None)
    if name_raw is not None and "USPlayer" in type(raw).__name__:
        name_raw = None
    name = cast(str | None, name_raw)
    return CanonicalPlayer(
        player_id=_safe_str(player_id),
        name=name or "",
        first_name=None,
        last_name=None,
        nationality=None,
        position=getattr(raw, "position", None),
        date_of_birth=None,
        height_cm=None,
        weight_kg=None,
    )


def normalize_understat_fixture(
    raw: UnderstatMatch | UnderstatMatchSource | USMatchRaw,
    league_name: str = "",
    season: str = "",
    venue: str = "understat",
) -> CanonicalFixture:
    """Convert UnderstatMatch, UnderstatMatchSource or USMatchRaw to CanonicalFixture."""
    if isinstance(raw, UnderstatMatchSource):
        home_team = CanonicalTeam(
            team_id=_safe_str(raw.home_team_id),
            name=_safe_str(raw.home_team_name),
            short_name=None,
            country=None,
            founded=None,
            logo_url=None,
            venue=None,
        )
        away_team = CanonicalTeam(
            team_id=_safe_str(raw.away_team_id),
            name=_safe_str(raw.away_team_name),
            short_name=None,
            country=None,
            founded=None,
            logo_url=None,
            venue=None,
        )
        fixture_id = str(raw.fixture_id)
        kickoff = raw.date if raw.date.tzinfo else raw.date.replace(tzinfo=UTC)
        home_goals = raw.home_goals
        away_goals = raw.away_goals
        home_xg = raw.home_xg
        away_xg = raw.away_xg
        league = CanonicalLeague(
            league_id=_safe_str(league_name) or raw.league,
            name=league_name or str(raw.league),
            country="unknown",
            league_type=None,
            logo_url=None,
        )
        season_val = str(raw.season) if raw.season else season
    elif isinstance(raw, USMatchRaw):
        home_team = CanonicalTeam(
            team_id="",
            name=_safe_str(raw.home_team),
            short_name=None,
            country=None,
            founded=None,
            logo_url=None,
            venue=None,
        )
        away_team = CanonicalTeam(
            team_id="",
            name=_safe_str(raw.away_team),
            short_name=None,
            country=None,
            founded=None,
            logo_url=None,
            venue=None,
        )
        fixture_id = str(raw.us_fixture_id)
        kickoff = datetime.now(UTC)
        home_goals = raw.home_goals
        away_goals = raw.away_goals
        home_xg = raw.home_xg
        away_xg = raw.away_xg
        league = CanonicalLeague(
            league_id=_safe_str(raw.league),
            name=_safe_str(raw.league),
            country="unknown",
            league_type=None,
            logo_url=None,
        )
        season_val = _safe_str(raw.season)
    else:
        h = raw.h
        a = raw.a
        home_team = _extract_team(h)
        away_team = _extract_team(a)
        fixture_id = _safe_str(raw.id)
        kickoff = _parse_iso(raw.datetime) if raw.datetime else datetime.now(UTC)
        home_goals = raw.goals_h
        away_goals = raw.goals_a
        home_xg = raw.xg_h
        away_xg = raw.xg_a
        league = CanonicalLeague(
            league_id=league_name or "unknown",
            name=league_name or "unknown",
            country="unknown",
            league_type=None,
            logo_url=None,
        )
        season_val = season

    return CanonicalFixture(
        fixture_id=fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        kickoff_utc=kickoff,
        venue=None,
        referee=None,
        season=season_val,
        match_week=None,
        source=venue,
        status=None,
        home_goals=home_goals,
        away_goals=away_goals,
        home_goals_halftime=None,
        away_goals_halftime=None,
        home_xg=float(home_xg) if home_xg is not None else None,
        away_xg=float(away_xg) if away_xg is not None else None,
    )


def normalize_understat_feature_record(
    raw: UnderstatShot,
    venue: str = "understat",
) -> CanonicalFeatureRecord:
    """Convert UnderstatShot (xG per shot) to CanonicalFeatureRecord."""
    now = datetime.now(UTC).isoformat()
    xg = float(raw.xg) if raw.xg is not None else 0.0
    return CanonicalFeatureRecord(
        feature_name="shot_xg",
        value=xg,
        timestamp=now,
        metadata=FeatureMetadata(
            name="shot_xg",
            version="1.0",
            source=venue,
            domain="sports",
        ),
    )


__all__ = [
    "normalize_understat_feature_record",
    "normalize_understat_fixture",
    "normalize_understat_league",
    "normalize_understat_player",
    "normalize_understat_team",
]
