"""Regression lock for ``is_bookmaker_league_covered_exact``.

Part of the 2026-07-20 SPORTS shard-enumeration fix, step 1.3
(``plans/active/issues/sports_shard_enumeration_cartesian_blowup_2026_07_20.md``):
the sentinel-emission path must resolve (bookmaker, league) coverage at the
EXACT captured venue-key grain, not the base-key union that
``is_bookmaker_league_covered`` folds suffixed products into. Folding let a
suffixed key inherit coverage that only a SIBLING suffixed variant actually
earned (the root cause of ~15,570 false ``attempted_failed`` rows before this
fix line existed for bare ``BETFAIR``, and a live residual risk across any two
suffixed siblings of the same base book).
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.sports_bookmaker_league_coverage import (
    BOOKMAKER_LEAGUE_COVERAGE,
    is_bookmaker_league_covered,
    is_bookmaker_league_covered_exact,
)


@pytest.mark.unit
class TestIsBookmakerLeagueCoveredExact:
    def test_unobserved_bare_key_never_covered(self) -> None:
        """Bare BETFAIR never captured anything (it isn't a real requested key) —
        exact lookup must return False for any league, unlike the folded version
        which used to resolve it against the suffixed base union."""
        assert is_bookmaker_league_covered_exact("BETFAIR", "K_LEAGUE_1") is False

    def test_exact_key_covered_for_its_own_league(self) -> None:
        """A suffixed key IS covered for a league present in its own captured set."""
        own_leagues = BOOKMAKER_LEAGUE_COVERAGE["BETFAIR_EX_UK"]
        assert own_leagues, "fixture assumption: BETFAIR_EX_UK has >=1 covered league"
        some_league = next(iter(own_leagues))
        assert is_bookmaker_league_covered_exact("BETFAIR_EX_UK", some_league) is True

    def test_exact_does_not_fold_to_sibling_suffix(self) -> None:
        """BETFAIR_EX_UK covers leagues BETFAIR_EX_EU does not — the exact lookup on
        EX_EU for one of EX_UK's UK-only leagues must be False, whereas the folded
        (non-exact) lookup resolves True via the shared base-key union.  This is
        the precise defect class step 1.3 closes.
        """
        uk_only = BOOKMAKER_LEAGUE_COVERAGE["BETFAIR_EX_UK"] - BOOKMAKER_LEAGUE_COVERAGE["BETFAIR_EX_EU"]
        assert uk_only, "fixture assumption: BETFAIR_EX_UK has >=1 league EX_EU lacks"
        league = next(iter(uk_only))

        assert is_bookmaker_league_covered_exact("BETFAIR_EX_EU", league) is False
        # The non-exact function folds to the base-key union and DOES resolve
        # True here — proving the two functions genuinely diverge, not just in
        # name.
        assert is_bookmaker_league_covered(league_id=league, bookmaker="BETFAIR_EX_EU") is True

    def test_blank_league_is_false(self) -> None:
        assert is_bookmaker_league_covered_exact("BETFAIR_EX_UK", "") is False
        assert is_bookmaker_league_covered_exact("BETFAIR_EX_UK", "   ") is False

    def test_prediction_market_venue_is_false(self) -> None:
        """Prediction venues are excluded from the Odds-API bookmaker universe
        entirely, regardless of any coincidental key collision."""
        assert is_bookmaker_league_covered_exact("polymarket", "ANY_LEAGUE") is False
        assert is_bookmaker_league_covered_exact("KALSHI", "ANY_LEAGUE") is False

    def test_case_insensitive_on_both_args(self) -> None:
        own_leagues = BOOKMAKER_LEAGUE_COVERAGE["PINNACLE"]
        assert own_leagues, "fixture assumption: PINNACLE has >=1 covered league"
        some_league = next(iter(own_leagues))
        assert is_bookmaker_league_covered_exact("pinnacle", some_league.lower()) is True
