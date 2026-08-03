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
from unified_api_contracts.sports import get_mvp_football_league_ids


class TestAllLeagueEntities:
    """Entities with ``None`` coverage are expected on every fixture date,
    regardless of league. FIXTURE_STATS (game results) / FIXTURE_LINEUPS joined
    this set 2026-07-28 (operator ruling) — results and lineups are needed
    across the full curated universe, not just MVP/prediction scope, same as
    INJURIES. MATCHES LEFT this set 2026-08-03 — see
    ``TestFootystatsSubscriptionScopedCoverage`` below."""

    @pytest.mark.parametrize(
        "entity", ["FIXTURES", "TEAMS", "STANDINGS", "INJURIES", "FIXTURE_STATS", "FIXTURE_LINEUPS"]
    )
    def test_none_means_all_leagues_covered(self, entity: str) -> None:
        assert get_entity_league_coverage(entity) is None

    def test_unknown_entity_defaults_to_none(self) -> None:
        """An entity with no registry entry is treated as all-leagues-covered
        (conservative — never gates out a data_type nobody has classified yet)."""
        assert get_entity_league_coverage("SOME_UNKNOWN_ENTITY") is None


class TestPerFixtureEnrichmentEntitiesMvpScoped:
    """FIXTURE_EVENTS/PLAYER_STATS coverage is the MVP league set (96), NOT
    ``None`` (all leagues) — this per-event/per-player-granularity enrichment
    must not follow the much wider FIXTURES curated-universe denominator (383
    leagues) out past MVP/prediction scope. Distinct from FIXTURE_STATS/
    FIXTURE_LINEUPS (moved to ``TestAllLeagueEntities`` 2026-07-28) and from
    TEAMS/STANDINGS/INJURIES, which are a deliberate all-leagues decision
    (2026-07-13 fix, see ``sports_reference_core.py`` docstring)."""

    @pytest.mark.parametrize("entity", ["FIXTURE_EVENTS", "PLAYER_STATS"])
    def test_coverage_equals_mvp_leagues_not_none(self, entity: str) -> None:
        cov = get_entity_league_coverage(entity)
        assert cov is not None
        assert cov == get_mvp_football_league_ids()

    @pytest.mark.parametrize("entity", ["FIXTURE_EVENTS", "PLAYER_STATS"])
    def test_widened_curated_universe_only_league_not_covered(self, entity: str) -> None:
        """A league that's in the wider FIXTURES curated universe but NOT
        ``in_mvp_scope`` must be absent from enrichment coverage."""
        from unified_api_contracts.canonical.domain.sports.league_data import LEAGUE_REGISTRY

        non_mvp_widened = next(lg for lg in LEAGUE_REGISTRY.values() if lg.sport == "FOOTBALL" and not lg.in_mvp_scope)
        cov = get_entity_league_coverage(entity)
        assert cov is not None
        assert non_mvp_widened.league_id not in cov


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


class TestFootystatsSubscriptionScopedCoverage:
    """MATCHES/PREDICTIONS/ODDS coverage is subscription-scoped
    (``_FOOTYSTATS_LEAGUE_COVERAGE``), NOT ``None`` (all leagues) — fix for the
    structural blind spot in
    footystats_matches_predictions_odds_pending_fetch_universe_expansion_2026_07_27.md's
    [CODE] P2 follow-up. Before this fix the enumerator had NO footystats
    subscription gate at all: MATCHES/PREDICTIONS mapped to ``None`` and ODDS
    wasn't even a key, so it kept seeding fresh ``expected_unattempted`` rows
    for PRED_NO_FOOTYSTATS leagues forever, regardless of the fetch-loop
    write-gate or how many times the non-covered-league typing scripts were
    re-applied (their covered-league check is purely historical-capture-based
    and can never un-cover a league contaminated by even one pre-write-gate
    incidental captured row). Mirrors ``TestUnderstatXgLeagueScopedCoverage``
    above — the same shared (entity -> league allow-list) mechanism, a
    different source."""

    @pytest.mark.parametrize("entity", ["MATCHES", "PREDICTIONS", "ODDS"])
    def test_returns_a_frozenset_not_none(self, entity: str) -> None:
        cov = get_entity_league_coverage(entity)
        assert cov is not None
        assert isinstance(cov, frozenset)

    @pytest.mark.parametrize("entity", ["MATCHES", "PREDICTIONS", "ODDS"])
    def test_major_covered_league_included(self, entity: str) -> None:
        cov = get_entity_league_coverage(entity)
        assert cov is not None
        assert "EPL" in cov

    @pytest.mark.parametrize("entity", ["MATCHES", "PREDICTIONS", "ODDS"])
    @pytest.mark.parametrize("league_id", ["CHILE_PRIMERA", "K_LEAGUE_1", "LIGA_MX", "ARGENTINA_PRIMERA"])
    def test_pred_no_footystats_leagues_excluded(self, entity: str, league_id: str) -> None:
        """The exact 4 leagues diagnosed as contaminating the non-covered-league
        typing scripts' historical-capture-based covered-league check must be
        excluded from the enumerator's own denominator too — the fix closes
        the gap at its source (the seeder), not just the typing-script symptom."""
        cov = get_entity_league_coverage(entity)
        assert cov is not None
        assert league_id not in cov

    def test_matches_the_fetch_loop_write_gate_denominator(self) -> None:
        """MATCHES/PREDICTIONS/ODDS must all share the IDENTICAL denominator
        the fetch-loop write-gate already uses
        (instruments-service/engine/orchestrator/footystats.py's
        ``get_expected_leagues_for_source("footystats", classifications=
        ["Prediction", "Features"])``) — not three independently-drifting sets."""
        from unified_api_contracts.canonical.domain.sports.league_data import get_expected_leagues_for_source

        expected = frozenset(
            lg.league_id
            for lg in get_expected_leagues_for_source("footystats", classifications=["Prediction", "Features"])
        )
        for entity in ("MATCHES", "PREDICTIONS", "ODDS"):
            assert get_entity_league_coverage(entity) == expected
