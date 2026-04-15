"""Soccer-Football-Info normalizers — sports reference domain.

Converts SFI* schemas to CanonicalFixture, CanonicalTeam, CanonicalLeague,
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
    CanonicalReferee,
    CanonicalTeam,
    CanonicalVenue,
)
from unified_api_contracts.canonical.domain.features import FeatureMetadata
from unified_api_contracts.canonical.domain.sports.progressive import (
    CanonicalProgressiveStats,
)

from .schemas import (
    SFILeague,
    SFIMatch,
    SFIMatchDominance,
    SFIMatchProgressiveStats,
    SFITeam,
    SFLeagueRaw,
    SFMatchRaw,
    SFTeamRaw,
    SoccerFootballPlayer,
)


def _parse_iso(s: str | None) -> datetime:
    """Parse ISO 8601 timestamp string to UTC datetime (from _helpers)."""
    if not s:
        return datetime.now(UTC)
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.now(UTC)


def _safe_str(val: object) -> str:
    return str(val) if val is not None else ""


def normalize_soccer_football_info_league(
    raw: SFILeague | SFLeagueRaw,
    venue: str = "soccer_football_info",
) -> CanonicalLeague:
    """Convert SFILeague or SFLeagueRaw to CanonicalLeague."""
    league_id = getattr(raw, "league_id", None) or getattr(raw, "sf_league_id", None)
    name = getattr(raw, "league_name", None)
    country = getattr(raw, "country_code", None)
    return CanonicalLeague(
        league_id=_safe_str(league_id),
        name=_safe_str(name),
        country=_safe_str(country) or "unknown",
        league_type=None,
        logo_url=None,
    )


def normalize_soccer_football_info_team(
    raw: SFITeam | SFTeamRaw,
    venue: str = "soccer_football_info",
) -> CanonicalTeam:
    """Convert SFITeam or SFTeamRaw to CanonicalTeam."""
    team_id = getattr(raw, "team_id", None) or getattr(raw, "sf_team_id", None)
    name = getattr(raw, "team_name", None)
    return CanonicalTeam(
        team_id=_safe_str(team_id),
        name=_safe_str(name),
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )


def normalize_soccer_football_info_player(
    raw: SoccerFootballPlayer,
    venue: str = "soccer_football_info",
) -> CanonicalPlayer:
    """Convert SoccerFootballPlayer to CanonicalPlayer."""
    return CanonicalPlayer(
        player_id=_safe_str(raw.id),
        name=_safe_str(raw.name),
        first_name=None,
        last_name=None,
        nationality=_safe_str(raw.country),
        position=None,
        date_of_birth=None,
        height_cm=None,
        weight_kg=None,
    )


def normalize_soccer_football_info_fixture(
    raw: SFIMatch | SFMatchRaw,
    venue: str = "soccer_football_info",
) -> CanonicalFixture:
    """Convert SFIMatch or SFMatchRaw to CanonicalFixture."""
    fixture_id = getattr(raw, "match_id", None) or getattr(raw, "sf_match_id", None)
    home_team_id = getattr(raw, "home_team_id", None) or getattr(raw, "sf_home_id", None)
    home_team_name = getattr(raw, "home_team_name", None) or getattr(raw, "home_name", None)
    away_team_id = getattr(raw, "away_team_id", None) or getattr(raw, "sf_away_id", None)
    away_team_name = getattr(raw, "away_team_name", None) or getattr(raw, "away_name", None)
    league_id = getattr(raw, "league_id", None) or getattr(raw, "sf_league_id", None)
    league_name = getattr(raw, "league_name", None)

    home_team = CanonicalTeam(
        team_id=_safe_str(home_team_id),
        name=_safe_str(home_team_name),
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )
    away_team = CanonicalTeam(
        team_id=_safe_str(away_team_id),
        name=_safe_str(away_team_name),
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )
    league = CanonicalLeague(
        league_id=_safe_str(league_id),
        name=_safe_str(league_name),
        country="unknown",
        league_type=None,
        logo_url=None,
    )

    date_val = getattr(raw, "date", None)
    if isinstance(date_val, datetime):
        kickoff = date_val if date_val.tzinfo else date_val.replace(tzinfo=UTC)
    elif isinstance(date_val, str):
        kickoff = _parse_iso(date_val)
    else:
        kickoff = datetime.now(UTC)

    venue_obj: CanonicalVenue | None = None
    stadium_name: str | None = cast(str | None, getattr(raw, "stadium_name", None))
    if stadium_name:
        venue_obj = CanonicalVenue(
            venue_id="",
            name=stadium_name,
            city=None,
            country=None,
            capacity=None,
            surface=None,
            latitude=None,
            longitude=None,
            altitude=None,
        )

    referee_obj: CanonicalReferee | None = None
    referee_name: str | None = cast(str | None, getattr(raw, "referee_name", None))
    if referee_name:
        referee_obj = CanonicalReferee(
            referee_id="",
            name=referee_name,
            nationality=None,
        )

    home_goals = getattr(raw, "home_score", None) or getattr(raw, "ft_home", None)
    away_goals = getattr(raw, "away_score", None) or getattr(raw, "ft_away", None)
    home_xg: float | None = getattr(raw, "home_xg_kickoff", None) or getattr(raw, "home_xg_live", None)
    away_xg: float | None = getattr(raw, "away_xg_kickoff", None) or getattr(raw, "away_xg_live", None)
    home_possession = getattr(raw, "home_possession", None)
    away_possession = getattr(raw, "away_possession", None)

    return CanonicalFixture(
        fixture_id=_safe_str(fixture_id),
        home_team=home_team,
        away_team=away_team,
        league=league,
        kickoff_utc=kickoff,
        venue=venue_obj,
        referee=referee_obj,
        season="",
        match_week=None,
        source=venue,
        status=getattr(raw, "status", None),
        home_goals=home_goals,
        away_goals=away_goals,
        home_goals_halftime=getattr(raw, "ht_home", None),
        away_goals_halftime=getattr(raw, "ht_away", None),
        home_xg=float(home_xg) if home_xg is not None else None,
        away_xg=float(away_xg) if away_xg is not None else None,
        home_possession=home_possession,
        away_possession=away_possession,
    )


def normalize_soccer_football_info_feature_record(
    raw: SFIMatchDominance | SFIMatchProgressiveStats,
    venue: str = "soccer_football_info",
) -> CanonicalFeatureRecord:
    """Convert SFIMatchDominance or SFIMatchProgressiveStats to CanonicalFeatureRecord."""
    now = datetime.now(UTC).isoformat()
    if isinstance(raw, SFIMatchDominance):
        feature_name = "dominance"
        value = float(raw.home_dominance)
    else:
        feature_name = "progressive_stats"
        value = float(raw.goals or 0) + float(raw.possession or 0) / 100.0
    return CanonicalFeatureRecord(
        feature_name=feature_name,
        value=value,
        timestamp=now,
        metadata=FeatureMetadata(
            name=feature_name,
            version="1.0",
            source=venue,
            domain="sports",
        ),
    )


def normalize_soccer_football_info_progressive_stats(
    raw: SFIMatchProgressiveStats,
) -> CanonicalProgressiveStats:
    """Convert SFIMatchProgressiveStats to CanonicalProgressiveStats.

    SFI provides 30-second interval stats per team including goals,
    possession, shots, corners, fouls, cards, dangerous attacks, and
    dominance percentage.  The timer field is a string like "00:30",
    "01:00" etc. — parsed to total seconds.
    """
    timer_seconds = _parse_timer_to_seconds(raw.timer)
    return CanonicalProgressiveStats(
        fixture_id=raw.match_id,
        timer_seconds=timer_seconds,
        team=raw.team,
        goals=raw.goals,
        possession_pct=float(raw.possession) if raw.possession is not None else None,
        dangerous_attacks=raw.dangerous_attacks,
        attacks=None,
        shots_on_target=raw.shots_on_target,
        shots_off_target=None,
        corners=raw.corners,
        fouls=raw.fouls,
        yellow_cards=raw.yellow_cards,
        red_cards=raw.red_cards,
        substitutions=None,
        dominance_pct=None,
    )


def _parse_timer_to_seconds(timer: str) -> int:
    """Parse SFI timer string "MM:SS" to total seconds.

    Examples: "00:30" -> 30, "45:00" -> 2700, "90:00" -> 5400.
    Falls back to 0 on parse errors.
    """
    parts = timer.split(":")
    if len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, TypeError):
            return 0
    return 0


__all__ = [
    "normalize_soccer_football_info_feature_record",
    "normalize_soccer_football_info_fixture",
    "normalize_soccer_football_info_league",
    "normalize_soccer_football_info_player",
    "normalize_soccer_football_info_progressive_stats",
    "normalize_soccer_football_info_team",
]
