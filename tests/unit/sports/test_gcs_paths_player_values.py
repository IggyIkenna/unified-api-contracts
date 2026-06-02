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
        # Canonical season-partitioned path first; bare-path fallback last.
        assert paths[0] == (
            "sports_reference/by_date/day=2024-08-01/entity=player_values/season=2024/player_values.parquet"
        )
        # league_id is NOT in the path — league filter happens intra-file.
        assert "league=" not in paths[0]
        # Bare fallback present so historic writes that omitted season still resolve.
        assert paths[-1] == ("sports_reference/by_date/day=2024-08-01/entity=player_values/player_values.parquet")

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
        # Three season candidates + bare fallback = 4 total.
        season_paths = [p for p in paths if "season=" in p]
        assert len(season_paths) == 3
        seasons = sorted({p.split("season=")[1].split("/")[0] for p in season_paths})
        assert seasons == ["2023", "2024", "2025"]
        bare_paths = [p for p in paths if "season=" not in p]
        assert len(bare_paths) == 1

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
