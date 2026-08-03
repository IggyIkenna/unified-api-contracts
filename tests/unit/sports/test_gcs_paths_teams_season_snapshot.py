"""Lock the TEAMS_SEASON_SNAPSHOT SSOT layout — ``FLAT_PER_SEASON`` (2026-08-03).

Ruled 2026-07-28 (Option A): add a net-new season-keyed FLAT layout for the
legacy ``day=all/entity=teams`` archive (30,069 rows, seasons 2019-2025)
instead of forcing a fake ``day=``/``league=`` label onto genuinely
season-keyed data to fit the existing PER_DAY_PER_LEAGUE layout the routine
daily "TEAMS" data_type uses. See
``plans/archive/2026_08/sports_day_all_teams_venues_fold_key_scheme_mismatch_2026_07_25.md``.
"""

from __future__ import annotations

from unified_api_contracts.sports import (
    SPORTS_DATA_TYPE_LAYOUT,
    SPORTS_DATA_TYPE_TO_FOLDER,
    TEAMS_SEASON_SNAPSHOT,
    SportsPathLayout,
    candidate_parquet_paths,
)


class TestTeamsSeasonSnapshotSSOT:
    """Lock the FLAT_PER_SEASON layout for TEAMS_SEASON_SNAPSHOT."""

    def test_folder_is_teams(self) -> None:
        """Shares the 'teams' folder name with the daily TEAMS data_type --
        the two never collide on disk because FLAT_PER_SEASON vs
        PER_DAY_PER_LEAGUE produce disjoint path shapes."""
        assert SPORTS_DATA_TYPE_TO_FOLDER[TEAMS_SEASON_SNAPSHOT] == "teams"

    def test_layout_is_flat_per_season(self) -> None:
        assert SPORTS_DATA_TYPE_LAYOUT[TEAMS_SEASON_SNAPSHOT] == SportsPathLayout.FLAT_PER_SEASON

    def test_daily_teams_data_type_is_unaffected(self) -> None:
        """The routine daily "TEAMS" data_type must stay PER_DAY_PER_LEAGUE --
        adding the season-keyed sibling must not touch it."""
        assert SPORTS_DATA_TYPE_LAYOUT["TEAMS"] == SportsPathLayout.PER_DAY_PER_LEAGUE
        assert SPORTS_DATA_TYPE_TO_FOLDER["TEAMS"] == "teams"

    def test_explicit_season_returns_exact_flat_path(self) -> None:
        paths = candidate_parquet_paths(TEAMS_SEASON_SNAPSHOT, "2024-08-01", season="2024")
        assert paths == ["sports_reference/teams/season=2024/teams.parquet"]

    def test_no_season_probes_three_year_window(self) -> None:
        paths = candidate_parquet_paths(TEAMS_SEASON_SNAPSHOT, "2024-08-01")
        seasons = sorted(p.split("season=")[1].split("/")[0] for p in paths)
        assert seasons == ["2023", "2024", "2025"]
        assert all(p.startswith("sports_reference/teams/season=") for p in paths)
        assert all(p.endswith("/teams.parquet") for p in paths)

    def test_no_by_date_partition_in_any_candidate(self) -> None:
        """FLAT_PER_SEASON has no by_date/day= segment anywhere -- distinguishes
        it from PER_DAY_PER_SEASON (e.g. PLAYER_VALUES)."""
        paths = candidate_parquet_paths(TEAMS_SEASON_SNAPSHOT, "2024-08-01", season="2024")
        assert all("by_date" not in p and "day=" not in p for p in paths)

    def test_league_id_ignored(self) -> None:
        """league_id is meaningless for a season-flat singleton -- passing one
        must not change the output."""
        with_league = candidate_parquet_paths(TEAMS_SEASON_SNAPSHOT, "2024-08-01", "EPL", season="2024")
        without_league = candidate_parquet_paths(TEAMS_SEASON_SNAPSHOT, "2024-08-01", season="2024")
        assert with_league == without_league

    def test_pipeline_mode_ignored(self) -> None:
        """FLAT_PER_SEASON has no date partition -- pipeline_mode is inapplicable,
        same as FLAT (VENUES)."""
        with_pm = candidate_parquet_paths(
            TEAMS_SEASON_SNAPSHOT, "2024-08-01", season="2024", pipeline_mode="batch_api_football"
        )
        without_pm = candidate_parquet_paths(TEAMS_SEASON_SNAPSHOT, "2024-08-01", season="2024")
        assert with_pm == without_pm

    def test_invalid_day_format_does_not_crash(self) -> None:
        """Bad day input with no explicit season -> year=0 fallback window,
        never a crash (mirrors PLAYER_VALUES's PER_DAY_PER_SEASON resilience)."""
        paths = candidate_parquet_paths(TEAMS_SEASON_SNAPSHOT, "not-a-date")
        assert any("sports_reference/teams/season=" in p for p in paths)

    def test_uri_helper_propagates_season_kwarg(self) -> None:
        from unified_api_contracts.sports import candidate_parquet_uris

        uris = candidate_parquet_uris(
            TEAMS_SEASON_SNAPSHOT,
            "2024-08-01",
            project_id="test-project",
            season="2024",
        )
        assert uris == [
            "gs://instruments-store-sports-prd-test-project/sports_reference/teams/season=2024/teams.parquet"
        ]
