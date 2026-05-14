"""BatchExecutionMode canonical SSOT and node_builder algo-type constants.

:class:`BatchExecutionMode` lives at ``unified_api_contracts.internal.execution``
(SSOT) and is re-exported here for discoverability in the crosscutting namespace.

Node-builder algo-type strings
-------------------------------
``execution-service/engine/backtest/node_builder.py`` reads an ``exec_algo_type``
string from run config and compares it against two sentinel values:

- ``"NORMAL"`` — regular market orders, no Nautilus exec algorithm.
- ``"BENCHMARK_FILL"`` — always fills at the requested price (zero commission, zero
  slippage).  Corresponds to :attr:`BatchExecutionMode.BENCHMARK`.

These strings were previously hardcoded literals in ``node_builder.py``.  This module
provides named constants so callers can import the SSOT rather than repeating raw
strings.  See ``codex/06-coding-standards/mode-axis-discipline.md`` AP-4 for why
``BatchExecutionMode`` is run-config, NOT a CLI flag.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.internal.execution import BatchExecutionMode

__all__ = [
    "BATCH_FILL_ALGO_TYPES",
    "BENCHMARK_FILL_ALGO_TYPE",
    "NORMAL_ALGO_TYPE",
    "BatchExecutionMode",
]

# ---------------------------------------------------------------------------
# Nautilus exec-algo type sentinel values
# Used by execution-service node_builder.py to select fill mode.
# ---------------------------------------------------------------------------

BENCHMARK_FILL_ALGO_TYPE: Final[str] = "BENCHMARK_FILL"
"""Algo-type sentinel for benchmark (always-fill-at-price) mode.

Corresponds to :attr:`BatchExecutionMode.BENCHMARK`.  When ``exec_algo_type``
equals this value, node_builder sets ``benchmark_fill_mode=True`` on the strategy
config.  No Nautilus exec-algorithm class is wired — fills are synthetic.
"""

NORMAL_ALGO_TYPE: Final[str] = "NORMAL"
"""Algo-type sentinel for normal market-order mode.

When ``exec_algo_type`` equals this value (or is absent), node_builder uses regular
Nautilus market orders with no exec-algorithm override.
"""

BATCH_FILL_ALGO_TYPES: Final[frozenset[str]] = frozenset({BENCHMARK_FILL_ALGO_TYPE, NORMAL_ALGO_TYPE})
"""Set of algo-type strings that bypass the Nautilus exec-algorithm registry.

Usage in node_builder::

    if exec_algo_type not in BATCH_FILL_ALGO_TYPES:
        # wire exec algorithm
    elif exec_algo_type == BENCHMARK_FILL_ALGO_TYPE:
        # enable benchmark_fill_mode
"""
