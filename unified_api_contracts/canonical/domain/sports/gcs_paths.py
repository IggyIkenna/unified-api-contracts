"""SSOT for SPORTS GCS parquet paths — canonical layout per data_type.

Before this module, each script (rescan, backfill, audit, FSS reader,
data-status) hardcoded its own path. That fragmentation caused the
2026-04-29 phantom-row audit incident: the reconciliation probe used
``entity=odds/`` instead of the actual ``entity=footystats_odds/``,
falsely reporting 26% phantom for ODDS when the data was right there.

Use this module instead of constructing paths in-line. If you find a
hardcoded ``"sports_reference/by_date/day=..."`` string anywhere, replace
it with ``candidate_parquet_paths()``.

GCS layout (by date partition):
    sports_reference/by_date/day={D}/entity={folder}/league={L}/{folder}.parquet
        ↑ per-league subpartition (most entities — modern layout)
    sports_reference/by_date/day={D}/entity={folder}/{folder}.parquet
        ↑ bare path (legacy or single-file-per-day entities)

Flat path (no by_date partition):
    sports_reference/{folder}/{folder}.parquet
        ↑ singletons like VENUES that don't change daily
"""

from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# data_type → entity folder mapping
# ---------------------------------------------------------------------------
# Folder names are wire-format (lowercase with underscores) and stable —
# changing them is a migration. Source: instruments-service writer + the
# rescan scripts. SSOT for downstream consumers (FSS reader, deployment-api
# data-status, audit/reconciliation tools).
SPORTS_DATA_TYPE_TO_FOLDER: dict[str, str] = {
    # api-football
    "FIXTURES": "fixtures",
    "FIXTURE_EVENTS": "fixture_events",
    "FIXTURE_LINEUPS": "fixture_lineups",
    "FIXTURE_STATS": "fixture_stats",
    "PLAYER_STATS": "player_stats",
    "INJURIES": "injuries",
    "STANDINGS": "standings",
    "LEAGUES": "leagues",
    "TEAMS": "teams",
    "VENUES": "venues",
    # footystats
    "MATCHES": "footystats_matches",
    "ODDS": "footystats_odds",
    "PREDICTIONS": "footystats_predictions",
    # understat
    "XG": "understat_xg",
    # transfermarkt
    "TRANSFERMARKT_LEAGUES": "transfermarkt_leagues",
    "PLAYER_VALUES": "transfermarkt_teams",
    # soccer-football-info
    "SFI_LEAGUES": "sfi_leagues",
    "SFI_PROGRESSIVE_STATS": "progressive_stats",
    # open-meteo
    "WEATHER": "weather",
}


class SportsPathLayout(StrEnum):
    """Granularity of GCS storage for a sports data_type."""

    PER_DAY_PER_LEAGUE = "per_day_per_league"
    """``sports_reference/by_date/day={D}/entity={F}/league={L}/{F}.parquet``"""

    PER_DAY_BARE = "per_day_bare"
    """``sports_reference/by_date/day={D}/entity={F}/{F}.parquet``

    Used for single-file-per-day entities OR pre-per-league layout legacy.
    Some entities have BOTH (per-league split + bare for older days)."""

    FLAT = "flat"
    """``sports_reference/{F}/{F}.parquet`` — singleton, not partitioned by date."""


# Default layout per data_type. When ``BOTH`` is needed (per-league + bare
# path probed) callers should request ``candidate_parquet_paths`` which
# returns multiple candidates ordered by likelihood.
SPORTS_DATA_TYPE_LAYOUT: dict[str, SportsPathLayout] = {
    # Per-league subpartition (modern layout for most entities)
    "FIXTURES": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "FIXTURE_EVENTS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "FIXTURE_LINEUPS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "FIXTURE_STATS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "PLAYER_STATS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "INJURIES": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "STANDINGS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "TEAMS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "MATCHES": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "ODDS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "PREDICTIONS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "PLAYER_VALUES": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "TRANSFERMARKT_LEAGUES": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "SFI_LEAGUES": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "SFI_PROGRESSIVE_STATS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    # Bare path (single file per day — XG/WEATHER often un-partitioned)
    "XG": SportsPathLayout.PER_DAY_BARE,
    "WEATHER": SportsPathLayout.PER_DAY_BARE,
    "LEAGUES": SportsPathLayout.PER_DAY_BARE,
    # Flat (singleton)
    "VENUES": SportsPathLayout.FLAT,
}


# ---------------------------------------------------------------------------
# Path builders
# ---------------------------------------------------------------------------
SPORTS_BUCKET_TEMPLATE = "instruments-store-sports-{project_id}"
SPORTS_BY_DATE_PREFIX = "sports_reference/by_date/"
SPORTS_FLAT_PREFIX = "sports_reference/"


def sports_bucket_name(project_id: str) -> str:
    """Return the canonical sports reference bucket name for a project."""
    return SPORTS_BUCKET_TEMPLATE.format(project_id=project_id)


def candidate_parquet_paths(
    data_type: str,
    day: str,
    league_id: str = "",
    *,
    include_legacy_archive: bool = False,
) -> list[str]:
    """Return ordered list of candidate GCS paths (without bucket prefix) for
    a SPORTS shard.

    Use to probe whether data exists for a manifest row. Caller checks each
    path; first hit wins. Empty list returned for unknown ``data_type``.

    Args:
        data_type: Canonical SPORTS data_type (e.g. ``"FIXTURES"``).
        day: ``YYYY-MM-DD`` partition.
        league_id: Canonical UAC league_id. Required for
            ``PER_DAY_PER_LEAGUE`` data_types — without it the per-league
            subpartition path can't be built and only the bare fallback is
            returned (typically a phantom).
        include_legacy_archive: If True, also include
            ``sports_reference_v1_archive/...`` paths (pre-2026-04-28
            schema migration). Default False.

    Returns:
        List of GCS paths (relative to bucket). Empty if data_type unknown.
    """
    folder = SPORTS_DATA_TYPE_TO_FOLDER.get(data_type)
    if folder is None:
        return []
    layout = SPORTS_DATA_TYPE_LAYOUT.get(data_type, SportsPathLayout.PER_DAY_BARE)

    paths: list[str] = []
    if layout == SportsPathLayout.FLAT:
        paths.append(f"{SPORTS_FLAT_PREFIX}{folder}/{folder}.parquet")
        return paths

    base = f"{SPORTS_BY_DATE_PREFIX}day={day}/entity={folder}"
    if layout == SportsPathLayout.PER_DAY_PER_LEAGUE and league_id:
        # Per-league subpartition (modern layout) — try first.
        paths.append(f"{base}/league={league_id}/{folder}.parquet")
    # Bare path — fallback for legacy / single-file-per-day entities,
    # OR when league_id is empty.
    paths.append(f"{base}/{folder}.parquet")
    if include_legacy_archive:
        archive_base = f"sports_reference_v1_archive/by_date/day={day}/entity={folder}"
        if league_id:
            paths.append(f"{archive_base}/league={league_id}/{folder}.parquet")
        paths.append(f"{archive_base}/{folder}.parquet")
    return paths


def candidate_parquet_uris(
    data_type: str,
    day: str,
    league_id: str = "",
    *,
    project_id: str,
    include_legacy_archive: bool = False,
) -> list[str]:
    """Same as ``candidate_parquet_paths`` but returns full ``gs://`` URIs."""
    bucket = sports_bucket_name(project_id)
    return [
        f"gs://{bucket}/{p}"
        for p in candidate_parquet_paths(data_type, day, league_id, include_legacy_archive=include_legacy_archive)
    ]


__all__ = [
    "SPORTS_BUCKET_TEMPLATE",
    "SPORTS_BY_DATE_PREFIX",
    "SPORTS_DATA_TYPE_LAYOUT",
    "SPORTS_DATA_TYPE_TO_FOLDER",
    "SPORTS_FLAT_PREFIX",
    "SportsPathLayout",
    "candidate_parquet_paths",
    "candidate_parquet_uris",
    "sports_bucket_name",
]
