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
        assert uris[0].startswith("gs://instruments-store-sports-test-project/")
        assert "season=2024" in uris[0]
