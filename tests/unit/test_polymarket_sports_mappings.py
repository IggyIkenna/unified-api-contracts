"""Tests for external/polymarket/sports_mappings.py — Polymarket sports market mappings."""

from __future__ import annotations

import pytest

from unified_api_contracts.external.polymarket.sports_mappings import (
    POLYMARKET_PREDICTION_LEAGUES,
    POLYMARKET_SERIES_TO_LEAGUE,
    POLYMARKET_SPORTS_TAG_SLUGS,
    get_canonical_league_for_polymarket_series,
    get_canonical_team_for_polymarket,
    get_polymarket_series_for_league,
    get_polymarket_sports_tag_for_league,
)


class TestPolymarketSportsTagSlugs:
    def test_frozenset(self) -> None:
        assert isinstance(POLYMARKET_SPORTS_TAG_SLUGS, frozenset)

    def test_soccer_included(self) -> None:
        assert "soccer" in POLYMARKET_SPORTS_TAG_SLUGS

    def test_football_included(self) -> None:
        assert "football" in POLYMARKET_SPORTS_TAG_SLUGS

    def test_premier_league_included(self) -> None:
        assert "premier-league" in POLYMARKET_SPORTS_TAG_SLUGS

    def test_non_empty(self) -> None:
        assert len(POLYMARKET_SPORTS_TAG_SLUGS) > 0

    def test_all_strings(self) -> None:
        for slug in POLYMARKET_SPORTS_TAG_SLUGS:
            assert isinstance(slug, str)


class TestPolymarketPredictionLeagues:
    def test_frozenset(self) -> None:
        assert isinstance(POLYMARKET_PREDICTION_LEAGUES, frozenset)

    def test_epl_included(self) -> None:
        assert "EPL" in POLYMARKET_PREDICTION_LEAGUES

    def test_la_liga_included(self) -> None:
        assert "LA_LIGA" in POLYMARKET_PREDICTION_LEAGUES

    def test_bundesliga_included(self) -> None:
        assert "BUNDESLIGA" in POLYMARKET_PREDICTION_LEAGUES

    def test_mls_included(self) -> None:
        assert "MLS" in POLYMARKET_PREDICTION_LEAGUES

    def test_non_empty(self) -> None:
        assert len(POLYMARKET_PREDICTION_LEAGUES) > 0

    def test_all_uppercase(self) -> None:
        for league in POLYMARKET_PREDICTION_LEAGUES:
            assert league == league.upper(), f"Expected uppercase league ID, got: {league}"


class TestPolymarketSeriesToLeague:
    def test_premier_league_maps_to_epl(self) -> None:
        assert POLYMARKET_SERIES_TO_LEAGUE["premier-league-2025"] == "EPL"

    def test_la_liga_series_maps_correctly(self) -> None:
        assert POLYMARKET_SERIES_TO_LEAGUE["la-liga-2025"] == "LA_LIGA"

    def test_efl_championship_maps_correctly(self) -> None:
        assert POLYMARKET_SERIES_TO_LEAGUE["efl-championship"] == "ENG_CHAMPIONSHIP"

    def test_non_empty(self) -> None:
        assert len(POLYMARKET_SERIES_TO_LEAGUE) > 0

    def test_all_values_are_canonical_league_ids(self) -> None:
        for league_id in POLYMARKET_SERIES_TO_LEAGUE.values():
            assert league_id == league_id.upper()


class TestGetPolymarketSportsTagForLeague:
    def test_epl_returns_premier_league(self) -> None:
        tag = get_polymarket_sports_tag_for_league("EPL")
        assert tag == "premier-league"

    def test_la_liga_returns_la_liga_slug(self) -> None:
        tag = get_polymarket_sports_tag_for_league("LA_LIGA")
        assert tag == "la-liga"

    def test_bundesliga_returns_bundesliga(self) -> None:
        tag = get_polymarket_sports_tag_for_league("BUNDESLIGA")
        assert tag == "bundesliga"

    def test_unknown_league_returns_none_or_generic(self) -> None:
        tag = get_polymarket_sports_tag_for_league("COMPLETELY_UNKNOWN_LEAGUE_XY")
        # Either None or falls back to "soccer"
        assert tag is None or tag in POLYMARKET_SPORTS_TAG_SLUGS

    def test_uppercase_canonical_id_required(self) -> None:
        # Functions expect canonical uppercase league IDs
        tag = get_polymarket_sports_tag_for_league("EPL")
        assert tag == "premier-league"
        tag_lower = get_polymarket_sports_tag_for_league("epl")
        # lowercase → None (not mapped)
        assert tag_lower is None


class TestGetCanonicalLeagueForPolymarketSeries:
    def test_premier_league_2025(self) -> None:
        result = get_canonical_league_for_polymarket_series("premier-league-2025")
        assert result == "EPL"

    def test_la_liga_2025(self) -> None:
        result = get_canonical_league_for_polymarket_series("la-liga-2025")
        assert result == "LA_LIGA"

    def test_efl_championship(self) -> None:
        result = get_canonical_league_for_polymarket_series("efl-championship")
        assert result == "ENG_CHAMPIONSHIP"

    def test_unknown_series_returns_none(self) -> None:
        result = get_canonical_league_for_polymarket_series("unknown-series-xyz")
        assert result is None

    def test_all_series_in_map_resolve(self) -> None:
        for series_slug, expected_league in POLYMARKET_SERIES_TO_LEAGUE.items():
            result = get_canonical_league_for_polymarket_series(series_slug)
            assert result == expected_league


class TestGetPolymarketSeriesForLeague:
    def test_epl_returns_premier_league_series(self) -> None:
        result = get_polymarket_series_for_league("EPL")
        assert result == "premier-league-2025"

    def test_la_liga_returns_correct_series(self) -> None:
        result = get_polymarket_series_for_league("LA_LIGA")
        assert result == "la-liga-2025"

    def test_unknown_league_returns_none(self) -> None:
        result = get_polymarket_series_for_league("COMPLETELY_UNKNOWN_LEAGUE_ZZ")
        assert result is None

    def test_roundtrip_via_series(self) -> None:
        series = get_polymarket_series_for_league("EPL")
        assert series is not None
        reverse = get_canonical_league_for_polymarket_series(series)
        assert reverse == "EPL"

    def test_uppercase_canonical_id_required(self) -> None:
        # Functions expect canonical uppercase league IDs
        result = get_polymarket_series_for_league("EPL")
        assert result == "premier-league-2025"


class TestGetCanonicalTeamForPolymarket:
    def test_inter_milan_resolves(self) -> None:
        result = get_canonical_team_for_polymarket("Inter Milan")
        assert result == "INTER_MILAN"

    def test_unknown_team_returns_none(self) -> None:
        result = get_canonical_team_for_polymarket("ZZXXX_UNKNOWN_TEAM_9999")
        assert result is None

    def test_non_alias_name_returns_none(self) -> None:
        result = get_canonical_team_for_polymarket("Arsenal")
        assert result is None

    def test_returns_string_or_none(self) -> None:
        for team in ["Inter Milan", "Liverpool", "Unknown Team XY"]:
            result = get_canonical_team_for_polymarket(team)
            assert result is None or isinstance(result, str)


@pytest.mark.parametrize(
    ("league_id", "expected_tag"),
    [
        ("EPL", "premier-league"),
        ("LA_LIGA", "la-liga"),
        ("BUNDESLIGA", "bundesliga"),
        ("SERIE_A", "serie-a"),
        ("LIGUE_1", "ligue-1"),
    ],
)
def test_sports_tag_for_league_parametrized(league_id: str, expected_tag: str) -> None:
    tag = get_polymarket_sports_tag_for_league(league_id)
    assert tag == expected_tag, f"Expected {expected_tag!r} for {league_id!r}, got {tag!r}"


@pytest.mark.parametrize(
    ("series_slug", "expected_league"),
    [
        ("premier-league-2025", "EPL"),
        ("la-liga-2025", "LA_LIGA"),
        ("efl-championship", "ENG_CHAMPIONSHIP"),
    ],
)
def test_canonical_league_for_series_parametrized(series_slug: str, expected_league: str) -> None:
    result = get_canonical_league_for_polymarket_series(series_slug)
    assert result == expected_league
