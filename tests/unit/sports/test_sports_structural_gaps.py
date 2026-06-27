"""Unit tests for the sports structural (league × source) honest-absence registry.

operator 2026-06-27 decision #6: encode the (league × source) combos a source
STRUCTURALLY does not carry so honest-coverage treats them as expected-absent
AND the IS sports producers skip them (no attempt → no ``attempted_failed``).

SSOT: ``unified_api_contracts.canonical.domain.sports.league_data`` —
``SPORTS_STRUCTURAL_GAPS`` / ``SPORTS_SOURCE_LEAGUE_ALLOWLIST`` /
``is_sports_structural_gap``.
"""

from __future__ import annotations

from unified_api_contracts.canonical.domain.sports.league_data import (
    LEAGUE_REGISTRY,
    SPORTS_SOURCE_LEAGUE_ALLOWLIST,
    SPORTS_STRUCTURAL_GAPS,
    is_sports_structural_gap,
)


class TestExplicitStructuralGaps:
    """A_LEAGUE × footystats and GREEK_SUPER_LEAGUE × transfermarkt."""

    def test_a_league_footystats_is_gap(self) -> None:
        assert is_sports_structural_gap("footystats", "A_LEAGUE")

    def test_greek_super_league_transfermarkt_is_gap(self) -> None:
        assert is_sports_structural_gap("transfermarkt", "GREEK_SUPER_LEAGUE")

    def test_non_gap_leagues_not_flagged(self) -> None:
        assert not is_sports_structural_gap("footystats", "EPL")
        assert not is_sports_structural_gap("transfermarkt", "EPL")
        # A_LEAGUE is only a gap for footystats, not transfermarkt.
        assert not is_sports_structural_gap("transfermarkt", "A_LEAGUE")

    def test_case_insensitive(self) -> None:
        assert is_sports_structural_gap("footystats", "a_league")
        assert is_sports_structural_gap("transfermarkt", "greek_super_league")

    def test_registry_membership(self) -> None:
        assert SPORTS_STRUCTURAL_GAPS["footystats"] == frozenset({"A_LEAGUE"})
        assert SPORTS_STRUCTURAL_GAPS["transfermarkt"] == frozenset({"GREEK_SUPER_LEAGUE"})


class TestUnderstatAllowList:
    """understat carries ONLY the big-5 — every other league is a structural gap."""

    def test_big5_not_gaps(self) -> None:
        for lid in ("EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"):
            assert not is_sports_structural_gap("understat", lid), f"{lid} should be understat-carried"

    def test_non_big5_football_is_gap(self) -> None:
        for lid in ("MLS", "A_LEAGUE", "EREDIVISIE", "BRASILEIRAO", "J1_LEAGUE"):
            assert is_sports_structural_gap("understat", lid), f"{lid} should be an understat structural gap"

    def test_allowlist_is_exactly_big5(self) -> None:
        assert SPORTS_SOURCE_LEAGUE_ALLOWLIST["understat"] == frozenset(
            {"EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"}
        )

    def test_all_89_other_football_leagues_are_understat_gaps(self) -> None:
        big5 = {"EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"}
        football = [lg.league_id for lg in LEAGUE_REGISTRY.values() if lg.sport == "FOOTBALL"]
        others = [lid for lid in football if lid not in big5]
        assert len(others) == 89  # 94 football − 5 big-5
        for lid in others:
            assert is_sports_structural_gap("understat", lid)


class TestConsistencyWithDataSources:
    """The structural-gap SSOT must AGREE with the per-league ``data_sources``
    field (which drives ``get_expected_leagues_for_source`` → the IS sports
    adapters' skip logic). A declared structural gap MUST also be excluded from
    that source's expected-league set, and vice-versa for these combos."""

    def test_a_league_excluded_from_footystats_expected(self) -> None:
        from unified_api_contracts.canonical.domain.sports.league_data import (
            get_expected_leagues_for_source,
        )

        expected = {lg.league_id for lg in get_expected_leagues_for_source("footystats")}
        assert "A_LEAGUE" not in expected
        assert is_sports_structural_gap("footystats", "A_LEAGUE")

    def test_greek_excluded_from_transfermarkt_expected(self) -> None:
        from unified_api_contracts.canonical.domain.sports.league_data import (
            get_expected_leagues_for_source,
        )

        expected = {lg.league_id for lg in get_expected_leagues_for_source("transfermarkt")}
        assert "GREEK_SUPER_LEAGUE" not in expected
        assert is_sports_structural_gap("transfermarkt", "GREEK_SUPER_LEAGUE")

    def test_understat_expected_set_equals_allowlist(self) -> None:
        from unified_api_contracts.canonical.domain.sports.league_data import (
            get_expected_leagues_for_source,
        )

        expected = {lg.league_id for lg in get_expected_leagues_for_source("understat")}
        assert expected == SPORTS_SOURCE_LEAGUE_ALLOWLIST["understat"]


class TestUnaffectedSources:
    """A source with no structural-gap entry never flags any league."""

    def test_api_football_no_structural_gaps(self) -> None:
        # api_football carries broad coverage — no structural-gap entry.
        for lid in ("EPL", "A_LEAGUE", "GREEK_SUPER_LEAGUE", "MLS"):
            assert not is_sports_structural_gap("api_football", lid)

    def test_unknown_source_never_a_gap(self) -> None:
        assert not is_sports_structural_gap("some_unknown_source", "EPL")
