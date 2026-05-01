"""Strategy service domain schemas — cross-service data contracts."""

from unified_api_contracts.internal.domain.strategy_service.catalogue import (
    STRATEGY_INSTANCE_CATALOGUE,
    StrategyInstance,
    StrategyInstanceCatalogue,
    compute_instance_id,
)
from unified_api_contracts.internal.domain.strategy_service.client_config import (
    ClientStrategyOverride,
)
from unified_api_contracts.internal.domain.strategy_service.client_registry import (
    CLIENT_REGISTRY,
    AccountType,
    ClientDefinition,
    ClientRegistry,
)
from unified_api_contracts.internal.domain.strategy_service.instruction import (
    INSTRUCTION_TYPE_TO_OPERATIONS,
    FuturesRollInstruction,
    OptionsComboInstruction,
    PredictionBetInstruction,
    SportsBetInstruction,
    SportsExchangeOrderInstruction,
    StrategyInstruction,
    StrategyInstructionType,
    TransferInstruction,
    Urgency,
)
from unified_api_contracts.internal.domain.strategy_service.instruction import (
    DeFiSignal as StrategyDeFiSignal,
)
from unified_api_contracts.internal.domain.strategy_service.instrument_intent import (
    ResolvedInstruments,
    StrategyInstrumentIntent,
)
from unified_api_contracts.internal.domain.strategy_service.lifecycle import (
    PaperTradeComparison,
    PhaseTransition,
    ProductRouting,
    StrategyInstanceLifecycle,
    StrategyLifecycleStage,
    StrategyLifecycleTransition,
    StrategyMaturityPhase,
    is_valid_maturity_transition,
    maturity_phase_rank,
)
from unified_api_contracts.internal.domain.strategy_service.pnl import (
    PnLAttribution,
    PnLSummary,
    RewardAttributionRow,
    SettlementDelta,
    SettlementType,
)
from unified_api_contracts.internal.domain.strategy_service.position import (
    PositionSnapshot,
    StrategyPosition,
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
from unified_api_contracts.internal.domain.strategy_service.strategy_mode_params import (
    StrategyModeParams,
)
from unified_api_contracts.internal.domain.strategy_service.trigger_subscription import (
    TriggerEvent,
    TriggerEventType,
    TriggerSubscription,
)
from unified_api_contracts.internal.domain.strategy_service.venue_set_variants import (
    VENUE_SET_VARIANTS,
    PricingTier,
    VenueSetVariant,
    get_venue_set_variant,
    get_venue_set_variants,
)

__all__ = [
    "CLIENT_REGISTRY",
    "INSTRUCTION_TYPE_TO_OPERATIONS",
    "STRATEGY_INSTANCE_CATALOGUE",
    "STRATEGY_REGISTRY",
    "VENUE_SET_VARIANTS",
    "AccountType",
    "Category",
    "ClientDefinition",
    "ClientRegistry",
    "ClientStrategyOverride",
    "ExecutionMode",
    "FuturesRollInstruction",
    "OptionsComboInstruction",
    "PaperTradeComparison",
    "PhaseTransition",
    "PnLAttribution",
    "PnLSummary",
    "PositionSnapshot",
    "PredictionBetInstruction",
    "PricingTier",
    "ProductRouting",
    "ResolvedInstruments",
    "RewardAttributionRow",
    "SettlementDelta",
    "SettlementType",
    "SportsBetInstruction",
    "SportsExchangeOrderInstruction",
    "StrategyArchetype",
    "StrategyDeFiSignal",
    "StrategyDefinition",
    "StrategyFamily",
    "StrategyInstance",
    "StrategyInstanceCatalogue",
    "StrategyInstanceLifecycle",
    "StrategyInstruction",
    "StrategyInstructionType",
    "StrategyInstrumentIntent",
    "StrategyLifecycleStage",
    "StrategyLifecycleTransition",
    "StrategyMaturityPhase",
    "StrategyModeParams",
    "StrategyPosition",
    "StrategyRegistry",
    "TransferInstruction",
    "TriggerEvent",
    "TriggerEventType",
    "TriggerSubscription",
    "Urgency",
    "VenueSetVariant",
    "compute_instance_id",
    "get_venue_set_variant",
    "get_venue_set_variants",
    "is_valid_maturity_transition",
    "maturity_phase_rank",
    "validate_mode_for_category",
]
