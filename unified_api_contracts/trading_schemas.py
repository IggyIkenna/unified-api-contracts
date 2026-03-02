"""Trading config schemas and validation constants."""

from __future__ import annotations

# REQUIRED for ALL configs (backtest will fail without these)
REQUIRED_CONFIG_FIELDS: list[str] = [
    "config_id",
    "strategy_id",
    "config_version",
    "category",
    "asset",
    "strategy_base",
    "execution_mode",
    "timeframe",
    "timeframe_seconds",
    "instruments",
    "execution",
]

# OPTIONAL fields (enhance config but not required for basic backtest)
OPTIONAL_CONFIG_FIELDS: list[str] = [
    "risk",
    "data_source",
    "grid_metadata",
    "instrument",
    "venue",
    "strategy",
]

VALID_CATEGORIES: list[str] = ["cefi", "tradfi", "defi"]
VALID_MODES: list[str] = ["SCE", "HUF"]
VALID_TIMEFRAMES: list[str] = ["1M", "5M", "15M", "30M", "1H", "4H", "8H", "24H"]
VALID_INSTRUCTION_TYPES: list[str] = [
    "TRADE",
    "SWAP",
    "LEND",
    "BORROW",
    "STAKE",
    "UNSTAKE",
    "TRANSFER",
    "WITHDRAW",
    "REPAY",
]
VALID_ALGORITHMS: list[str] = [
    "TWAP",
    "VWAP",
    "ICEBERG",
    "ADAPTIVE_TWAP",
    "ALMGREN_CHRISS",
    "POV_DYNAMIC",
    "HYBRID_OPTIMAL",
    "PASSIVE_AGGRESSIVE_HYBRID",
    "SMART_ORDER_ROUTER",
    "SOR_TWAP",
    "SWAP_TWAP",
    "MAX_SLIPPAGE",
    "BENCHMARK_FILL",
]
VALID_BOOK_TYPES: list[str] = [
    "L1_MBP",
    "L2_MBP",
    "AMM",
    "LENDING_POOL",
    "STAKING_POOL",
]
VALID_OMS_TYPES: list[str] = ["NETTING", "HEDGING"]
VALID_ACCOUNT_TYPES: list[str] = ["CASH", "MARGIN"]

CONFIG_REQUIRED_FIELDS: list[str] = ["config_id", "strategy_id", "execution"]

INSTRUMENT_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string", "pattern": r"^[A-Z0-9_-]+:[A-Z0-9_]+:[A-Z0-9@-]+$"},
        "venue": {"type": "string"},
        "price_precision": {"type": "integer", "minimum": 0},
        "size_precision": {"type": "integer", "minimum": 0},
        "tick_size": {"type": ["string", "number"]},
        "lot_size": {"type": ["string", "number"]},
        "multiplier": {"type": ["string", "number"]},
    },
}

INSTRUMENTS_BY_TYPE_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["primary"],
        "properties": {
            "primary": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "secondary": {
                "type": "array",
                "items": {"type": "string"},
            },
            "related_balance": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    },
}

VENUE_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["name", "starting_balance", "base_currency"],
    "properties": {
        "name": {"type": "string"},
        "oms_type": {"type": "string", "enum": VALID_OMS_TYPES},
        "account_type": {"type": "string", "enum": VALID_ACCOUNT_TYPES},
        "book_type": {"type": "string", "enum": VALID_BOOK_TYPES},
        "starting_balance": {"type": "number", "minimum": 0},
        "base_currency": {"type": "string"},
        "maker_fee": {"type": "number", "minimum": 0},
        "taker_fee": {"type": "number", "minimum": 0},
        "latency_ms": {"type": "integer", "minimum": 0},
    },
}

EXECUTION_SECTION_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["algorithm"],
        "properties": {
            "algorithm": {"type": "string", "enum": VALID_ALGORITHMS},
            "params": {"type": "object"},
        },
    },
}

CONFIG_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": CONFIG_REQUIRED_FIELDS,
    "properties": {
        "config_id": {"type": "string"},
        "strategy_id": {"type": "string"},
        "config_version": {"type": "string", "pattern": r"^V\d+$"},
        "strategy_base": {"type": "string"},
        "category": {"type": "string", "enum": VALID_CATEGORIES},
        "asset": {"type": "string"},
        "execution_mode": {"type": "string", "enum": VALID_MODES},
        "timeframe": {"type": "string", "enum": VALID_TIMEFRAMES},
        "timeframe_seconds": {"type": "integer", "minimum": 1},
        "instruments": INSTRUMENTS_BY_TYPE_SCHEMA,
        "venues": {"type": "object"},
        "instrument": INSTRUMENT_SCHEMA,
        "venue": VENUE_SCHEMA,
        "execution": EXECUTION_SECTION_SCHEMA,
        "strategy": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "order_quantity": {"type": "number", "minimum": 0},
                "execution_mode": {"type": "string"},
                "exit_strategy_type": {"type": "string"},
            },
        },
        "risk": {"type": "object"},
        "data_source": {"type": "string"},
        "grid_metadata": {"type": "object"},
    },
}

INSTRUCTION_SCHEMA: dict[str, object] = INSTRUMENTS_BY_TYPE_SCHEMA
