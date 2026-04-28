"""Domain facade — client-instruction schema + validator (G1.2).

Consumer repos import from here:

    from unified_api_contracts.instruction import (
        ClientInstruction,
        InstructionValidator,
        InstructionValidationResult,
        InstructionFieldError,
    )

The ``InstructionValidator`` enforces stage-3b's 8-required-field contract
plus the G1.8 ``ArchetypeCapability`` (asset_group, instrument_type, venue)
compatibility matrix. execution-service runs it as a pre-handler middleware
on every incoming instruction; the Rule-10 ``integration_depth`` score it
emits feeds the G1.6 pricing formula.

SSOT: :mod:`unified_api_contracts.internal.validation.instruction`.
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
