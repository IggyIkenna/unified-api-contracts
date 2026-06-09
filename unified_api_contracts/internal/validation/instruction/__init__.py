"""Client-instruction schema + validator — rule 10 + stage-3b contract.

G1.2 of ``stage-3e-refactor-plan``. The validator runs at the
execution-service edge and rejects instructions that do not conform to
stage-3b's 8-required-field shape OR that target a
(category, instrument_type, venue) tuple not declared SUPPORTED /
PARTIAL in the UAC ``ArchetypeCapability`` registry (G1.8).

Pipeline position:
    client ── POST ──► execution-service pre-handler
                            │
                            ▼
                    InstructionValidator.validate()
                            │
                ┌───────────┴───────────┐
                │                       │
          InstructionValidationResult   │
                │                       │
          integration_depth (0-1)  InstructionFieldError[]
                │                       │
          log UTL event ──► 400 structured rejection
    ``INSTRUCTION_INTEGRATION_DEPTH_OBSERVED``

Symbol naming is deliberately scoped to ``Instruction*`` to avoid
collisions with:
- ``unified_trading_library.domain.validation.ValidationResult``
  (different domain — trade-event validation).
- ``strategy_service.engine.core.validation_service`` (different
  concept — strategy-config validation).

Consumers import via the public facade ``unified_api_contracts.instruction``.

SSOT:
- ``codex/16-strategy-playbooks/infra-spec/stage-3b-instruction-schema-contract.md``
  §2 (the 8 required fields + nested validation rules).
- ``codex/14-playbooks/_ssot-rules/10-strategy-instruction-schema-principles.md``
  (rule 10 — schema depth as pricing dimension).
- ``codex/09-strategy/architecture-v2/category-instrument-coverage.md``
  (BL-1..BL-10 block-list groupings surfaced through
  ``archetypes_for_pair``).

Organized into submodules (_enums, _schemas, …) for maintainability; this package re-exports the public API.
"""

# Import all enums
from ._enums import (
    InstructionAction,
    LifecycleSemantic,
    TimeframeMode,
    TimeInForce,
)

# Import main models and error types
from ._main_models import (
    ClientInstruction,
    InstructionFieldError,
    InstructionValidationResult,
)

# Import all nested models
from ._nested_models import (
    AtomicLeg,
    CorrelationLimit,
    InstrumentVenueContext,
    KillSwitchCondition,
    LifecycleReplaceCancel,
    OrderConstraints,
    RiskAndAllocationConstraints,
    SizeOrTargetExposure,
    StrategyInstructionId,
    TimeframeUrgency,
)

# Import scoring (internal function made public through validator)
from ._scoring import compute_integration_depth

# Import validator
from ._validator import InstructionValidator

# errors_from_pydantic is now a static method of InstructionValidator class

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
    "compute_integration_depth",
]
