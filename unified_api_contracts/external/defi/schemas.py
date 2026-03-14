"""DeFi protocol schemas: Pydantic lending models + raw column schemas for DataFrame validation.

Pydantic models re-exported from protocol_sdks for ENDPOINT_SCHEMA_MAP resolution.
Raw column schemas for AAVE, Uniswap, LST, Aster, Barchart, Yahoo Finance.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from unified_api_contracts.external.protocol_sdks.schemas import (
    AaveV3ReserveData,
    AaveV3UserAccountData,
    AaveV3UserReserveData,
    CompoundV3MarketInfo,
    CompoundV3UserPosition,
    EulerUserPosition,
    EulerVaultData,
    MorphoMarketParams,
    MorphoUserPosition,
)

# =============================================================================
# AAVE V3 raw column schemas
# =============================================================================

AAVE_RATES_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "datetime",
        "required": True,
        "description": "Data timestamp (UTC)",
    },
    {
        "name": "reserve",
        "type": "string",
        "required": True,
        "description": "Reserve address (e.g., WETH)",
    },
    {
        "name": "liquidityRate",
        "type": "float64",
        "required": True,
        "description": "Supply APY (ray format, divide by 1e27)",
    },
    {
        "name": "variableBorrowRate",
        "type": "float64",
        "required": True,
        "description": "Variable borrow APY (ray format)",
    },
    {
        "name": "stableBorrowRate",
        "type": "float64",
        "required": False,
        "description": "Stable borrow APY (ray format, if available)",
    },
    {
        "name": "liquidityIndex",
        "type": "float64",
        "required": True,
        "description": "Cumulative liquidity index",
    },
    {
        "name": "variableBorrowIndex",
        "type": "float64",
        "required": True,
        "description": "Cumulative variable borrow index",
    },
]

AAVE_ORACLE_PRICES_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "datetime",
        "required": True,
        "description": "Data timestamp (UTC)",
    },
    {"name": "reserve", "type": "string", "required": True, "description": "Reserve address"},
    {
        "name": "priceInEth",
        "type": "float64",
        "required": True,
        "description": "Price denominated in ETH",
    },
    {
        "name": "priceInUsd",
        "type": "float64",
        "required": False,
        "description": "Price denominated in USD",
    },
]

AAVE_RISK_PARAMS_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "datetime",
        "required": True,
        "description": "Data timestamp (UTC)",
    },
    {"name": "reserve", "type": "string", "required": True, "description": "Reserve address"},
    {
        "name": "ltv",
        "type": "float64",
        "required": True,
        "description": "Loan-to-value ratio (percentage)",
    },
    {
        "name": "liquidationThreshold",
        "type": "float64",
        "required": True,
        "description": "Liquidation threshold (percentage)",
    },
    {
        "name": "liquidationBonus",
        "type": "float64",
        "required": True,
        "description": "Liquidation bonus (percentage)",
    },
]

# =============================================================================
# Uniswap V3 raw column schemas (The Graph)
# =============================================================================

UNISWAP_SWAPS_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "id", "type": "string", "required": True, "description": "Swap transaction ID"},
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Swap timestamp (Unix seconds)",
    },
    {"name": "pool", "type": "string", "required": True, "description": "Pool address"},
    {
        "name": "sender",
        "type": "string",
        "required": True,
        "description": "Transaction sender address",
    },
    {
        "name": "recipient",
        "type": "string",
        "required": True,
        "description": "Token recipient address",
    },
    {
        "name": "amount0",
        "type": "float64",
        "required": True,
        "description": "Amount of token0 swapped (negative = out)",
    },
    {
        "name": "amount1",
        "type": "float64",
        "required": True,
        "description": "Amount of token1 swapped (negative = out)",
    },
    {
        "name": "sqrtPriceX96",
        "type": "string",
        "required": True,
        "description": "sqrt(price) * 2^96 after swap",
    },
    {"name": "tick", "type": "int64", "required": True, "description": "Pool tick after swap"},
]

UNISWAP_POOL_HOUR_DATA_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "id",
        "type": "string",
        "required": True,
        "description": "Pool hour data ID (pool-hour)",
    },
    {
        "name": "periodStartUnix",
        "type": "int64",
        "required": True,
        "description": "Hour start timestamp (Unix seconds)",
    },
    {"name": "pool", "type": "string", "required": True, "description": "Pool address"},
    {
        "name": "liquidity",
        "type": "string",
        "required": True,
        "description": "In-range liquidity (bigint as string)",
    },
    {"name": "sqrtPrice", "type": "string", "required": True, "description": "sqrt(price) * 2^96"},
    {
        "name": "token0Price",
        "type": "float64",
        "required": True,
        "description": "Price of token0 in terms of token1",
    },
    {
        "name": "token1Price",
        "type": "float64",
        "required": True,
        "description": "Price of token1 in terms of token0",
    },
    {"name": "tick", "type": "int64", "required": False, "description": "Current tick"},
    {
        "name": "tvlUSD",
        "type": "float64",
        "required": False,
        "description": "Total value locked in USD",
    },
    {
        "name": "volumeUSD",
        "type": "float64",
        "required": False,
        "description": "Volume in USD for the hour",
    },
    {
        "name": "feesUSD",
        "type": "float64",
        "required": False,
        "description": "Fees collected in USD for the hour",
    },
    {
        "name": "open",
        "type": "float64",
        "required": False,
        "description": "Opening price (token0 in token1)",
    },
    {"name": "high", "type": "float64", "required": False, "description": "Highest price"},
    {"name": "low", "type": "float64", "required": False, "description": "Lowest price"},
    {"name": "close", "type": "float64", "required": False, "description": "Closing price"},
]

# =============================================================================
# LST (Liquid Staking Token) raw column schemas — Lido, EtherFi
# =============================================================================

LST_ORACLE_PRICES_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "datetime",
        "required": True,
        "description": "Data timestamp (UTC)",
    },
    {
        "name": "token",
        "type": "string",
        "required": True,
        "description": "LST token symbol (wstETH, weETH)",
    },
    {
        "name": "priceInEth",
        "type": "float64",
        "required": True,
        "description": "Exchange rate to ETH",
    },
    {
        "name": "priceInUsd",
        "type": "float64",
        "required": False,
        "description": "Price in USD (if available)",
    },
]

LST_YIELDS_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "datetime",
        "required": True,
        "description": "Data timestamp (UTC)",
    },
    {"name": "token", "type": "string", "required": True, "description": "LST token symbol"},
    {
        "name": "stakingApy",
        "type": "float64",
        "required": True,
        "description": "Base staking APY (percentage)",
    },
    {
        "name": "rewardsApy",
        "type": "float64",
        "required": False,
        "description": "Additional rewards APY (EIGEN, ETHFI, etc.)",
    },
    {"name": "totalApy", "type": "float64", "required": False, "description": "Total combined APY"},
]

# =============================================================================
# Aster raw column schemas (DeFi Perpetuals)
# =============================================================================

ASTER_TRADES_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Trade timestamp (Unix milliseconds)",
    },
    {"name": "id", "type": "string", "required": True, "description": "Trade ID"},
    {"name": "symbol", "type": "string", "required": True, "description": "Trading pair symbol"},
    {"name": "side", "type": "string", "required": True, "description": "Trade side (buy/sell)"},
    {"name": "price", "type": "float64", "required": True, "description": "Trade price"},
    {"name": "size", "type": "float64", "required": True, "description": "Trade size"},
]

ASTER_FUNDING_RATES_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Funding timestamp (Unix milliseconds)",
    },
    {"name": "symbol", "type": "string", "required": True, "description": "Trading pair symbol"},
    {
        "name": "fundingRate",
        "type": "float64",
        "required": True,
        "description": "Funding rate (percentage per 8 hours)",
    },
    {
        "name": "fundingTime",
        "type": "int64",
        "required": True,
        "description": "Next funding time (Unix milliseconds)",
    },
]

ASTER_OPEN_INTEREST_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "timestamp",
        "type": "int64",
        "required": True,
        "description": "Data timestamp (Unix milliseconds)",
    },
    {"name": "symbol", "type": "string", "required": True, "description": "Trading pair symbol"},
    {
        "name": "openInterest",
        "type": "float64",
        "required": True,
        "description": "Open interest in base currency",
    },
    {
        "name": "openInterestValue",
        "type": "float64",
        "required": False,
        "description": "Open interest value in USD",
    },
]

# =============================================================================
# Barchart raw column schema (VIX 15-minute CSV)
# =============================================================================

BARCHART_OHLCV_15M_SCHEMA: list[dict[str, str | bool]] = [
    {
        "name": "Time",
        "type": "string",
        "required": True,
        "description": "Timestamp in US Eastern Time (format: YYYY-MM-DD HH:MM)",
    },
    {"name": "Open", "type": "float64", "required": True, "description": "Opening price"},
    {"name": "High", "type": "float64", "required": True, "description": "Highest price"},
    {"name": "Low", "type": "float64", "required": True, "description": "Lowest price"},
    {
        "name": "Last",
        "type": "float64",
        "required": True,
        "description": "Closing price (Barchart uses 'Last' for close)",
    },
    {
        "name": "Change",
        "type": "float64",
        "required": False,
        "description": "Price change (absolute)",
    },
    {
        "name": "%Change",
        "type": "string",
        "required": False,
        "description": "Price change (percentage)",
    },
    {
        "name": "Volume",
        "type": "float64",
        "required": False,
        "description": "Volume (typically 0 for VIX index)",
    },
]

# =============================================================================
# Yahoo Finance raw column schema (Daily OHLCV)
# =============================================================================

YAHOO_OHLCV_24H_SCHEMA: list[dict[str, str | bool]] = [
    {"name": "Date", "type": "datetime", "required": True, "description": "Trading date"},
    {"name": "Open", "type": "float64", "required": True, "description": "Opening price"},
    {"name": "High", "type": "float64", "required": True, "description": "Highest price"},
    {"name": "Low", "type": "float64", "required": True, "description": "Lowest price"},
    {"name": "Close", "type": "float64", "required": True, "description": "Closing price"},
    {
        "name": "Adj Close",
        "type": "float64",
        "required": False,
        "description": "Adjusted closing price (for equities)",
    },
    {"name": "Volume", "type": "float64", "required": False, "description": "Trading volume"},
]

# =============================================================================
# Schema mapping
# =============================================================================

DEFI_SCHEMA_MAP: dict[str, list[dict[str, str | bool]]] = {
    "aave_rates": AAVE_RATES_SCHEMA,
    "aave_oracle_prices": AAVE_ORACLE_PRICES_SCHEMA,
    "aave_risk_params": AAVE_RISK_PARAMS_SCHEMA,
    "uniswap_swaps": UNISWAP_SWAPS_SCHEMA,
    "uniswap_pool_hour_data": UNISWAP_POOL_HOUR_DATA_SCHEMA,
    "lst_oracle_prices": LST_ORACLE_PRICES_SCHEMA,
    "lst_yields": LST_YIELDS_SCHEMA,
    "aster_trades": ASTER_TRADES_SCHEMA,
    "aster_funding_rates": ASTER_FUNDING_RATES_SCHEMA,
    "aster_open_interest": ASTER_OPEN_INTEREST_SCHEMA,
    "barchart_ohlcv_15m": BARCHART_OHLCV_15M_SCHEMA,
    "yahoo_ohlcv_24h": YAHOO_OHLCV_24H_SCHEMA,
}


def get_defi_schema(data_type: str) -> list[dict[str, str | bool]]:
    """Get DeFi/external provider raw schema for a specific data type."""
    return DEFI_SCHEMA_MAP.get(data_type, [])


def get_defi_required_columns(data_type: str) -> list[str]:
    """Get required column names for a DeFi data type."""
    schema = get_defi_schema(data_type)
    return [str(col["name"]) for col in schema if col.get("required", False)]


__all__ = [
    "AAVE_ORACLE_PRICES_SCHEMA",
    "AAVE_RATES_SCHEMA",
    "AAVE_RISK_PARAMS_SCHEMA",
    "ASTER_FUNDING_RATES_SCHEMA",
    "ASTER_OPEN_INTEREST_SCHEMA",
    "ASTER_TRADES_SCHEMA",
    "BARCHART_OHLCV_15M_SCHEMA",
    "DEFI_SCHEMA_MAP",
    "LST_ORACLE_PRICES_SCHEMA",
    "LST_YIELDS_SCHEMA",
    "UNISWAP_POOL_HOUR_DATA_SCHEMA",
    "UNISWAP_SWAPS_SCHEMA",
    "YAHOO_OHLCV_24H_SCHEMA",
    "AaveV3ReserveData",
    "AaveV3UserAccountData",
    "AaveV3UserReserveData",
    "CompoundV3MarketInfo",
    "CompoundV3UserPosition",
    "EulerUserPosition",
    "EulerVaultData",
    "MorphoMarketParams",
    "MorphoUserPosition",
    "get_defi_required_columns",
    "get_defi_schema",
]
