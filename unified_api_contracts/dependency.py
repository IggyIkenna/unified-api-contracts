"""Dependency facade — workspace-public surface for the 5-class dependency taxonomy.

Consumers MUST import from this facade, not from the deep
``unified_api_contracts.canonical.crosscutting.dependency.*`` paths
(per UAC import-surface rules).

Example::

    from unified_api_contracts.dependency import (
        DependencyClass,
        DependencyHealthPolicy,
    )

Codex SSOT: implementation plan
``plans/active/connectivity_dependency_buffer_policy_2026_05_23.md``.
"""

from __future__ import annotations

from .canonical.crosscutting.dependency import (
    DependencyClass,
    DependencyHealthPolicy,
)

__all__ = [
    "DependencyClass",
    "DependencyHealthPolicy",
]
