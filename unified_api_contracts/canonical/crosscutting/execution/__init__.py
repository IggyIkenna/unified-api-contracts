"""Canonical crosscutting execution contracts.

Re-exports :class:`BatchExecutionMode` from the internal SSOT at
``unified_api_contracts.internal.execution``.  Consumer services import from the
internal path directly; this canonical package is the documentation-level pointer
that makes the SSOT discoverable via the crosscutting namespace.
"""

from unified_api_contracts.internal.execution import BatchExecutionMode
from .batch_execution_mode import BATCH_FILL_ALGO_TYPES, BENCHMARK_FILL_ALGO_TYPE, NORMAL_ALGO_TYPE

__all__ = [
    "BatchExecutionMode",
    "BATCH_FILL_ALGO_TYPES",
    "BENCHMARK_FILL_ALGO_TYPE",
    "NORMAL_ALGO_TYPE",
]
