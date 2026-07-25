"""Lock the WEATHER SSOT layout — ``PER_DAY_PER_LEAGUE`` (2026-07-25).

Pre-2026-07-25 WEATHER was incorrectly tagged ``PER_DAY_BARE`` — the same
drift class already fixed for PLAYER_VALUES (2026-05-05, see
``test_gcs_paths_player_values.py``). The IS weather writer
(``instruments_service/engine/orchestrator/weather.py``) emits ONE
per-league partitioned parquet per (date, league) — "Per-league partitioned
write — single SSOT, no bare write" per its own code comment — confirmed
both in code and via live GCS listing (2026-07-25): every ``entity=weather``
object found on disk lives under a ``league=`` subpartition, zero bare
``entity=weather/weather.parquet`` objects exist.

``candidate_parquet_paths()`` derived its probe path from the (wrong)
``PER_DAY_BARE`` layout, so it never built the ``league=`` path the writer
actually uses — the dispatcher reported every captured WEATHER object as
absent, feeding >=106 proven false positives into the sports phantom
ceiling (``issues/sports_weather_uac_layout_per_day_bare_vs_writer_per_day_per_league_2026_07_20.md``).
This test locks the corrected SSOT so a future refactor can't silently
regress it back to the drifted state.
"""

from __future__ import annotations

from unified_api_contracts.sports import (
    SPORTS_DATA_TYPE_LAYOUT,
    SPORTS_DATA_TYPE_TO_FOLDER,
    SportsPathLayout,
    candidate_parquet_paths,
)


class TestWeatherSSOT:
    """Lock the post-2026-07-25 WEATHER SSOT alignment."""

    def test_folder_is_weather(self) -> None:
        assert SPORTS_DATA_TYPE_TO_FOLDER["WEATHER"] == "weather"

    def test_layout_is_per_day_per_league(self) -> None:
        """Layout must match how the writer actually partitions on disk:
        entity=weather/league={L}/weather.parquet — NOT the bare
        entity=weather/weather.parquet the pre-2026-07-25 SSOT declared."""
        assert SPORTS_DATA_TYPE_LAYOUT["WEATHER"] == SportsPathLayout.PER_DAY_PER_LEAGUE

    def test_candidate_paths_build_the_league_path(self) -> None:
        """The primary regression gate: with a league_id, candidate_parquet_paths
        must build the league= path the writer actually uses (mirrors the
        existing PLAYER_VALUES alignment test)."""
        paths = candidate_parquet_paths("WEATHER", "2026-07-10", league_id="K_LEAGUE_2")
        assert "sports_reference/by_date/day=2026-07-10/entity=weather/league=K_LEAGUE_2/weather.parquet" in paths

    def test_league_path_precedes_bare_fallback(self) -> None:
        """The per-league path (the real writer output) must be probed before
        the bare fallback (which no longer corresponds to any real object)."""
        paths = candidate_parquet_paths("WEATHER", "2026-07-10", league_id="K_LEAGUE_2")
        league_idx = paths.index(
            "sports_reference/by_date/day=2026-07-10/entity=weather/league=K_LEAGUE_2/weather.parquet"
        )
        bare_idx = paths.index("sports_reference/by_date/day=2026-07-10/entity=weather/weather.parquet")
        assert league_idx < bare_idx

    def test_no_league_id_omits_league_candidate(self) -> None:
        """Without league_id, only the bare fallback is returned (can't build
        the per-league path without knowing the league)."""
        paths = candidate_parquet_paths("WEATHER", "2026-07-10")
        assert not any("league=" in p for p in paths)
        assert "sports_reference/by_date/day=2026-07-10/entity=weather/weather.parquet" in paths

    def test_pipeline_mode_prepends_canonical_league_path(self) -> None:
        """pipeline_mode-aware candidate is probed first, still per-league."""
        paths = candidate_parquet_paths(
            "WEATHER", "2026-07-10", league_id="K_LEAGUE_2", pipeline_mode="batch_open_meteo"
        )
        assert paths[0] == (
            "sports_reference/by_date/day=2026-07-10/pipeline_mode=batch_open_meteo/"
            "entity=weather/league=K_LEAGUE_2/weather.parquet"
        )
