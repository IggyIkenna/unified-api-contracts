"""Domain facade — strategy registry, families, and client identity.

Consumer repos import from here:
    from unified_api_contracts.strategy import STRATEGY_REGISTRY, StrategyFamily, ...
"""

from unified_api_contracts.internal.domain.strategy_service.client_registry import (
    CLIENT_REGISTRY,
    ClientDefinition,
    ClientRegistry,
)
from unified_api_contracts.internal.domain.strategy_service.registry import (
    STRATEGY_REGISTRY,
    Category,
    ExecutionMode,
    StrategyArchetype,
    StrategyDefinition,
    StrategyFamily,
    StrategyRegistry,
    validate_mode_for_category,
)

__all__ = [
    "CLIENT_REGISTRY",
    "STRATEGY_REGISTRY",
    "Category",
    "ClientDefinition",
    "ClientRegistry",
    "ExecutionMode",
    "StrategyArchetype",
    "StrategyDefinition",
    "StrategyFamily",
    "StrategyRegistry",
    "validate_mode_for_category",
]
