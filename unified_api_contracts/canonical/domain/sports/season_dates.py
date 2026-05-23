"""Season start dates and reference-data trigger calendar.

Combines per-league season boundaries (from LeagueDefinition.season_months)
with transfer window dates (from transfer_windows.py) to produce a unified
trigger calendar.  The orchestrator uses this to decide WHEN to refresh
slow-moving reference data (teams, player values, mappings) instead of
re-fetching identical data every day.

Trigger dates per league per year:
  1. Season start (first day of start_month) - promotion/relegation changes
  2. Transfer window open dates - squad changes begin
  3. Transfer window close dates - squad changes finalize

For historical backfill, fetch reference data at each trigger date.
For live mode, check ``is_reference_refresh_date()`` on each batch run.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal, NamedTuple

from .league_data import LEAGUE_REGISTRY
from .league_registry import LeagueDefinition
from .transfer_windows import (
    get_country_for_league,
    get_transfer_windows_for_year,
)

# Bridge LeagueDefinition.country (ISO 3166-1 alpha-2) to
# transfer_windows.py country codes (ISO 3166-1 alpha-3).
_COUNTRY_2_TO_3: dict[str, str] = {
    "GB": "ENG",
    "ES": "ESP",
    "DE": "DEU",
    "IT": "ITA",
    "FR": "FRA",
    "NL": "NLD",
    "PT": "PRT",
    "BE": "BEL",
    "TR": "TUR",
    "GR": "GRC",
    "AT": "AUT",
    "CH": "CHE",
    "DK": "DNK",
    "NO": "NOR",
    "SE": "SWE",
    "PL": "POL",
    "AR": "ARG",
    "BR": "BRA",
    "CL": "CHL",
    "US": "USA",
    "MX": "MEX",
    "JP": "JPN",
    "KR": "KOR",
    "AU": "AUS",
    "SC": "SCO",
}


class SeasonBoundary(NamedTuple):
    """Season start and end dates for a league-year."""

    league_id: str
    season_year: int
    start_date: date
    end_date: date


def get_season_start(league_id: str, season_year: int) -> date:
    """Return the approximate season start date for a league.

    Uses ``season_months`` from the league registry.  The start date is the
    first day of the start month in ``season_year``.

    For cross-year seasons (e.g. EPL Aug 2025 - May 2026), ``season_year``
    is the year the season STARTS (2025 for the 2025-26 EPL season).
    """
    league_def = _get_league_def(league_id)
    if league_def is None:
        # Unknown league -- fall back to generic European Aug 1
        return date(season_year, 8, 1)
    start_month = league_def.season_months[0]
    return date(season_year, start_month, 1)


def get_season_end(league_id: str, season_year: int) -> date:
    """Return the approximate season end date for a league.

    For cross-year seasons, the end date is in ``season_year + 1``.
    For calendar-year seasons, the end is in ``season_year``.
    """
    league_def = _get_league_def(league_id)
    if league_def is None:
        return date(season_year + 1, 5, 31)
    start_month, end_month = league_def.season_months
    # Cross-year season (e.g. Aug-May): end is in the next calendar year
    end_year = season_year + 1 if end_month < start_month else season_year
    # Last day of end month (approximate with 28 for safety)
    if end_month == 12:
        return date(end_year, 12, 31)
    return date(end_year, end_month + 1, 1) - timedelta(days=1)


def get_season_boundary(league_id: str, season_year: int) -> SeasonBoundary:
    """Return the full season boundary for a league-year."""
    return SeasonBoundary(
        league_id=league_id,
        season_year=season_year,
        start_date=get_season_start(league_id, season_year),
        end_date=get_season_end(league_id, season_year),
    )


# ---------------------------------------------------------------------------
# FootyStats per-league season bounds
#
# FootyStats refreshes its per-league season IDs every season
# (``FOOTYSTATS_SEASON_IDS`` in provider_league_ids.py), but the season
# *boundary dates* are source-agnostic — a 2025-26 EPL season runs Aug 2025 →
# May 2026 whether you read it from FootyStats, api_football or understat.  So
# the FootyStats season-bounds view is derived from the existing
# :func:`get_season_boundary` (which reads ``LeagueDefinition.season_months``)
# rather than carrying duplicate per-(league, season) date pairs (per the
# workspace "no double SSOT" rule — the league registry's ``season_months`` is
# the single source).  These helpers exist so the sports per-source classifier
# can flip a FootyStats ``empty_confirmed`` shard whose day falls before/after
# the league's season window to the typed ``EXPECTED_PRE_SEASON`` /
# ``EXPECTED_POST_SEASON`` reason instead of the catch-all ``SOURCE_RETURNED_ZERO``
# (the SOURCE_COVERAGE_START clip in UAC ``sports`` handles the
# before-FootyStats-coverage-started case separately).
# ---------------------------------------------------------------------------


def get_footystats_season_bounds(league_id: str, season_year: int) -> tuple[date, date]:
    """Return ``(season_start, season_end)`` for ``league_id``'s ``season_year`` season.

    Thin wrapper over :func:`get_season_boundary` — same data, tuple shape for
    callers that just want the bounds.  ``season_year`` is the year the season
    STARTS (2025 for the 2025-26 EPL season; equal to the calendar year for
    calendar-year leagues like Allsvenskan / J.League).
    """
    boundary = get_season_boundary(league_id, season_year)
    return (boundary.start_date, boundary.end_date)


def is_within_footystats_season(league_id: str, season_year: int, day: date) -> bool:
    """Whether ``day`` falls inside ``league_id``'s ``season_year`` season window.

    ``season_year`` is the year the season STARTS.  Inclusive of both bounds.
    """
    start, end = get_footystats_season_bounds(league_id, season_year)
    return start <= day <= end


def footystats_season_status_for_day(
    league_id: str,
    day: date,
) -> Literal["EXPECTED_PRE_SEASON", "EXPECTED_POST_SEASON"] | None:
    """Classify ``day`` relative to ``league_id``'s season windows.

    Checks the season boundaries for the three candidate season-years that could
    plausibly contain ``day`` (``day.year - 1`` / ``day.year`` / ``day.year + 1``)
    — this handles both cross-year leagues (Aug→May) and calendar-year leagues
    (Jan→Dec) without the caller needing to know which kind it is.

    Returns:
      - ``None`` if ``day`` is inside any of those season windows (in-season —
        FootyStats data is genuinely expected, so a zero-row shard is a real
        absence, not a season-gap).
      - ``"EXPECTED_PRE_SEASON"`` if ``day`` is in the off-season gap and is
        closer to the *upcoming* season's start than to the *just-ended* season's
        end (or there is no just-ended season among the candidates).
      - ``"EXPECTED_POST_SEASON"`` otherwise (off-season gap, closer to the
        season that just ended).

    The returned strings are exactly the values of
    ``unified_api_contracts.canonical.crosscutting.honest_coverage.EmptyConfirmedReason.EXPECTED_PRE_SEASON``
    / ``.EXPECTED_POST_SEASON`` — returned as bare strings here to keep this
    module dependency-free of ``crosscutting`` (the classifier validates against
    ``EMPTY_CONFIRMED_REASONS``).
    """
    candidate_years = (day.year - 1, day.year, day.year + 1)
    bounds = [get_season_boundary(league_id, sy) for sy in candidate_years]
    for b in bounds:
        if b.start_date <= day <= b.end_date:
            return None  # in-season
    # Off-season gap: decide pre vs post by which season window is nearer.
    later_starts = [b.start_date for b in bounds if b.start_date > day]
    earlier_ends = [b.end_date for b in bounds if b.end_date < day]
    if not earlier_ends:
        return "EXPECTED_PRE_SEASON"
    if not later_starts:
        return "EXPECTED_POST_SEASON"
    dist_to_next = min(later_starts) - day
    dist_from_prev = day - max(earlier_ends)
    return "EXPECTED_PRE_SEASON" if dist_to_next <= dist_from_prev else "EXPECTED_POST_SEASON"


def get_reference_refresh_dates(league_id: str, year: int) -> list[date]:
    """Return all dates when reference data should be refreshed for a league.

    Combines:
      1. Season start date (teams change via promotion/relegation)
      2. Transfer window open dates (squad changes begin)
      3. Transfer window close dates (squad changes finalize)

    Returns sorted, deduplicated list of trigger dates.
    """
    triggers: set[date] = set()

    # 1. Season start
    triggers.add(get_season_start(league_id, year))

    # 2. Transfer window dates
    tw_country = get_country_for_league(league_id) or "_GENERIC"
    for window in get_transfer_windows_for_year(tw_country, year):
        triggers.add(window.open_date)
        triggers.add(window.close_date)

    # Also check prior year's windows that might close in this year
    # (e.g. Sweden's off-season window opens Nov, closes Mar+1)
    for window in get_transfer_windows_for_year(tw_country, year - 1):
        if window.close_date.year == year:
            triggers.add(window.close_date)

    return sorted(triggers)


def is_reference_refresh_date(
    league_id: str,
    d: date,
    *,
    tolerance_days: int = 3,
) -> bool:
    """Check if date ``d`` is within ``tolerance_days`` of a trigger date.

    The tolerance allows the batch scheduler to hit the trigger even if
    it doesn't run on the exact date (e.g. weekends, outages).
    """
    triggers = get_reference_refresh_dates(league_id, d.year)
    return any(abs((d - t).days) <= tolerance_days for t in triggers)


def is_any_league_refresh_date(
    d: date,
    *,
    tolerance_days: int = 3,
) -> bool:
    """Check if date ``d`` is a refresh trigger for ANY tracked league.

    Used by the orchestrator to decide whether to run the slow-moving
    reference data fetch on a given batch date.
    """
    return any(is_reference_refresh_date(league_id, d, tolerance_days=tolerance_days) for league_id in LEAGUE_REGISTRY)


def get_leagues_needing_refresh(
    d: date,
    *,
    tolerance_days: int = 3,
) -> list[str]:
    """Return league IDs that need reference data refresh on date ``d``."""
    return [
        league_id
        for league_id in LEAGUE_REGISTRY
        if is_reference_refresh_date(league_id, d, tolerance_days=tolerance_days)
    ]


def get_transfer_window_country(league_id: str) -> str:
    """Get the 3-letter country code used by transfer_windows.py for a league.

    Falls back to looking up LeagueDefinition.country and bridging via
    _COUNTRY_2_TO_3.  Returns '_GENERIC' if no mapping found.
    """
    # Direct lookup in transfer_windows mapping
    direct = get_country_for_league(league_id)
    if direct is not None:
        return direct

    # Bridge via LeagueDefinition.country (2-letter)
    league_def = _get_league_def(league_id)
    if league_def is not None:
        return _COUNTRY_2_TO_3.get(league_def.country, "_GENERIC")

    return "_GENERIC"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_league_def(league_id: str) -> LeagueDefinition | None:
    """Lookup a LeagueDefinition by league_id."""
    return LEAGUE_REGISTRY.get(league_id)
