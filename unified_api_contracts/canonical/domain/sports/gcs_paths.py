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

Flat-per-season path (no by_date partition, season-keyed):
    sports_reference/{folder}/season={S}/{folder}.parquet
        ↑ season-keyed snapshots like TEAMS_SEASON_SNAPSHOT — genuinely
          season-keyed data (not date-keyed), so it does not fit the
          per-day-per-league layout without inventing a fake day=/league=
          label. See TEAMS_SEASON_SNAPSHOT below.
"""

from __future__ import annotations

from enum import StrEnum

from .fixture_lifecycle import FIXTURES_OUTCOMES, FIXTURES_SCHEDULE

# ---------------------------------------------------------------------------
# TEAMS_SEASON_SNAPSHOT — additive data_type (2026-08-03)
# ---------------------------------------------------------------------------
TEAMS_SEASON_SNAPSHOT: str = "TEAMS_SEASON_SNAPSHOT"
"""Canonical data_type for the season-keyed team x venue snapshot folded from
the legacy ``day=all/entity=teams`` archive. Distinct from the routine daily
``"TEAMS"`` data_type (``PER_DAY_PER_LEAGUE``) — this one is genuinely
season-keyed (22,241 unique ``(team_id, season)`` pairs, seasons 2019-2025),
so it gets its own ``FLAT_PER_SEASON`` layout instead of a fake
``day=``/``league=`` label forced onto rows that have neither.

Ruled 2026-07-28 (Option A of the sub-decision):
``sports_day_all_teams_venues_fold_key_scheme_mismatch_2026_07_25.md``.
"""

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
    # 2026-07-14+: the writer cut FIXTURES over to a two-entity split with NO legacy
    # dual-write (sports_fixtures_schema_split_completion_2026_06_20.md) — every date
    # on/after the cutover has ONLY these two entities, zero "fixtures" objects.
    # Registered here so callers that need the split entities explicitly can use the
    # SSOT instead of hardcoding the folder name; `candidate_parquet_paths("FIXTURES", ...)`
    # ALSO auto-appends FIXTURES_SCHEDULE candidates (see below) so existing "FIXTURES"
    # callers stay correct across the cutover without changing their call sites.
    FIXTURES_SCHEDULE: "fixtures_schedule",
    FIXTURES_OUTCOMES: "fixtures_outcomes",
    "FIXTURE_EVENTS": "fixture_events",
    "FIXTURE_LINEUPS": "fixture_lineups",
    "FIXTURE_STATS": "fixture_stats",
    "PLAYER_STATS": "player_stats",
    "INJURIES": "injuries",
    "STANDINGS": "standings",
    "LEAGUES": "leagues",
    "TEAMS": "teams",
    "VENUES": "venues",
    # 2026-08-03: season-keyed TEAMS archive, distinct from the routine daily
    # "TEAMS" data_type above (PER_DAY_PER_LEAGUE). Folded from the legacy
    # day=all/entity=teams snapshot (30,069 rows, seasons 2019-2025) — see
    # sports_day_all_teams_venues_fold_key_scheme_mismatch_2026_07_25.md.
    # Shares the "teams" folder name with the daily data_type; the two never
    # collide on disk because their layouts (FLAT_PER_SEASON vs
    # PER_DAY_PER_LEAGUE) produce disjoint path shapes.
    TEAMS_SEASON_SNAPSHOT: "teams",
    # footystats
    "MATCHES": "footystats_matches",
    "ODDS": "footystats_odds",
    "PREDICTIONS": "footystats_predictions",
    # understat
    "XG": "understat_xg",
    "XG_SHOTS": "understat_xg_shots",
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

    FLAT_PER_SEASON = "flat_per_season"
    """``sports_reference/{F}/season={S}/{F}.parquet`` — singleton per season, not
    partitioned by date. Used by ``TEAMS_SEASON_SNAPSHOT`` (a genuinely
    season-keyed snapshot, not a daily capture)."""


# Default layout per data_type. When ``BOTH`` is needed (per-league + bare
# path probed) callers should request ``candidate_parquet_paths`` which
# returns multiple candidates ordered by likelihood.
SPORTS_DATA_TYPE_LAYOUT: dict[str, SportsPathLayout] = {
    # Per-league subpartition (modern layout for most entities)
    "FIXTURES": SportsPathLayout.PER_DAY_PER_LEAGUE,
    FIXTURES_SCHEDULE: SportsPathLayout.PER_DAY_PER_LEAGUE,
    FIXTURES_OUTCOMES: SportsPathLayout.PER_DAY_PER_LEAGUE,
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
    # Per-shot xG — per-league subpartition (one file per league per day)
    "XG_SHOTS": SportsPathLayout.PER_DAY_PER_LEAGUE,
    # Bare path (single file per day — XG often un-partitioned)
    "XG": SportsPathLayout.PER_DAY_BARE,
    # WEATHER: 2026-07-25 SSOT realignment (same drift class as PLAYER_VALUES
    # above). The IS weather writer (engine/orchestrator/weather.py) emits
    # ONE per-league partitioned parquet per (date, league) — "Per-league
    # partitioned write — single SSOT, no bare write" per its own code
    # comment — never a bare entity=weather/weather.parquet. Confirmed both
    # in code and via live GCS listing (2026-07-25): entity=weather/ objects
    # only ever exist under a league= subpartition, zero bare objects found.
    # The pre-2026-07-25 SSOT pointed at PER_DAY_BARE, which never matched
    # the writer — candidate_parquet_paths() then probed the wrong path and
    # false-flagged every captured WEATHER row as phantom (>=106 proven false
    # positives). Aligned to the writer's truth: PER_DAY_PER_LEAGUE.
    "WEATHER": SportsPathLayout.PER_DAY_PER_LEAGUE,
    "LEAGUES": SportsPathLayout.PER_DAY_BARE,
    # Flat (singleton)
    "VENUES": SportsPathLayout.FLAT,
    # Flat, season-keyed (singleton per season) — see TEAMS_SEASON_SNAPSHOT above.
    TEAMS_SEASON_SNAPSHOT: SportsPathLayout.FLAT_PER_SEASON,
}


# ---------------------------------------------------------------------------
# Path builders
# ---------------------------------------------------------------------------
SPORTS_BUCKET_TEMPLATE = "instruments-store-sports-{env}-{project_id}"
SPORTS_BY_DATE_PREFIX = "sports_reference/by_date/"
SPORTS_FLAT_PREFIX = "sports_reference/"

# Entities that write per-hourly-fetch snapshots under a fetched_at_hour= sub-partition.
# The IS footystats writer adds fetched_at_hour={YYYY-MM-DDTHH} between entity= and
# league= so each polling run gets its own partition (latest-wins when reading).
# The hour value is dynamic, so candidate_parquet_paths emits these as wildcard
# candidates (fetched_at_hour=*) that the reconciler resolves via startswith/endswith.
_FETCHED_AT_HOUR_FOLDERS: frozenset[str] = frozenset({"footystats_odds", "footystats_predictions"})


def sports_bucket_name(project_id: str, *, env: str = "prd") -> str:
    """Return the canonical sports reference bucket name for a project.

    Args:
        project_id: GCP project id (e.g. ``my-gcp-project``).
        env: Deployment environment short form (``"prd"`` / ``"stg"`` /
            ``"dev"``). Defaults to ``"prd"`` — the production env.
            Matches ``DEPLOYMENT_ENV_SHORT`` from cloud-providers.yaml.
    """
    return SPORTS_BUCKET_TEMPLATE.format(env=env, project_id=project_id)


def candidate_parquet_paths(
    data_type: str,
    day: str,
    league_id: str = "",
    *,
    season: str | None = None,
    pipeline_mode: str | None = None,
) -> list[str]:
    """Return ordered list of candidate GCS paths (without bucket prefix) for
    a SPORTS shard.

    Use to probe whether data exists for a manifest row. Caller checks each
    path; ANY hit means data is on disk for the shard. Callers MUST iterate
    the full list — early-return on ``cands[0]`` only is wrong for layouts
    that emit multiple plausible paths (PER_DAY_PER_SEASON probes 3 seasons).
    Empty list returned for unknown ``data_type``.

    ``data_type="FIXTURES"`` also appends ``FIXTURES_SCHEDULE`` candidates: the
    2026-07-14+ writer cutover to the fixtures_schedule/fixtures_outcomes entity
    split shipped with no legacy dual-write, so every date on/after the cutover
    has zero ``entity=fixtures`` objects. This keeps existing "FIXTURES" callers
    correct across the cutover without requiring a call-site change.

    Args:
        data_type: Canonical SPORTS data_type (e.g. ``"FIXTURES"``).
        day: ``YYYY-MM-DD`` partition.
        league_id: Canonical UAC league_id. Required for
            ``PER_DAY_PER_LEAGUE`` data_types — without it the per-league
            subpartition path can't be built and only the bare fallback is
            returned (typically a phantom). Informational only for
            ``PER_DAY_PER_SEASON`` (league filtering happens intra-file).
        season: Explicit season (e.g. ``"2024"``) for
            ``PER_DAY_PER_SEASON``/``FLAT_PER_SEASON`` data_types. When
            ``None`` the function returns paths for ``[year-1, year, year+1]``
            (derived from ``day``) to cover transfer-window overlap where
            multiple seasons co-exist. Ignored for other layouts.
        pipeline_mode: When provided, the pipeline_mode-aware canonical path
            ``sports_reference/by_date/day={D}/pipeline_mode={mode}/entity=...``
            is prepended as the first probe (Phase 5.3 migration fallback
            chain). Default ``None`` skips the canonical level (back-compat).
            Ignored for ``FLAT``/``FLAT_PER_SEASON`` layouts (no date partition).

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

    if layout == SportsPathLayout.FLAT_PER_SEASON:
        if season:
            paths.append(f"{SPORTS_FLAT_PREFIX}{folder}/season={season}/{folder}.parquet")
        else:
            # No explicit season: probe a [year-1, year, year+1] window derived
            # from `day` (mirrors PER_DAY_PER_SEASON's fallback) — `day` itself
            # is not part of this layout's path, only used as a year hint.
            try:
                year = int(day[:4])
            except (ValueError, TypeError):
                year = 0
            for s in (str(year - 1), str(year), str(year + 1)):
                paths.append(f"{SPORTS_FLAT_PREFIX}{folder}/season={s}/{folder}.parquet")
        return paths

    base = f"{SPORTS_BY_DATE_PREFIX}day={day}/entity={folder}"
    pm_base = (
        f"{SPORTS_BY_DATE_PREFIX}day={day}/pipeline_mode={pipeline_mode}/entity={folder}" if pipeline_mode else None
    )

    if layout == SportsPathLayout.PER_DAY_PER_SEASON:
        try:
            year = int(day[:4])
        except (ValueError, TypeError):
            year = 0
        year_window = (str(year - 1), str(year), str(year + 1))

        # Level 1: pipeline_mode-aware canonical paths (migrated data)
        if pm_base:
            if season:
                paths.append(f"{pm_base}/season={season}/{folder}.parquet")
            else:
                for s in year_window:
                    paths.append(f"{pm_base}/season={s}/{folder}.parquet")
            paths.append(f"{pm_base}/{folder}.parquet")

        # Level 2+: existing paths (pre-migration or legacy)
        if season:
            paths.append(f"{base}/season={season}/{folder}.parquet")
        else:
            for s in year_window:
                paths.append(f"{base}/season={s}/{folder}.parquet")
        paths.append(f"{base}/{folder}.parquet")

        # (b) Legacy filename: pre-SSOT-realignment writes used transfermarkt_teams.parquet
        # as the filename even after the entity folder moved to player_values/. Add these as
        # fallback candidates so the reconciler's forward pass can find historic captures.
        _legacy_name = "transfermarkt_teams.parquet"
        if pm_base:
            if season:
                paths.append(f"{pm_base}/season={season}/{_legacy_name}")
            else:
                for s in year_window:
                    paths.append(f"{pm_base}/season={s}/{_legacy_name}")
            paths.append(f"{pm_base}/{_legacy_name}")
        if season:
            paths.append(f"{base}/season={season}/{_legacy_name}")
        else:
            for s in year_window:
                paths.append(f"{base}/season={s}/{_legacy_name}")
        paths.append(f"{base}/{_legacy_name}")

        # (c) Legacy per-league layout without season= (pre-2026-05-05 partial writes used
        # entity=player_values/league={L}/ without a season= segment — these survive on disk
        # and the reconciler's forward pass must recognise them as real captures).
        if league_id:
            paths.append(f"{base}/league={league_id}/{folder}.parquet")
            paths.append(f"{base}/league={league_id}/{_legacy_name}")

        return paths

    # PER_DAY_PER_LEAGUE or PER_DAY_BARE
    # Level 1: pipeline_mode-aware canonical paths (migrated data)
    if pm_base:
        if layout == SportsPathLayout.PER_DAY_PER_LEAGUE and league_id:
            paths.append(f"{pm_base}/league={league_id}/{folder}.parquet")
        paths.append(f"{pm_base}/{folder}.parquet")

    # Level 2+: existing paths (pre-migration or legacy)
    if layout == SportsPathLayout.PER_DAY_PER_LEAGUE and league_id:
        paths.append(f"{base}/league={league_id}/{folder}.parquet")
    paths.append(f"{base}/{folder}.parquet")

    # (a) fetched_at_hour= sub-partitioning (footystats ODDS + PREDICTIONS):
    # Each polling run writes its own hourly snapshot partition between entity= and league=.
    # The hour value is unknown at query time, so we use fetched_at_hour=* as a wildcard
    # segment. Callers that do exact path lookup must handle * via startswith/endswith;
    # the reconciler's _audit_sports function recognises and resolves these candidates.
    if folder in _FETCHED_AT_HOUR_FOLDERS:
        _fah = "fetched_at_hour=*"
        if pm_base:
            if layout == SportsPathLayout.PER_DAY_PER_LEAGUE and league_id:
                paths.append(f"{pm_base}/{_fah}/league={league_id}/{folder}.parquet")
            paths.append(f"{pm_base}/{_fah}/{folder}.parquet")
        if layout == SportsPathLayout.PER_DAY_PER_LEAGUE and league_id:
            paths.append(f"{base}/{_fah}/league={league_id}/{folder}.parquet")
        paths.append(f"{base}/{_fah}/{folder}.parquet")

    # 2026-07-14+ writer cutover fallback: FIXTURES has no legacy dual-write, so every
    # date on/after the cutover has ONLY entity=fixtures_schedule (+ fixtures_outcomes),
    # zero entity=fixtures objects. Append FIXTURES_SCHEDULE candidates so existing
    # "FIXTURES" callers (e.g. MTDS fixture_id_resolver.py) keep resolving fixture rows
    # across the cutover without changing their call sites. FIXTURES_OUTCOMES is
    # deliberately NOT probed here — it's a subset (completed fixtures only) and would
    # under-report thin/no-completed-match days as missing when used as a presence marker.
    if data_type == "FIXTURES":
        paths.extend(
            candidate_parquet_paths(
                FIXTURES_SCHEDULE,
                day,
                league_id,
                pipeline_mode=pipeline_mode,
            )
        )

    return paths


def candidate_parquet_uris(
    data_type: str,
    day: str,
    league_id: str = "",
    *,
    project_id: str,
    env: str = "prd",
    season: str | None = None,
    pipeline_mode: str | None = None,
) -> list[str]:
    """Same as ``candidate_parquet_paths`` but returns full ``gs://`` URIs.

    Args:
        data_type: Canonical SPORTS data_type (e.g. ``"FIXTURES"``).
        day: ``YYYY-MM-DD`` partition.
        league_id: Canonical UAC league_id.
        project_id: GCP project id (e.g. ``my-gcp-project``).
        env: Deployment environment short form (``"prd"`` / ``"stg"`` /
            ``"dev"``). Defaults to ``"prd"``. Passed to
            :func:`sports_bucket_name` to produce the env-tiered bucket name.
        season: Explicit season for ``PER_DAY_PER_SEASON`` data_types.
        pipeline_mode: Pipeline-mode canonical path prefix.
    """
    bucket = sports_bucket_name(project_id, env=env)
    return [
        f"gs://{bucket}/{p}"  # noqa: gs-uri — URI composer, bucket already resolved via sports_bucket_name()
        for p in candidate_parquet_paths(
            data_type,
            day,
            league_id,
            season=season,
            pipeline_mode=pipeline_mode,
        )
    ]


__all__ = [
    "SPORTS_BUCKET_TEMPLATE",
    "SPORTS_BY_DATE_PREFIX",
    "SPORTS_DATA_TYPE_LAYOUT",
    "SPORTS_DATA_TYPE_TO_FOLDER",
    "SPORTS_FLAT_PREFIX",
    "TEAMS_SEASON_SNAPSHOT",
    "SportsPathLayout",
    "candidate_parquet_paths",
    "candidate_parquet_uris",
    "sports_bucket_name",
]
