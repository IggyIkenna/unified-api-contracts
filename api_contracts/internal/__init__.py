"""Internal API contracts — schemas for data flowing between services.

Covers:
- ``domain``       : Instrument records, market ticks, order books, OHLCV, candles
- ``execution``    : Orders, fills, execution instructions, execution results
- ``signals``      : Strategy instructions, DeFi signals, GCS output records
- ``health``       : Health status, dependency checks, circuit breakers
- ``config``       : Config store records, change notifications, active pointers
- ``sor``          : Smart order routing schemas

NOTE: lifecycle events, features, ML, pubsub topics, and risk schemas live in
``unified-internal-contracts`` (the SSOT for all internal cross-service contracts).
"""

from api_contracts.internal.config import (
    ConfigChangeNotification,
    ConfigStoreActivePointer,
    ConfigStoreMetadata,
    ConfigStoreRecord,
    ConfigValidationResponse,
    ConfigValidationResult,
)
from api_contracts.internal.domain import (
    CanonicalOrderBook,
    CanonicalTrade,
    DerivativeTicker,
    InstrumentRecord,
    InstrumentType,
    LiquidationRecord,
    MarketTrade,
    OhlcvBar,
    OptionType,
    OrderBookSnapshot5,
    ProcessedCandle,
    QuoteRecord,
)
from api_contracts.internal.execution import (
    BenchmarkType,
    CandleCloseWarningMessage,
    CanonicalFill,
    CanonicalOrder,
    ExecutionInstruction,
    ExecutionResult,
    ExecutionStatus,
    FillEventPubSubPayload,
    ManualInstructionRequest,
    ManualInstructionResponse,
    OperationType,
    OrderSide,
    OrderStatus,
    OrderSubmittedMessage,
    OrderType,
    SLHitMessage,
    TimeInForce,
    TPHitMessage,
)
from api_contracts.internal.health import (
    CircuitBreakerEvent,
    CircuitBreakerState,
    CircuitBreakerStateEnum,
    ComponentHealth,
    DependencyFailure,
    DependencyReport,
    DependencyStatus,
    HealthStatusEnum,
    ServiceHealthStatus,
)
from api_contracts.internal.signals import (
    DeFiSignal,
    DeFiSignalRecord,
    InstructionRecord,
    StrategyInstruction,
)
from api_contracts.internal.sor import (
    SorChildOrder,
    SorExecutionSummary,
    SorRouteDecision,
    SorTwapSlice,
    SorVenueCapacity,
    SorVenueScore,
)

__all__ = [
    # execution
    "BenchmarkType",
    "CandleCloseWarningMessage",
    "CanonicalFill",
    "CanonicalOrder",
    # domain
    "CanonicalOrderBook",
    "CanonicalTrade",
    # health
    "CircuitBreakerEvent",
    "CircuitBreakerState",
    "CircuitBreakerStateEnum",
    "ComponentHealth",
    # config
    "ConfigChangeNotification",
    "ConfigStoreActivePointer",
    "ConfigStoreMetadata",
    "ConfigStoreRecord",
    "ConfigValidationResponse",
    "ConfigValidationResult",
    # signals
    "DeFiSignal",
    "DeFiSignalRecord",
    "DependencyFailure",
    "DependencyReport",
    "DependencyStatus",
    "DerivativeTicker",
    "ExecutionInstruction",
    "ExecutionResult",
    "ExecutionStatus",
    "FillEventPubSubPayload",
    "HealthStatusEnum",
    "InstructionRecord",
    "InstrumentRecord",
    "InstrumentType",
    "LiquidationRecord",
    "ManualInstructionRequest",
    "ManualInstructionResponse",
    "MarketTrade",
    "OhlcvBar",
    "OperationType",
    "OptionType",
    "OrderBookSnapshot5",
    "OrderSide",
    "OrderStatus",
    "OrderSubmittedMessage",
    "OrderType",
    "ProcessedCandle",
    "QuoteRecord",
    "SLHitMessage",
    "ServiceHealthStatus",
    # sor
    "SorChildOrder",
    "SorExecutionSummary",
    "SorRouteDecision",
    "SorTwapSlice",
    "SorVenueCapacity",
    "SorVenueScore",
    "StrategyInstruction",
    "TPHitMessage",
    "TimeInForce",
]
