"""Synthetic-data generator taxonomy — closed-set workspace SSOT for the mock-data benchmark harness.

Split into modules for maintainability while maintaining backward compatibility.
"""

# Import everything from backup to maintain compatibility temporarily
# This allows the codebase to continue working while we do proper splits
from ..synthetic_generator_backup import (
    SYNTHETIC_GENERATOR_REGISTRY,
    SyntheticDataDomain,
    SyntheticGeneratorId,
    SyntheticGeneratorSpec,
    SyntheticOutputManifest,
    SyntheticParams,
    SyntheticRealismAxis,
    SyntheticRunManifest,
    SyntheticShardLayout,
    SyntheticShardManifest,
    generators_for_archetype,
    get_generator_spec,
    make_decimal,
    register_generator,
)

# Also import from our new split modules for verification
from ._enums import SyntheticDataDomain as _SyntheticDataDomain

# Verify consistency
assert SyntheticDataDomain.CEFI_TICK == _SyntheticDataDomain.CEFI_TICK

__all__ = [
    "SYNTHETIC_GENERATOR_REGISTRY",
    "SyntheticDataDomain",
    "SyntheticGeneratorId",
    "SyntheticGeneratorSpec",
    "SyntheticOutputManifest",
    "SyntheticParams",
    "SyntheticRealismAxis",
    "SyntheticRunManifest",
    "SyntheticShardLayout",
    "SyntheticShardManifest",
    "generators_for_archetype",
    "get_generator_spec",
    "make_decimal",
    "register_generator",
]
