"""Strategy Architecture v2 canonical schemas.

Single source of truth for the 8-family / 18-archetype / 7-axis /
10-cross-cutting taxonomy. See codex/09-strategy/architecture-v2/README.md
and the 60-doc v2 corpus for the full architectural narrative.

Split across enums.py + schemas.py to stay under the 900-line QG limit.
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.enums import (
    ARCHETYPE_TO_FAMILY,
    AccountActionV2,
    AllocatorArchetype,
    AtomicExecutionMode,
    BacktestGroup,
    BenchmarkFillMode,
    CommissionStructureType,
    CompensationPolicy,
    EdgeMethod,
    FillSource,
    HoldPolicy,
    InstructionActionV2,
    KillSwitchReason,
    MarginMode,
    MevSubmissionMode,
    RiskGateDecision,
    RiskGateLayer,
    ShareClass,
    StakingMethod,
    StrategyArchetypeV2,
    StrategyFamilyV2,
    TransferType,
    Urgency,
    VenueCategoryV2,
    VenueFeature,
    VenueRoutingMode,
    VenueType,
)
from unified_api_contracts.internal.architecture_v2.schemas import (
    COMPATIBILITY_SEED,
    AccountInstruction,
    AllocationDirective,
    AtomicInstruction,
    AtomicLeg,
    BorrowInstruction,
    BridgeInstructionV2,
    CancelInstruction,
    ChildVenueDecl,
    CollateralRulesV2,
    CommissionStructureV2,
    CommissionTier,
    CompatibilityEntry,
    LendInstruction,
    LtvAndHaircut,
    MarginSpec,
    NettingRule,
    QuoteInstruction,
    RateLimitsV2,
    RegionalRestrictions,
    RiskGateResult,
    StakeInstruction,
    StrategyEquityDirective,
    StrategyInstanceDefinition,
    StrategyInstanceIdentity,
    StrategyInstructionEnvelope,
    SwapInstruction,
    TradeInstruction,
    TransferInstructionV2,
    UnityChildVenue,
    UnstakeInstruction,
    VenueCapabilityV2,
    VenueConstraints,
)

# StrategyInstructionV2 is a union — exposed as a type alias here to let
# consumers import it from the sub-package root rather than reaching into
# schemas.py. We inline the alias to avoid Pydantic reimport races.
StrategyInstructionV2 = (
    TradeInstruction
    | SwapInstruction
    | LendInstruction
    | BorrowInstruction
    | StakeInstruction
    | UnstakeInstruction
    | QuoteInstruction
    | TransferInstructionV2
    | BridgeInstructionV2
    | AtomicInstruction
    | CancelInstruction
)


__all__ = [
    "ARCHETYPE_TO_FAMILY",
    "COMPATIBILITY_SEED",
    "AccountActionV2",
    "AccountInstruction",
    "AllocationDirective",
    "AllocatorArchetype",
    "AtomicExecutionMode",
    "AtomicInstruction",
    "AtomicLeg",
    "BacktestGroup",
    "BenchmarkFillMode",
    "BorrowInstruction",
    "BridgeInstructionV2",
    "CancelInstruction",
    "ChildVenueDecl",
    "CollateralRulesV2",
    "CommissionStructureType",
    "CommissionStructureV2",
    "CommissionTier",
    "CompatibilityEntry",
    "CompensationPolicy",
    "EdgeMethod",
    "FillSource",
    "HoldPolicy",
    "InstructionActionV2",
    "KillSwitchReason",
    "LendInstruction",
    "LtvAndHaircut",
    "MarginMode",
    "MarginSpec",
    "MevSubmissionMode",
    "NettingRule",
    "QuoteInstruction",
    "RateLimitsV2",
    "RegionalRestrictions",
    "RiskGateDecision",
    "RiskGateLayer",
    "RiskGateResult",
    "ShareClass",
    "StakeInstruction",
    "StakingMethod",
    "StrategyArchetypeV2",
    "StrategyEquityDirective",
    "StrategyFamilyV2",
    "StrategyInstanceDefinition",
    "StrategyInstanceIdentity",
    "StrategyInstructionEnvelope",
    "StrategyInstructionV2",
    "SwapInstruction",
    "TradeInstruction",
    "TransferInstructionV2",
    "TransferType",
    "UnityChildVenue",
    "UnstakeInstruction",
    "Urgency",
    "VenueCapabilityV2",
    "VenueCategoryV2",
    "VenueConstraints",
    "VenueFeature",
    "VenueRoutingMode",
    "VenueType",
]
