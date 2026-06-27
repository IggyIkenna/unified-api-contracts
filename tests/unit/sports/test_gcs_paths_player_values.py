"""Lock the PLAYER_VALUES SSOT layout — ``PER_DAY_PER_SEASON`` (2026-05-05).

Pre-2026-05-05 PLAYER_VALUES was incorrectly tagged ``PER_DAY_PER_LEAGUE`` with
folder ``transfermarkt_teams`` — the audit script then probed
``entity=transfermarkt_teams/league={LID}/transfermarkt_teams.parquet`` and
found nothing because the writer (instruments-service orchestrator) puts the
real data at ``entity=player_values/season={S}/player_values.parquet`` (one
bulk file per (date, season) containing all leagues for that snapshot).

A band-aid script (``write_player_values_placeholders.py``, deleted 2026-05-05)
wrote 906 zero-row placeholders to mask the drift — the criminal placeholder
pattern CLAUDE.md flags. This test locks the corrected SSOT so a future
refactor can't silently regress.
"""

from __future__ import annotations

from unified_api_contracts.sports import (
    SPORTS_DATA_TYPE_LAYOUT,
    SPORTS_DATA_TYPE_TO_FOLDER,
    SportsPathLayout,
    candidate_parquet_paths,
)


class TestPlayerValuesSSOT:
    """Lock the post-2026-05-05 PLAYER_VALUES SSOT alignment."""

    def test_folder_is_player_values(self) -> None:
        """Folder must match where the writer actually writes (not legacy
        'transfermarkt_teams' which never had real data)."""
        assert SPORTS_DATA_TYPE_TO_FOLDER["PLAYER_VALUES"] == "player_values"

    def test_layout_is_per_day_per_season(self) -> None:
        """Layout must match how the writer partitions on disk: one bulk file
        per (date, season) at season=*/player_values.parquet — NOT
        per-league-subpartition (the legacy aspirational layout that never
        had real data)."""
        assert SPORTS_DATA_TYPE_LAYOUT["PLAYER_VALUES"] == SportsPathLayout.PER_DAY_PER_SEASON

    def test_explicit_season_returns_one_canonical_path(self) -> None:
        """When the caller knows the season, return exactly that path first."""
        paths = candidate_parquet_paths(
            "PLAYER_VALUES",
            "2024-08-01",
            league_id="BUNDESLIGA",
            season="2024",
        )
        # Canonical season-partitioned path first.
        assert paths[0] == (
            "sports_reference/by_date/day=2024-08-01/entity=player_values/season=2024/player_values.parquet"
        )
        # league_id is NOT in the canonical path — league filter happens intra-file.
        assert "league=" not in paths[0]
        # Bare fallback present so historic writes that omitted season still resolve.
        assert (
            "sports_reference/by_date/day=2024-08-01/entity=player_values/player_values.parquet" in paths
        )

    def test_no_season_probes_three_year_window(self) -> None:
        """When the caller doesn't know the season, probe year-1 / year / year+1
        — covers transfer-window overlap where multiple seasons co-exist on the
        same day (743 of 2,548 inventoried bulk parquets had multi-season
        co-existence per 2026-05-05 inventory)."""
        paths = candidate_parquet_paths(
            "PLAYER_VALUES",
            "2024-08-01",
            league_id="BUNDESLIGA",
        )
        # At least three season candidates (year-1, year, year+1) present.
        season_paths = [p for p in paths if "season=" in p]
        assert len(season_paths) >= 3
        seasons = sorted({p.split("season=")[1].split("/")[0] for p in season_paths})
        assert "2023" in seasons and "2024" in seasons and "2025" in seasons
        # Bare path (no season=) present for legacy fallback.
        assert (
            "sports_reference/by_date/day=2024-08-01/entity=player_values/player_values.parquet" in paths
        )

    def test_legacy_per_day_per_league_layout_still_works_for_other_data_types(self) -> None:
        """Sanity: the new PER_DAY_PER_SEASON layout doesn't break the existing
        PER_DAY_PER_LEAGUE entities (FIXTURES, FIXTURE_EVENTS, ODDS, etc.)."""
        paths = candidate_parquet_paths("FIXTURES", "2024-08-01", league_id="BUNDESLIGA")
        assert "league=BUNDESLIGA" in paths[0]
        assert "season=" not in paths[0]
        assert SPORTS_DATA_TYPE_LAYOUT["FIXTURES"] == SportsPathLayout.PER_DAY_PER_LEAGUE

    def test_invalid_day_format_does_not_crash(self) -> None:
        """Bad day input → no season window probed (year=0), but bare path still emitted.
        Resilience guard so audit scripts iterating malformed manifest rows don't crash."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "not-a-date", league_id="BUNDESLIGA")
        # Will probe season=-1, season=0, season=1 — bizarre but won't raise.
        assert any("entity=player_values" in p for p in paths)

    def test_uri_helper_propagates_season_kwarg(self) -> None:
        """``candidate_parquet_uris`` threads the new ``season`` kwarg through."""
        from unified_api_contracts.sports import candidate_parquet_uris

        uris = candidate_parquet_uris(
            "PLAYER_VALUES",
            "2024-08-01",
            league_id="BUNDESLIGA",
            project_id="test-project",
            season="2024",
        )
        assert uris[0].startswith("gs://instruments-store-sports-prd-test-project/")
        assert "season=2024" in uris[0]


class TestSportsPipelineModeFallbackChain:
    """pipeline_mode kwarg on candidate_parquet_paths (Phase 5.3 fallback chain)."""

    def test_fixtures_pipeline_mode_prepends_canonical_path(self) -> None:
        """PER_DAY_PER_LEAGUE: pipeline_mode paths precede existing paths."""
        paths = candidate_parquet_paths("FIXTURES", "2024-01-15", "BUNDESLIGA", pipeline_mode="batch_api_football")
        assert any("pipeline_mode=batch_api_football" in p for p in paths)
        # pipeline_mode paths come first
        assert "pipeline_mode=batch_api_football" in paths[0]
        # Existing paths follow (no pipeline_mode)
        assert any("pipeline_mode=" not in p for p in paths)
        existing = [p for p in paths if "pipeline_mode=" not in p]
        assert any("league=BUNDESLIGA" in p for p in existing)

    def test_fixtures_no_pipeline_mode_unchanged(self) -> None:
        """Without pipeline_mode, output matches pre-Phase-5 behaviour."""
        paths_with = candidate_parquet_paths("FIXTURES", "2024-01-15", "BUNDESLIGA")
        paths_without = candidate_parquet_paths("FIXTURES", "2024-01-15", "BUNDESLIGA", pipeline_mode=None)
        assert paths_with == paths_without
        assert all("pipeline_mode=" not in p for p in paths_with)

    def test_odds_pipeline_mode_bare_path_included(self) -> None:
        """Without league_id, pipeline_mode bare path is still included."""
        paths = candidate_parquet_paths("ODDS", "2024-01-15", pipeline_mode="batch_footystats")
        pm_paths = [p for p in paths if "pipeline_mode=batch_footystats" in p]
        assert pm_paths, "pipeline_mode paths missing"
        assert any("league=" not in p for p in pm_paths)

    def test_player_values_pipeline_mode_season_window(self) -> None:
        """PER_DAY_PER_SEASON: pipeline_mode paths cover the season window."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "2024-08-01", pipeline_mode="batch_transfermarkt")
        pm_paths = [p for p in paths if "pipeline_mode=batch_transfermarkt" in p]
        assert len(pm_paths) >= 3, "expected 3-year window + bare for pipeline_mode"
        assert any("season=2024" in p for p in pm_paths)

    def test_xg_pipeline_mode_bare_layout(self) -> None:
        """PER_DAY_BARE: single pipeline_mode path prepended."""
        paths = candidate_parquet_paths("XG", "2024-01-15", pipeline_mode="batch_understat")
        assert paths[0] == (
            "sports_reference/by_date/day=2024-01-15/pipeline_mode=batch_understat/"
            "entity=understat_xg/understat_xg.parquet"
        )
        assert paths[1] == "sports_reference/by_date/day=2024-01-15/entity=understat_xg/understat_xg.parquet"

    def test_venues_flat_layout_ignores_pipeline_mode(self) -> None:
        """FLAT layout has no date partition — pipeline_mode is inapplicable."""
        paths_with = candidate_parquet_paths("VENUES", "2024-01-15", pipeline_mode="batch_api_football")
        paths_without = candidate_parquet_paths("VENUES", "2024-01-15")
        assert paths_with == paths_without
        assert all("pipeline_mode=" not in p for p in paths_with)

    def test_uri_helper_propagates_pipeline_mode(self) -> None:
        from unified_api_contracts.sports import candidate_parquet_uris

        uris = candidate_parquet_uris(
            "FIXTURES",
            "2024-01-15",
            "BUNDESLIGA",
            project_id="test-project",
            pipeline_mode="batch_api_football",
        )
        assert any("pipeline_mode=batch_api_football" in u for u in uris)


class TestForwardPhantomPathShapes:
    """Gate tests for the three path shapes missing before 2026-06-27.

    These shapes caused candidate_parquet_paths to under-report real on-disk
    paths, making the forward phantom pass false-flag ~145k captured rows as
    phantom. Each test enumerates the shape from candidate_parquet_paths to
    prove the forward --apply is now safe (#5 fix gate).
    """

    # (a) fetched_at_hour= sub-partitioning — footystats ODDS + PREDICTIONS
    def test_odds_fetched_at_hour_wildcard_with_league(self) -> None:
        """ODDS with pipeline_mode: fetched_at_hour=* wildcard candidate emitted."""
        paths = candidate_parquet_paths("ODDS", "2025-09-01", "EPL", pipeline_mode="batch_footystats")
        fah_paths = [p for p in paths if "fetched_at_hour=*" in p]
        assert fah_paths, "expected fetched_at_hour=* candidates for ODDS"
        # League-specific wildcard candidate must be present.
        assert any("league=EPL" in p for p in fah_paths), (
            "league-specific fetched_at_hour=* candidate missing for ODDS/EPL"
        )
        # pipeline_mode-aware candidate must be present.
        assert any("pipeline_mode=batch_footystats" in p for p in fah_paths), (
            "pipeline_mode-aware fetched_at_hour=* candidate missing for ODDS"
        )

    def test_odds_fetched_at_hour_wildcard_bare(self) -> None:
        """ODDS bare (no league): bare fetched_at_hour=* wildcard emitted."""
        paths = candidate_parquet_paths("ODDS", "2025-09-01", pipeline_mode="batch_footystats")
        fah_paths = [p for p in paths if "fetched_at_hour=*" in p]
        assert fah_paths, "expected fetched_at_hour=* candidates for bare ODDS"
        # All fetched_at_hour candidates end with footystats_odds.parquet.
        assert all(p.endswith("footystats_odds.parquet") for p in fah_paths)

    def test_predictions_fetched_at_hour_wildcard(self) -> None:
        """PREDICTIONS: fetched_at_hour=* wildcard emitted (same hourly-snapshot pattern)."""
        paths = candidate_parquet_paths("PREDICTIONS", "2025-09-01", "EPL", pipeline_mode="batch_footystats")
        fah_paths = [p for p in paths if "fetched_at_hour=*" in p]
        assert fah_paths, "expected fetched_at_hour=* candidates for PREDICTIONS"
        assert any("league=EPL" in p for p in fah_paths)

    def test_fetched_at_hour_wildcard_not_emitted_for_non_footystats(self) -> None:
        """Non-footystats PER_DAY_PER_LEAGUE entities do NOT get fetched_at_hour=* paths."""
        paths_fixtures = candidate_parquet_paths("FIXTURES", "2025-09-01", "EPL")
        assert not any("fetched_at_hour=*" in p for p in paths_fixtures)
        paths_xg = candidate_parquet_paths("XG", "2025-09-01")
        assert not any("fetched_at_hour=*" in p for p in paths_xg)

    # (b) transfermarkt_teams.parquet legacy filename — PLAYER_VALUES
    def test_player_values_transfermarkt_teams_filename_with_season(self) -> None:
        """Explicit season: transfermarkt_teams.parquet filename emitted alongside player_values.parquet."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "2024-08-01", season="2024")
        assert any("season=2024/transfermarkt_teams.parquet" in p for p in paths), (
            "transfermarkt_teams.parquet + season= candidate missing"
        )

    def test_player_values_transfermarkt_teams_filename_year_window(self) -> None:
        """No season: transfermarkt_teams.parquet emitted for all three year-window seasons."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "2024-08-01")
        tm_paths = [p for p in paths if "transfermarkt_teams.parquet" in p and "season=" in p]
        seasons = sorted({p.split("season=")[1].split("/")[0] for p in tm_paths})
        assert "2023" in seasons and "2024" in seasons and "2025" in seasons, (
            "transfermarkt_teams.parquet not emitted for all three year-window seasons"
        )

    def test_player_values_transfermarkt_teams_bare_fallback(self) -> None:
        """Bare (no season) transfermarkt_teams.parquet candidate emitted as final fallback."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "2024-08-01")
        assert any(
            p.endswith("entity=player_values/transfermarkt_teams.parquet") for p in paths
        ), "bare transfermarkt_teams.parquet fallback missing"

    # (c) league= without season= — PLAYER_VALUES
    def test_player_values_league_without_season_candidate(self) -> None:
        """league_id provided: entity=player_values/league={L}/player_values.parquet emitted."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "2024-08-01", league_id="BUNDESLIGA")
        assert any(
            "league=BUNDESLIGA/player_values.parquet" in p and "season=" not in p for p in paths
        ), "league-without-season player_values.parquet candidate missing"

    def test_player_values_league_without_season_legacy_name(self) -> None:
        """league_id provided: transfermarkt_teams.parquet also emitted for the per-league legacy shape."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "2024-08-01", league_id="BUNDESLIGA")
        assert any(
            "league=BUNDESLIGA/transfermarkt_teams.parquet" in p and "season=" not in p for p in paths
        ), "league-without-season transfermarkt_teams.parquet candidate missing"

    def test_player_values_no_league_no_league_candidates(self) -> None:
        """Without league_id the per-league-without-season candidates are NOT emitted."""
        paths = candidate_parquet_paths("PLAYER_VALUES", "2024-08-01")
        assert not any("league=" in p and "season=" not in p for p in paths), (
            "per-league-without-season candidates should only appear when league_id is provided"
        )
