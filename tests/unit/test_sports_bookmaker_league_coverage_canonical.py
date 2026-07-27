"""Regression lock for the BOOKMAKER_LEAGUE_COVERAGE canonical-id lookup path.

sports_satellite_ao_dispatch_batch7_2026_07_27.md todo 3 (Track H, "RESTORED
2026-07-24"): the observed coverage map (``registry/data/sports_bookmaker_league_coverage.json``)
was derived straight from the manifest's raw ``league_id`` column, which was not
always canonical — some historical captures recorded the raw Odds-API ``sport_key``
(e.g. ``SOCCER_EPL``) instead of the UAC canonical league id (``EPL``). The sports v2
sentinel (``sentinels.py``) calls ``is_bookmaker_league_covered`` with a CANONICAL
league id, so a book whose captured rows were keyed ONLY under the raw sport_key read
as uncovered — a standing false negative. Fixed by canonicalising at load time
(``canonicalize_odds_api_league_id`` in ``provider_league_ids.py``) and regenerating
the committed JSON so both live-code AND the raw data are honestly canonical.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.domain.sports.league_data import get_league
from unified_api_contracts.canonical.domain.sports.provider_league_ids import (
    canonicalize_odds_api_league_id,
)
from unified_api_contracts.registry.sports_bookmaker_league_coverage import (
    BOOKMAKER_LEAGUE_COVERAGE,
    is_bookmaker_league_covered,
)


@pytest.mark.unit
class TestCanonicalizeOddsApiLeagueId:
    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("SOCCER_EPL", "EPL"),
            ("soccer_epl", "EPL"),
            ("SOCCER_ARGENTINA_PRIMERA_DIVISION", "ARGENTINA_PRIMERA"),
            ("SOCCER_ITALY_SERIE_A", "SERIE_A"),
            ("SOCCER_USA_MLS", "MLS"),
        ],
    )
    def test_raw_sport_key_resolves_to_canonical(self, raw: str, canonical: str) -> None:
        assert canonicalize_odds_api_league_id(raw) == canonical

    def test_already_canonical_is_unchanged(self) -> None:
        assert canonicalize_odds_api_league_id("EPL") == "EPL"
        assert canonicalize_odds_api_league_id("epl") == "EPL"

    def test_idempotent(self) -> None:
        once = canonicalize_odds_api_league_id("SOCCER_EPL")
        twice = canonicalize_odds_api_league_id(once)
        assert once == twice == "EPL"

    def test_unresolvable_key_returned_unchanged(self) -> None:
        assert canonicalize_odds_api_league_id("NOT_A_REAL_LEAGUE") == "NOT_A_REAL_LEAGUE"


@pytest.mark.unit
class TestBookmakerLeagueCoverageIsCanonical:
    def test_no_raw_sport_key_survives_in_the_loaded_registry(self) -> None:
        """Every league value BOOKMAKER_LEAGUE_COVERAGE exposes at runtime must
        resolve against the canonical league registry — locks the canonical-id
        lookup path (not just the raw-name one) so a future non-canonicalising
        refresh can't silently reintroduce the false-negative class."""
        all_leagues = {lg for leagues in BOOKMAKER_LEAGUE_COVERAGE.values() for lg in leagues}
        assert all_leagues, "fixture assumption: the coverage map is non-empty"
        non_canonical = {lg for lg in all_leagues if get_league(lg) is None}
        assert not non_canonical, f"non-canonical league ids leaked into BOOKMAKER_LEAGUE_COVERAGE: {non_canonical}"

    def test_is_bookmaker_league_covered_true_for_sample_canonical_leagues(self) -> None:
        """Done-when: is_bookmaker_league_covered(bookmaker, canonical_league_id)
        returns True for leagues previously confirmed captured under their
        canonical id."""
        checked = 0
        for book, leagues in BOOKMAKER_LEAGUE_COVERAGE.items():
            if not leagues:
                continue
            league = next(iter(leagues))
            assert is_bookmaker_league_covered(book, league) is True
            checked += 1
            if checked >= 5:
                break
        assert checked >= 5, "fixture assumption: at least 5 bookmakers have >=1 covered league"
