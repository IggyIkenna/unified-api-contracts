"""Per-asset_group scenario registry — populates :data:`SCENARIO_REGISTRY` at import time.

Phase 1.D of `simulation_scenarios_topology_price_shocks_2026_05_09.md`.
Per-asset_group seed modules (`cefi.py` / `defi.py` / `cross_asset.py`) register
:class:`ScenarioOverlay` instances via the
:func:`unified_api_contracts.canonical.crosscutting.scenario_overlay.register_scenario`
helper. Per CLAUDE.md asset-group vocabulary rule: lowercase keys.

Compressed-scope (2026-05-12 slot 7 Day-2): 10 scenarios shipped.

- ``cefi.py`` (3): ``cefi_venue_circuit_breaker_trip``, ``cefi_funding_spike_10x``,
  ``cefi_execution_slippage_spike_book_thinning``.
- ``defi.py`` (8): ``defi_chain_rpc_outage_solana``, ``defi_liquidity_drain_lending_pool``,
  ``defi_oracle_deviation_30sigma``, ``defi_gas_surge_50x``,
  ``defi_mempool_congestion_inclusion_delay``, ``defi_stablecoin_depeg``,
  ``defi_lst_depeg_steth_5pct``, ``defi_execution_slippage_spike_pool_drain``.
- ``cross_asset.py`` (2): ``cross_asset_flash_crash``,
  ``cross_asset_basis_blowout_perp_spot``.

The book-thinning/pool-drain pair (2026-07-31,
``scenario_library_completion_13_16_2026_07_27.md``) implements Day-1 fragment
``13_execution_slippage_spike.md`` — the last 2 of the original 18 Day-1
scenario designs with zero downstream consumption.

Phase 4 broader coverage (≥34 scenarios) deferred to successor
``simulation_scenarios_post_cutover_2026_06_01.md``.
"""

from __future__ import annotations

from . import cefi as _cefi
from . import cross_asset as _cross_asset
from . import defi as _defi

__all__: list[str] = []

# Re-export per-module seed tuples for downstream introspection.
CEFI_SCENARIOS = _cefi.SCENARIOS
DEFI_SCENARIOS = _defi.SCENARIOS
CROSS_ASSET_SCENARIOS = _cross_asset.SCENARIOS
