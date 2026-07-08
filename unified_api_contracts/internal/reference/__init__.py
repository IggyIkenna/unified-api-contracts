"""Reference data contracts — canonical instrument definitions and enums."""

from unified_api_contracts.internal.reference.availability import (
    get_instruments_available_on,
)
from unified_api_contracts.internal.reference.canonical_id_builder import (
    SUPPORTED_INSTRUMENT_TYPES,
    UNSUPPORTED_BY_DESIGN,
    build_canonical_instrument_id,
    build_combo_id,
    build_instrument_id,
    build_leg,
)
from unified_api_contracts.internal.reference.circuit_breaker_config import (
    CircuitBreakerConfigRegistry,
    VenueCircuitBreakerConfig,
)
from unified_api_contracts.internal.reference.corporate_actions import (
    DividendRecord,
    DividendType,
    EarningsResultRecord,
    StockSplitRecord,
)
from unified_api_contracts.internal.reference.data_freshness import (
    ACCOUNT_STATE_FRESHNESS,
    ALL_FRESHNESS_CONTRACTS,
    FEATURE_FRESHNESS,
    MARKET_TICK_FRESHNESS,
    ML_FRESHNESS,
    DataFreshnessContract,
    DataStalenessError,
)
from unified_api_contracts.internal.reference.economic_calendar import (
    MacroResultRecord,
)
from unified_api_contracts.internal.reference.fee_schedule import (
    ClientFeeSchedule,
    ClientPrimeBrokerLink,
    FeeScheduleEntry,
    FeeType,
    PrimeBrokerEntity,
)
from unified_api_contracts.internal.reference.instrument import (
    AssetClass,
    InstrumentLeg,
    InstrumentRecord,
    InstrumentStatus,
    InstrumentType,
    MarginType,
    OptionType,
)
from unified_api_contracts.internal.reference.instrument_definition import InstrumentDefinition
from unified_api_contracts.internal.reference.instrument_key import InstrumentKey
from unified_api_contracts.internal.reference.instrument_validation import validate_instrument_records
from unified_api_contracts.internal.reference.ledger_asset_resolution import (
    UnknownInstrumentTypeError,
    asset_class_for_instrument_type,
    derive_ledger_asset_fields,
    instrument_type_for_action,
)
from unified_api_contracts.internal.reference.onchain_freshness import OnchainDataFreshnessConfig
from unified_api_contracts.internal.reference.ticker_registry import (
    EXCHANGE_BY_TICKER,
    UNDERLYING_NORMALIZATION,
    normalize_underlying,
    resolve_exchange,
)
from unified_api_contracts.internal.reference.universe_snapshot import UniverseSnapshot

__all__ = [
    "ACCOUNT_STATE_FRESHNESS",
    "ALL_FRESHNESS_CONTRACTS",
    "EXCHANGE_BY_TICKER",
    "FEATURE_FRESHNESS",
    "MARKET_TICK_FRESHNESS",
    "ML_FRESHNESS",
    "SUPPORTED_INSTRUMENT_TYPES",
    "UNDERLYING_NORMALIZATION",
    "UNSUPPORTED_BY_DESIGN",
    "AssetClass",
    "CircuitBreakerConfigRegistry",
    "ClientFeeSchedule",
    "ClientPrimeBrokerLink",
    "DataFreshnessContract",
    "DataStalenessError",
    "DividendRecord",
    "DividendType",
    "EarningsResultRecord",
    "FeeScheduleEntry",
    "FeeType",
    "InstrumentDefinition",
    "InstrumentKey",
    "InstrumentLeg",
    "InstrumentRecord",
    "InstrumentStatus",
    "InstrumentType",
    "MacroResultRecord",
    "MarginType",
    "OnchainDataFreshnessConfig",
    "OptionType",
    "PrimeBrokerEntity",
    "StockSplitRecord",
    "UniverseSnapshot",
    "UnknownInstrumentTypeError",
    "VenueCircuitBreakerConfig",
    "asset_class_for_instrument_type",
    "build_canonical_instrument_id",
    "build_combo_id",
    "build_instrument_id",
    "build_leg",
    "derive_ledger_asset_fields",
    "get_instruments_available_on",
    "instrument_type_for_action",
    "normalize_underlying",
    "resolve_exchange",
    "validate_instrument_records",
]
