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
    # transfermarkt — TRANSFERMARKT_LEAGUES retired 2026-05-05 (was static
    # provider-catalog mapping, belongs in UAC TRANSFERMARKT_IDS not as
    # captured GCS data; orchestrator still calls adapter.get_leagues() at
    # runtime for prediction-tier filtering).
    #
    # PLAYER_VALUES: 2026-05-05 SSOT realignment. The orchestrator writes ONE
    # bulk parquet per (date, season) at entity=player_values/ containing all
    # leagues' team values for that snapshot — NOT a per-league-subpartition
    # layout. Pre-2026-05-05 SSOT pointed at "transfermarkt_teams" with
    # PER_DAY_PER_LEAGUE, which never matched the writer; the audit script
    # then false-flagged every captured row as phantom + a band-aid script
    # (`write_player_values_placeholders.py`, deleted 2026-05-05) wrote 906
    # zero-row placeholders to mask the drift. Aligned to the writer's truth:
    # folder=player_values + layout=PER_DAY_PER_SEASON.
    "PLAYER_VALUES": "player_values",
    # soccer-football-info — SFI_LEAGUES retired 2026-05-05 same reason
    # (mapping in UAC SOCCER_FOOTBALL_INFO_IDS; runtime fetch only).
    "SFI_PROGRESSIVE_STATS": "progressive_stats",
    # open-meteo
    "WEATHER": "weather",
}


class SportsPathLayout(StrEnum):
    """Granularity of GCS storage for a sports data_type."""

    PER_DAY_PER_LEAGUE = "per_day_per_league"
    """``sports_reference/by_date/day={D}/entity={F}/league={L}/{F}.parquet``"""

    PER_DAY_PER_SEASON = "per_day_per_season"
    """``sports_reference/by_date/day={D}/entity={F}/season={S}/{F}.parquet``

    One bulk file per (date, season) containing all leagues' rows for that
    snapshot. League filtering happens intra-file via the ``canonical_league``
    column. Multiple seasons can co-exist for the same day (transfer-window
    overlap when old + new season values are both legitimate).
    Used by ``PLAYER_VALUES`` (transfermarkt team values)."""

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
    "PLAYER_VALUES": SportsPathLayout.PER_DAY_PER_SEASON,
    # TRANSFERMARKT_LEAGUES + SFI_LEAGUES retired 2026-05-05 — provider
    # catalog mappings live in UAC, not as captured GCS data.
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
    season: str | None = None,
    include_legacy_archive: bool = False,
) -> list[str]:
    """Return ordered list of candidate GCS paths (without bucket prefix) for
    a SPORTS shard.

    Use to probe whether data exists for a manifest row. Caller checks each
    path; ANY hit means data is on disk for the shard. Callers MUST iterate
    the full list — early-return on ``cands[0]`` only is wrong for layouts
    that emit multiple plausible paths (PER_DAY_PER_SEASON probes 3 seasons).
    Empty list returned for unknown ``data_type``.

    Args:
        data_type: Canonical SPORTS data_type (e.g. ``"FIXTURES"``).
        day: ``YYYY-MM-DD`` partition.
        league_id: Canonical UAC league_id. Required for
            ``PER_DAY_PER_LEAGUE`` data_types — without it the per-league
            subpartition path can't be built and only the bare fallback is
            returned (typically a phantom). Informational only for
            ``PER_DAY_PER_SEASON`` (league filtering happens intra-file).
        season: Explicit season (e.g. ``"2024"``) for
            ``PER_DAY_PER_SEASON`` data_types. When ``None`` the function
            returns paths for ``[year-1, year, year+1]`` to cover transfer-
            window overlap where multiple seasons co-exist on the same day.
            Ignored for other layouts.
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

    if layout == SportsPathLayout.PER_DAY_PER_SEASON:
        # Per-(date, season) bulk file. League filter happens intra-file
        # on the ``canonical_league`` column.
        if season:
            paths.append(f"{base}/season={season}/{folder}.parquet")
        else:
            # Probe a 3-year window around the day's year — covers transfer-
            # window overlap when old + new season values legitimately
            # co-exist for the same day (e.g. 2023-08-01 may carry both
            # season=2022 final-window updates AND season=2023 pre-season).
            try:
                year = int(day[:4])
            except (ValueError, TypeError):
                year = 0
            for s in (str(year - 1), str(year), str(year + 1)):
                paths.append(f"{base}/season={s}/{folder}.parquet")
        # Bare fallback for any historical writes that omitted the season
        # subpartition (orchestrator omits ``season=`` when ``season`` arg
        # is None — captured here so the bare path doesn't silently miss).
        paths.append(f"{base}/{folder}.parquet")
        if include_legacy_archive:
            archive_base = f"sports_reference_v1_archive/by_date/day={day}/entity={folder}"
            paths.append(f"{archive_base}/{folder}.parquet")
        return paths

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
    season: str | None = None,
    include_legacy_archive: bool = False,
) -> list[str]:
    """Same as ``candidate_parquet_paths`` but returns full ``gs://`` URIs."""
    bucket = sports_bucket_name(project_id)
    return [
        f"gs://{bucket}/{p}"
        for p in candidate_parquet_paths(
            data_type,
            day,
            league_id,
            season=season,
            include_legacy_archive=include_legacy_archive,
        )
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
