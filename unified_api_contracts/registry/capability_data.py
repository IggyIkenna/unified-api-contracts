"""Capability declarations for all external data sources.

Each declaration describes what the source provides: domains, crosscutting
concerns, live/batch/historical support, auth, and per-domain operations.

Declarations are split by category in ``capability_declarations/`` and
aggregated here as the single public entry point.
"""

from __future__ import annotations

from .capability import SourceCapability, register_capability
from .capability_declarations import (
    ALTDATA_CAPABILITIES,
    CEFI_CAPABILITIES,
    DEFI_CAPABILITIES,
    SPORTS_CAPABILITIES,
    TRADFI_CAPABILITIES,
)

__all__ = [
    "CAPABILITY_DECLARATIONS",
    "bootstrap_capabilities",
]

# ---------------------------------------------------------------------------
# All declarations (ordered)
# ---------------------------------------------------------------------------

CAPABILITY_DECLARATIONS: list[SourceCapability] = [
    *CEFI_CAPABILITIES,
    *DEFI_CAPABILITIES,
    *SPORTS_CAPABILITIES,
    *TRADFI_CAPABILITIES,
    *ALTDATA_CAPABILITIES,
]


def bootstrap_capabilities() -> None:
    """Register all built-in capability declarations."""
    for cap in CAPABILITY_DECLARATIONS:
        register_capability(cap)
