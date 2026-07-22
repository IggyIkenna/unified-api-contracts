"""Observed (bookmaker x league) coverage for the sports ODDS pipeline.

SSOT for "does this Odds-API bookmaker actually price this league?".  DERIVED
from the captured market-data-tick-sports corpus: a ``(bookmaker, league)`` pair
is *covered* iff >=1 captured odds row exists for it across history.  A book that
has NEVER produced odds for a league does NOT cover it, so its zero-row shard for
that league is honest absence (``empty_confirmed``), not a fetch failure.

This closes the root cause of the ~72% ``attempted_failed`` over-count in the
sports ODDS manifest: the sentinel fan-out used to enumerate EVERY bookmaker x
EVERY fixture, and a niche book's "I don't price this league" zero-row was forced
to ``attempted_failed`` by the live-instrument guard.

Two complementary registries live here:

* ``PREDICTION_MARKET_VENUES`` — venues that are PREDICTION MARKETS
  (Kalshi/Polymarket/Novig/BetOpenly/ProphetX), sourced via the *prediction*
  pipeline (``polymarket_clob`` / ``kalshi`` connectors), NOT Odds-API
  bookmakers.  They must NOT appear in the sports-ODDS expected-universe — their
  prices flow through the prediction pipeline; pred-vs-book dispersion is a
  feature-layer join, not a source merge.
* ``BOOKMAKER_LEAGUE_COVERAGE`` — the observed ``{bookmaker: [league_id, ...]}``
  map (committed JSON resource ``data/sports_bookmaker_league_coverage.json``,
  refreshed by
  ``market-tick-data-service/scripts/refresh_sports_bookmaker_league_coverage_2026_06_21.py``).

Mirrors the existing per-source coverage pattern
(``sports_per_source_rules.is_expected_for_source`` / ``understat`` league
whitelist).

SSOT: ``plans/active/data_completion_to_100_all_ag_2026_06_21.md`` §sports-odds
coverage-correctness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, cast

# ---------------------------------------------------------------------------
# Part 0 — the REQUEST scope (Phase 6d prerequisite for MTDS venue-injection)
# ---------------------------------------------------------------------------
# UAC-side mirror of ``market-tick-data-service``'s
# ``market_interface/adapters/sports/odds_api_adapter.py::REQUESTED_ODDS_API_BOOKMAKERS``
# — the exact books sent as the Odds-API ``bookmakers=`` request parameter, and
# therefore the only defensible basis for a per-bookmaker EXPECTATION (see that
# module's docstring for the 2026-07-20 finding this closes: deriving scope from
# UAC venue CATEGORIES instead of the real request list manufactured 418,860
# structurally-false honest-absence rows on 3 never-requested keys).
#
# This is a DELIBERATE duplication, not an import (MTDS depends on UAC, not the
# reverse — "no service-to-service deps", tier-and-import-architecture). UAC is
# the SSOT going forward: MTDS's copy should re-point to import this constant in
# a follow-up change; until then keep both lists in sync by hand when the
# Odds-API request scope changes (rare — audited additions only).
#
# Consumed by :func:`expected_odds_api_bookmaker_keys` for the deployment-api
# MTDS SPORTS venue-injection (Phase 6d, ``mtds.py::MTDS_CATEGORY_META["SPORTS"]``
# — the axis is bookmaker x league x fixture-date, NOT the generic venue x
# data_type x calendar-date axis the other MTDS categories use; the injection
# loop for this axis is separate follow-up work, see
# ``plans/active/issues/sports_shard_enumeration_cartesian_blowup_2026_07_20.md`` §4.4).
REQUESTED_ODDS_API_BOOKMAKERS: Final[tuple[str, ...]] = (
    "pinnacle",
    "betfair_ex_uk",
    "betfair_ex_eu",
    "betonlineag",
    "coral",
    "paddypower",
    "casumo",
    "virginbet",
    "betsson",
    "unibet",
    "fanduel",
    "draftkings",
    "betrivers",
    "matchbook",
    "smarkets",
    "williamhill",
    "ladbrokes_uk",
    "betvictor",
    "unibet_uk",
    "skybet",
    "betfair_sb_uk",
    "sport888",
    "livescorebet",
)


def expected_odds_api_bookmaker_keys() -> list[str]:
    """Canonical UPPERCASE bookmaker keys an Odds-API response can contain.

    Mirrors MTDS's ``expected_odds_api_venue_keys()`` exactly (same request
    list, same uppercasing — the capture writer groups on ``bookmaker_key``
    upper-cased). A bookmaker not in this list can never legitimately appear
    in a captured row and must never be treated as an expected venue; a
    bookmaker IN this list that never captures must be injected as a
    zero-row entry (Phase 6d) so it renders as an honest 0%, not silently
    absent from the data-status UI.
    """
    return sorted(k.upper() for k in REQUESTED_ODDS_API_BOOKMAKERS)


# ---------------------------------------------------------------------------
# Part 1 — prediction-market venues (NOT Odds-API bookmakers)
# ---------------------------------------------------------------------------
# Lowercase canonical keys as they appear in the bookmaker registry's
# "Prediction Markets" block.  These venues are asset_group=prediction; their
# odds are sourced via the prediction pipeline (polymarket_clob / kalshi), so
# they are EXCLUDED from the sports-ODDS bookmaker scope.  Matched
# case-insensitively against both the bare key and the manifest ``venue`` column
# (which may be uppercased), so ``POLYMARKET`` / ``polymarket`` / ``KALSHI``
# all resolve.
PREDICTION_MARKET_VENUES: frozenset[str] = frozenset(
    {
        "polymarket",
        "kalshi",
        "novig",
        "betopenly",
        "prophetx",
    }
)


def is_prediction_market_venue(venue: str) -> bool:
    """Whether ``venue`` is a prediction market (excluded from sports-ODDS books)."""
    return venue.strip().lower() in PREDICTION_MARKET_VENUES


# ---------------------------------------------------------------------------
# Part 2 — observed (bookmaker x league) coverage map
# ---------------------------------------------------------------------------
_DATA_PATH = Path(__file__).parent / "data" / "sports_bookmaker_league_coverage.json"

# Canonical observed map: ``{BOOKMAKER_UPPER: [LEAGUE_ID_UPPER, ...]}``.
BOOKMAKER_LEAGUE_COVERAGE: dict[str, frozenset[str]] = {
    str(book).upper(): frozenset(str(lg).upper() for lg in leagues)
    for book, leagues in cast(dict[str, list[str]], json.loads(_DATA_PATH.read_text())).items()
}

# Every bookmaker key that has EVER produced a captured odds row (any league).
COVERED_BOOKMAKERS: frozenset[str] = frozenset(BOOKMAKER_LEAGUE_COVERAGE.keys())


def _normalize_bookmaker(bookmaker: str) -> str:
    """Uppercase + collapse common region/product suffixes to a base key.

    The captured manifest uses region/product-suffixed keys (``BETFAIR_EX_UK`` /
    ``UNIBET_EU`` / ``LADBROKES_UK``) while the sentinel scope and the bookmaker
    registry use bare keys (``BETFAIR`` / ``UNIBET`` / ``LADBROKES``).  Coverage
    is resolved at the BASE-key grain so a bare sentinel key reconciles with any
    of its suffixed captured variants (and vice-versa).
    """
    key = bookmaker.strip().upper()
    for suffix in ("_EX_UK", "_EX_EU", "_EX_AU", "_SB_UK", "_UK", "_EU", "_AU", "_US"):
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


# Base-key -> union of covered leagues across all suffixed variants of that book.
_COVERAGE_BY_BASE: dict[str, frozenset[str]] = {}
for _book, _leagues in BOOKMAKER_LEAGUE_COVERAGE.items():
    _base = _normalize_bookmaker(_book)
    _COVERAGE_BY_BASE[_base] = _COVERAGE_BY_BASE.get(_base, frozenset()) | _leagues

# Base keys of every book that has produced captured odds for >=1 league.
_COVERED_BASE_BOOKMAKERS: frozenset[str] = frozenset(_COVERAGE_BY_BASE.keys())


def is_bookmaker_observed(bookmaker: str) -> bool:
    """Whether ``bookmaker`` has EVER produced a captured odds row for any league.

    A book that has never produced odds (and is not a prediction market) is out
    of the Odds-API odds universe entirely -> its shards are honest absence.
    Resolved at the base-key grain (suffix-insensitive).
    """
    if is_prediction_market_venue(bookmaker):
        return False
    key = bookmaker.strip().upper()
    if key in COVERED_BOOKMAKERS:
        return True
    return _normalize_bookmaker(bookmaker) in _COVERED_BASE_BOOKMAKERS


def is_bookmaker_league_covered(bookmaker: str, league_id: str) -> bool:
    """Whether the observed corpus shows ``bookmaker`` prices ``league_id``.

    Returns ``True`` iff >=1 captured odds row exists for the (bookmaker, league)
    pair across history — i.e. the (book, league) cell is IN coverage and a
    zero-row fixture there is a real fetch failure.  Returns ``False`` for a
    prediction-market venue, an unobserved book, or an observed book that has
    never priced this league (out-of-coverage honest absence).

    Matching is suffix-insensitive on the bookmaker (``BETFAIR_EX_UK`` <->
    ``BETFAIR``) and uppercase-insensitive on both args.
    """
    if is_prediction_market_venue(bookmaker):
        return False
    league = league_id.strip().upper()
    if not league:
        return False
    book = bookmaker.strip().upper()
    exact = BOOKMAKER_LEAGUE_COVERAGE.get(book)
    if exact is not None and league in exact:
        return True
    base = _COVERAGE_BY_BASE.get(_normalize_bookmaker(bookmaker))
    return base is not None and league in base


def is_bookmaker_league_covered_exact(bookmaker: str, league_id: str) -> bool:
    """Whether the EXACT ``bookmaker`` key has captured odds for ``league_id``.

    Unlike :func:`is_bookmaker_league_covered`, this does **not** fall back to
    the base-key union (``_COVERAGE_BY_BASE``): ``BETFAIR_EX_UK`` is resolved
    only against its own captured league set, never against a sibling suffixed
    variant's (``BETFAIR_EX_EU``, ``BETFAIR_SB_UK``) or bare ``BETFAIR``'s.

    Use this on the sentinel-emission path
    (``market-tick-data-service/.../engine/orchestrator/sentinels.py``), where
    ``bookmakers_scope`` already carries the exact requested key
    (``expected_odds_api_venue_keys()``) — folding to a shared base risks
    marking one suffixed variant "covered" for leagues only a SIBLING variant
    has actually priced, manufacturing false ``attempted_failed`` rows (the
    2026-07-20 bare-BETFAIR grain-mismatch class,
    ``plans/active/issues/sports_shard_enumeration_cartesian_blowup_2026_07_20.md``
    step 1.3). Uppercase-insensitive on both args; still ``False`` for a
    prediction-market venue or a blank league.
    """
    if is_prediction_market_venue(bookmaker):
        return False
    league = league_id.strip().upper()
    if not league:
        return False
    book = bookmaker.strip().upper()
    exact = BOOKMAKER_LEAGUE_COVERAGE.get(book)
    return exact is not None and league in exact


__all__ = [
    "BOOKMAKER_LEAGUE_COVERAGE",
    "COVERED_BOOKMAKERS",
    "PREDICTION_MARKET_VENUES",
    "is_bookmaker_league_covered",
    "is_bookmaker_league_covered_exact",
    "is_bookmaker_observed",
    "is_prediction_market_venue",
]
