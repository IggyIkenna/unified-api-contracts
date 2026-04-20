"""Domain facade — strategy registry, families, and client identity.

Consumer repos import from here:
    from unified_api_contracts.strategy import STRATEGY_REGISTRY, StrategyFamily, ...

G1.8 added the v2 archetype-capability surface (``ArchetypeCapability`` +
``ARCHETYPE_CAPABILITY_REGISTRY`` + ``archetypes_for_pair`` + friends) so
pricing / derivation / instruction-validation consumers can query per-
archetype (category, instrument_type) support without reaching into the
strategy-service v2 code or the UI coverage.ts.
"""

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeCapability,
    ArchetypeCapabilityCell,
    ArchetypeInstrumentType,
    CoverageStatus,
    RollMode,
    all_capabilities,
    archetypes_for_pair,
    archetypes_for_venue,
    capability_for,
)
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
    "ARCHETYPE_CAPABILITY_REGISTRY",
    "CLIENT_REGISTRY",
    "STRATEGY_REGISTRY",
    "ArchetypeCapability",
    "ArchetypeCapabilityCell",
    "ArchetypeInstrumentType",
    "Category",
    "ClientDefinition",
    "ClientRegistry",
    "CoverageStatus",
    "ExecutionMode",
    "RollMode",
    "StrategyArchetype",
    "StrategyDefinition",
    "StrategyFamily",
    "StrategyRegistry",
    "all_capabilities",
    "archetypes_for_pair",
    "archetypes_for_venue",
    "capability_for",
    "validate_mode_for_category",
]
