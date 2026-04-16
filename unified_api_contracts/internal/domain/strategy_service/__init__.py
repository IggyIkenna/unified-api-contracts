"""Strategy service domain schemas — cross-service data contracts."""

from unified_api_contracts.internal.domain.strategy_service.client_config import (
    ClientStrategyOverride,
)
from unified_api_contracts.internal.domain.strategy_service.client_registry import (
    CLIENT_REGISTRY,
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
    StrategyLifecycleStage,
    StrategyLifecycleTransition,
)
from unified_api_contracts.internal.domain.strategy_service.pnl import (
    PnLAttribution,
    PnLSummary,
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

__all__ = [
    "CLIENT_REGISTRY",
    "INSTRUCTION_TYPE_TO_OPERATIONS",
    "STRATEGY_REGISTRY",
    "Category",
    "ClientDefinition",
    "ClientRegistry",
    "ClientStrategyOverride",
    "ExecutionMode",
    "FuturesRollInstruction",
    "OptionsComboInstruction",
    "PaperTradeComparison",
    "PnLAttribution",
    "PnLSummary",
    "PositionSnapshot",
    "PredictionBetInstruction",
    "ResolvedInstruments",
    "SettlementDelta",
    "SettlementType",
    "SportsBetInstruction",
    "SportsExchangeOrderInstruction",
    "StrategyArchetype",
    "StrategyDeFiSignal",
    "StrategyDefinition",
    "StrategyFamily",
    "StrategyInstruction",
    "StrategyInstructionType",
    "StrategyInstrumentIntent",
    "StrategyLifecycleStage",
    "StrategyLifecycleTransition",
    "StrategyModeParams",
    "StrategyPosition",
    "StrategyRegistry",
    "TransferInstruction",
    "TriggerEvent",
    "TriggerEventType",
    "TriggerSubscription",
    "Urgency",
    "validate_mode_for_category",
]
