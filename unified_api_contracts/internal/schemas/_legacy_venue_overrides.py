"""Legacy venue-specific SchemaContract overrides (Uniswap V2/V3/V4, Curve, Balancer, Ethena, Aave a_token extensions).

Split out of ``contracts.py`` to keep the main module under the 900-line
codex-compliance limit. This module is imported at module load time by
``contracts.py`` via a side-effect import so the mutations to
``CONTRACT_REGISTRY`` and ``VENUE_CONTRACT_OVERRIDES`` happen before any
consumer performs a lookup.

Do NOT import this module directly — import from
``unified_api_contracts.internal.schemas.contracts`` which re-exports the
public SchemaContract names.
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas.contracts import (
    CHAIN_COL,
    CONTRACT_REGISTRY,
    DEFI_DEX_POOL_DEX_POOL_STATE,
    DEFI_POOL_DEX_POOL_SWAPS,
    INSTRUMENT_ID_COL,
    TS_EVENT_COL,
    VENUE_COL,
    VENUE_CONTRACT_OVERRIDES,
    ColumnSpec,
    SchemaContract,
)

# Historical/raw Uniswap (V2/V3/V4), Curve, Balancer pool rows carry the
# pool hex address under ``pool_address`` rather than the canonical
# ``symbol`` column the live handlers emit. These overrides let the
# migration pipeline resolve to a contract that points to the column the
# row actually has, without silent fallback.
DEFI_UNISWAP_POOL_STATE_LEGACY = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_pool_state",
    columns=list(DEFI_DEX_POOL_DEX_POOL_STATE.columns),
    symbol_column="pool_address",
    required_row_count_min=1,
)

DEFI_UNISWAP_POOL_SWAPS_LEGACY = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_pool_swaps",
    columns=list(DEFI_POOL_DEX_POOL_SWAPS.columns),
    symbol_column="pool_address",
    required_row_count_min=1,
)

# Uniswap V3/V4/Curve/Balancer legacy rows carry the pool hex under
# ``pool_address``. Uniswap V2 uses the older ``pair_address`` naming.
DEFI_UNISWAP_V2_POOL_STATE_LEGACY = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_pool_state",
    columns=list(DEFI_DEX_POOL_DEX_POOL_STATE.columns),
    symbol_column="pair_address",
    required_row_count_min=1,
)
DEFI_UNISWAP_V2_POOL_SWAPS_LEGACY = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_pool_swaps",
    columns=list(DEFI_POOL_DEX_POOL_SWAPS.columns),
    symbol_column="pair_address",
    required_row_count_min=1,
)

for _venue in ("UNISWAP_V3", "CURVE", "BALANCER"):
    VENUE_CONTRACT_OVERRIDES[("defi", _venue, "pool", "dex_pool_state")] = DEFI_UNISWAP_POOL_STATE_LEGACY
    VENUE_CONTRACT_OVERRIDES[("defi", _venue, "pool", "dex_pool_swaps")] = DEFI_UNISWAP_POOL_SWAPS_LEGACY

VENUE_CONTRACT_OVERRIDES[("defi", "UNISWAP_V2", "pool", "dex_pool_state")] = DEFI_UNISWAP_V2_POOL_STATE_LEGACY
VENUE_CONTRACT_OVERRIDES[("defi", "UNISWAP_V2", "pool", "dex_pool_swaps")] = DEFI_UNISWAP_V2_POOL_SWAPS_LEGACY

# Uniswap V4 raw rows use ``pool_id`` as the pool identifier (not
# ``pool_address`` like V3). Separate override keeps V3/V4 in sync with
# their actual writer grammars.
DEFI_UNISWAP_V4_POOL_STATE_LEGACY = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_pool_state",
    columns=list(DEFI_DEX_POOL_DEX_POOL_STATE.columns),
    symbol_column="pool_id",
    required_row_count_min=1,
)
DEFI_UNISWAP_V4_POOL_SWAPS_LEGACY = SchemaContract(
    category="defi",
    instrument_type="pool",
    data_type="dex_pool_swaps",
    columns=list(DEFI_POOL_DEX_POOL_SWAPS.columns),
    symbol_column="pool_id",
    required_row_count_min=1,
)
VENUE_CONTRACT_OVERRIDES[("defi", "UNISWAP_V4", "pool", "dex_pool_state")] = DEFI_UNISWAP_V4_POOL_STATE_LEGACY
VENUE_CONTRACT_OVERRIDES[("defi", "UNISWAP_V4", "pool", "dex_pool_swaps")] = DEFI_UNISWAP_V4_POOL_SWAPS_LEGACY


# Aave V3 reserve-level datasets: oracle prices, rate indices (liquidity +
# borrow), utilization %, and risk parameters (LTV, liquidation threshold,
# reserve factor). All keyed per-asset symbol (USDC, WETH, …).
DEFI_A_TOKEN_ORACLE_PRICES = SchemaContract(
    category="defi",
    instrument_type="a_token",
    data_type="oracle_prices",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="price", dtype="float64", nullable=False),
    ],
    symbol_column="token",
    required_row_count_min=1,
)

DEFI_A_TOKEN_RATE_INDICES = SchemaContract(
    category="defi",
    instrument_type="a_token",
    data_type="rate_indices",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="liquidity_index", dtype="float64", nullable=True),
        ColumnSpec(name="variable_borrow_index", dtype="float64", nullable=True),
    ],
    symbol_column="token",
    required_row_count_min=1,
)

DEFI_A_TOKEN_RISK_PARAMS = SchemaContract(
    category="defi",
    instrument_type="a_token",
    data_type="risk_params",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="ltv", dtype="float64", nullable=True),
        ColumnSpec(name="liquidation_threshold", dtype="float64", nullable=True),
        ColumnSpec(name="reserve_factor", dtype="float64", nullable=True),
    ],
    symbol_column="token",
    required_row_count_min=1,
)

DEFI_A_TOKEN_UTILIZATION = SchemaContract(
    category="defi",
    instrument_type="a_token",
    data_type="utilization",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="utilization_rate", dtype="float64", nullable=True),
    ],
    symbol_column="token",
    required_row_count_min=1,
)

# Morpho (generic lending) reserve datasets — same shape as a_token variants
# but routed under instrument_type=lending per the live handler convention.
DEFI_LENDING_RATE_INDICES = SchemaContract(
    category="defi",
    instrument_type="lending",
    data_type="rate_indices",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="supply_rate", dtype="float64", nullable=True),
        ColumnSpec(name="borrow_rate", dtype="float64", nullable=True),
    ],
    symbol_column="instrument_key",
    required_row_count_min=1,
)

DEFI_LENDING_UTILIZATION = SchemaContract(
    category="defi",
    instrument_type="lending",
    data_type="utilization",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="utilization_rate", dtype="float64", nullable=True),
    ],
    symbol_column="instrument_key",
    required_row_count_min=1,
)

# LST (Lido, EtherFi, Ethena) oracle prices + rewards — per-token snapshots.
# Legacy rows use ``token`` as the per-row symbol column (not ``symbol``).
# ETHENA legacy oracle_prices lack even ``token``; it falls back to
# ``instrument_key``. Keep ``token`` as the canonical default; add a
# venue override for ETHENA.
DEFI_LST_ORACLE_PRICES = SchemaContract(
    category="defi",
    instrument_type="lst",
    data_type="oracle_prices",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="price", dtype="float64", nullable=False),
    ],
    symbol_column="token",
    required_row_count_min=1,
)

DEFI_LST_ORACLE_PRICES_ETHENA = SchemaContract(
    category="defi",
    instrument_type="lst",
    data_type="oracle_prices",
    columns=list(DEFI_LST_ORACLE_PRICES.columns),
    symbol_column="instrument_key",
    required_row_count_min=1,
)

DEFI_LST_REWARDS = SchemaContract(
    category="defi",
    instrument_type="lst",
    data_type="rewards",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        ColumnSpec(name="reward_rate", dtype="float64", nullable=True),
        ColumnSpec(name="apy", dtype="float64", nullable=True),
    ],
    symbol_column="token",
    required_row_count_min=1,
)

CONTRACT_REGISTRY[("defi", "a_token", "oracle_prices")] = DEFI_A_TOKEN_ORACLE_PRICES
CONTRACT_REGISTRY[("defi", "a_token", "rate_indices")] = DEFI_A_TOKEN_RATE_INDICES
CONTRACT_REGISTRY[("defi", "a_token", "risk_params")] = DEFI_A_TOKEN_RISK_PARAMS
CONTRACT_REGISTRY[("defi", "a_token", "utilization")] = DEFI_A_TOKEN_UTILIZATION
CONTRACT_REGISTRY[("defi", "lending", "rate_indices")] = DEFI_LENDING_RATE_INDICES
CONTRACT_REGISTRY[("defi", "lending", "utilization")] = DEFI_LENDING_UTILIZATION
CONTRACT_REGISTRY[("defi", "lst", "oracle_prices")] = DEFI_LST_ORACLE_PRICES
CONTRACT_REGISTRY[("defi", "lst", "rewards")] = DEFI_LST_REWARDS
VENUE_CONTRACT_OVERRIDES[("defi", "ETHENA", "lst", "oracle_prices")] = DEFI_LST_ORACLE_PRICES_ETHENA
