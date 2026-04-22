"""Tests for ``get_expected_team_count_for_league`` and per-league seeds.

Plan: ``transfermarkt_sfi_team_mapping_cache_and_drift_detection_2026_04_22``.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from unified_api_contracts.sports import (
    LEAGUE_EXPECTED_TEAM_COUNTS,
    LEAGUE_REGISTRY,
    LeagueDefinition,
    get_expected_team_count_for_league,
)


@pytest.mark.unit
class TestSeedDict:
    def test_epl_20_teams_across_seasons(self) -> None:
        assert LEAGUE_EXPECTED_TEAM_COUNTS["EPL"][2020] == 20
        assert LEAGUE_EXPECTED_TEAM_COUNTS["EPL"][2024] == 20
        assert LEAGUE_EXPECTED_TEAM_COUNTS["EPL"][2026] == 20

    def test_bundesliga_18_teams(self) -> None:
        assert LEAGUE_EXPECTED_TEAM_COUNTS["BUNDESLIGA"][2024] == 18

    def test_mls_expansion_tracked_across_seasons(self) -> None:
        counts = LEAGUE_EXPECTED_TEAM_COUNTS["MLS"]
        assert counts[2020] == 26
        assert counts[2023] == 29
        assert counts[2026] == 30

    def test_ligue_1_shrinkage_2023(self) -> None:
        counts = LEAGUE_EXPECTED_TEAM_COUNTS["LIGUE_1"]
        assert counts[2022] == 20
        assert counts[2023] == 18
        assert counts[2024] == 18


@pytest.mark.unit
class TestAccessorKnownLeagues:
    def test_epl_known_season(self) -> None:
        assert get_expected_team_count_for_league("EPL", 2024) == 20

    def test_case_insensitive_league_id(self) -> None:
        assert get_expected_team_count_for_league("epl", 2024) == 20
        assert get_expected_team_count_for_league("Epl", 2024) == 20

    def test_mls_expansion_2026(self) -> None:
        assert get_expected_team_count_for_league("MLS", 2026) == 30

    def test_mls_expansion_2020(self) -> None:
        assert get_expected_team_count_for_league("MLS", 2020) == 26


@pytest.mark.unit
class TestAccessorUnknown:
    def test_unknown_league_returns_none(self) -> None:
        assert get_expected_team_count_for_league("FAKE_LEAGUE", 2024) is None

    def test_unseeded_season_returns_none(self) -> None:
        # 1999 is outside the 2020-2026 seed window.
        assert get_expected_team_count_for_league("EPL", 1999) is None

    def test_unseeded_league_with_known_id_returns_none(self) -> None:
        # Tier-3+ leagues below LIGA_3 are not seeded — silent skip.
        assert get_expected_team_count_for_league("LIGA_3_BELOW_TIER", 2024) is None


@pytest.mark.unit
class TestLeagueDefinitionField:
    def test_field_default_is_none(self) -> None:
        defn = LEAGUE_REGISTRY["EPL"]
        assert defn.expected_team_count_per_season is None

    def test_field_accepts_optional_per_instance_override(self) -> None:
        override = replace(
            LEAGUE_REGISTRY["EPL"],
            expected_team_count_per_season={2024: 22},
        )
        assert isinstance(override, LeagueDefinition)
        assert override.expected_team_count_per_season == {2024: 22}
        # Registry is untouched by a ``replace`` — the original definition stays
        # at its default ``None`` and the accessor continues to read from
        # ``LEAGUE_EXPECTED_TEAM_COUNTS``.
        assert LEAGUE_REGISTRY["EPL"].expected_team_count_per_season is None
        assert get_expected_team_count_for_league("EPL", 2024) == 20
