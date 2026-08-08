"""Observed (league x per-fixture-entity) coverage for the instruments-service
sports reference enrichment pipeline.

SSOT for "does API-Football actually provide this enrichment ENTITY for this
league?".  DERIVED from the captured ``instruments-store-sports`` corpus: a
``(league, entity)`` pair is *covered* iff >=1 ``captured`` manifest row exists
for it across history.  A league that has NEVER produced rows for an entity does
NOT cover it, so its zero-row enrichment for that ``(league, entity)`` is honest
absence (``empty_confirmed``), not a fetch failure.

This closes the wasted-fetch + false-failure root cause in the per-fixture
enrichment: API-Football only provides PLAYER_STATS / FIXTURE_LINEUPS /
FIXTURE_EVENTS / FIXTURE_STATS for SOME leagues (measured: ~57% of
``/fixtures/players`` calls return 0 — 729 of 790 leagues never yield
PLAYER_STATS).  For an out-of-coverage league the enrichment loop used to (a)
burn an API call per fixture anyway and (b) when the zero-row hit the
live-instrument guard, land the cell as ``attempted_failed`` (coverage looks
falsely incomplete).  The IS write-path SKIPS the call for an out-of-coverage
``(league, entity)`` and records ``EXPECTED_NO_PROVIDER_COVERAGE`` so the cell
is honest-empty (and excluded from the data-status completion-% denominator).

The entity axis is the per-fixture enrichment entities plus the league-axis
reference entities written by the same api_football orchestrator stage:
``PLAYER_STATS`` / ``FIXTURE_LINEUPS`` / ``FIXTURE_EVENTS`` / ``FIXTURE_STATS``
/ ``TEAMS`` / ``STANDINGS`` / ``INJURIES``.

Mirrors the sibling per-(bookmaker, league) ODDS observed-coverage pattern
(``sports_bookmaker_league_coverage.is_bookmaker_league_covered``) and the
per-(source, league) whitelist pattern (Understat).  Here the source is a
SINGLE provider (API-Football) that covers some entities-for-a-league but not
others, so the axis is per-(league, ENTITY).

The observed map ``{ENTITY: [LEAGUE_ID, ...]}`` is the committed JSON resource
``data/sports_league_entity_coverage.json``, refreshed by
``instruments-service/scripts/refresh_sports_league_entity_coverage_2026_06_21.py``.

SSOT: ``plans/active/data_completion_to_100_all_ag_2026_06_21.md`` §sports IS
per-fixture-entity coverage-correctness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

# Per-fixture + league-axis api_football enrichment entities that participate in
# the observed (league x entity) coverage map.  Canonical lowercase data_type
# names (P1 2026-08-08 vocabulary merge; IS writers still write uppercase to
# manifest in P1 — lowercase here is the contract form, IS manifest is P2 scope).
LEAGUE_ENTITY_COVERAGE_ENTITIES: frozenset[str] = frozenset(
    {
        "player_stats",
        "fixture_lineups",
        "fixture_events",
        "fixture_stats",
        "teams",
        "standings",
        "injuries",
        "weather",
        "player_values",
    }
)

_DATA_PATH = Path(__file__).parent / "data" / "sports_league_entity_coverage.json"

# Canonical observed map: ``{entity_lower: frozenset(LEAGUE_ID_UPPER, ...)}``.
LEAGUE_ENTITY_COVERAGE: dict[str, frozenset[str]] = {
    str(entity).lower(): frozenset(str(lg).upper() for lg in leagues)
    for entity, leagues in cast(dict[str, list[str]], json.loads(_DATA_PATH.read_text())).items()
}

# Every entity key that has EVER produced a captured row for >=1 league.
COVERED_ENTITIES: frozenset[str] = frozenset(LEAGUE_ENTITY_COVERAGE.keys())


def is_league_entity_covered(league_id: str, entity: str) -> bool:
    """Whether the observed corpus shows API-Football provides ``entity`` for ``league_id``.

    Returns ``True`` iff >=1 ``captured`` manifest row exists for the
    ``(league_id, entity)`` pair across history — i.e. the cell is IN coverage
    and a zero-row enrichment there is a real fetch failure to retry.  Returns
    ``False`` for an unknown entity, a blank league, or a league that has NEVER
    produced this entity (out-of-coverage honest absence → the IS write-path
    skips the fetch + records ``EXPECTED_NO_PROVIDER_COVERAGE``).

    Both args are matched uppercase-insensitively.  An entity not in
    :data:`LEAGUE_ENTITY_COVERAGE_ENTITIES` (and never observed) is treated as
    not-covered (conservative — never forces a fetch for an unknown entity).
    """
    league = league_id.strip().upper()
    if not league:
        return False
    covered = LEAGUE_ENTITY_COVERAGE.get(entity.strip().lower())
    return covered is not None and league in covered


__all__ = [
    "COVERED_ENTITIES",
    "LEAGUE_ENTITY_COVERAGE",
    "LEAGUE_ENTITY_COVERAGE_ENTITIES",
    "is_league_entity_covered",
]
