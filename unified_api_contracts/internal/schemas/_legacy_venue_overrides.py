"""Legacy venue-specific SchemaContract overrides (Ethena, Aave a_token extensions).

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
    INSTRUMENT_ID_COL,
    TS_EVENT_COL,
    VENUE_COL,
    VENUE_CONTRACT_OVERRIDES,
    ColumnSpec,
    SchemaContract,
)

# Uniswap V2/V3/V4, Curve, Balancer: REMOVED 2026-07-09
# (defi_dex_pool_symbol_shape_fix_2026_07_09) — these 6 legacy per-venue
# overrides pointed ``symbol_column`` at the bare on-chain address column
# (``pool_address``/``pair_address``/``pool_id``) because the raw row never
# carried a real canonical symbol. All 13 DEX-pool protocols' writers
# (market_tick_data_service.cli.handlers._dex_pool_symbol) now resolve a real
# ``symbol`` (``TOKEN0-TOKEN1[-FEE_TIER]`` when derivable, else the honest
# unchanged bare address) for every row, so these venues fall through to the
# now-consistent DEFI_DEX_POOL_DEX_POOL_STATE / DEFI_POOL_DEX_POOL_SWAPS
# defaults (``symbol_column="symbol"``) — same behavior, one fewer legacy
# branch. No other venue referenced these override objects (verified via
# repo-wide grep before removal).


# Aave V3 reserve-level datasets: oracle prices, rate indices (liquidity +
# borrow), utilization %, and risk parameters (LTV, liquidation threshold,
# reserve factor). All keyed per-asset symbol (USDC, WETH, …).
DEFI_A_TOKEN_ORACLE_PRICES = SchemaContract(
    asset_group="defi",
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
    asset_group="defi",
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
    asset_group="defi",
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
    asset_group="defi",
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
    asset_group="defi",
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
    asset_group="defi",
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
    asset_group="defi",
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
    asset_group="defi",
    instrument_type="lst",
    data_type="oracle_prices",
    columns=list(DEFI_LST_ORACLE_PRICES.columns),
    symbol_column="instrument_key",
    required_row_count_min=1,
)

DEFI_LST_REWARDS = SchemaContract(
    asset_group="defi",
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
