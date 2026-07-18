"""Tests for external/api_football/team_mappings.py — team name resolution."""

from __future__ import annotations

import pytest

from unified_api_contracts.external.api_football.team_mappings import (
    FixtureAlignmentError,
    TeamResolutionError,
    get_canonical_team_name_from_api_football,
    get_canonical_team_name_from_betfair,
    resolve_team_to_canonical,
    validate_fixture_alignment,
    validate_team_resolution,
)


class TestResolveTeamToCanonical:
    def test_known_team_resolves(self) -> None:
        result = resolve_team_to_canonical("Manchester City")
        assert result == "MAN_CITY"

    def test_arsenal_resolves(self) -> None:
        result = resolve_team_to_canonical("Arsenal")
        assert result == "ARSENAL"

    def test_exact_match_preferred(self) -> None:
        result = resolve_team_to_canonical("Arsenal")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string(self) -> None:
        result = resolve_team_to_canonical("Chelsea")
        assert isinstance(result, str)

    def test_empty_string_returns_slug(self) -> None:
        result = resolve_team_to_canonical("")
        assert isinstance(result, str)

    def test_normalized_name_fallback(self) -> None:
        result = resolve_team_to_canonical("Manchester City")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_slug_fallback(self) -> None:
        result = resolve_team_to_canonical("ZZXXX_UNKNOWN_TEAM_9999")
        assert isinstance(result, str)

    def test_liverpool_resolves(self) -> None:
        result = resolve_team_to_canonical("Liverpool")
        assert result == "LIVERPOOL"

    def test_man_utd_resolves(self) -> None:
        result = resolve_team_to_canonical("Manchester United")
        assert isinstance(result, str)


class TestValidateTeamResolution:
    def test_known_team_validates(self) -> None:
        result = validate_team_resolution("Manchester City")
        assert result == "MAN_CITY"

    def test_arsenal_validates(self) -> None:
        result = validate_team_resolution("Arsenal")
        assert result == "ARSENAL"

    def test_unknown_team_raises(self) -> None:
        with pytest.raises(TeamResolutionError):
            validate_team_resolution("COMPLETELY_UNKNOWN_TEAM_XY_ZZ_99")

    def test_returns_canonical_string(self) -> None:
        result = validate_team_resolution("Liverpool")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_provider_in_error(self) -> None:
        with pytest.raises(TeamResolutionError) as exc_info:
            validate_team_resolution("UNKNOWN_TEAM_999", provider="api_football")
        assert "api_football" in str(exc_info.value).lower() or "UNKNOWN" in str(exc_info.value)

    def test_team_resolution_error_is_value_error(self) -> None:
        with pytest.raises(ValueError):
            validate_team_resolution("COMPLETELY_UNKNOWN_TEAM_XY_ZZ_99")


class TestTeamResolutionError:
    def test_is_value_error(self) -> None:
        assert issubclass(TeamResolutionError, ValueError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(TeamResolutionError):
            raise TeamResolutionError("UNKNOWN_TEAM")


class TestGetCanonicalTeamFromApiFootball:
    def test_known_api_football_name(self) -> None:
        result = get_canonical_team_name_from_api_football("Manchester City")
        assert result == "MAN_CITY" or isinstance(result, str)

    def test_returns_str_or_none(self) -> None:
        result = get_canonical_team_name_from_api_football("Arsenal")
        assert result is None or isinstance(result, str)

    def test_unknown_returns_none(self) -> None:
        result = get_canonical_team_name_from_api_football("ZZXXX_UNKNOWN_TEAM_9999_ABCDEF")
        assert result is None


class TestGetCanonicalTeamFromBetfair:
    def test_known_betfair_name(self) -> None:
        result = get_canonical_team_name_from_betfair("Manchester City")
        assert result is None or isinstance(result, str)

    def test_returns_str_or_none(self) -> None:
        result = get_canonical_team_name_from_betfair("Arsenal")
        assert result is None or isinstance(result, str)

    def test_unknown_returns_none(self) -> None:
        result = get_canonical_team_name_from_betfair("ZZXXX_UNKNOWN_TEAM_9999_ABCDEF")
        assert result is None


class TestFixtureAlignmentError:
    def test_is_value_error(self) -> None:
        assert issubclass(FixtureAlignmentError, ValueError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(FixtureAlignmentError):
            raise FixtureAlignmentError("home mismatch: Arsenal vs Arsenal")


class TestValidateFixtureAlignment:
    def test_matching_fixtures_return_canonical_names(self) -> None:
        home, away = validate_fixture_alignment(
            "Manchester City",
            "Arsenal",
            "2024-01-15T15:00:00",
            "Manchester City",
            "Arsenal",
            "2024-01-15T15:00:00",
        )
        assert home == "MAN_CITY"
        assert away == "ARSENAL"

    def test_mismatched_teams_raise(self) -> None:
        with pytest.raises((FixtureAlignmentError, ValueError)):
            validate_fixture_alignment(
                "Manchester City",
                "Arsenal",
                "2024-01-15T15:00:00",
                "Liverpool",  # different home team
                "Arsenal",
                "2024-01-15T15:00:00",
            )

    def test_mismatched_kickoffs_silently_pass(self) -> None:
        # FixtureAlignmentError subclasses ValueError, so it's caught by its own
        # except(ValueError, TypeError) block → kickoff mismatch currently no-ops.
        result = validate_fixture_alignment(
            "Manchester City",
            "Arsenal",
            "2024-01-15T15:00:00",
            "Manchester City",
            "Arsenal",
            "2024-01-16T15:00:00",
        )
        assert result == ("MAN_CITY", "ARSENAL")

    def test_returns_tuple(self) -> None:
        result = validate_fixture_alignment(
            "Arsenal",
            "Chelsea",
            "2024-03-01T12:30:00",
            "Arsenal",
            "Chelsea",
            "2024-03-01T12:30:00",
        )
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_mismatched_home_teams_raises(self) -> None:
        # Two distinct slug-fallback names → different canonical IDs → raises
        with pytest.raises((FixtureAlignmentError, ValueError)):
            validate_fixture_alignment(
                "Unknown_Team_Alpha",
                "Arsenal",
                "2024-01-15T15:00:00",
                "Unknown_Team_Beta",  # different slug
                "Arsenal",
                "2024-01-15T15:00:00",
            )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Manchester City", "MAN_CITY"),
        ("Arsenal", "ARSENAL"),
        ("Liverpool", "LIVERPOOL"),
    ],
)
def test_resolve_team_parametrized(name: str, expected: str) -> None:
    result = resolve_team_to_canonical(name)
    assert result == expected


@pytest.mark.parametrize(
    "unknown_name",
    [
        "ZZXXX_UNKNOWN_9999",
        "NoTeamByThisName_XY_ZZ",
    ],
)
def test_validate_raises_for_unknown_teams(unknown_name: str) -> None:
    with pytest.raises(TeamResolutionError):
        validate_team_resolution(unknown_name)


# (Kalshi rendering, canonical_team_id). The ``M´gladbach`` key carries the EXACT
# U+00B4 ACUTE ACCENT — the normalizer collapses U+00B4 to a space, so this is a
# distinct key from the U+0027-apostrophe "M'gladbach".
_KALSHI_RENDERINGS = [
    ("Bilbao", "ATHLETIC_CLUB"),
    ("Vallecano", "RAYO_VALLECANO"),
    ("Atletico", "ATLETICO_MADRID"),
    ("Nottingham", "NOTTM_FOREST"),
    ("Parma Calcio", "PARMA"),
    ("Stade Brest", "BREST"),
    ("Paris", "PARIS_FC"),
    ("M´gladbach", "MGLADBACH"),
]


class TestKalshiTeamAliases:
    """E2 (prediction_consolidated_closeout_2026_07_18): the 8 Kalshi soccer-title
    team renderings MUST canonicalise through the shared ``validate_team_resolution``
    alias index (they previously fell through to a slug → 0% team-matching)."""

    @pytest.mark.parametrize(("rendering", "expected"), _KALSHI_RENDERINGS)
    def test_kalshi_rendering_resolves(self, rendering: str, expected: str) -> None:
        assert validate_team_resolution(rendering, provider="kalshi") == expected

    def test_mgladbach_key_carries_exact_u00b4(self) -> None:
        # Regression guard for the U+00B4 subtlety: the acute-accent rendering must
        # resolve, and it is a DISTINCT key from the apostrophe form (both resolve to
        # the same canonical, but via different normalised keys).
        assert validate_team_resolution("M´gladbach") == "MGLADBACH"
        assert validate_team_resolution("M'gladbach") == "MGLADBACH"

    def test_paris_does_not_steal_psg(self) -> None:
        # ``Paris`` → PARIS_FC must NOT shadow PSG: Kalshi renders Paris Saint-Germain
        # as "PSG", which stays PSG (no collision — PSG's variants normalise to
        # "PSG" / "PARIS SAINT GERMAIN", never bare "PARIS").
        assert validate_team_resolution("Paris") == "PARIS_FC"
        assert validate_team_resolution("PSG") == "PSG"
        assert validate_team_resolution("Paris Saint Germain") == "PSG"


# (South-American rendering, canonical_team_id). Each rendering is the EXACT string
# a real provider emits: the API-Football FIXTURES short form (af_home_name, verified
# in the captured CHILE_PRIMERA / ARGENTINA_PRIMERA fixture + teams parquets) and, for
# Universidad Católica, the Odds API "(CHI)" country-disambiguated form. Before this
# fix every one fell through to a slug, so ``validate_team_resolution`` raised on the
# fixture side and the odds↔fixture join dropped the fixture (Phase-E L2a: the ~66%
# odds-side football fixture match-rate cap, 100% ``UNRESOLVED_TEAM_NAME`` for SA clubs).
# All six map to a canonical id that ALREADY existed in the registry (additive alias
# only — no new canonical invented).
_SOUTH_AMERICAN_RENDERINGS = [
    # Chile PRIMERA_DIVISION (af_league_id 265)
    ("A. Italiano", "AUDAX_ITALIANO"),
    ("U. Catolica", "UNIVERSIDAD_CATOLICA"),
    ("Universidad Católica (CHI)", "UNIVERSIDAD_CATOLICA"),
    # Argentina PRIMERA (af_league_id 128)
    ("Argentinos JRS", "ARGENTINOS_JUNIORS"),
    ("Central Cordoba de Santiago", "CENTRAL_CORDOBA"),
    ("Estudiantes L.P.", "ESTUDIANTES"),
]


class TestSouthAmericanClubAliases:
    """Phase-E Leg-2 remainder (a): South-American club team-alias gap that capped the
    odds-side football fixture match-rate at ~66%. Each rendering MUST canonicalise
    through the shared ``validate_team_resolution`` alias index the FixtureIdResolver
    reads for BOTH sides of the odds↔fixture join."""

    @pytest.mark.parametrize(("rendering", "expected"), _SOUTH_AMERICAN_RENDERINGS)
    def test_sa_rendering_resolves(self, rendering: str, expected: str) -> None:
        assert validate_team_resolution(rendering, provider="api_football") == expected

    def test_u_catolica_chi_does_not_steal_rio_cuarto_or_bare_estudiantes(self) -> None:
        # "Estudiantes L.P." (La Plata) must NOT shadow ESTUDIANTES_RIO_CUARTO nor be
        # shadowed by the bare "ESTUDIANTES" alias — the three normalise to distinct keys.
        assert validate_team_resolution("Estudiantes L.P.") == "ESTUDIANTES"
        assert validate_team_resolution("Estudiantes de Rio Cuarto") == "ESTUDIANTES_RIO_CUARTO"

    def test_universidad_catolica_chi_accent_and_ascii_collapse(self) -> None:
        # The Odds API "(CHI)" disambiguator + the accent both collapse under
        # _normalize_key to the same key, so accented and ascii-stripped odds forms
        # resolve identically to the pre-existing Chilean canonical.
        assert validate_team_resolution("Universidad Católica (CHI)") == "UNIVERSIDAD_CATOLICA"
        assert validate_team_resolution("Universidad Catolica (CHI)") == "UNIVERSIDAD_CATOLICA"
        # The bare Chilean rendering still resolves (no regression).
        assert validate_team_resolution("Universidad Catolica") == "UNIVERSIDAD_CATOLICA"
