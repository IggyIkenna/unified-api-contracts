"""Unit tests for ``get_entity_league_coverage`` / ``SPORTS_ENTITY_LEAGUE_COVERAGE``.

Covers the (entity -> covered-league allow-list) SSOT the sports enumerator
(``instruments-service/scripts/enumerate_expected_universe.py::_enumerate_v2_sports``)
consults to gate ``expected_unattempted`` seeding — a league outside an
entity's coverage set is a legitimate "source doesn't cover this league"
absence, not a real pending-fetch gap.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.domain.sports.provider_league_ids import (
    get_entity_league_coverage,
)


class TestAllLeagueEntities:
    """Entities with ``None`` coverage are expected on every fixture date,
    regardless of league."""

    @pytest.mark.parametrize("entity", ["FIXTURES", "TEAMS", "STANDINGS", "INJURIES", "FIXTURE_STATS", "MATCHES"])
    def test_none_means_all_leagues_covered(self, entity: str) -> None:
        assert get_entity_league_coverage(entity) is None

    def test_unknown_entity_defaults_to_none(self) -> None:
        """An entity with no registry entry is treated as all-leagues-covered
        (conservative — never gates out a data_type nobody has classified yet)."""
        assert get_entity_league_coverage("SOME_UNKNOWN_ENTITY") is None


class TestOddsHorizonBucketCoverage:
    """odds_horizon_bucket (mdps_odds_horizon_bucket): the provider only lists
    markets for major domestic top flights — cup/lower-tier leagues
    structurally never appear
    (sports_post_backfill_relabel_premise_resolved_residual_gap_2026_07_25.md).
    """

    def test_returns_a_frozenset_not_none(self) -> None:
        cov = get_entity_league_coverage("ODDS_HORIZON_BUCKET")
        assert cov is not None
        assert isinstance(cov, frozenset)

    @pytest.mark.parametrize(
        "league_id",
        ["EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1", "BRASILEIRAO", "MLS", "A_LEAGUE"],
    )
    def test_major_top_flights_covered(self, league_id: str) -> None:
        cov = get_entity_league_coverage("ODDS_HORIZON_BUCKET")
        assert cov is not None
        assert league_id in cov

    @pytest.mark.parametrize(
        "league_id",
        ["COPA_DEL_REY", "CARABAO_CUP", "BRASILEIRAO_SERIE_B", "AUSTRIAN_2_LIGA"],
    )
    def test_cup_and_lower_tier_leagues_not_covered(self, league_id: str) -> None:
        """These are the exact examples cited in the diagnosed residual —
        real leagues the provider structurally never lists odds markets for."""
        cov = get_entity_league_coverage("ODDS_HORIZON_BUCKET")
        assert cov is not None
        assert league_id not in cov

    def test_case_insensitive_entity_lookup(self) -> None:
        assert get_entity_league_coverage("odds_horizon_bucket") == get_entity_league_coverage("ODDS_HORIZON_BUCKET")


class TestUnderstatXgLeagueScopedCoverage:
    """Pre-existing entry (not touched by this change) — regression guard
    that the shared mechanism still works for a different entity."""

    def test_xg_covers_only_the_big5(self) -> None:
        cov = get_entity_league_coverage("XG")
        assert cov == frozenset({"EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"})
