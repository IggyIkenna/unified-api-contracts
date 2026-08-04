"""Regression tests for ``normalize_api_football_fixture``'s league_id resolution.

Root-caused 2026-08-04
(``sports_peripheral_bucket_league_vocabulary_contamination_2026_07_20.md``): the
fixture normalizer used to build ``CanonicalLeague.league_id`` from a bare
``build_league_id(country, name)`` slug of the raw api-football COUNTRY NAME
("England" -> "ENGLAND_PREMIER_LEAGUE") instead of the UAC league registry's
canonical slug ("EPL") — a completely different, ungoverned vocabulary from every
other sports write path. These tests lock in the fix: registry-first resolution via
the numeric ``api_football_id``, non-lossy fallback to the raw slug only when the
league genuinely isn't in the registry.
"""

from __future__ import annotations

from unified_api_contracts.external.api_football.normalize import (
    normalize_api_football_fixture,
)
from unified_api_contracts.external.api_football.schemas import (
    ApiFootballFixture,
    ApiFootballLeague,
)


def _fixture(*, league: ApiFootballLeague | None) -> ApiFootballFixture:
    return ApiFootballFixture(id=123, date="2026-03-22T15:00:00+00:00", league=league)


def test_registered_league_resolves_via_registry_not_raw_slug() -> None:
    """api_football_id=39 (EPL) with a raw display country/name that would slug to
    the contaminated "ENGLAND_PREMIER_LEAGUE" form must resolve to the registry's
    canonical "EPL" instead."""
    league = ApiFootballLeague(id=39, name="Premier League", country="England", type="League")
    fixture = normalize_api_football_fixture(_fixture(league=league))

    assert fixture.league.league_id == "EPL"
    assert fixture.league.league_id != "ENGLAND_PREMIER_LEAGUE"
    assert fixture.league.api_football_id == 39


def test_registered_league_never_produces_country_prefixed_slug() -> None:
    """For ANY registered league (id resolves via the registry), the result must
    never be the raw ``{COUNTRY}_{LEAGUE}`` slug shape the contamination reports
    described — it must be the registry's own short canonical form."""
    league = ApiFootballLeague(id=61, name="Ligue 1", country="France", type="League")
    fixture = normalize_api_football_fixture(_fixture(league=league))

    assert fixture.league.league_id
    assert not fixture.league.league_id.startswith("FRANCE_")


def test_unregistered_league_falls_back_to_raw_slug_non_lossy() -> None:
    """A league with no registry entry for its api_football_id must NOT be
    dropped/blanked -- non-lossy CF-7 passthrough via the raw country/name slug,
    matching instruments-service's own documented invariant."""
    league = ApiFootballLeague(id=999999, name="Some Obscure Cup", country="Nowhereland", type="Cup")
    fixture = normalize_api_football_fixture(_fixture(league=league))

    assert fixture.league.league_id == "NOWHERELAND_SOME_OBSCURE_CUP"
    assert fixture.league.api_football_id == 999999


def test_no_api_football_id_falls_back_to_raw_slug() -> None:
    """A league payload with no numeric id at all (id=None) can't be registry-
    resolved -- falls back to the raw slug, same as the unregistered case."""
    league = ApiFootballLeague(id=None, name="Championship", country="England", type="League")
    fixture = normalize_api_football_fixture(_fixture(league=league))

    assert fixture.league.league_id == "ENGLAND_CHAMPIONSHIP"


def test_no_league_at_all_yields_blank_league_id() -> None:
    fixture = normalize_api_football_fixture(_fixture(league=None))
    assert fixture.league.league_id == ""
