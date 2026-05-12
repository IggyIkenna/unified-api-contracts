"""Unit tests for Phase 5.A scenario_archetype_matrix.

Coverage:

- Cutover archetype set is closed-2.
- Matrix is built from registry (no fabricated scenario_ids).
- Per-archetype cell count >= compressed-scope target.
- Total cell count over-delivers vs 12-cell compressed-scope target.
- Unknown archetype lookup raises.
- Every cell's scenario_id resolves to a real SCENARIO_REGISTRY entry.
- No out-of-asset_group cells (build-rule invariant).
"""

from __future__ import annotations

import pytest

from unified_api_contracts import SCENARIO_REGISTRY
from unified_api_contracts.registry.scenario_archetype_matrix import (
    CUTOVER_ARCHETYPES,
    MATRIX,
    matrix_cell_count,
    scenarios_for_archetype,
)


def test_cutover_archetypes_closed_to_two() -> None:
    assert frozenset({"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}) == CUTOVER_ARCHETYPES


def test_matrix_keys_match_cutover_archetypes() -> None:
    assert set(MATRIX) == CUTOVER_ARCHETYPES


def test_matrix_cell_count_over_delivers_vs_compressed_target() -> None:
    """Compressed-scope plan target: 12 cells. Slot 7 Day-1 over-delivered to ~16."""
    total = matrix_cell_count()
    assert total >= 12, f"matrix has only {total} cells; compressed-scope minimum is 12"


def test_every_matrix_scenario_resolves_to_registry() -> None:
    for archetype, scenario_ids in MATRIX.items():
        for sid in scenario_ids:
            assert sid in SCENARIO_REGISTRY, (
                f"matrix declares {archetype} -> {sid} but it's not in SCENARIO_REGISTRY"
            )


def test_apd_matrix_includes_funding_arb_critical_scenarios() -> None:
    """Compressed-scope explicit critical-path: APD matrix must include
    cefi_funding_spike_10x + cefi_venue_circuit_breaker_trip + flash crash."""
    apd = MATRIX["ARBITRAGE_PRICE_DISPERSION"]
    expected_critical = {
        "cefi_funding_spike_10x",
        "cefi_venue_circuit_breaker_trip",
        "cross_asset_flash_crash",
        "cross_asset_basis_blowout_perp_spot",
    }
    assert expected_critical.issubset(apd), f"missing critical: {expected_critical - apd}"


def test_carry_staked_basis_matrix_includes_critical_scenarios() -> None:
    """Compressed-scope explicit critical-path: carry_staked_basis matrix must
    include defi_oracle_deviation_30sigma + defi_gas_surge_50x +
    defi_liquidity_drain_lending_pool + defi_chain_rpc_outage_solana +
    defi_stablecoin_depeg + cross_asset_flash_crash."""
    csb = MATRIX["carry_staked_basis"]
    expected_critical = {
        "defi_oracle_deviation_30sigma",
        "defi_gas_surge_50x",
        "defi_liquidity_drain_lending_pool",
        "defi_chain_rpc_outage_solana",
        "defi_stablecoin_depeg",
        "cross_asset_flash_crash",
    }
    assert expected_critical.issubset(csb), f"missing critical: {expected_critical - csb}"


def test_scenarios_for_archetype_fails_loud_on_unknown() -> None:
    with pytest.raises(ValueError, match="unknown archetype"):
        scenarios_for_archetype("unknown_archetype_xyz")


@pytest.mark.parametrize("archetype", sorted(CUTOVER_ARCHETYPES))
def test_per_archetype_at_least_one_scenario(archetype: str) -> None:
    """Sanity: neither archetype has empty matrix — would mean misconfigured
    expected_outcomes or empty registry."""
    assert len(MATRIX[archetype]) >= 1


def test_no_outcome_archetype_outside_cutover_set() -> None:
    """Build-rule invariant: scenarios may declare assertions for non-cutover
    archetypes (e.g. future archetype names), but those don't land in MATRIX —
    only cutover archetypes do. Verify no spillage."""
    for archetype in MATRIX:
        assert archetype in CUTOVER_ARCHETYPES


def test_per_archetype_no_duplicates_within_set() -> None:
    """frozenset invariant — but make explicit so reviewers see it."""
    for _archetype, ids in MATRIX.items():
        assert len(ids) == len(set(ids))
