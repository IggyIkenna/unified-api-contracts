"""Per-archetype scenario regression matrix — Phase 5.A SSOT.

Phase 5.A of `simulation_scenarios_topology_price_shocks_2026_05_09.md`
(slot 7 Day-3 2026-05-12).

Declares ``MATRIX: dict[str, frozenset[str]]`` mapping each cutover
archetype (`carry_staked_basis`, `ARBITRAGE_PRICE_DISPERSION`) to the
frozenset of :class:`ScenarioId` values its regression matrix iterates.

The matrix is the per-cell scope contract Phase 5.B
:class:`ScenarioMatrixRunner` (UTL) drives. Matrix-green iff every
``(archetype, scenario_id)`` cell PASSES every declared
:class:`ScenarioOutcomeAssertion` within its
``expected_within_seconds`` SLA.

Per the compressed-scope plan body (line 73-74): pre-cutover target is
12-cell matrix. Slot 7 over-delivered Day-1 by shipping 10 scenarios
(6 critical-path + 4 price-shocks); applied to the 2 archetypes filtered
to applicable, the resulting matrix is **16 cells** (over by 4 vs
compressed target). Out-of-asset_group scenarios excluded by
construction — see :data:`MATRIX` build rule below.

Build rule
----------

For each ``ScenarioOverlay`` in :data:`SCENARIO_REGISTRY`:

1. Read ``scenario.expected_outcomes`` and project the set of declared
   archetype strings (the assertion's ``archetype`` field).
2. For each declared archetype in the cutover set, the scenario is
   IN the matrix cell ``(archetype, scenario_id)``.

This guarantees: a scenario only ends up in an archetype's matrix iff
it has at least one declared expected outcome for that archetype. No
out-of-domain cells (e.g. a CeFi-only scenario never lands in
`carry_staked_basis` unless explicitly declared as a hedge-leg
assertion).
"""

from __future__ import annotations

from typing import Final

from ..canonical.crosscutting.scenario_overlay import SCENARIO_REGISTRY

CUTOVER_ARCHETYPES: Final[frozenset[str]] = frozenset(
    {"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"},
)
"""Closed set of archetypes the May-23 cutover matrix targets.

`carry_staked_basis` — Solana LST yield + ETH hedge-leg (DeFi-dominant).
`ARBITRAGE_PRICE_DISPERSION` — perp funding-arb (CeFi-dominant). Names
match the upstream UAC ``StrategyArchetype`` enum + the per-archetype
risk + breaker registries (Phase 2.A of risk plan; Phase 1.B of DR plan).
"""


def _build_matrix() -> dict[str, frozenset[str]]:
    """Derive the per-archetype scenario set from the registry.

    Run at import-time. A scenario lands in an archetype's matrix iff at
    least one of its ``expected_outcomes`` declares that archetype.
    """
    accumulator: dict[str, set[str]] = {a: set() for a in CUTOVER_ARCHETYPES}
    for scenario_id, overlay in SCENARIO_REGISTRY.items():
        for outcome in overlay.expected_outcomes:
            if outcome.archetype in CUTOVER_ARCHETYPES:
                accumulator[outcome.archetype].add(scenario_id)
    return {archetype: frozenset(ids) for archetype, ids in accumulator.items()}


MATRIX: Final[dict[str, frozenset[str]]] = _build_matrix()
"""Per-archetype scenario set.

Lookup: ``MATRIX["carry_staked_basis"]`` -> ``frozenset[ScenarioId]``.

Per Phase 5.C done-definition: a matrix run is GREEN iff every
``(archetype, scenario_id)`` cell passes every declared expected outcome
within its SLA. Any FAIL = matrix red. RED matrix = cutover blocker
(Phase 10).
"""


def matrix_cell_count() -> int:
    """Total (archetype, scenario_id) cells in the matrix.

    Pre-cutover compressed-scope target: 12 cells. Day-1 over-delivered
    to 16 cells (verified by ``test_matrix_cell_count_over_delivers``).
    """
    return sum(len(ids) for ids in MATRIX.values())


def scenarios_for_archetype(archetype: str) -> frozenset[str]:
    """Return the scenarios applicable to ``archetype``.

    Fail-loud on unknown archetype (avoids silent typo-induced empty
    matrix at run-time).
    """
    if archetype not in CUTOVER_ARCHETYPES:
        raise ValueError(
            f"unknown archetype {archetype!r}; "
            f"matrix declares {sorted(CUTOVER_ARCHETYPES)}",
        )
    return MATRIX[archetype]


__all__ = [
    "CUTOVER_ARCHETYPES",
    "MATRIX",
    "matrix_cell_count",
    "scenarios_for_archetype",
]
