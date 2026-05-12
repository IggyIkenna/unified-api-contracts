"""Per-asset_group synthetic-generator registry — populates :data:`SYNTHETIC_GENERATOR_REGISTRY` at import time.

Phase 1.B of ``mock_data_pipeline_benchmarking_2026_05_10.md``. Per-asset_group
seed modules (``cefi.py`` / ``defi.py`` / ``tradfi.py``) register
:class:`SyntheticGeneratorSpec` instances via the
:func:`unified_api_contracts.canonical.crosscutting.synthetic_generator.register_generator`
helper. Per CLAUDE.md asset-group vocabulary rule: lowercase keys.

Pre-cutover coverage (2026-05-12 slot 7) — the 2 cutover archetypes only:

- ``cefi.py`` (6): ``cefi_trades``, ``cefi_ohlcv_1m``, ``cefi_ohlcv_15m``,
  ``cefi_funding_rate``, ``cefi_open_interest``, ``cefi_liquidations`` —
  consumed by ``leveraged_funding_arb`` / ``ARBITRAGE_PRICE_DISPERSION``.
- ``defi.py`` (5): ``defi_gas``, ``defi_lst_rates``,
  ``defi_lending_indices``, ``defi_dex_pool_state``, ``defi_oracle_feeds``
  — consumed by ``carry_staked_basis`` (lead).
- ``tradfi.py`` (2): ``tradfi_ohlcv_1m``, ``tradfi_ohlcv_1d`` — minimal
  cross-asset hedge-overlay path.

Sports / prediction generators + full per-asset_group coverage beyond
cutover archetypes are DEFERRED post-cutover per the plan's "Deferred
work" table.
"""

from __future__ import annotations

from . import cefi as _cefi
from . import defi as _defi
from . import tradfi as _tradfi

# Re-export per-module seed tuples for downstream introspection.
CEFI_GENERATORS = _cefi.SPECS
DEFI_GENERATORS = _defi.SPECS
TRADFI_GENERATORS = _tradfi.SPECS

ALL_GENERATORS = (*CEFI_GENERATORS, *DEFI_GENERATORS, *TRADFI_GENERATORS)

__all__ = [
    "ALL_GENERATORS",
    "CEFI_GENERATORS",
    "DEFI_GENERATORS",
    "TRADFI_GENERATORS",
]
