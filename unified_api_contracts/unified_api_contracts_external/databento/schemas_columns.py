"""Raw column schemas and helper utilities for Databento DataFrame validation.

Separated from schemas.py to keep file size within limits.
All column schema constants define expected dtypes and required flags for DataFrame validation.
"""

from pydantic import BaseModel, Field

from .schemas import DATABENTO_PRICE_DIVISOR

# =============================================================================
# Raw column schemas (for DataFrame validation)
# =============================================================================

DATABENTO_OHLCV_1M_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Bar close timestamp in nanoseconds since epoch (UTC)",
    },
    {
        "name": "rtype",
        "type": "int8",
        "required": True,
        "description": "Record type identifier (32 for OHLCV-1M)",
    },
    {
        "name": "publisher_id",
        "type": "int16",
        "required": True,
        "description": "Publisher/venue ID",
    },
    {
        "name": "instrument_id",
        "type": "int32",
        "required": True,
        "description": "Databento internal instrument ID",
    },
    {
        "name": "open",
        "type": "int64",
        "required": True,
        "description": "Opening price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "high",
        "type": "int64",
        "required": True,
        "description": "Highest price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "low",
        "type": "int64",
        "required": True,
        "description": "Lowest price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "close",
        "type": "int64",
        "required": True,
        "description": "Closing price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "volume",
        "type": "int64",
        "required": True,
        "description": "Total volume traded during bar",
    },
]

DATABENTO_OHLCV_1S_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Bar close timestamp in nanoseconds since epoch (UTC)",
    },
    {
        "name": "rtype",
        "type": "int8",
        "required": True,
        "description": "Record type identifier (17 for OHLCV-1S)",
    },
    {
        "name": "publisher_id",
        "type": "int16",
        "required": True,
        "description": "Publisher/venue ID",
    },
    {
        "name": "instrument_id",
        "type": "int32",
        "required": True,
        "description": "Databento internal instrument ID",
    },
    {
        "name": "open",
        "type": "int64",
        "required": True,
        "description": "Opening price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "high",
        "type": "int64",
        "required": True,
        "description": "Highest price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "low",
        "type": "int64",
        "required": True,
        "description": "Lowest price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "close",
        "type": "int64",
        "required": True,
        "description": "Closing price (fixed-point, divide by 1e9 for float)",
    },
    {
        "name": "volume",
        "type": "int64",
        "required": True,
        "description": "Total volume traded during bar",
    },
]

DATABENTO_TRADES_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Trade timestamp in nanoseconds since epoch (UTC)",
    },
    {"name": "rtype", "type": "int8", "required": True, "description": "Record type identifier"},
    {
        "name": "publisher_id",
        "type": "int16",
        "required": True,
        "description": "Publisher/venue ID",
    },
    {
        "name": "instrument_id",
        "type": "int32",
        "required": True,
        "description": "Databento internal instrument ID",
    },
    {
        "name": "action",
        "type": "string",
        "required": True,
        "description": "Trade action type (T=trade)",
    },
    {
        "name": "side",
        "type": "string",
        "required": True,
        "description": "Aggressor side (A=ask/sell, B=bid/buy)",
    },
    {
        "name": "price",
        "type": "int64",
        "required": True,
        "description": "Trade price (fixed-point, divide by 1e9 for float)",
    },
    {"name": "size", "type": "int32", "required": True, "description": "Trade size/quantity"},
    {
        "name": "sequence",
        "type": "int64",
        "required": False,
        "description": "Exchange sequence number",
    },
]

DATABENTO_MBP_1_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Quote timestamp in nanoseconds since epoch (UTC)",
    },
    {"name": "rtype", "type": "int8", "required": True, "description": "Record type identifier"},
    {
        "name": "publisher_id",
        "type": "int16",
        "required": True,
        "description": "Publisher/venue ID",
    },
    {
        "name": "instrument_id",
        "type": "int32",
        "required": True,
        "description": "Databento internal instrument ID",
    },
    {
        "name": "bid_px_00",
        "type": "int64",
        "required": True,
        "description": "Best bid price (fixed-point)",
    },
    {
        "name": "ask_px_00",
        "type": "int64",
        "required": True,
        "description": "Best ask price (fixed-point)",
    },
    {"name": "bid_sz_00", "type": "int32", "required": True, "description": "Best bid size"},
    {"name": "ask_sz_00", "type": "int32", "required": True, "description": "Best ask size"},
    {"name": "bid_ct_00", "type": "int32", "required": False, "description": "Bid order count"},
    {"name": "ask_ct_00", "type": "int32", "required": False, "description": "Ask order count"},
]

DATABENTO_DEFINITION_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "ts_recv",
        "type": "int64",
        "required": True,
        "description": "Definition receive timestamp in nanoseconds",
    },
    {
        "name": "publisher_id",
        "type": "int16",
        "required": True,
        "description": "Publisher/venue ID",
    },
    {
        "name": "instrument_id",
        "type": "int32",
        "required": True,
        "description": "Databento internal instrument ID",
    },
    {
        "name": "raw_symbol",
        "type": "string",
        "required": True,
        "description": "Raw exchange symbol",
    },
    {
        "name": "security_update_action",
        "type": "string",
        "required": True,
        "description": "Update action (A=add, M=modify, D=delete)",
    },
    {
        "name": "min_lot_size_round_lot",
        "type": "int32",
        "required": False,
        "description": "Minimum lot size for round lot",
    },
    {
        "name": "instrument_class",
        "type": "string",
        "required": True,
        "description": "Instrument class (F=future, O=option, S=stock, etc.)",
    },
    {
        "name": "strike_price",
        "type": "int64",
        "required": False,
        "description": "Strike price for options (fixed-point)",
    },
    {
        "name": "underlying",
        "type": "string",
        "required": False,
        "description": "Underlying symbol for derivatives",
    },
    {
        "name": "expiration",
        "type": "int64",
        "required": False,
        "description": "Expiration timestamp in nanoseconds",
    },
    {
        "name": "currency",
        "type": "string",
        "required": False,
        "description": "Trading currency (e.g., USD)",
    },
    {
        "name": "unit_of_measure",
        "type": "string",
        "required": False,
        "description": "Unit of measure for commodities",
    },
    {
        "name": "unit_of_measure_qty",
        "type": "int64",
        "required": False,
        "description": "Contract size in units",
    },
    {
        "name": "min_price_increment",
        "type": "int64",
        "required": False,
        "description": "Tick size (fixed-point)",
    },
]

DATABENTO_OPTION_QUOTE_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "ts_recv",
        "type": "int64",
        "required": True,
        "description": "Receive timestamp (nanoseconds)",
    },
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Event timestamp (nanoseconds)",
    },
    {"name": "rtype", "type": "int8", "required": True, "description": "Record type identifier"},
    {
        "name": "publisher_id",
        "type": "int16",
        "required": True,
        "description": "Publisher ID (OPRA)",
    },
    {
        "name": "instrument_id",
        "type": "int32",
        "required": True,
        "description": "Databento instrument ID",
    },
    {
        "name": "underlying",
        "type": "string",
        "required": True,
        "description": "Underlying symbol (SPY, QQQ)",
    },
    {
        "name": "strike_price",
        "type": "int64",
        "required": True,
        "description": "Strike price (fixed-point)",
    },
    {
        "name": "expiration",
        "type": "int64",
        "required": True,
        "description": "Expiration timestamp (nanoseconds)",
    },
    {"name": "option_type", "type": "string", "required": True, "description": "C=call, P=put"},
    {
        "name": "bid_px_00",
        "type": "int64",
        "required": True,
        "description": "Best bid price (fixed-point)",
    },
    {
        "name": "ask_px_00",
        "type": "int64",
        "required": True,
        "description": "Best ask price (fixed-point)",
    },
    {
        "name": "bid_sz_00",
        "type": "int32",
        "required": True,
        "description": "Best bid size (contracts)",
    },
    {
        "name": "ask_sz_00",
        "type": "int32",
        "required": True,
        "description": "Best ask size (contracts)",
    },
    {"name": "bid_ct_00", "type": "int32", "required": False, "description": "Bid order count"},
    {"name": "ask_ct_00", "type": "int32", "required": False, "description": "Ask order count"},
    {
        "name": "implied_volatility",
        "type": "int64",
        "required": False,
        "description": "Implied volatility (fixed-point)",
    },
    {"name": "delta", "type": "int64", "required": False, "description": "Delta (fixed-point)"},
    {"name": "gamma", "type": "int64", "required": False, "description": "Gamma (fixed-point)"},
    {"name": "theta", "type": "int64", "required": False, "description": "Theta (fixed-point)"},
    {"name": "vega", "type": "int64", "required": False, "description": "Vega (fixed-point)"},
]

DATABENTO_CME_OPTION_QUOTE_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "ts_recv",
        "type": "int64",
        "required": True,
        "description": "Receive timestamp (nanoseconds)",
    },
    {
        "name": "ts_event",
        "type": "int64",
        "required": True,
        "description": "Event timestamp (nanoseconds)",
    },
    {"name": "rtype", "type": "int8", "required": True, "description": "Record type identifier"},
    {
        "name": "publisher_id",
        "type": "int16",
        "required": True,
        "description": "Publisher ID (CME)",
    },
    {
        "name": "instrument_id",
        "type": "int32",
        "required": True,
        "description": "Databento instrument ID",
    },
    {
        "name": "underlying",
        "type": "string",
        "required": True,
        "description": "Underlying symbol (GC, NG, CL)",
    },
    {
        "name": "strike_price",
        "type": "int64",
        "required": True,
        "description": "Strike price (fixed-point)",
    },
    {
        "name": "expiration",
        "type": "int64",
        "required": True,
        "description": "Expiration timestamp (nanoseconds)",
    },
    {"name": "option_type", "type": "string", "required": True, "description": "C=call, P=put"},
    {
        "name": "bid_px_00",
        "type": "int64",
        "required": True,
        "description": "Best bid price (fixed-point)",
    },
    {
        "name": "ask_px_00",
        "type": "int64",
        "required": True,
        "description": "Best ask price (fixed-point)",
    },
    {
        "name": "bid_sz_00",
        "type": "int32",
        "required": True,
        "description": "Best bid size (contracts)",
    },
    {
        "name": "ask_sz_00",
        "type": "int32",
        "required": True,
        "description": "Best ask size (contracts)",
    },
    {"name": "bid_ct_00", "type": "int32", "required": False, "description": "Bid order count"},
    {"name": "ask_ct_00", "type": "int32", "required": False, "description": "Ask order count"},
    {
        "name": "implied_volatility",
        "type": "int64",
        "required": False,
        "description": "Implied volatility (fixed-point)",
    },
    {"name": "delta", "type": "int64", "required": False, "description": "Delta (fixed-point)"},
    {"name": "gamma", "type": "int64", "required": False, "description": "Gamma (fixed-point)"},
    {"name": "theta", "type": "int64", "required": False, "description": "Theta (fixed-point)"},
    {"name": "vega", "type": "int64", "required": False, "description": "Vega (fixed-point)"},
    {
        "name": "contract_size",
        "type": "int32",
        "required": False,
        "description": "Contract size/multiplier",
    },
    {
        "name": "unit_of_measure",
        "type": "string",
        "required": False,
        "description": "Unit of measure (oz, MMBtu)",
    },
]

DATABENTO_SCHEMA_MAP: dict[str, list[dict[str, str | bool]]] = {
    "ohlcv_1m": DATABENTO_OHLCV_1M_SCHEMA,
    "ohlcv_1s": DATABENTO_OHLCV_1S_SCHEMA,
    "trades": DATABENTO_TRADES_SCHEMA,
    "mbp_1": DATABENTO_MBP_1_SCHEMA,
    "definition": DATABENTO_DEFINITION_SCHEMA,
    "option_quote": DATABENTO_OPTION_QUOTE_SCHEMA,
    "cme_option_quote": DATABENTO_CME_OPTION_QUOTE_SCHEMA,
}


# =============================================================================
# CME FUTURES GAP DETECTION SCHEMAS
# =============================================================================
# DatabentoOhlcvBar supports CME BTC futures via dataset=GLBX.MDP3.
# BTC future root symbols: BTC (monthly), MBTC (micro). Weekly CME gaps form
# between Friday close (US ET) and Sunday open, detectable via GLBX.MDP3 bars.
# No new Pydantic model needed — DatabentoOhlcvBar is sufficient.
# The CmeFuturesGapRecord is a derived/computed schema, not a raw API schema.


class CmeFuturesGapRecord(BaseModel):
    """
    Derived record representing a detected CME futures price gap.

    Computed by the cme_gap calculator in features-cross-instrument-service
    by comparing consecutive GLBX.MDP3 OHLCV bars across the weekend boundary.
    This is NOT a raw Databento schema — it is the output of gap detection logic.
    """

    symbol: str = Field(description="CME futures symbol, e.g. BTCU4 or BTC")
    gap_open_price: float = Field(description="Sunday open price (gap bottom/top)")
    gap_close_price: float = Field(description="Friday close price (gap bottom/top)")
    gap_size_pct: float = Field(description="Gap size as percentage of gap_close_price")
    gap_direction: str = Field(description="'up' if Sunday open > Friday close, else 'down'")
    gap_formed_at_ts: int = Field(description="Timestamp (nanoseconds) when gap was detected")
    is_filled: bool = Field(default=False, description="True once price trades through the gap level")
    filled_at_ts: int | None = Field(default=None, description="Timestamp gap was filled (nanoseconds)")


def get_databento_schema(data_type: str) -> list[dict[str, str | bool]]:
    """Get Databento raw schema for a specific data type."""
    return DATABENTO_SCHEMA_MAP.get(data_type, [])


def get_databento_required_columns(data_type: str) -> list[str]:
    """Get required column names for a Databento data type."""
    schema = get_databento_schema(data_type)
    return [str(col["name"]) for col in schema if col.get("required", False)]


def convert_databento_price(fixed_point_price: int) -> float:
    """Convert Databento fixed-point price to float (divide by 1e9)."""
    return fixed_point_price / DATABENTO_PRICE_DIVISOR
