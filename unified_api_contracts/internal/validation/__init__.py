"""Internal instruction-schema validator (G1.2).

Public consumers import from :mod:`unified_api_contracts.instruction` —
this module is the implementation home per UAC Citadel rules (types +
business logic live under ``internal/``; public surface re-exports via
the per-domain facade file).
"""

from unified_api_contracts.internal.validation.instruction import (
    AtomicLeg,
    ClientInstruction,
    CorrelationLimit,
    InstructionAction,
    InstructionFieldError,
    InstructionValidationResult,
    InstructionValidator,
    InstrumentVenueContext,
    KillSwitchCondition,
    LifecycleReplaceCancel,
    LifecycleSemantic,
    OrderConstraints,
    RiskAndAllocationConstraints,
    SizeOrTargetExposure,
    StrategyInstructionId,
    TimeframeMode,
    TimeframeUrgency,
    TimeInForce,
)

__all__ = [
    "AtomicLeg",
    "ClientInstruction",
    "CorrelationLimit",
    "InstructionAction",
    "InstructionFieldError",
    "InstructionValidationResult",
    "InstructionValidator",
    "InstrumentVenueContext",
    "KillSwitchCondition",
    "LifecycleReplaceCancel",
    "LifecycleSemantic",
    "OrderConstraints",
    "RiskAndAllocationConstraints",
    "SizeOrTargetExposure",
    "StrategyInstructionId",
    "TimeInForce",
    "TimeframeMode",
    "TimeframeUrgency",
]
