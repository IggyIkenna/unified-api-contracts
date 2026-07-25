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
        # 131 football - 5 big-5 (China+Russia added 2026-07-21; +11 curated-universe
        # continental cups/majors + 15 curated-universe domestic top+below+cup
        # (Ukraine/Croatia/Morocco/Serbia/Egypt) + 9 curated-universe Central Asia
        # (Kazakhstan/Kyrgyzstan/Tajikistan/Turkmenistan/Uzbekistan) + 19 curated-universe
        # South America/CONMEBOL (Bolivia/Colombia/Ecuador/Paraguay/Peru/Uruguay/Venezuela)
        # + 49 Eastern Europe (UEFA) domestic top+below+cup (16 countries, Crimea
        # skipped) + 30 Middle East/AFC-WAFF (Bahrain/Iran/Iraq/Israel/Jordan/Kuwait/
        # Lebanon/Oman/Palestine/Qatar/Saudi Arabia/Syria/UAE/Yemen) + 16 West Africa
        # (Benin/Cameroon/Congo/Gabon/Gambia/Ghana/Guinea/Liberia/Mali/Mauritania/
        # Nigeria/Senegal/Togo) + 30 North/East/Southern Africa (CAF, 21 countries)
        # + 10 South Asia (AFC, 6 countries), all added 2026-07-25, in_mvp_scope=False
        # but still genuine Understat gaps — verified below, not assumed)
        assert len(others) == 280
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


class TestGetExpectedLeaguesConsultsStructuralGap:
    """``get_expected_leagues_for_source`` must actually CALL
    ``is_sports_structural_gap`` — not just happen to agree with it because
    ``data_sources`` is hand-curated the same way. Proven by monkeypatching a
    synthetic gap for a league that ``data_sources`` alone would NOT exclude,
    so the test can only pass if the structural-gap check is really wired in."""

    def test_synthetic_gap_excludes_a_league_data_sources_would_keep(self, monkeypatch: object) -> None:
        import unified_api_contracts.canonical.domain.sports.league_data as league_data_module
        from unified_api_contracts.canonical.domain.sports.league_data import (
            LEAGUE_REGISTRY,
            get_expected_leagues_for_source,
        )

        # EPL carries api_football in its data_sources and has no real gap —
        # confirm the baseline before injecting the synthetic one.
        assert "api_football" in LEAGUE_REGISTRY["EPL"].data_sources
        before = {lg.league_id for lg in get_expected_leagues_for_source("api_football")}
        assert "EPL" in before

        synthetic_gaps = {**league_data_module.SPORTS_STRUCTURAL_GAPS, "api_football": frozenset({"EPL"})}
        monkeypatch.setattr(league_data_module, "SPORTS_STRUCTURAL_GAPS", synthetic_gaps)  # type: ignore[attr-defined]

        after = {lg.league_id for lg in get_expected_leagues_for_source("api_football")}
        assert "EPL" not in after
        assert after == before - {"EPL"}


class TestIsCupProperty:
    """``LeagueDefinition.is_cup`` — derived from ``tier == 0`` scoped to football."""

    def test_known_cups_are_cups(self) -> None:
        for lid in ("FA_CUP", "COPA_DEL_REY", "DFB_POKAL", "COPPA_ITALIA"):
            assert LEAGUE_REGISTRY[lid].is_cup, f"{lid} should be a cup"

    def test_known_leagues_are_not_cups(self) -> None:
        for lid in ("EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"):
            assert not LEAGUE_REGISTRY[lid].is_cup, f"{lid} should not be a cup"

    def test_is_cup_matches_tier_zero_football(self) -> None:
        for league in LEAGUE_REGISTRY.values():
            expected = league.tier == 0 and league.sport == "FOOTBALL"
            assert league.is_cup == expected, f"{league.league_id}: is_cup mismatch"
