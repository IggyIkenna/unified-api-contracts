"""Per-dependency health policy + 5-class taxonomy.

Codex SSOT: implementation plan
``plans/active/connectivity_dependency_buffer_policy_2026_05_23.md``.
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting.dependency.health_policy import (
    DependencyClass,
    DependencyHealthPolicy,
)

__all__ = [
    "DependencyClass",
    "DependencyHealthPolicy",
]
