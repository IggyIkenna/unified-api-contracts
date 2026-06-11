"""
Strategy Instruction Models — import facade.

Defines StrategyInstruction, StrategyInstructionType, and DeFiSignal models
for generating typed trade instructions to execution-services, plus the
specialized per-domain instruction builders (transfer / prediction / sports /
futures roll / options combo).

Implementation lives in ``_instruction_base`` (vocabulary enums +
StrategyInstruction + DeFiSignal) and ``_instruction_specialized`` (the
domain-specific builders); this module is the stable import surface —
import paths MUST NOT change for fleet consumers.

OperationType and OrderType SSOT: unified_api_contracts.internal.domain.execution_service.types
"""

from unified_api_contracts.internal.domain.strategy_service._instruction_base import (
    INSTRUCTION_TYPE_TO_OPERATIONS,
    DeFiSignal,
    MetadataMap,
    MetadataValue,
    StrategyInstruction,
    StrategyInstructionType,
    Urgency,
)
from unified_api_contracts.internal.domain.strategy_service._instruction_specialized import (
    FuturesRollInstruction,
    OptionsComboInstruction,
    PredictionBetInstruction,
    SportsBetInstruction,
    SportsExchangeOrderInstruction,
    TransferInstruction,
)

__all__ = [
    "INSTRUCTION_TYPE_TO_OPERATIONS",
    "DeFiSignal",
    "FuturesRollInstruction",
    "MetadataMap",
    "MetadataValue",
    "OptionsComboInstruction",
    "PredictionBetInstruction",
    "SportsBetInstruction",
    "SportsExchangeOrderInstruction",
    "StrategyInstruction",
    "StrategyInstructionType",
    "TransferInstruction",
    "Urgency",
]
